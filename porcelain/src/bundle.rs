//! `pub bundle`: the reading data a theme turns into pages.
//!
//! A host shows publets through a theme of its choosing; the theme decides
//! how a page looks, and this command decides nothing about that. It
//! writes, for a set of objects, one JSON bundle per page a theme may want
//! -- one per object and one per name a definition goes by -- holding
//! everything that page needs: the object decoded, what it rests on and
//! what cites it, its critiques and its lineage, and a short summary of
//! every other object it mentions. A theme reads one bundle per page and
//! never resolves anything itself, so every theme shows the same graph.
//!
//! Names follow Section 5.9.1: a node serving definitions under
//! human-readable names derives the mapping from the definitions it holds,
//! and a name two definitions share lists both. Each object's canonical
//! bytes are written at `pub/v1/object/<CID>`, the retrieval interface's
//! path (Section 14.4), so any page can be checked against its object.
//!
//! The bundles are a rendering input, not publets: they are regenerated
//! from the objects and never stored. Their shape is versioned by the
//! `bundle` field, which changes only when a theme would need to.

use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

use publet_core::{Cid, Object, cbor::Value};
use publet_graph::{ConceptForm, Data, Definition, Graph, Lineage, ProseClaim};
use serde_json::{Value as Json, json};

use crate::workspace::Workspace;

/// The version of the bundle shape. A theme checks it before reading.
const VERSION: u64 = 1;

/// Longest label given for a claim before it is shortened.
const LABEL_CHARS: usize = 110;

struct Options {
    dir: Option<PathBuf>,
    out: PathBuf,
    title: String,
    base: Option<String>,
}

/// `pub bundle --out=DIR [--dir=DIR] [--title=TEXT] [--base=URL]`.
///
/// Reads the workspace's objects, or a directory of object files given
/// `--dir`, and writes the bundles to `--out`, which must be absent or
/// empty so nothing from an earlier set survives into this one. `--base`
/// is the address the pages will be served from; it is used to give each
/// name its address, never to link between bundles.
///
/// # Errors
///
/// Returns a message if an argument is wrong, the objects cannot be read
/// or do not form a valid graph, or a file cannot be written.
pub(crate) fn run(args: &[String]) -> Result<(), String> {
    let options = parse(args)?;
    let graph = if let Some(dir) = &options.dir {
        publet_graph::load::from_dir(dir).map_err(|e| e.to_string())?
    } else {
        let here = std::env::current_dir().map_err(|e| e.to_string())?;
        let ws = Workspace::open(&here)?;
        crate::build::graph_of(&ws.store()?)?
    };
    prepare(&options.out)?;
    let bundles = Bundles::new(&graph, &options);
    bundles.write(&options.out)?;
    println!(
        "bundles for {} object(s) and {} name(s) in {}",
        bundles.cids.len(),
        bundles.terms.len(),
        options.out.display()
    );
    Ok(())
}

fn parse(args: &[String]) -> Result<Options, String> {
    let mut dir = None;
    let mut out = None;
    let mut title = "Publets".to_owned();
    let mut base = None;
    for arg in args {
        if let Some(v) = arg.strip_prefix("--dir=") {
            dir = Some(PathBuf::from(v));
        } else if let Some(v) = arg.strip_prefix("--out=") {
            out = Some(PathBuf::from(v));
        } else if let Some(v) = arg.strip_prefix("--title=") {
            v.clone_into(&mut title);
        } else if let Some(v) = arg.strip_prefix("--base=") {
            if !(v.starts_with("https://") || v.starts_with("http://")) {
                return Err(format!("--base must be an http(s) address: {v}"));
            }
            base = Some(v.trim_end_matches('/').to_owned());
        } else {
            return Err(format!(
                "unknown argument: {arg}\nusage: pub bundle --out=DIR [--dir=DIR] [--title=TEXT] [--base=URL]"
            ));
        }
    }
    let out = out.ok_or("--out=DIR is required: the directory the bundles are written to")?;
    Ok(Options {
        dir,
        out,
        title,
        base,
    })
}

/// Refuse to write into a directory holding anything: a bundle left from
/// an earlier set of objects would go on being shown as if it were current.
fn prepare(out: &Path) -> Result<(), String> {
    if out.exists() {
        let mut entries = std::fs::read_dir(out).map_err(|e| format!("{}: {e}", out.display()))?;
        if entries.next().is_some() {
            return Err(format!(
                "{} is not empty; bundles are written to an empty or new directory",
                out.display()
            ));
        }
    }
    std::fs::create_dir_all(out).map_err(|e| format!("{}: {e}", out.display()))
}

struct Bundles<'g> {
    graph: &'g Graph,
    title: String,
    base: Option<String>,
    /// Every object, in identifier order.
    cids: Vec<Cid>,
    /// Each name a definition goes by, and the definitions going by it.
    terms: BTreeMap<String, Vec<Cid>>,
    /// The name each definition goes by.
    term_of: BTreeMap<String, String>,
    /// What cites each object, and how.
    cited_by: BTreeMap<String, BTreeSet<(String, String)>>,
    /// Every `classifies` annotation: (annotation, member, subject).
    classifications: Vec<(String, String, String)>,
    /// Each concept by CID: its PDC code and form (Section 5.9.1).
    concepts: BTreeMap<String, (String, &'static str)>,
    /// The calculations solving each relation concept, by PDC code (Section 5.9.5).
    solvers: BTreeMap<String, Vec<String>>,
    /// Triage annotations by each object they name, as target or ref (Section 7.4).
    suggestions: BTreeMap<String, BTreeSet<String>>,
}

impl<'g> Bundles<'g> {
    fn new(graph: &'g Graph, options: &Options) -> Self {
        let mut cids: Vec<Cid> = graph.cids().iter().filter_map(|c| c.parse().ok()).collect();
        cids.sort_by_key(ToString::to_string);

        let mut terms: BTreeMap<String, Vec<Cid>> = BTreeMap::new();
        let mut term_of = BTreeMap::new();
        let mut segments: BTreeMap<String, String> = BTreeMap::new();
        for (term, cid) in graph.terms() {
            if !servable(&term) {
                eprintln!(
                    "warning: no bundle for the name {term:?} ({cid}): it cannot be a path segment"
                );
                continue;
            }
            let taken = segments
                .entry(segment(&term))
                .or_insert_with(|| term.clone());
            if *taken != term {
                eprintln!(
                    "warning: no bundle for the name {term:?} ({cid}): its path segment is {taken:?}'s"
                );
                continue;
            }
            term_of.insert(cid.to_string(), term.clone());
            terms.entry(term).or_default().push(cid);
        }

        let mut cited_by: BTreeMap<String, BTreeSet<(String, String)>> = BTreeMap::new();
        for cid in &cids {
            if let Some(object) = graph.object(cid) {
                for (how, target) in cites(graph, cid, object) {
                    cited_by
                        .entry(target)
                        .or_default()
                        .insert((cid.to_string(), how));
                }
            }
        }

        let Scan {
            classifications,
            concepts,
            solvers,
            suggestions,
        } = scan(graph, &cids);

        Self {
            graph,
            title: options.title.clone(),
            base: options.base.clone(),
            cids,
            terms,
            term_of,
            cited_by,
            classifications,
            concepts,
            solvers,
            suggestions,
        }
    }

    fn write(&self, out: &Path) -> Result<(), String> {
        put_json(&out.join("index.json"), &self.index())?;
        for cid in &self.cids {
            let Some(object) = self.graph.object(cid) else {
                continue;
            };
            let text = cid.to_string();
            put(&out.join("pub/v1/object").join(&text), object.bytes())?;
            put_json(
                &out.join("o").join(format!("{text}.json")),
                &self.object_bundle(cid, object),
            )?;
        }
        for (term, cids) in &self.terms {
            put_json(
                &out.join("def").join(format!("{}.json", segment(term))),
                &self.name_bundle(term, cids),
            )?;
        }
        Ok(())
    }

    // ------------------------------------------------------------ bundles

    fn index(&self) -> Json {
        let names: BTreeMap<&String, Vec<String>> = self
            .terms
            .iter()
            .map(|(t, cids)| (t, cids.iter().map(ToString::to_string).collect()))
            .collect();
        json!({
            "bundle": VERSION,
            "title": self.title,
            "base": self.base,
            "objects": self.cids.iter().map(|c| self.summary(c)).collect::<Vec<_>>(),
            "names": names,
            "name_paths": self.terms.keys().map(|t| (t.clone(), format!("def/{}.json", segment(t))))
                .collect::<BTreeMap<_, _>>(),
        })
    }

    fn object_bundle(&self, cid: &Cid, object: &Object) -> Json {
        let text = cid.to_string();
        let claim = self.graph.prose_claim(cid);
        let rests_on = claim.map(|c| rests_on(c, object)).unwrap_or_default();
        let used_by: Vec<(String, String)> = self
            .cited_by
            .get(&text)
            .map(|s| s.iter().cloned().collect())
            .unwrap_or_default();
        let closure: Vec<String> = claim
            .and_then(|_| self.graph.depends_closure(cid).ok())
            .map(|c| c.iter().map(ToString::to_string).collect())
            .unwrap_or_default();
        let critiques: Vec<String> = self
            .graph
            .critiques_of(cid)
            .iter()
            .map(|a| a.cid().to_string())
            .collect();
        let lineage = self.graph.lineage(cid, Lineage::Authoritative);
        let lineage = json!({
            "genesis": lineage.genesis.to_string(),
            "members": lineage.members.iter().map(ToString::to_string).collect::<Vec<_>>(),
            "heads": lineage.heads.iter().map(ToString::to_string).collect::<Vec<_>>(),
        });

        // Every identifier the page might show, summarized once, so a theme
        // can name what it links to without reading another bundle.
        let mut mentioned: BTreeSet<String> = BTreeSet::new();
        collect_cids(&Value::Map(object.body().clone()), &mut mentioned);
        mentioned.insert(object.author().to_string());
        mentioned.extend(rests_on.iter().map(|(c, _)| c.clone()));
        mentioned.extend(used_by.iter().map(|(c, _)| c.clone()));
        mentioned.extend(closure.iter().cloned());
        mentioned.extend(critiques.iter().cloned());
        let classified_under: Vec<Json> = self
            .classifications
            .iter()
            .filter(|(_, member, _)| *member == text)
            .map(|(by, _, subject)| {
                mentioned.insert(subject.clone());
                json!({ "concept": subject, "by": by })
            })
            .collect();
        let suggestions: Vec<String> = self
            .suggestions
            .get(&text)
            .map(|s| s.iter().cloned().collect())
            .unwrap_or_default();
        mentioned.extend(suggestions.iter().cloned());
        let concept = self.concept(cid, &mut mentioned);
        mentioned.remove(&text);

        json!({
            "bundle": VERSION,
            "cid": text,
            "summary": self.summary(cid),
            "object": crate::read::to_json(&Value::Map(object_map(object))),
            "bytes": { "path": format!("pub/v1/object/{text}"), "size": object.bytes().len() },
            "address": self.term_of.get(&text).map(|t| self.address(t)),
            "rests_on": edges(&rests_on),
            "closure": closure,
            "used_by": edges(&used_by),
            "critiques": critiques,
            "lineage": lineage,
            "parameters": claim.map(|c| self.parameters(c)).unwrap_or_default(),
            "classified_under": classified_under,
            "suggestions": suggestions,
            "concept": concept,
            "related": self.related(&mentioned),
        })
    }

    /// For a concept (Section 5.9.1): its code and form, the concepts it is
    /// placed under and over, its members, the calculations solving it, the
    /// other concepts claiming its code, and the anchors (expert groups)
    /// covering it or a broader concept. `null` for anything else.
    fn concept(&self, cid: &Cid, mentioned: &mut BTreeSet<String>) -> Json {
        let text = cid.to_string();
        let Some((pdc, form)) = self.concepts.get(&text) else {
            return Json::Null;
        };
        let under = |member: &str| -> Vec<String> {
            self.classifications
                .iter()
                .filter(|(_, m, s)| m == member && self.concepts.contains_key(s))
                .map(|(_, _, s)| s.clone())
                .collect()
        };
        let broader = under(&text);
        let (narrower, members): (Pairs, Pairs) = self
            .classifications
            .iter()
            .filter(|(_, _, s)| *s == text)
            .map(|(by, m, _)| (m.clone(), by.clone()))
            .partition(|(m, _)| self.concepts.contains_key(m));
        let solved_by = self.solvers.get(pdc).cloned().unwrap_or_default();
        let genesis = |c: &Cid| {
            self.graph
                .lineage(c, Lineage::Authoritative)
                .genesis
                .to_string()
        };
        let own = genesis(cid);
        let competing: Vec<String> = self
            .concepts
            .iter()
            .filter(|(c, (code, _))| code == pdc && **c != text)
            .filter(|(c, _)| c.parse::<Cid>().is_ok_and(|c| genesis(&c) != own))
            .map(|(c, _)| c.clone())
            .collect();
        // An anchor covers this concept when it anchors its lineage or that
        // of a concept it is placed under, at any depth (Section 9.3).
        let mut covered: BTreeMap<String, String> = BTreeMap::from([(own, text.clone())]);
        let mut frontier = broader.clone();
        while let Some(next) = frontier.pop() {
            if let Ok(c) = next.parse::<Cid>()
                && !covered.contains_key(&genesis(&c))
            {
                covered.insert(genesis(&c), next.clone());
                frontier.extend(under(&next));
            }
        }
        let anchors: Vec<Json> = self
            .cids
            .iter()
            .filter_map(|c| self.graph.anchor(c).map(|a| (c, a)))
            .filter_map(|(c, a)| {
                covered.get(&a.lineage().to_string()).map(|over| {
                    json!({
                        "cid": c.to_string(),
                        "over": over,
                        "stewards": a.stewards().iter().map(ToString::to_string).collect::<Vec<_>>(),
                        "threshold": a.threshold(),
                    })
                })
            })
            .collect();
        for list in [&broader, &solved_by, &competing] {
            mentioned.extend(list.iter().cloned());
        }
        for (m, by) in narrower.iter().chain(&members) {
            mentioned.insert(m.clone());
            mentioned.insert(by.clone());
        }
        for a in &anchors {
            if let Some(over) = a["over"].as_str() {
                mentioned.insert(over.to_owned());
            }
        }
        let pairs = |list: &[(String, String)]| -> Vec<Json> {
            list.iter()
                .map(|(m, by)| json!({ "cid": m, "by": by }))
                .collect()
        };
        json!({
            "pdc": pdc,
            "form": form,
            "broader": broader,
            "narrower": pairs(&narrower),
            "members": pairs(&members),
            "solved_by": solved_by,
            "competing": competing,
            "anchors": anchors,
        })
    }

    fn name_bundle(&self, term: &str, cids: &[Cid]) -> Json {
        let mentioned: BTreeSet<String> = cids.iter().map(ToString::to_string).collect();
        json!({
            "bundle": VERSION,
            "name": term,
            "segment": segment(term),
            "address": self.address(term),
            "definitions": cids.iter().map(ToString::to_string).collect::<Vec<_>>(),
            "related": self.related(&mentioned),
        })
    }

    // ------------------------------------------------------------ pieces

    /// What a theme needs to name and file an object in a list or a link.
    fn summary(&self, cid: &Cid) -> Json {
        let text = cid.to_string();
        let Some(object) = self.graph.object(cid) else {
            return json!({ "cid": text, "held": false });
        };
        let claim = self.graph.prose_claim(cid);
        let defines = claim.and_then(ProseClaim::defines);
        json!({
            "cid": text,
            "held": true,
            "type": object.kind(),
            "class": claim.map(|c| c.class().id()),
            "sort": defines.map(Definition::sort),
            "name": self.term_of.get(&text),
            "label": label(object, defines),
            "path": format!("o/{text}.json"),
        })
    }

    fn related(&self, cids: &BTreeSet<String>) -> Json {
        let map: serde_json::Map<String, Json> = cids
            .iter()
            .filter_map(|c| c.parse::<Cid>().ok())
            .map(|c| (c.to_string(), self.summary(&c)))
            .collect();
        Json::Object(map)
    }

    /// Each measure a column cites, with its parameters in the order it
    /// states them, so a quantity cell reads low, likely, high.
    fn parameters(&self, claim: &ProseClaim) -> Json {
        let mut out = serde_json::Map::new();
        if let Some(Data::Table { columns, .. }) = claim.data() {
            for measure in columns.iter().filter_map(|c| c.measure.as_ref()) {
                if let Some(Definition::Measure { parameters, .. }) = self
                    .graph
                    .prose_claim(measure)
                    .and_then(ProseClaim::defines)
                {
                    let names: Vec<&str> = parameters.iter().map(|p| p.name.as_str()).collect();
                    out.insert(measure.to_string(), json!(names));
                }
            }
        }
        Json::Object(out)
    }

    fn address(&self, term: &str) -> String {
        match &self.base {
            Some(base) => format!("{base}/def/{}", encode(&segment(term))),
            None => format!("def/{}", encode(&segment(term))),
        }
    }
}

// ---------------------------------------------------------------- helpers

/// An object as a map of its header and body, the shape `pub read --json`
/// prints.
fn object_map(object: &Object) -> BTreeMap<String, Value> {
    let mut map = BTreeMap::new();
    map.insert("type".to_owned(), Value::Text(object.kind().to_owned()));
    map.insert(
        "author".to_owned(),
        Value::Text(object.author().to_string()),
    );
    map.insert(
        "created".to_owned(),
        Value::Text(object.created().to_owned()),
    );
    if let Some(prev) = object.prev() {
        map.insert("prev".to_owned(), Value::Text(prev.to_string()));
    }
    map.insert("body".to_owned(), Value::Map(object.body().clone()));
    map
}

/// What a claim rests on, one level up, each with the strongest reason it
/// is there: the role it plays in the claim's evidence or columns, else
/// that the claim presupposes it.
fn rests_on(claim: &ProseClaim, object: &Object) -> Vec<(String, String)> {
    let mut how: BTreeMap<String, String> = BTreeMap::new();
    for d in claim.depends() {
        how.insert(d.to_string(), "presupposes".to_owned());
    }
    if let Some(Data::Table { columns, .. }) = claim.data() {
        for column in columns {
            for (field, cid) in column.cited() {
                let role = field.rsplit('.').next().unwrap_or(field);
                let role = if role == "unit_defs" { "unit" } else { role };
                how.insert(cid.to_string(), role.to_owned());
            }
        }
    }
    if let Some(Value::Array(evidence)) = object.body().get("evidence") {
        for e in evidence {
            if let (Some(role), Some(reference)) = (
                e.get("role").and_then(Value::as_text),
                e.get("ref").and_then(Value::as_text),
            ) && reference.parse::<Cid>().is_ok()
            {
                how.insert(reference.to_owned(), role.to_owned());
            }
        }
    }
    how.into_iter().collect()
}

/// Every object this one cites, and how, as seen from the cited object:
/// presupposed by, method of, source of, a relation's ends, an
/// annotation's or signature's target, a document's references.
fn cites(graph: &Graph, cid: &Cid, object: &Object) -> Vec<(String, String)> {
    let body = object.body();
    let mut out = Vec::new();
    if let Some(claim) = graph.prose_claim(cid) {
        for (target, how) in rests_on(claim, object) {
            let how = match how.as_str() {
                "presupposes" => "presupposed by".to_owned(),
                role => format!("{role} of"),
            };
            out.push((how, target));
        }
    }
    let mut add = |how: String, v: Option<&Value>| {
        if let Some(t) = v.and_then(Value::as_text)
            && t.parse::<Cid>().is_ok()
        {
            out.push((how, t.to_owned()));
        }
    };
    match object.kind() {
        "claim.relation" => {
            let kind = body
                .get("kind")
                .and_then(Value::as_text)
                .unwrap_or("relation");
            add(format!("{kind} relation"), body.get("from"));
            add(format!("{kind} relation"), body.get("to"));
        }
        "claim.annotation" => {
            let kind = body
                .get("kind")
                .and_then(Value::as_text)
                .unwrap_or("annotation");
            add(format!("{kind} annotation"), body.get("target"));
        }
        "sig" => add("signature".to_owned(), body.get("target")),
        "doc" => {
            if let Some(Value::Array(sections)) = body.get("sections") {
                for item in sections
                    .iter()
                    .filter_map(|s| match s.get("items") {
                        Some(Value::Array(items)) => Some(items),
                        _ => None,
                    })
                    .flatten()
                {
                    let role = item
                        .get("role")
                        .and_then(Value::as_text)
                        .unwrap_or("assert");
                    add(format!("cited in document ({role})"), item.get("ref"));
                }
            }
        }
        _ => {}
    }
    out.sort();
    out.dedup();
    out
}

/// Pairs of identifiers: (object, the annotation relating it).
type Pairs = Vec<(String, String)>;

/// What `pub bundle` gathers about concepts, before writing any bundle.
struct Scan {
    classifications: Vec<(String, String, String)>,
    concepts: BTreeMap<String, (String, &'static str)>,
    solvers: BTreeMap<String, Vec<String>>,
    suggestions: BTreeMap<String, BTreeSet<String>>,
}

/// Every `classifies` and `triage` annotation, every concept, and every
/// calculation solving a relation concept, among `cids`.
fn scan(graph: &Graph, cids: &[Cid]) -> Scan {
    let mut classifications = Vec::new();
    let mut concepts = BTreeMap::new();
    let mut solvers: BTreeMap<String, Vec<String>> = BTreeMap::new();
    let mut suggestions: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for cid in cids {
        let text = cid.to_string();
        if let Some(claim) = graph.prose_claim(cid) {
            if let Some(Definition::Concept { pdc, form, .. }) = claim.defines() {
                let form = match form {
                    ConceptForm::Quantity { .. } => "quantity",
                    ConceptForm::Relation(_) => "relation",
                    _ => "subject",
                };
                concepts.insert(text.clone(), (pdc.clone(), form));
            }
            if let Some(solves) = claim.computes().and_then(|c| c.solves.as_ref()) {
                solvers
                    .entry(solves.concept.clone())
                    .or_default()
                    .push(text.clone());
            }
        }
        let Some(object) = graph.object(cid) else {
            continue;
        };
        if object.kind() != "claim.annotation" {
            continue;
        }
        let body = object.body();
        let target = body
            .get("target")
            .and_then(Value::as_text)
            .map(ToOwned::to_owned);
        match (body.get("kind").and_then(Value::as_text), target) {
            (Some("classifies"), Some(target)) => {
                if let Some(subject) = body
                    .get("value")
                    .and_then(|v| v.get("subject"))
                    .and_then(Value::as_text)
                {
                    classifications.push((text, target, subject.to_owned()));
                }
            }
            (Some("triage"), Some(target)) => {
                let mut named = BTreeSet::from([target]);
                if let Some(Value::Array(refs)) = body.get("value").and_then(|v| v.get("refs")) {
                    named.extend(
                        refs.iter()
                            .filter_map(Value::as_text)
                            .map(ToOwned::to_owned),
                    );
                }
                for n in named {
                    suggestions.entry(n).or_default().insert(text.clone());
                }
            }
            _ => {}
        }
    }

    Scan {
        classifications,
        concepts,
        solvers,
        suggestions,
    }
}

fn edges(pairs: &[(String, String)]) -> Json {
    pairs
        .iter()
        .map(|(cid, how)| json!({ "cid": cid, "how": how }))
        .collect()
}

/// Every text value anywhere in `value` that parses as an identifier.
fn collect_cids(value: &Value, out: &mut BTreeSet<String>) {
    match value {
        Value::Text(t) if t.parse::<Cid>().is_ok() => {
            out.insert(t.clone());
        }
        Value::Array(items) => items.iter().for_each(|v| collect_cids(v, out)),
        Value::Map(map) => map.values().for_each(|v| collect_cids(v, out)),
        _ => {}
    }
}

/// What an object is called in a list: a definition by its symbol or name,
/// a document by its title, a claim by its content, anything else by its
/// type and kind.
fn label(object: &Object, defines: Option<&Definition>) -> String {
    if let Some(d) = defines {
        return d.term().to_owned();
    }
    let body = object.body();
    if let Some(t) = body.get("title").and_then(Value::as_text) {
        return t.to_owned();
    }
    if let Some(t) = body.get("content").and_then(Value::as_text) {
        return shorten(t);
    }
    match body.get("kind").and_then(Value::as_text) {
        Some(kind) => format!("{} {kind}", object.kind()),
        None => object.kind().to_owned(),
    }
}

/// Whether a name can be one path segment on any server.
fn servable(term: &str) -> bool {
    let s = segment(term);
    !s.is_empty() && s != "." && s != ".." && !s.chars().any(|c| c == '\\' || c.is_control())
}

/// A name's path segment: the name with each `/` as `_`. A slash cannot
/// sit inside one segment of a static site, and names have them: UDC's
/// ranges, such as the PDC code `631/635`. No UDC notation uses `_`; two
/// names meeting in one segment keep the first, with a warning.
fn segment(term: &str) -> String {
    term.replace('/', "_")
}

/// A name as a URL path segment: every byte outside RFC 3986's unreserved
/// characters percent-encoded.
fn encode(term: &str) -> String {
    use std::fmt::Write as _;
    let mut out = String::new();
    for byte in term.bytes() {
        if byte.is_ascii_alphanumeric() || matches!(byte, b'-' | b'.' | b'_' | b'~') {
            out.push(char::from(byte));
        } else {
            let _ = write!(out, "%{byte:02X}");
        }
    }
    out
}

fn shorten(text: &str) -> String {
    if text.chars().count() <= LABEL_CHARS {
        return text.to_owned();
    }
    let cut: String = text.chars().take(LABEL_CHARS).collect();
    let cut = cut.rsplit_once(' ').map_or(cut.as_str(), |(head, _)| head);
    format!("{cut}…")
}

fn put(path: &Path, bytes: &[u8]) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
    }
    std::fs::write(path, bytes).map_err(|e| format!("{}: {e}", path.display()))
}

fn put_json(path: &Path, value: &Json) -> Result<(), String> {
    let mut text = serde_json::to_string_pretty(value).map_err(|e| e.to_string())?;
    text.push('\n');
    put(path, text.as_bytes())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn names_are_encoded_as_one_path_segment() {
        assert_eq!(encode("{tray}"), "%7Btray%7D");
        assert_eq!(encode("[eur]"), "%5Beur%5D");
        assert_eq!(encode("energy per tray"), "energy%20per%20tray");
        assert_eq!(encode("ucum"), "ucum");
    }

    #[test]
    fn a_name_that_is_not_one_segment_gets_no_bundle() {
        assert!(servable("{tray}"));
        assert!(servable("631/635"));
        assert_eq!(segment("631/635"), "631_635");
        assert!(!servable("a\\b"));
        assert!(!servable(".."));
        assert!(!servable(""));
    }

    #[test]
    fn long_content_is_shortened_at_a_word() {
        let text = "word ".repeat(40);
        let label = shorten(&text);
        assert!(label.ends_with('…'));
        assert!(label.chars().count() <= LABEL_CHARS + 1);
    }

    #[test]
    fn identifiers_are_found_anywhere_in_a_value() {
        let cid = Cid::of(b"x", publet_core::HashAlg::Sha2_256).to_string();
        let mut nested = BTreeMap::new();
        nested.insert("ref".to_owned(), Value::Text(cid.clone()));
        let value = Value::Array(vec![Value::Map(nested), Value::Text("not one".to_owned())]);
        let mut out = BTreeSet::new();
        collect_cids(&value, &mut out);
        assert_eq!(out.into_iter().collect::<Vec<_>>(), vec![cid]);
    }
}
