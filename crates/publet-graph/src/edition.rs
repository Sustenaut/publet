//! What a family or an edition must agree with beyond itself (Section
//! 5.9.1).
//!
//! The rules that can be checked on one object are its reading, in
//! `quantity`. These need other objects: the families an edition lists, the
//! edition it supersedes, the family a `classifies` annotation names. Objects
//! arrive in any order and a reader may hold only part of a release, so they
//! are found once a graph is loaded, and a family not held is left unchecked
//! rather than treated as a disagreement. What they find is refused when
//! authoring, and reported and left out when loading (Section 5.2).

use std::collections::{BTreeMap, BTreeSet};

use publet_core::Cid;

use crate::GraphError;
use crate::graph::Graph;
use crate::quantity::{Definition, EDITION_SECTIONS, Edition, Family, Tally};
use crate::view::{ProseClaim, RelationKind};

impl Graph {
    /// What Section 5.9.1 makes inadmissible, each with why: an edition its
    /// families or predecessors disagree with, a `classifies` annotation
    /// placing something under no class of a family, and any argument about
    /// or judgement of a definition at a PDC code.
    pub(crate) fn inadmissible_at_definitions(&self) -> Vec<(Cid, GraphError)> {
        let mut out = self.debated_definitions();
        for claim in self.prose_claims() {
            if let Some(Definition::Edition(edition)) = claim.defines()
                && let Err(reason) = self.check_edition(claim, edition)
            {
                out.push((
                    claim.cid().clone(),
                    GraphError::EditionDisagrees {
                        edition: claim.cid().to_string(),
                        reason,
                    },
                ));
            }
        }
        for annotation in self.annotations_of_kind("classifies") {
            let Some(subject) = self
                .object(annotation.cid())
                .and_then(|o| o.body().get("value")?.get("subject")?.as_text())
                .and_then(|s| s.parse::<Cid>().ok())
            else {
                continue;
            };
            let Some(family) = self.family(&subject) else {
                continue;
            };
            let aspect = annotation.aspect();
            if !family.classes().any(|c| Some(c.pdc.as_str()) == aspect) {
                out.push((
                    annotation.cid().clone(),
                    GraphError::ClassifiedUnderNoClass {
                        family: subject.to_string(),
                        found: aspect.map(str::to_owned),
                    },
                ));
            }
        }
        out
    }

    /// A definition at a PDC code is a stipulation: it changes by a new
    /// version, never by debate (R6). A target not held is not known to be
    /// one, and is checked by whoever holds it.
    fn debated_definitions(&self) -> Vec<(Cid, GraphError)> {
        let stipulated = |target: &Cid| {
            matches!(
                self.prose_claim(target).and_then(ProseClaim::defines),
                Some(Definition::Concept { .. } | Definition::Family(_) | Definition::Edition(_))
            )
        };
        let refused = |kind: &str, target: &Cid| GraphError::StipulationDebated {
            kind: kind.to_owned(),
            target: target.to_string(),
        };
        let mut out = Vec::new();
        for kind in [RelationKind::Disputes, RelationKind::Supports] {
            for relation in self.relations_of_kind(kind) {
                if stipulated(relation.to()) {
                    out.push((relation.cid().clone(), refused(kind.id(), relation.to())));
                }
            }
        }
        for kind in ["assessment", "verdict", "critique"] {
            for annotation in self.annotations_of_kind(kind) {
                if stipulated(annotation.target()) {
                    out.push((annotation.cid().clone(), refused(kind, annotation.target())));
                }
            }
        }
        out
    }

    /// The family `cid` defines, if it is held and defines one.
    fn family(&self, cid: &Cid) -> Option<&Family> {
        match self.prose_claim(cid)?.defines()? {
            Definition::Family(family) => Some(family),
            _ => None,
        }
    }

    fn check_edition(&self, claim: &ProseClaim, edition: &Edition) -> Result<(), String> {
        // Every parent code the edition lists a family under, across sections.
        let under: BTreeSet<&str> = edition
            .sections
            .iter()
            .flat_map(BTreeMap::keys)
            .map(String::as_str)
            .collect();
        let listed = self.listed_families(edition)?;
        let defined = check_classes(&listed.held, &under)?;
        if listed.whole {
            check_counts(edition, &listed, &under, &defined)?;
        }
        for previous in self.superseded_by_own_author(claim.cid()) {
            let Some(Definition::Edition(old)) =
                self.prose_claim(&previous).and_then(ProseClaim::defines)
            else {
                continue;
            };
            grows_from("group", &old.groups, &edition.groups)?;
            grows_from("grouping", &old.groupings, &edition.groupings)?;
        }
        Ok(())
    }

    /// The families an edition lists that are held, each held to where it is
    /// listed and to the groupings the edition defines, and what they add up
    /// to.
    fn listed_families(&self, edition: &'_ Edition) -> Result<Listed<'_>, String> {
        let mut out = Listed {
            whole: true,
            held: Vec::new(),
            sections: [Tally::default(); 3],
            total: Tally::default(),
        };
        let top = std::iter::once((None, None, &edition.top));
        let rest = edition
            .sections
            .iter()
            .enumerate()
            .flat_map(|(i, section)| {
                section
                    .iter()
                    .map(move |(parent, cid)| (Some(i), Some(parent.as_str()), cid))
            });
        for (section, parent, cid) in top.chain(rest) {
            let Some(found) = self.prose_claim(cid) else {
                out.whole = false;
                continue;
            };
            let Some(Definition::Family(family)) = found.defines() else {
                return Err(format!(
                    "{cid} is listed as a family and does not define one"
                ));
            };
            if family.parent.as_deref() != parent {
                return Err(match parent {
                    Some(code) => format!(
                        "the family listed under {code} states the parent {:?}",
                        family.parent
                    ),
                    None => format!("the top family states the parent {:?}", family.parent),
                });
            }
            if !edition.groupings.contains_key(&family.grouping) {
                return Err(format!(
                    "the family {cid} names the grouping {}, which the edition does not define",
                    family.grouping
                ));
            }
            let add = |t: &mut Tally| {
                t.families += 1;
                t.classes += family.members.len() as u64;
                t.auxiliaries += family.auxiliaries.len() as u64;
            };
            if let Some(tally) = section.and_then(|i| out.sections.get_mut(i)) {
                add(tally);
            }
            add(&mut out.total);
            out.held.push(family);
        }
        Ok(out)
    }
}

/// What an edition's held families add up to.
struct Listed<'g> {
    /// Whether every family it lists is held.
    whole: bool,
    held: Vec<&'g Family>,
    sections: [Tally; 3],
    total: Tally,
}

/// Each code once, and each `children` flag true exactly where the edition
/// lists a family under that class. Returns the codes defined.
fn check_classes<'g>(
    held: &[&'g Family],
    under: &BTreeSet<&str>,
) -> Result<BTreeSet<&'g str>, String> {
    let mut defined = BTreeSet::new();
    for class in held.iter().flat_map(|f| f.classes()) {
        if !defined.insert(class.pdc.as_str()) {
            return Err(format!("its families define {} twice", class.pdc));
        }
        let heads = under.contains(class.pdc.as_str());
        if class.children != heads {
            return Err(if heads {
                format!("{} heads a family and has no `children` flag", class.pdc)
            } else {
                format!("{} has a `children` flag and no family under it", class.pdc)
            });
        }
    }
    Ok(defined)
}

/// With every family in hand: each parent is defined, and the counts are
/// what the families make.
fn check_counts(
    edition: &Edition,
    listed: &Listed<'_>,
    under: &BTreeSet<&str>,
    defined: &BTreeSet<&str>,
) -> Result<(), String> {
    if let Some(parent) = under.difference(defined).next() {
        return Err(format!(
            "it lists a family under {parent}, which no listed family defines"
        ));
    }
    for ((name, stated), found) in EDITION_SECTIONS
        .iter()
        .zip(&edition.counts)
        .zip(&listed.sections)
    {
        if stated != found {
            return Err(format!(
                "its counts give `{name}` as {stated:?}, and its families make {found:?}"
            ));
        }
    }
    if edition.total != listed.total {
        return Err(format!(
            "its counts give `total` as {:?}, and its families make {:?}",
            edition.total, listed.total
        ));
    }
    Ok(())
}

/// Section 5.9.1's grow-only rule: every number keeps every member, so a
/// family's `grouping` means what it meant when the family was signed.
fn grows_from<T: Ord + std::fmt::Debug>(
    what: &str,
    old: &BTreeMap<u64, BTreeSet<T>>,
    new: &BTreeMap<u64, BTreeSet<T>>,
) -> Result<(), String> {
    for (number, before) in old {
        let Some(after) = new.get(number) else {
            return Err(format!(
                "{what} {number} of the edition it supersedes is gone, and a number is never dropped"
            ));
        };
        if !before.is_empty() && before.is_disjoint(after) {
            return Err(format!(
                "{what} {number} is reused with a different meaning: it held {before:?}, and now {after:?}"
            ));
        }
        if let Some(lost) = before.difference(after).next() {
            return Err(format!(
                "{what} {number} lost {lost:?}; groups and groupings only grow"
            ));
        }
    }
    Ok(())
}
