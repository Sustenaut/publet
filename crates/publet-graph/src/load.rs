//! Loading a graph from a directory of object files.
//!
//! The plumbing commands all need the same thing: read every object under a
//! directory, verify each against the identifier its filename claims, and
//! index it. Putting it here rather than in each binary keeps the binaries
//! thin and makes this testable.

use std::collections::BTreeSet;
use std::path::Path;

use publet_core::{Cid, HashAlg, Object};

use crate::{Dropped, Graph, GraphError};

/// Why a directory could not be loaded.
#[derive(Debug)]
#[non_exhaustive]
pub enum LoadError {
    /// The directory could not be read.
    Io(std::io::Error),
    /// An object failed to parse or verify.
    Object(String, String),
    /// An object was rejected by a graph rule.
    Graph(GraphError),
}

impl std::fmt::Display for LoadError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Io(e) => write!(f, "{e}"),
            Self::Object(name, why) => write!(f, "{name}: {why}"),
            Self::Graph(e) => write!(f, "{e}"),
        }
    }
}

impl std::error::Error for LoadError {}

/// Build a graph from objects already in hand.
///
/// Each pair is verified against its identifier before it is indexed, and
/// objects rejected on the first pass are retried once everything else is
/// in, so arrival order does not decide validity. An object inadmissible
/// given the others is reported on stderr and left out, and the rest loads
/// (Section 5.2): [`Graph::dropped`] lists them.
///
/// # Errors
///
/// Returns [`LoadError`] if an object fails to parse or verify, or if the
/// graph rejects it once the whole set is present.
pub fn from_objects<I>(objects: I) -> Result<Graph, LoadError>
where
    I: IntoIterator<Item = (Cid, Vec<u8>)>,
{
    let graph = from_objects_quietly(objects)?;
    report(&graph);
    Ok(graph)
}

/// As [`from_objects`], leaving it to the caller to [`report`] what was left
/// out: an authoring tool refuses what its own object would make inadmissible.
///
/// # Errors
///
/// As [`from_objects`].
pub fn from_objects_quietly<I>(objects: I) -> Result<Graph, LoadError>
where
    I: IntoIterator<Item = (Cid, Vec<u8>)>,
{
    let items: Vec<_> = objects
        .into_iter()
        .map(|(cid, bytes)| (cid.to_string(), cid, bytes))
        .collect();
    build(&items)
}

/// Say on stderr what a load left out, and why (Section 5.2).
pub fn report(graph: &Graph) {
    for dropped in graph.dropped() {
        eprintln!("warning: dropped {}: {}", dropped.cid, dropped.reason);
    }
}

/// Load every `*.cbor` file under `dir` into a graph.
///
/// Each file's bytes are verified against their own computed identifier, so
/// a corrupted file is refused rather than indexed. What [`from_objects`]
/// leaves out, this leaves out and reports too.
///
/// # Errors
///
/// Returns [`LoadError`] on the first file that cannot be read, parsed,
/// verified, or admitted.
pub fn from_dir(dir: &Path) -> Result<Graph, LoadError> {
    let mut entries: Vec<_> = std::fs::read_dir(dir)
        .map_err(LoadError::Io)?
        .filter_map(Result::ok)
        .map(|e| e.path())
        .filter(|p| p.extension().is_some_and(|x| x == "cbor"))
        .collect();
    // Deterministic order: a graph built twice from one directory must be
    // the same graph, and directory iteration order is not guaranteed.
    entries.sort();

    let mut items = Vec::with_capacity(entries.len());
    for path in entries {
        let bytes = std::fs::read(&path).map_err(LoadError::Io)?;
        let name = path.file_name().map_or_else(
            || path.display().to_string(),
            |n| n.to_string_lossy().into_owned(),
        );
        let cid = Cid::of(&bytes, HashAlg::Sha2_256);
        items.push((name, cid, bytes));
    }
    let graph = build(&items)?;
    report(&graph);
    Ok(graph)
}

/// Index named objects, leaving out what is inadmissible given the rest.
fn build(items: &[(String, Cid, Vec<u8>)]) -> Result<Graph, LoadError> {
    let whole = index(items, &BTreeSet::new())?;
    let inadmissible = whole.inadmissible();
    if inadmissible.is_empty() {
        // Rules whose subject is a target cannot be checked on insert,
        // because objects arrive in whatever order they arrive.
        whole.validate_structure().map_err(LoadError::Graph)?;
        return Ok(whole);
    }
    // Indexed afresh, so no edge or lineage still rests on what is left out.
    // Taking objects away only removes targets, so nothing new turns up.
    let left_out: BTreeSet<String> = inadmissible.iter().map(|(c, _)| c.to_string()).collect();
    let mut graph = index(items, &left_out)?;
    graph.validate_structure().map_err(LoadError::Graph)?;
    let mut dropped: Vec<Dropped> = inadmissible
        .into_iter()
        .map(|(cid, reason)| Dropped { cid, reason })
        .collect();
    dropped.sort_by_key(|d| d.cid.to_string());
    graph.set_dropped(dropped);
    Ok(graph)
}

/// Index every object but those in `skip`. Relations referring to objects
/// not yet loaded are retried once everything else is in, so order does not
/// decide validity.
fn index(items: &[(String, Cid, Vec<u8>)], skip: &BTreeSet<String>) -> Result<Graph, LoadError> {
    let verified = |name: &str, cid: &Cid, bytes: &[u8]| {
        Object::parse(bytes)
            .map_err(|e| LoadError::Object(name.to_owned(), e.to_string()))?
            .verify(cid)
            .map_err(|e| LoadError::Object(name.to_owned(), e.to_string()))
    };
    let mut graph = Graph::new();
    let mut deferred = Vec::new();
    for item @ (name, cid, bytes) in items {
        if skip.contains(&cid.to_string()) {
            continue;
        }
        if graph
            .insert_for_load(cid, verified(name, cid, bytes)?)
            .is_err()
        {
            deferred.push(item);
        }
    }
    for (name, cid, bytes) in deferred {
        graph
            .insert_for_load(cid, verified(name, cid, bytes)?)
            .map_err(LoadError::Graph)?;
    }
    Ok(graph)
}
