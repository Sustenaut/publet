//! `pub site`: write a static website showing a set of objects.
//!
//! Every object gets a page at `o/<CID>/`, and every name a definition
//! goes by (Section 5.9.1, `term(D)` for Section 9.2) gets one at
//! `def/<name>/`, so a node can serve definitions under human-readable
//! names as that section describes. The mapping is derived from the
//! definitions themselves: a name two definitions share lists both,
//! because choosing between them belongs to a viewpoint, not to the site.
//! The canonical bytes of each object are written beside the pages at
//! `pub/v1/object/<CID>`, the retrieval interface's path (Section 14.4),
//! so a reader can check every page against the object it shows.
//!
//! The site is a rendering, not a publet: it is regenerated from the
//! objects and never stored. Pages carry no script, and every link is
//! relative, so the same output works from a web server or a directory.

use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;
use std::path::{Path, PathBuf};

use publet_core::{Cid, Object, cbor::Value};
use publet_graph::{Cell, Data, Definition, Describes, Graph, ParameterType, ProseClaim};

use crate::workspace::Workspace;

/// Longest label shown for a claim in a list before it is shortened.
const LABEL_CHARS: usize = 110;

/// The order claim classes are listed in on the index.
const CLASS_ORDER: [&str; 9] = [
    "normative",
    "empirical",
    "formal",
    "attributive",
    "archival",
    "procedural",
    "performative",
    "expressive",
    "definitional",
];

/// The order definition sorts are listed in on the index.
const SORT_ORDER: [&str; 5] = ["system", "dimension", "unit", "kind", "measure"];

struct Options {
    dir: Option<PathBuf>,
    out: PathBuf,
    title: String,
    base: Option<String>,
}

/// `pub site --out=DIR [--dir=DIR] [--title=TEXT] [--base=URL]`.
///
/// Reads the workspace's objects, or a directory of object files given
/// `--dir`, and writes the site to `--out`, which must be absent or empty
/// so no page from an earlier set survives into this one. `--base` is the
/// address the site will be served from; it is used only to show each
/// definition's address under its name, never in links.
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
    let site = Site::new(&graph, &options);
    let written = site.write(&options.out)?;
    println!(
        "{} page(s) for {} object(s) and {} name(s) in {}",
        written,
        site.cids.len(),
        site.terms.len(),
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
                "unknown argument: {arg}\nusage: pub site --out=DIR [--dir=DIR] [--title=TEXT] [--base=URL]"
            ));
        }
    }
    let out = out.ok_or("--out=DIR is required: the directory the site is written to")?;
    Ok(Options {
        dir,
        out,
        title,
        base,
    })
}

/// Refuse to write into a directory holding anything: a page left from an
/// earlier set of objects would go on being served as if it were current.
fn prepare(out: &Path) -> Result<(), String> {
    if out.exists() {
        let mut entries = std::fs::read_dir(out).map_err(|e| format!("{}: {e}", out.display()))?;
        if entries.next().is_some() {
            return Err(format!(
                "{} is not empty; the site is written to an empty or new directory",
                out.display()
            ));
        }
    }
    std::fs::create_dir_all(out).map_err(|e| format!("{}: {e}", out.display()))
}

// ------------------------------------------------------------------ model

struct Site<'g> {
    graph: &'g Graph,
    title: String,
    base: Option<String>,
    /// Every object, in identifier order.
    cids: Vec<Cid>,
    /// Each name a definition goes by, and the definitions going by it.
    terms: BTreeMap<String, Vec<Cid>>,
    /// The name each definition goes by.
    term_of: BTreeMap<String, String>,
    /// Objects that cite each object: depends, evidence, relations,
    /// annotations, signatures, document references.
    cited_by: BTreeMap<String, BTreeSet<(String, String)>>,
}

impl<'g> Site<'g> {
    fn new(graph: &'g Graph, options: &Options) -> Self {
        let mut cids: Vec<Cid> = graph.cids().iter().filter_map(|c| c.parse().ok()).collect();
        cids.sort_by_key(ToString::to_string);

        let mut terms: BTreeMap<String, Vec<Cid>> = BTreeMap::new();
        let mut term_of = BTreeMap::new();
        for (term, cid) in graph.terms() {
            if !servable(&term) {
                eprintln!(
                    "warning: no page for the name {term:?} ({cid}): it cannot be a path segment"
                );
                continue;
            }
            term_of.insert(cid.to_string(), term.clone());
            terms.entry(term).or_default().push(cid);
        }

        let mut cited_by: BTreeMap<String, BTreeSet<(String, String)>> = BTreeMap::new();
        for cid in &cids {
            let Some(object) = graph.object(cid) else {
                continue;
            };
            for (how, target) in citations(object) {
                cited_by
                    .entry(target)
                    .or_default()
                    .insert((cid.to_string(), how));
            }
        }

        Self {
            graph,
            title: options.title.clone(),
            base: options.base.clone(),
            cids,
            terms,
            term_of,
            cited_by,
        }
    }

    fn write(&self, out: &Path) -> Result<usize, String> {
        let mut pages = 0;
        put(&out.join("style.css"), STYLE.as_bytes())?;
        put(&out.join("index.html"), self.index().as_bytes())?;
        pages += 1;
        put(&out.join("index.json"), self.index_json()?.as_bytes())?;
        for cid in &self.cids {
            let Some(object) = self.graph.object(cid) else {
                continue;
            };
            let text = cid.to_string();
            put(&out.join("pub/v1/object").join(&text), object.bytes())?;
            put(
                &out.join("o").join(&text).join("index.html"),
                self.object_page(cid, object).as_bytes(),
            )?;
            pages += 1;
        }
        for (term, cids) in &self.terms {
            put(
                &out.join("def").join(term).join("index.html"),
                self.term_page(term, cids).as_bytes(),
            )?;
            pages += 1;
        }
        Ok(pages)
    }

    // -------------------------------------------------------------- pages

    fn index(&self) -> String {
        let mut body = String::new();
        let _ = writeln!(body, "<h1>{}</h1>", esc(&self.title));
        let _ = writeln!(
            body,
            "<p class=\"lede\">{} objects. Each page shows one object as it was \
             stored; its identifier is the hash of its bytes, which \
             are linked from the page.</p>",
            self.cids.len()
        );

        let documents: Vec<&Cid> = self.of_kind("doc");
        if !documents.is_empty() {
            body.push_str("<h2>Documents</h2>\n<ul class=\"list\">\n");
            for cid in documents {
                let _ = writeln!(body, "<li>{}</li>", self.link(cid, 0));
            }
            body.push_str("</ul>\n");
        }

        let mut by_class: BTreeMap<&str, Vec<&Cid>> = BTreeMap::new();
        let mut by_sort: BTreeMap<&str, Vec<&Cid>> = BTreeMap::new();
        for cid in &self.cids {
            let Some(claim) = self.graph.prose_claim(cid) else {
                continue;
            };
            match claim.defines() {
                Some(d) => by_sort.entry(d.sort()).or_default().push(cid),
                None => by_class.entry(claim.class().id()).or_default().push(cid),
            }
        }

        if !by_class.is_empty() {
            body.push_str("<h2>Claims</h2>\n");
            for class in CLASS_ORDER {
                let Some(cids) = by_class.get(class) else {
                    continue;
                };
                let _ = writeln!(
                    body,
                    "<h3>{}</h3>\n<ul class=\"list\">",
                    esc(&heading(class))
                );
                for cid in cids {
                    let _ = writeln!(body, "<li>{}</li>", self.link(cid, 0));
                }
                body.push_str("</ul>\n");
            }
        }

        if !by_sort.is_empty() {
            body.push_str("<h2>Definitions</h2>\n");
            for sort in SORT_ORDER {
                let Some(cids) = by_sort.get(sort) else {
                    continue;
                };
                let _ = writeln!(body, "<h3>{}</h3>\n<ul class=\"list\">", esc(&plural(sort)));
                for cid in cids {
                    let _ = writeln!(body, "<li>{}</li>", self.link(cid, 0));
                }
                body.push_str("</ul>\n");
            }
        }

        if !self.terms.is_empty() {
            body.push_str(
                "<h2>Names</h2>\n<p>Each name a definition goes by has an \
                 address of its own. A name two definitions share lists both.</p>\n\
                 <ul class=\"names\">\n",
            );
            for (term, cids) in &self.terms {
                let shared = if cids.len() > 1 {
                    format!(" <span class=\"tag\">{} definitions</span>", cids.len())
                } else {
                    String::new()
                };
                let _ = writeln!(
                    body,
                    "<li><a href=\"def/{}/\"><code>{}</code></a>{shared}</li>",
                    encode(term),
                    esc(term)
                );
            }
            body.push_str("</ul>\n");
        }

        let others: Vec<&Cid> = self
            .cids
            .iter()
            .filter(|c| {
                self.graph.prose_claim(c).is_none()
                    && self.graph.object(c).is_some_and(|o| o.kind() != "doc")
            })
            .collect();
        if !others.is_empty() {
            body.push_str("<h2>Other objects</h2>\n<ul class=\"list\">\n");
            for cid in others {
                let _ = writeln!(body, "<li>{}</li>", self.link(cid, 0));
            }
            body.push_str("</ul>\n");
        }
        self.page(&self.title, 0, &body)
    }

    fn object_page(&self, cid: &Cid, object: &Object) -> String {
        let mut body = String::new();
        let _ = writeln!(
            body,
            "<p class=\"crumbs\"><a href=\"../../\">{}</a></p>",
            esc(&self.title)
        );
        body.push_str(&self.object_section(cid, object, 2, "h1"));
        self.page(&self.label(cid), 2, &body)
    }

    fn term_page(&self, term: &str, cids: &[Cid]) -> String {
        let mut body = String::new();
        let _ = writeln!(
            body,
            "<p class=\"crumbs\"><a href=\"../../\">{}</a></p>",
            esc(&self.title)
        );
        let _ = writeln!(body, "<h1>{}</h1>", esc(term));
        if let Some(base) = &self.base {
            let _ = writeln!(
                body,
                "<p class=\"address\">{}/def/{}</p>",
                esc(base),
                esc(&encode(term))
            );
        }
        if cids.len() > 1 {
            let _ = writeln!(
                body,
                "<p class=\"note\">{} definitions go by this name. They are different \
                 definitions, each with its own identifier; which one a reader means is \
                 theirs to say (Section 9.1).</p>",
                cids.len()
            );
        }
        for cid in cids {
            if let Some(object) = self.graph.object(cid) {
                body.push_str("<section class=\"definition\">\n");
                body.push_str(&self.object_section(cid, object, 2, "h2"));
                body.push_str("</section>\n");
            }
        }
        self.page(term, 2, &body)
    }

    /// One object, fully: what it says, under what scope, what it
    /// defines or measures, how it is repeated, and what it rests on.
    fn object_section(&self, cid: &Cid, object: &Object, depth: usize, h: &str) -> String {
        let mut s = String::new();
        let body = object.body();
        let claim = self.graph.prose_claim(cid);

        let _ = writeln!(s, "<{h}>{}</{h}>", esc(&self.label(cid)));
        let mut tags = vec![object.kind().to_owned()];
        if let Some(claim) = claim {
            tags.push(claim.class().id().to_owned());
            if let Some(d) = claim.defines() {
                tags.push(d.sort().to_owned());
            }
        }
        s.push_str("<p class=\"tags\">");
        for tag in tags {
            let _ = write!(s, "<span class=\"tag\">{}</span> ", esc(&tag));
        }
        s.push_str("</p>\n");

        // A claim's heading is its content when that is short enough to
        // be one; otherwise the content follows in full.
        if let Some(content) = body.get("content").and_then(Value::as_text)
            && self.label(cid) != content
        {
            let _ = writeln!(s, "<p class=\"content\">{}</p>", esc(content));
        }
        match object.kind() {
            "doc" => s.push_str(&self.document(body, depth)),
            "claim.relation" | "claim.annotation" | "sig" => s.push_str(&self.fields(body, depth)),
            _ => {}
        }
        if body.contains_key("content") {
            s.push_str(&scope(body.get("scope")));
        }
        if let Some(claim) = claim {
            if let Some(d) = claim.defines() {
                s.push_str(&self.defines(d, body.get("defines"), depth));
            }
            if let Some(data) = claim.data() {
                s.push_str(&self.data(data, depth));
            }
            if let Some(c) = claim.computes() {
                s.push_str(&self.computes(c, depth));
            }
        }
        s.push_str(&self.evidence(body.get("evidence"), depth));
        s.push_str(&self.depends(claim, depth));
        s.push_str(&self.cited(cid, depth));

        // The header last: who and when matter less to a reader than what,
        // and the identifier is what they need to check it.
        s.push_str(&self.meta(cid, object, depth));
        s
    }

    fn meta(&self, cid: &Cid, object: &Object, depth: usize) -> String {
        let up = "../".repeat(depth);
        let mut s = String::from("<h3>Object</h3>\n<dl class=\"meta\">\n");
        let _ = writeln!(
            s,
            "<dt>identifier</dt><dd><code>{}</code></dd>",
            esc(&cid.to_string())
        );
        if let Some(term) = self.term_of.get(&cid.to_string()) {
            let address = match &self.base {
                Some(base) => format!("{base}/def/{}", encode(term)),
                None => format!("def/{}/", encode(term)),
            };
            let _ = writeln!(
                s,
                "<dt>name</dt><dd><a href=\"{up}def/{}/\"><code>{}</code></a> &middot; {}</dd>",
                encode(term),
                esc(term),
                esc(&address)
            );
        }
        let _ = writeln!(s, "<dt>type</dt><dd>{}</dd>", esc(object.kind()));
        let _ = writeln!(
            s,
            "<dt>author</dt><dd>{}</dd>",
            self.reference(&object.author().to_string(), depth)
        );
        let _ = writeln!(s, "<dt>created</dt><dd>{}</dd>", esc(object.created()));
        // Signatures are listed, not checked: checking one needs the
        // signing key and a viewpoint that trusts it, which `pub why` has.
        let signatures = self.cited_by.get(&cid.to_string()).map_or(0, |c| {
            c.iter().filter(|(_, how)| how == "signature").count()
        });
        let signed = match signatures {
            0 => "none held: this object is unsigned".to_owned(),
            n => format!("{n} held, listed under Cited by; check them with <code>pub why</code>"),
        };
        let _ = writeln!(s, "<dt>signatures</dt><dd>{signed}</dd>");
        if let Some(prev) = object.prev() {
            let _ = writeln!(s, "<dt>previous</dt><dd>{}</dd>", self.link(prev, depth));
        }
        let _ = writeln!(
            s,
            "<dt>bytes</dt><dd><a href=\"{up}pub/v1/object/{}\">canonical CBOR</a>, {} bytes</dd>",
            esc(&cid.to_string()),
            object.bytes().len()
        );
        s.push_str("</dl>\n");
        s
    }

    fn computes(&self, c: &publet_graph::Computes, depth: usize) -> String {
        let mut s = String::new();
        s.push_str("<h3>Computes</h3>\n<dl>\n");
        for (name, kind) in &c.inputs {
            let _ = writeln!(
                s,
                "<dt>input <code>{}</code></dt><dd>{}</dd>",
                esc(name),
                self.link(kind, depth)
            );
        }
        for (name, kind) in &c.outputs {
            let _ = writeln!(
                s,
                "<dt>output <code>{}</code></dt><dd>{}</dd>",
                esc(name),
                self.link(kind, depth)
            );
        }
        if let Some(r) = &c.rounding {
            let _ = writeln!(s, "<dt>rounding</dt><dd>{}</dd>", esc(r));
        }
        if let Some(seed) = c.seed {
            let _ = writeln!(s, "<dt>seed</dt><dd>{seed}</dd>");
        }
        s.push_str("</dl>\n");
        s
    }

    fn defines(&self, d: &Definition, raw: Option<&Value>, depth: usize) -> String {
        let mut s = String::from("<h3>Defines</h3>\n<dl>\n");
        let _ = writeln!(s, "<dt>sort</dt><dd>{}</dd>", esc(d.sort()));
        match d {
            Definition::System { name, version } => {
                let _ = writeln!(s, "<dt>system</dt><dd>{} {}</dd>", esc(name), esc(version));
            }
            Definition::Dimension { symbol } => {
                let _ = writeln!(s, "<dt>symbol</dt><dd><code>{}</code></dd>", esc(symbol));
            }
            Definition::Unit {
                symbol,
                value,
                unit,
            } => {
                let _ = writeln!(
                    s,
                    "<dt>unit</dt><dd><code>{}</code> = {} <code>{}</code></dd>",
                    esc(symbol),
                    esc(value),
                    esc(unit)
                );
            }
            Definition::Kind {
                name,
                dimension,
                units,
            } => {
                let _ = writeln!(s, "<dt>name</dt><dd>{}</dd>", esc(name));
                let dim: Vec<String> = dimension
                    .iter()
                    .map(|(base, exp)| {
                        if *exp == 1 {
                            esc(base)
                        } else {
                            format!("{}<sup>{exp}</sup>", esc(base))
                        }
                    })
                    .collect();
                let _ = writeln!(s, "<dt>dimension</dt><dd>{}</dd>", dim.join(" &middot; "));
                if !units.is_empty() {
                    let list: Vec<String> = units
                        .iter()
                        .map(|u| format!("<code>{}</code>", esc(u)))
                        .collect();
                    let _ = writeln!(s, "<dt>units</dt><dd>{}</dd>", list.join(", "));
                }
            }
            Definition::Measure {
                name,
                describes,
                parameters,
            } => {
                let _ = writeln!(s, "<dt>name</dt><dd>{}</dd>", esc(name));
                let what = match describes {
                    Describes::Exact => "an exact value",
                    Describes::Variation => "variation in what was measured",
                    Describes::Uncertainty => "uncertainty in what is known",
                    _ => "something this site does not know",
                };
                let _ = writeln!(s, "<dt>describes</dt><dd>{what}</dd>");
                s.push_str("<dt>parameters</dt><dd><table class=\"params\">\n");
                for p in parameters {
                    let kind = match p.kind {
                        ParameterType::Quantity => "quantity",
                        ParameterType::Fraction => "fraction",
                        ParameterType::Count => "count",
                        ParameterType::Blob => "blob",
                        _ => "other",
                    };
                    let _ = writeln!(
                        s,
                        "<tr><td><code>{}</code></td><td>{kind}</td><td>{}</td></tr>",
                        esc(&p.name),
                        esc(&p.meaning)
                    );
                }
                s.push_str("</table></dd>\n");
            }
            _ => {}
        }
        if let Some(matches) = raw.and_then(|r| r.get("matches")) {
            let _ = writeln!(s, "<dt>matches</dt><dd>{}</dd>", self.value(matches, depth));
        }
        s.push_str("</dl>\n");
        s
    }

    fn data(&self, data: &Data, depth: usize) -> String {
        let mut s = String::from("<h3>Values</h3>\n");
        match data {
            Data::Table { columns, rows } => {
                s.push_str("<div class=\"scroll\"><table class=\"data\">\n<thead><tr>");
                for column in columns {
                    let _ = write!(s, "<th>{}", esc(&column.name));
                    if let Some(unit) = &column.unit {
                        let _ = write!(s, "<br><code class=\"unit\">{}</code>", esc(unit));
                    }
                    if let Some(kind) = &column.kind {
                        let _ = write!(
                            s,
                            "<br><span class=\"small\">kind: {}</span>",
                            self.link_short(kind, depth)
                        );
                    }
                    if let Some(measure) = &column.measure {
                        let _ = write!(
                            s,
                            "<br><span class=\"small\">as: {}</span>",
                            self.link_short(measure, depth)
                        );
                    }
                    for (symbol, def) in &column.unit_defs {
                        let _ = write!(
                            s,
                            "<br><span class=\"small\"><code>{}</code>: {}</span>",
                            esc(symbol),
                            self.link_short(def, depth)
                        );
                    }
                    s.push_str("</th>");
                }
                s.push_str("</tr></thead>\n<tbody>\n");
                for row in rows {
                    s.push_str("<tr>");
                    for (cell, column) in row.iter().zip(columns) {
                        let order = column
                            .measure
                            .as_ref()
                            .map(|m| self.parameter_order(m))
                            .unwrap_or_default();
                        let _ = write!(s, "<td>{}</td>", cell_html(cell, &order));
                    }
                    s.push_str("</tr>\n");
                }
                s.push_str("</tbody></table></div>\n");
                if rows.iter().flatten().any(|c| matches!(c, Cell::Null)) {
                    s.push_str(
                        "<p class=\"small\">A cell marked <span class=\"unknown\">not yet \
                         known</span> holds null: the value has not been gathered.</p>\n",
                    );
                }
            }
            Data::File { media, blob, size } => {
                let _ = writeln!(
                    s,
                    "<p>A file: {}, {size} bytes, blob <code>{}</code>.</p>",
                    esc(media),
                    esc(&blob.to_string())
                );
            }
            _ => {}
        }
        s
    }

    /// A measure's parameter names, in the order it states them, so a
    /// quantity cell reads low, likely, high rather than alphabetically.
    fn parameter_order(&self, measure: &Cid) -> Vec<String> {
        match self
            .graph
            .prose_claim(measure)
            .and_then(ProseClaim::defines)
        {
            Some(Definition::Measure { parameters, .. }) => {
                parameters.iter().map(|p| p.name.clone()).collect()
            }
            _ => Vec::new(),
        }
    }

    /// Method, derivation and sources (Section 5.5). External sources are
    /// outside the protocol's integrity guarantees and are marked so.
    fn evidence(&self, evidence: Option<&Value>, depth: usize) -> String {
        let Some(Value::Array(entries)) = evidence else {
            return String::new();
        };
        if entries.is_empty() {
            return String::new();
        }
        let mut s = String::from("<h3>Evidence</h3>\n<ul class=\"evidence\">\n");
        for entry in entries {
            let role = entry
                .get("role")
                .and_then(Value::as_text)
                .unwrap_or("evidence");
            let kind = entry.get("kind").and_then(Value::as_text).unwrap_or("");
            let reference = entry.get("ref").and_then(Value::as_text).unwrap_or("");
            let target = if kind == "external" {
                let shown = if reference.starts_with("https://") || reference.starts_with("http://")
                {
                    format!("<a href=\"{0}\" rel=\"nofollow\">{0}</a>", esc(reference))
                } else {
                    esc(reference)
                };
                format!("{shown} <span class=\"tag warn\">unverified</span>")
            } else {
                self.reference(reference, depth)
            };
            let _ = write!(s, "<li><span class=\"role\">{}</span> {target}", esc(role));
            for field in ["revision", "locator", "query", "note"] {
                if let Some(v) = entry.get(field).and_then(Value::as_text) {
                    let _ = write!(s, "<br><span class=\"small\">{field}: {}</span>", esc(v));
                }
            }
            s.push_str("</li>\n");
        }
        s.push_str("</ul>\n");
        s
    }

    fn depends(&self, claim: Option<&ProseClaim>, depth: usize) -> String {
        let Some(claim) = claim else {
            return String::new();
        };
        if claim.depends().is_empty() {
            return String::new();
        }
        let mut s = String::from("<h3>Presupposes</h3>\n<ul class=\"list\">\n");
        for d in claim.depends() {
            let _ = writeln!(s, "<li>{}</li>", self.link(d, depth));
        }
        s.push_str("</ul>\n");
        s
    }

    fn cited(&self, cid: &Cid, depth: usize) -> String {
        let Some(citing) = self.cited_by.get(&cid.to_string()) else {
            return String::new();
        };
        let mut s = String::from("<h3>Cited by</h3>\n<ul class=\"list\">\n");
        for (from, how) in citing {
            let _ = writeln!(
                s,
                "<li><span class=\"role\">{}</span> {}</li>",
                esc(how),
                self.reference(from, depth)
            );
        }
        s.push_str("</ul>\n");
        s
    }

    fn document(&self, body: &BTreeMap<String, Value>, depth: usize) -> String {
        let mut s = String::new();
        if let Some(title) = body.get("title").and_then(Value::as_text) {
            let _ = writeln!(s, "<p class=\"content\">{}</p>", esc(title));
        }
        for field in ["abstract", "license"] {
            if let Some(v) = body.get(field).and_then(Value::as_text) {
                let _ = writeln!(
                    s,
                    "<p><span class=\"role\">{field}</span> {}</p>",
                    self.reference(v, depth)
                );
            }
        }
        let Some(Value::Array(sections)) = body.get("sections") else {
            return s;
        };
        for section in sections {
            if let Some(heading) = section.get("heading").and_then(Value::as_text) {
                let _ = writeln!(s, "<h3>{}</h3>", esc(heading));
            }
            let Some(Value::Array(items)) = section.get("items") else {
                continue;
            };
            s.push_str("<ul class=\"list\">\n");
            for item in items {
                let reference = item.get("ref").and_then(Value::as_text).unwrap_or("");
                s.push_str("<li>");
                if let Some(role) = item.get("role").and_then(Value::as_text) {
                    let _ = write!(s, "<span class=\"role\">{}</span> ", esc(role));
                }
                s.push_str(&self.reference(reference, depth));
                // Section 8: a gloss is connective tissue, not an assertion,
                // so it is set apart from the claim it introduces.
                if let Some(gloss) = item.get("gloss").and_then(Value::as_text) {
                    let _ = write!(s, "<br><span class=\"gloss\">{}</span>", esc(gloss));
                }
                s.push_str("</li>\n");
            }
            s.push_str("</ul>\n");
        }
        s
    }

    /// A relation, annotation or signature: each field, with identifiers
    /// linked where the object is held.
    fn fields(&self, body: &BTreeMap<String, Value>, depth: usize) -> String {
        let mut s = String::from("<dl>\n");
        for (key, value) in body {
            if key == "content" || key == "value" && matches!(value, Value::Bytes(_)) {
                continue;
            }
            let _ = writeln!(
                s,
                "<dt>{}</dt><dd>{}</dd>",
                esc(key),
                self.value(value, depth)
            );
        }
        s.push_str("</dl>\n");
        s
    }

    fn value(&self, value: &Value, depth: usize) -> String {
        match value {
            Value::Text(t) => self.reference(t, depth),
            Value::Uint(n) => n.to_string(),
            Value::Nint(n) => format!("-{}", u128::from(*n) + 1),
            Value::Bool(b) => b.to_string(),
            Value::Null => "null".to_owned(),
            Value::Bytes(b) => format!("{} bytes", b.len()),
            Value::Array(items) => items
                .iter()
                .map(|v| self.value(v, depth))
                .collect::<Vec<_>>()
                .join(", "),
            Value::Map(map) => {
                let mut s = String::from("<dl class=\"inner\">");
                for (k, v) in map {
                    let _ = write!(s, "<dt>{}</dt><dd>{}</dd>", esc(k), self.value(v, depth));
                }
                s.push_str("</dl>");
                s
            }
            _ => String::new(),
        }
    }

    // -------------------------------------------------------------- links

    /// Text that may be an identifier: a link if this site holds the
    /// object, the identifier as code if it does not, the text otherwise.
    fn reference(&self, text: &str, depth: usize) -> String {
        match text.parse::<Cid>() {
            Ok(cid) if self.graph.object(&cid).is_some() => self.link(&cid, depth),
            Ok(_) => format!(
                "<code>{}</code> <span class=\"small\">(not held here)</span>",
                esc(text)
            ),
            Err(_) => esc(text),
        }
    }

    fn link(&self, cid: &Cid, depth: usize) -> String {
        if self.graph.object(cid).is_none() {
            return self.reference(&cid.to_string(), depth);
        }
        format!(
            "<a href=\"{}o/{}/\">{}</a> <code class=\"cid\">{}</code>",
            "../".repeat(depth),
            esc(&cid.to_string()),
            esc(&self.label(cid)),
            esc(&short(cid))
        )
    }

    /// A link by name alone, for table headers where space is short.
    fn link_short(&self, cid: &Cid, depth: usize) -> String {
        if self.graph.object(cid).is_none() {
            return self.reference(&cid.to_string(), depth);
        }
        let name = self
            .graph
            .prose_claim(cid)
            .and_then(ProseClaim::defines)
            .map_or_else(|| self.label(cid), |d| d.term().to_owned());
        format!(
            "<a href=\"{}o/{}/\">{}</a>",
            "../".repeat(depth),
            esc(&cid.to_string()),
            esc(&name)
        )
    }

    /// What an object is called in a list: a definition by its name, a
    /// document by its title, a claim by its content, anything else by its
    /// type.
    fn label(&self, cid: &Cid) -> String {
        let Some(object) = self.graph.object(cid) else {
            return cid.to_string();
        };
        if let Some(d) = self.graph.prose_claim(cid).and_then(ProseClaim::defines) {
            return d.term().to_owned();
        }
        let body = object.body();
        if let Some(t) = body.get("title").and_then(Value::as_text) {
            return t.to_owned();
        }
        if let Some(t) = body.get("content").and_then(Value::as_text) {
            return shorten(t);
        }
        match (body.get("kind").and_then(Value::as_text), object.kind()) {
            (Some(kind), "claim.relation" | "claim.annotation") => {
                format!("{} {kind}", object.kind())
            }
            _ => object.kind().to_owned(),
        }
    }

    fn of_kind(&self, kind: &str) -> Vec<&Cid> {
        self.cids
            .iter()
            .filter(|c| self.graph.object(c).is_some_and(|o| o.kind() == kind))
            .collect()
    }

    fn index_json(&self) -> Result<String, String> {
        let objects: Vec<serde_json::Value> = self
            .cids
            .iter()
            .filter_map(|cid| {
                let object = self.graph.object(cid)?;
                let claim = self.graph.prose_claim(cid);
                Some(serde_json::json!({
                    "cid": cid.to_string(),
                    "type": object.kind(),
                    "class": claim.map(|c| c.class().id()),
                    "name": self.term_of.get(&cid.to_string()),
                    "label": self.label(cid),
                }))
            })
            .collect();
        let names: BTreeMap<&String, Vec<String>> = self
            .terms
            .iter()
            .map(|(t, cids)| (t, cids.iter().map(ToString::to_string).collect()))
            .collect();
        serde_json::to_string_pretty(&serde_json::json!({
            "title": self.title,
            "base": self.base,
            "objects": objects,
            "names": names,
        }))
        .map_err(|e| e.to_string())
    }

    fn page(&self, title: &str, depth: usize, body: &str) -> String {
        let up = "../".repeat(depth);
        let full = if title == self.title {
            esc(title)
        } else {
            format!("{} &middot; {}", esc(title), esc(&self.title))
        };
        format!(
            "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n\
             <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n\
             <title>{full}</title>\n<link rel=\"stylesheet\" href=\"{up}style.css\">\n\
             </head>\n<body>\n<main>\n{body}</main>\n<footer>Generated by <code>pub site</code> \
             from the objects it shows. Nothing on this page is stored; the objects are.</footer>\n\
             </body>\n</html>\n"
        )
    }
}

// ---------------------------------------------------------------- helpers

/// Every object this one cites, and how: what it presupposes, its
/// evidence, a relation's ends, an annotation's or signature's target, a
/// document's references.
fn citations(object: &Object) -> Vec<(String, String)> {
    let body = object.body();
    let mut out = Vec::new();
    let mut add = |how: &str, v: Option<&Value>| {
        if let Some(t) = v.and_then(Value::as_text)
            && t.parse::<Cid>().is_ok()
        {
            out.push((how.to_owned(), t.to_owned()));
        }
    };
    if let Some(Value::Array(depends)) = body.get("depends") {
        for d in depends {
            add("presupposed by", Some(d));
        }
    }
    if let Some(Value::Array(evidence)) = body.get("evidence") {
        for e in evidence {
            let role = e.get("role").and_then(Value::as_text).unwrap_or("evidence");
            add(&format!("{role} of"), e.get("ref"));
        }
    }
    match object.kind() {
        "claim.relation" => {
            let kind = body
                .get("kind")
                .and_then(Value::as_text)
                .unwrap_or("relation");
            add(&format!("{kind} relation"), body.get("from"));
            add(&format!("{kind} relation"), body.get("to"));
        }
        "claim.annotation" => {
            let kind = body
                .get("kind")
                .and_then(Value::as_text)
                .unwrap_or("annotation");
            add(&format!("{kind} annotation"), body.get("target"));
        }
        "sig" => add("signature", body.get("target")),
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
                    add("cited in document", item.get("ref"));
                }
            }
        }
        _ => {}
    }
    // A claim that both presupposes another and reads a value from it is
    // listed under each relation; nothing is listed twice under one.
    out.sort();
    out.dedup();
    out
}

fn scope(scope: Option<&Value>) -> String {
    let Some(scope) = scope else {
        return "<p class=\"note\">No scope declared: the author asserted this without \
                stating the conditions it holds under.</p>\n"
            .to_owned();
    };
    let mut s = String::from("<h3>Asserted under</h3>\n<dl>\n");
    if let Some(d) = scope.get("domain").and_then(Value::as_text) {
        let _ = writeln!(s, "<dt>domain</dt><dd>{}</dd>", esc(d));
    }
    if let Some(p) = scope.get("precision").and_then(Value::as_text) {
        let _ = writeln!(s, "<dt>precision</dt><dd>{}</dd>", esc(p));
    }
    if let Some(t) = scope.get("temporal") {
        let from = t.get("from").and_then(Value::as_text).unwrap_or("");
        let to = t.get("to").and_then(Value::as_text).unwrap_or("");
        let _ = writeln!(s, "<dt>period</dt><dd>{} to {}</dd>", esc(from), esc(to));
    }
    if let Some(Value::Array(conditions)) = scope.get("conditions") {
        for c in conditions {
            if let Some(c) = c.as_text() {
                let _ = writeln!(s, "<dt>condition</dt><dd>{}</dd>", esc(c));
            }
        }
    }
    s.push_str("</dl>\n");
    s
}

/// A cell as HTML. Null is "not yet known", never a blank a reader could
/// take for zero; a quantity lists its parameters in its measure's order.
fn cell_html(cell: &Cell, order: &[String]) -> String {
    match cell {
        Cell::Text(t) => esc(t),
        Cell::Uint(n) => n.to_string(),
        Cell::Nint(n) => format!("-{}", u128::from(*n) + 1),
        Cell::Null => "<span class=\"unknown\">not yet known</span>".to_owned(),
        Cell::Quantity(map) => {
            let mut keys: Vec<&String> = order.iter().filter(|k| map.contains_key(*k)).collect();
            keys.extend(map.keys().filter(|k| !order.contains(k)));
            let parts: Vec<String> = keys
                .into_iter()
                .filter_map(|k| {
                    map.get(k).map(|v| {
                        format!(
                            "<span class=\"param\">{}</span> {}",
                            esc(k),
                            cell_html(v, &[])
                        )
                    })
                })
                .collect();
            parts.join("<br>")
        }
        _ => String::new(),
    }
}

/// Whether a name can be one path segment on any server.
fn servable(term: &str) -> bool {
    !term.is_empty()
        && term != "."
        && term != ".."
        && !term
            .chars()
            .any(|c| c == '/' || c == '\\' || c.is_control())
}

/// A name as a URL path segment: every byte outside RFC 3986's unreserved
/// characters percent-encoded.
fn encode(term: &str) -> String {
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

fn esc(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    for c in text.chars() {
        match c {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            '"' => out.push_str("&quot;"),
            '\'' => out.push_str("&#39;"),
            c => out.push(c),
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

/// The first characters of an identifier's hash, enough to tell objects
/// apart by eye on one page; the full identifier is on the object's page.
fn short(cid: &Cid) -> String {
    let text = cid.to_string();
    let hash = text.rsplit(':').next().unwrap_or(&text);
    hash.chars().take(10).collect()
}

fn heading(class: &str) -> String {
    let mut chars = class.chars();
    chars.next().map_or_else(String::new, |first| {
        first.to_uppercase().chain(chars).collect()
    })
}

fn plural(sort: &str) -> String {
    let word = match sort {
        "system" => "Systems of units",
        "dimension" => "Base dimensions",
        "unit" => "Units",
        "kind" => "Quantity kinds",
        "measure" => "Statistical measures",
        other => other,
    };
    word.to_owned()
}

fn put(path: &Path, bytes: &[u8]) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
    }
    std::fs::write(path, bytes).map_err(|e| format!("{}: {e}", path.display()))
}

const STYLE: &str = r#":root {
  --bg: #fbfaf7; --fg: #1d1d1b; --muted: #66645e; --line: #dedbd2;
  --accent: #2f6b4f; --tag: #ecebe5; --warn: #8a5a00; --code: #f1efe9;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #161715; --fg: #e8e6e0; --muted: #a29f97; --line: #34352f;
    --accent: #7cc49e; --tag: #2a2b27; --warn: #e2b04a; --code: #22231f;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg);
  font: 16px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 52rem; margin: 0 auto; padding: 1.5rem 1rem 3rem; }
footer { max-width: 52rem; margin: 0 auto; padding: 1rem; color: var(--muted);
  font-size: 0.85rem; border-top: 1px solid var(--line); }
h1 { font-size: 1.6rem; line-height: 1.25; margin: 0.5rem 0; }
h2 { font-size: 1.25rem; margin-top: 2rem; border-bottom: 1px solid var(--line); }
h3 { font-size: 1rem; margin-top: 1.5rem; color: var(--muted); text-transform: uppercase;
  letter-spacing: 0.04em; }
a { color: var(--accent); }
code { background: var(--code); padding: 0 0.2em; border-radius: 3px; font-size: 0.9em;
  overflow-wrap: anywhere; }
.lede, .note, .crumbs, .small, .address { color: var(--muted); }
.small { font-size: 0.85rem; }
.content { font-size: 1.15rem; }
.tag { display: inline-block; background: var(--tag); border-radius: 3px; padding: 0 0.4em;
  font-size: 0.8rem; color: var(--muted); }
.tag.warn { color: var(--warn); }
.role { font-size: 0.8rem; color: var(--muted); }
.cid { font-size: 0.75rem; color: var(--muted); background: none; }
.unknown { color: var(--warn); font-style: italic; }
.param { color: var(--muted); font-size: 0.85em; }
.gloss { color: var(--muted); font-style: italic; }
ul.list, ul.evidence { padding-left: 1.1rem; }
ul.list li, ul.evidence li { margin: 0.3rem 0; }
ul.names { columns: 2 14rem; padding-left: 1.1rem; }
dl { display: grid; grid-template-columns: max-content 1fr; gap: 0.25rem 1rem; }
dt { color: var(--muted); }
dd { margin: 0; min-width: 0; overflow-wrap: anywhere; }
dl.inner { margin: 0; }
.scroll { overflow-x: auto; }
table { border-collapse: collapse; }
table.data th, table.data td { border: 1px solid var(--line); padding: 0.35rem 0.6rem;
  vertical-align: top; text-align: left; }
table.data th { font-weight: 600; }
table.params td { padding: 0.1rem 0.6rem 0.1rem 0; vertical-align: top; }
section.definition { border-top: 1px solid var(--line); margin-top: 1.5rem; }
@media (max-width: 30rem) { dl { grid-template-columns: 1fr; } dt { margin-top: 0.4rem; } }
"#;

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
    fn a_name_that_is_not_one_segment_gets_no_page() {
        assert!(servable("{tray}"));
        assert!(!servable("kW.h/{tray}"));
        assert!(!servable(".."));
        assert!(!servable(""));
    }

    #[test]
    fn markup_is_escaped() {
        assert_eq!(
            esc("<a href=\"x\">&'"),
            "&lt;a href=&quot;x&quot;&gt;&amp;&#39;"
        );
    }

    #[test]
    fn a_null_cell_reads_as_not_yet_known() {
        assert!(cell_html(&Cell::Null, &[]).contains("not yet known"));
    }

    #[test]
    fn a_quantity_follows_its_measures_order() {
        let mut map = BTreeMap::new();
        map.insert("high".to_owned(), Cell::Text("1.4".to_owned()));
        map.insert("likely".to_owned(), Cell::Text("1.1".to_owned()));
        map.insert("low".to_owned(), Cell::Text("0.8".to_owned()));
        let order = ["low".to_owned(), "likely".to_owned(), "high".to_owned()];
        let html = cell_html(&Cell::Quantity(map), &order);
        let low = html.find("low").unwrap_or(usize::MAX);
        let likely = html.find("likely").unwrap_or(usize::MAX);
        let high = html.find("high").unwrap_or(usize::MAX);
        assert!(low < likely && likely < high, "{html}");
    }

    #[test]
    fn long_content_is_shortened_at_a_word() {
        let text = "word ".repeat(40);
        let label = shorten(&text);
        assert!(label.ends_with('…'));
        assert!(label.chars().count() <= LABEL_CHARS + 1);
    }
}
