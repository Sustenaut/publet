//! Errors raised while typing objects and building the graph.

use publet_core::Cid;
use thiserror::Error;

use crate::view::RelationKind;

/// A reason an object could not be typed or admitted.
#[derive(Debug, Error, PartialEq, Eq, Clone)]
#[non_exhaustive]
pub enum GraphError {
    /// The object was of a different type than the view expected.
    #[error("expected a `{expected}` object, found `{found}`")]
    WrongKind {
        /// The type the view reads.
        expected: &'static str,
        /// The type the object declares.
        found: String,
    },

    /// A required body field was absent.
    #[error("missing required field `{field}`")]
    MissingField {
        /// The absent field.
        field: &'static str,
    },

    /// A body field had the wrong type or shape.
    #[error("field `{field}` must be {expected}")]
    BadField {
        /// The offending field.
        field: &'static str,
        /// What the specification requires.
        expected: &'static str,
    },

    /// The claim class is not one the specification defines.
    #[error("unknown claim class `{found}`")]
    UnknownClass {
        /// The unrecognized identifier.
        found: String,
    },

    /// The principal is not one the specification defines.
    #[error("unknown principal `{found}`; a key declares human, organization, or automated")]
    UnknownPrincipal {
        /// The unrecognized identifier.
        found: String,
    },

    /// A lineage-bound citation omitted the head its author read.
    #[error(
        "a lineage-bound citation of {reference} must record `at`, the head \
         its author actually read; without it a reader sees only what is \
         current and loses what was cited"
    )]
    LineageBindWithoutHead {
        /// The lineage genesis cited.
        reference: String,
    },

    /// An anchor recommends an object outside the lineage it names.
    #[error(
        "anchor points at {current}, which is not in the lineage {lineage} \
         it names; an anchor is a shortcut to the computation, not a \
         different claim wearing its shape"
    )]
    AnchorOutsideLineage {
        /// What the anchor recommends.
        current: String,
        /// The lineage it claims to anchor.
        lineage: String,
    },

    /// A `source` evidence entry named a claim the citing claim does not
    /// list in `depends` (Section 5.5).
    #[error(
        "source {claim} is a claim, so it must also be listed in `depends`; \
         a value read from another claim presupposes it, and `depends` is \
         what makes the chain back to the inputs walkable"
    )]
    SourceNotInDepends {
        /// The claim named as a source.
        claim: String,
    },

    /// An empirical claim named no method.
    #[error(
        "an `empirical` claim must carry an evidence entry with role `method`, \
         or, if its values are computed, one with role `derivation`; a \
         measurement without a reproducible method is a report of an experience"
    )]
    EmpiricalWithoutMethod,

    /// An empirical claim named both a method and a derivation, or more
    /// than one of either (Section 5.5).
    #[error(
        "an `empirical` claim names exactly one `method` or exactly one \
         `derivation`, never both or several; one identifier must say how it \
         is repeated"
    )]
    AmbiguousMethod,

    /// A body field reserved to one class appeared on another (Section 5.9).
    #[error("`{field}` belongs on a `{class}` claim only")]
    FieldOnWrongClass {
        /// The field: `defines` or `computes`.
        field: &'static str,
        /// The one class that may carry it.
        class: &'static str,
    },

    /// A column or calculation cited a claim the citing claim does not
    /// list in `depends` (Section 5.9).
    #[error(
        "{field} cites {claim}, so it must also be listed in `depends`; a unit, \
         kind or measure is presupposed by every value that uses it"
    )]
    QuantityNotInDepends {
        /// Where it was cited: `data.columns.kind`, `computes`, and so on.
        field: &'static str,
        /// The claim cited.
        claim: String,
    },

    /// The relation kind is not one the specification defines.
    #[error("unknown relation kind `{found}`")]
    UnknownKind {
        /// The unrecognized identifier.
        found: String,
    },

    /// An edge of an acyclic kind would close a cycle.
    #[error("`{kind}` edge from {from} to {to} closes a cycle")]
    CycleClosing {
        /// The kind that must stay acyclic.
        kind: &'static str,
        /// The edge's subject.
        from: String,
        /// The edge's object.
        to: String,
    },

    /// A verdict annotation targeted a class that is not truth-apt.
    #[error("a verdict may not target a `{class}` claim; it is not truth-apt")]
    VerdictOnNonTruthApt {
        /// The offending class.
        class: &'static str,
    },

    /// A verdict on a provenance-only class named another aspect.
    #[error(
        "a verdict on a `{class}` claim must have aspect `provenance`, found {found:?}; \
         a claim about the content is made by publishing an `empirical` claim"
    )]
    VerdictAspectNotProvenance {
        /// The class whose verdicts are confined to provenance.
        class: &'static str,
        /// The aspect the annotation actually named.
        found: Option<String>,
    },

    /// A `disputes` relation did not name grounds.
    #[error("a `disputes` relation must name a claim stating grounds")]
    DisputeWithoutGrounds,

    /// An object referenced an identifier the graph does not hold.
    #[error("{referrer} references {missing}, which is not in the graph")]
    DanglingReference {
        /// The object holding the reference.
        referrer: String,
        /// The identifier it names.
        missing: String,
    },
}

impl GraphError {
    /// Build a cycle error for an edge.
    pub(crate) fn cycle(kind: RelationKind, from: &Cid, to: &Cid) -> Self {
        Self::CycleClosing {
            kind: kind.id(),
            from: from.to_string(),
            to: to.to_string(),
        }
    }
}
