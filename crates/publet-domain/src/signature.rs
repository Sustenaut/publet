//! Whether a domain's generation records are signed by its publisher
//! (Section 14.1.1).
//!
//! A record's `author` names a key but proves nothing (Section 4.3). What
//! lets a reader hold the publisher to a record is a detached `sig` object
//! (Section 4.4), by that key, over the record's bytes, for the purpose
//! `authored`. A reader checks each record it takes in, in index order, before
//! it trusts the membership the records state.
//!
//! Records written before signing began are unsigned, so a domain's history
//! can start unsigned. [`unsigned_accepted`] is the one place that says what
//! such a record is worth.

#[cfg(test)]
use publet_core::HashAlg;
use publet_core::{Cid, Object};
use publet_graph::Graph;
use thiserror::Error;

/// The purpose a generation record is signed for.
pub const PURPOSE: &str = "authored";

/// What a record's signatures show.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[non_exhaustive]
pub enum RecordSignature {
    /// A signature by the record's author verifies.
    Signed,
    /// No signature targets the record.
    Unsigned,
    /// Signatures target the record, and none by its author verifies: a
    /// wrong key, or bytes that were changed.
    Forged,
}

/// Why a domain's records are refused.
#[derive(Debug, Error, PartialEq, Eq, Clone)]
#[non_exhaustive]
pub enum SignatureError {
    /// A signature targets the record and does not verify by its author.
    #[error(
        "generation {index} ({cid}) carries a signature that does not verify by its author: \
         a wrong key, or changed bytes"
    )]
    Forged {
        /// The record's index.
        index: u64,
        /// The record.
        cid: String,
    },
    /// The record is unsigned, after an earlier record of the domain was signed.
    #[error(
        "generation {index} ({cid}) is unsigned, after an earlier generation of this domain \
         was signed"
    )]
    UnsignedAfterSigned {
        /// The record's index.
        index: u64,
        /// The record.
        cid: String,
    },
    /// The record is signed by a key that does not continue the one that
    /// signed the domain's earlier records.
    #[error(
        "generation {index} ({cid}) is signed by {found}, which does not continue {expected}, \
         the key that signed the earlier generations"
    )]
    PublisherChanged {
        /// The record's index.
        index: u64,
        /// The record.
        cid: String,
        /// The key that signed before.
        expected: String,
        /// The key that signed this one.
        found: String,
    },
}

/// Whether an unsigned record is accepted, given whether an earlier record of
/// its domain was signed. Records from before signing began stay readable; a
/// signature that stops is refused, since dropping it is what a forger would
/// do. To refuse every unsigned record instead, return `false` here.
#[must_use]
pub fn unsigned_accepted(signed_before: bool) -> bool {
    !signed_before
}

/// What the signatures in `graph` show about `record`.
#[must_use]
pub fn record_signature(graph: &Graph, record: &Cid) -> RecordSignature {
    let Some(object) = graph.object(record) else {
        return RecordSignature::Unsigned;
    };
    if graph.is_signed_by(object.author(), record, PURPOSE) {
        RecordSignature::Signed
    } else if graph.signatures_of(record).is_empty() {
        RecordSignature::Unsigned
    } else {
        RecordSignature::Forged
    }
}

/// Check the signatures of a domain's records, given in index order from its
/// genesis or from where the reader is. Returns a warning for each unsigned
/// record accepted.
///
/// # Errors
///
/// Returns [`SignatureError`] for the first record whose signature is forged,
/// that is unsigned where [`unsigned_accepted`] refuses it, or that is signed
/// by a key that does not continue the earlier records' signer (Section 10.5).
pub fn check_records(graph: &Graph, chain: &[Cid]) -> Result<Vec<String>, SignatureError> {
    let mut publisher: Option<Cid> = None;
    let mut warnings = Vec::new();
    for cid in chain {
        let object = graph.object(cid);
        let index = object
            .and_then(|o| o.body().get("index"))
            .and_then(publet_core::cbor::Value::as_uint)
            .unwrap_or_default();
        let text = cid.to_string();
        match record_signature(graph, cid) {
            RecordSignature::Signed => {
                let Some(author) = object.map(Object::author) else {
                    continue;
                };
                if let Some(expected) = &publisher
                    && !graph.continues_key(expected, author)
                {
                    return Err(SignatureError::PublisherChanged {
                        index,
                        cid: text,
                        expected: expected.to_string(),
                        found: author.to_string(),
                    });
                }
                publisher = Some(author.clone());
            }
            RecordSignature::Forged => return Err(SignatureError::Forged { index, cid: text }),
            RecordSignature::Unsigned if unsigned_accepted(publisher.is_some()) => {
                warnings.push(format!(
                    "generation {index} ({text}) is unsigned; accepted, as no earlier generation \
                     of this domain is signed"
                ));
            }
            RecordSignature::Unsigned => {
                return Err(SignatureError::UnsignedAfterSigned { index, cid: text });
            }
        }
    }
    Ok(warnings)
}

/// The graph [`check_records`] needs: the generation records, signatures and
/// keys among `objects`, which may hold anything else too. An object that
/// cannot be read is left out.
#[must_use]
pub fn signature_graph(objects: &[(Cid, Vec<u8>)]) -> Graph {
    let relevant = objects
        .iter()
        .filter(|(cid, bytes)| {
            cid.verifies(bytes)
                && Object::parse(bytes)
                    .is_ok_and(|o| matches!(o.peek().kind(), "generation" | "sig" | "key"))
        })
        .cloned();
    publet_graph::load::from_objects_quietly(relevant).unwrap_or_default()
}

/// The records among `objects` that belong to `domain`, in index order.
#[must_use]
pub fn records_of(objects: &[(Cid, Vec<u8>)], domain: &Cid) -> Vec<Cid> {
    let mut records: Vec<(u64, Cid)> = objects
        .iter()
        .filter_map(|(cid, bytes)| {
            let parsed = Object::parse(bytes).ok()?;
            let object = parsed.peek();
            let body = object.body();
            (object.kind() == "generation"
                && body
                    .get("domain")
                    .and_then(publet_core::cbor::Value::as_text)
                    == Some(domain.to_string().as_str()))
            .then(|| {
                (
                    body.get("index")
                        .and_then(publet_core::cbor::Value::as_uint)
                        .unwrap_or_default(),
                    cid.clone(),
                )
            })
        })
        .collect();
    records.sort_by_key(|(index, cid)| (*index, cid.to_string()));
    records.dedup_by(|a, b| a.1 == b.1);
    records.into_iter().map(|(_, cid)| cid).collect()
}

#[cfg(test)]
mod tests {
    use publet_core::{SigAlg, cbor::Value};

    use super::*;

    const CREATED: &str = "2026-11-03T00:00:00Z";

    struct Key {
        seed: [u8; 32],
        cid: Cid,
        bytes: Vec<u8>,
    }

    fn key(n: u8) -> Key {
        let seed = [n; 32];
        let public = publet_core::verifying_key(SigAlg::Ed25519, &seed).unwrap();
        let bytes = Object::builder("key", &Cid::of(&public, HashAlg::Sha2_256).to_string())
            .created(CREATED)
            .field("alg", Value::Text("ed25519".into()))
            .field("pubkey", Value::Bytes(public))
            .field("principal", Value::Text("human".into()))
            .build()
            .unwrap();
        Key {
            seed,
            cid: Cid::of(&bytes, HashAlg::Sha2_256),
            bytes,
        }
    }

    fn record(author: &Key, index: u64) -> (Cid, Vec<u8>) {
        let bytes = Object::builder("generation", &author.cid.to_string())
            .created(CREATED)
            .field(
                "domain",
                Value::Text(Cid::of(b"d", HashAlg::Sha2_256).to_string()),
            )
            .field("index", Value::Uint(index))
            .build()
            .unwrap();
        (Cid::of(&bytes, HashAlg::Sha2_256), bytes)
    }

    fn sign(by: &Key, target: &(Cid, Vec<u8>), message: Option<&[u8]>) -> (Cid, Vec<u8>) {
        let value = publet_core::sign(
            SigAlg::Ed25519,
            &by.seed,
            PURPOSE,
            message.unwrap_or(&target.1),
        )
        .unwrap();
        let bytes = Object::builder("sig", &by.cid.to_string())
            .created(CREATED)
            .field("target", Value::Text(target.0.to_string()))
            .field("alg", Value::Text("ed25519".into()))
            .field("value", Value::Bytes(value))
            .field("purpose", Value::Text(PURPOSE.into()))
            .build()
            .unwrap();
        (Cid::of(&bytes, HashAlg::Sha2_256), bytes)
    }

    fn check(
        objects: &[(Cid, Vec<u8>)],
        chain: &[&(Cid, Vec<u8>)],
    ) -> Result<Vec<String>, SignatureError> {
        let graph = signature_graph(objects);
        let chain: Vec<Cid> = chain.iter().map(|(c, _)| c.clone()).collect();
        check_records(&graph, &chain)
    }

    // covers: check_records, record_signature, signature_graph
    #[test]
    fn signed_records_pass_and_unsigned_ones_before_them_are_only_warned_about() {
        let k = key(1);
        let (one, two) = (record(&k, 1), record(&k, 2));
        let signed = vec![
            (k.cid.clone(), k.bytes.clone()),
            one.clone(),
            two.clone(),
            sign(&k, &one, None),
            sign(&k, &two, None),
        ];
        assert_eq!(check(&signed, &[&one, &two]).unwrap(), Vec::<String>::new());

        let late = vec![
            (k.cid.clone(), k.bytes.clone()),
            one.clone(),
            two.clone(),
            sign(&k, &two, None),
        ];
        assert_eq!(check(&late, &[&one, &two]).unwrap().len(), 1);
    }

    // covers: check_records, unsigned_accepted
    #[test]
    fn an_unsigned_record_after_a_signed_one_is_refused() {
        let k = key(1);
        let (one, two) = (record(&k, 1), record(&k, 2));
        let objects = vec![
            (k.cid.clone(), k.bytes.clone()),
            one.clone(),
            two.clone(),
            sign(&k, &one, None),
        ];
        assert!(matches!(
            check(&objects, &[&one, &two]),
            Err(SignatureError::UnsignedAfterSigned { index: 2, .. })
        ));
        assert!(unsigned_accepted(false) && !unsigned_accepted(true));
    }

    // covers: check_records, record_signature
    #[test]
    fn a_signature_by_another_key_or_over_other_bytes_is_forged() {
        let (k, other) = (key(1), key(2));
        let one = record(&k, 1);
        let keys = vec![
            (k.cid.clone(), k.bytes.clone()),
            (other.cid.clone(), other.bytes.clone()),
        ];
        let mut wrong_key = keys.clone();
        wrong_key.extend([one.clone(), sign(&other, &one, None)]);
        assert!(matches!(
            check(&wrong_key, &[&one]),
            Err(SignatureError::Forged { .. })
        ));
        let mut tampered = keys;
        tampered.extend([one.clone(), sign(&k, &one, Some(b"other bytes"))]);
        assert!(matches!(
            check(&tampered, &[&one]),
            Err(SignatureError::Forged { .. })
        ));
    }

    // covers: check_records
    #[test]
    fn a_record_signed_by_a_key_that_does_not_continue_the_publisher_is_refused() {
        let (k, other) = (key(1), key(2));
        let (one, two) = (record(&k, 1), record(&other, 2));
        let objects = vec![
            (k.cid.clone(), k.bytes.clone()),
            (other.cid.clone(), other.bytes.clone()),
            one.clone(),
            two.clone(),
            sign(&k, &one, None),
            sign(&other, &two, None),
        ];
        assert!(matches!(
            check(&objects, &[&one, &two]),
            Err(SignatureError::PublisherChanged { index: 2, .. })
        ));
    }
}
