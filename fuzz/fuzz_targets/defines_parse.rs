//! Reading a definition's `defines`, families and editions above all, on
//! arbitrary values.
//!
//! Families and editions arrive inside claims from anyone. Reading one must
//! never panic, and a family it accepts must keep the rules checked on it
//! alone: each code once, and the parent never one of its classes.
#![no_main]

use std::collections::{BTreeMap, BTreeSet};

use arbitrary::Arbitrary;
use libfuzzer_sys::fuzz_target;
use publet_core::cbor::{Value, decode};
use publet_graph::Definition;

/// A family-shaped or edition-shaped value, so the fuzzer reaches their
/// rules rather than spending its time on maps with no `sort`.
#[derive(Arbitrary, Debug)]
struct Input {
    edition: bool,
    parent: Option<String>,
    grouping: u64,
    members: Vec<(String, String, bool)>,
    auxiliaries: Vec<(String, String)>,
    /// Canonical CBOR for one more field, under a name chosen from the
    /// fields these sorts have.
    extra: (u8, Vec<u8>),
    /// Read on its own as a whole `defines`.
    raw: Vec<u8>,
}

const FIELDS: [&str; 8] = [
    "parent",
    "grouping",
    "members",
    "auxiliaries",
    "top",
    "sections",
    "groups",
    "counts",
];

fn class(pdc: &str, name: &str, children: bool) -> Value {
    let mut fields = BTreeMap::from([
        ("pdc".to_owned(), Value::Text(pdc.into())),
        ("name".to_owned(), Value::Text(name.into())),
    ]);
    if children {
        fields.insert("children".to_owned(), Value::Bool(true));
    }
    Value::Map(fields)
}

fn check(defines: &Value) {
    if let Ok(Definition::Family(family)) = Definition::from_value(defines) {
        let mut seen = BTreeSet::new();
        for c in family.classes() {
            assert!(
                seen.insert(c.pdc.clone()),
                "a family accepted {} twice",
                c.pdc
            );
        }
        if let Some(parent) = &family.parent {
            assert!(
                !seen.contains(parent),
                "a family accepted its parent {parent} as a class"
            );
        }
    }
}

fuzz_target!(|input: Input| {
    if let Ok(raw) = decode(&input.raw) {
        check(&raw);
    }
    let sort = if input.edition { "edition" } else { "family" };
    let mut fields = BTreeMap::from([
        ("sort".to_owned(), Value::Text(sort.into())),
        ("grouping".to_owned(), Value::Uint(input.grouping)),
        (
            "members".to_owned(),
            Value::Array(
                input
                    .members
                    .iter()
                    .map(|(p, n, c)| class(p, n, *c))
                    .collect(),
            ),
        ),
        (
            "auxiliaries".to_owned(),
            Value::Array(
                input
                    .auxiliaries
                    .iter()
                    .map(|(p, n)| class(p, n, false))
                    .collect(),
            ),
        ),
    ]);
    if let Some(parent) = &input.parent {
        fields.insert("parent".to_owned(), Value::Text(parent.clone()));
    }
    if let Ok(extra) = decode(&input.extra.1) {
        let name = FIELDS[usize::from(input.extra.0) % FIELDS.len()];
        fields.insert(name.to_owned(), extra);
    }
    check(&Value::Map(fields));
});
