//! Definitions of units, kinds and measures, and calculations' signatures
//! (Section 5.9).
//!
//! A number in a table means nothing without its unit, what it measures,
//! how sure its author is of it, and how it was computed. Each of those is
//! a claim that columns cite, so each can be disputed and revised on its
//! own lineage. This module reads the two body fields that make them
//! checkable: `defines` on a `definitional` claim and `computes` on a
//! `procedural` one. Whether a column's unit actually measures its kind is
//! a question for a units system, which this crate does not carry: it reads
//! shapes, and leaves the arithmetic to an adapter.

use std::collections::BTreeMap;

use publet_core::{Cid, cbor::Value};

use crate::GraphError;

/// What a `definitional` claim's `defines` field states (Section 5.9.1).
#[derive(Debug, Clone, PartialEq, Eq)]
#[non_exhaustive]
pub enum Definition {
    /// A system of units, at a version: UCUM 2.2.
    System {
        /// The system's name.
        name: String,
        /// The version meant.
        version: String,
    },
    /// A base dimension the system lacks, named by the symbol of its unit.
    Dimension {
        /// `{tray}`, `[EUR]`.
        symbol: String,
    },
    /// A unit equal to `value` times `unit`.
    Unit {
        /// The new unit's symbol.
        symbol: String,
        /// The multiplier, a decimal string.
        value: String,
        /// The unit multiplied, in the system's syntax.
        unit: String,
    },
    /// A quantity kind: what a value measures, beyond its dimension.
    Kind {
        /// The kind's name.
        name: String,
        /// An integer exponent per base, by base symbol.
        dimension: BTreeMap<String, i64>,
        /// The units that may measure it; empty when any of the dimension
        /// may.
        units: Vec<String>,
    },
    /// A way of stating a value and how sure one is of it.
    Measure {
        /// The measure's name.
        name: String,
        /// What its parameters describe.
        describes: Describes,
        /// The parameters, in order. A quantity cell has exactly these keys.
        parameters: Vec<Parameter>,
    },
}

impl Definition {
    /// The name the definition goes by: its `symbol` or `name`. This is
    /// `term(D)` for Section 9.2.
    #[must_use]
    pub fn term(&self) -> &str {
        match self {
            Self::System { name, .. } | Self::Kind { name, .. } | Self::Measure { name, .. } => {
                name
            }
            Self::Dimension { symbol } | Self::Unit { symbol, .. } => symbol,
        }
    }

    /// The `sort` this definition has on the wire.
    #[must_use]
    pub fn sort(&self) -> &'static str {
        match self {
            Self::System { .. } => "system",
            Self::Dimension { .. } => "dimension",
            Self::Unit { .. } => "unit",
            Self::Kind { .. } => "kind",
            Self::Measure { .. } => "measure",
        }
    }

    /// Read a `defines` field.
    ///
    /// # Errors
    ///
    /// Returns [`GraphError::BadField`] if `sort` is not one of the five,
    /// a field is missing or ill-typed, a symbol is not `{...}` or
    /// `[...]`, a value is not a decimal string, an exponent is not an
    /// integer, or a measure has no parameters or repeats one.
    pub fn from_value(value: &Value) -> Result<Self, GraphError> {
        let Value::Map(_) = value else {
            return Err(bad("defines", "a map with a `sort`"));
        };
        let sort = value
            .get("sort")
            .and_then(Value::as_text)
            .ok_or(bad("defines.sort", "a text string"))?;
        match sort {
            "system" => Ok(Self::System {
                name: required_text(value, "name", "defines.name")?,
                version: required_text(value, "version", "defines.version")?,
            }),
            "dimension" => Ok(Self::Dimension {
                symbol: symbol(value)?,
            }),
            "unit" => {
                let multiplier = required_text(value, "value", "defines.value")?;
                if !is_decimal(&multiplier) {
                    return Err(bad("defines.value", "a decimal string"));
                }
                Ok(Self::Unit {
                    symbol: symbol(value)?,
                    value: multiplier,
                    unit: required_text(value, "unit", "defines.unit")?,
                })
            }
            "kind" => Ok(Self::Kind {
                name: required_text(value, "name", "defines.name")?,
                dimension: dimension(value.get("dimension"))?,
                units: match value.get("units") {
                    None => Vec::new(),
                    Some(Value::Array(items)) if !items.is_empty() => items
                        .iter()
                        .map(|u| {
                            u.as_text()
                                .filter(|t| !t.is_empty())
                                .map(ToOwned::to_owned)
                                .ok_or(bad("defines.units", "an array of units"))
                        })
                        .collect::<Result<_, _>>()?,
                    Some(_) => return Err(bad("defines.units", "a non-empty array of units")),
                },
            }),
            "measure" => Ok(Self::Measure {
                name: required_text(value, "name", "defines.name")?,
                describes: match value.get("describes").and_then(Value::as_text) {
                    Some("exact") => Describes::Exact,
                    Some("variation") => Describes::Variation,
                    Some("uncertainty") => Describes::Uncertainty,
                    _ => {
                        return Err(bad(
                            "defines.describes",
                            "`exact`, `variation`, or `uncertainty`",
                        ));
                    }
                },
                parameters: parameters(value.get("parameters"))?,
            }),
            _ => Err(bad(
                "defines.sort",
                "`system`, `dimension`, `unit`, `kind`, or `measure`",
            )),
        }
    }
}

/// What a measure's parameters describe (Section 5.9.1).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[non_exhaustive]
pub enum Describes {
    /// A value stated as exact: a count, a price on a receipt.
    Exact,
    /// Variation in what was measured: repeated measurements.
    Variation,
    /// Uncertainty in what is known: estimates, intervals.
    Uncertainty,
}

/// One parameter of a measure.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Parameter {
    /// The key a quantity cell gives it: `low`, `sd`, `n`.
    pub name: String,
    /// What its value is.
    pub kind: ParameterType,
    /// What it means, for a reader.
    pub meaning: String,
}

/// The type of a parameter's value in a quantity cell (Section 5.9.4).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[non_exhaustive]
pub enum ParameterType {
    /// A decimal string in the column's unit.
    Quantity,
    /// A decimal string from 0 to 1.
    Fraction,
    /// An unsigned integer.
    Count,
    /// The CID of a blob.
    Blob,
}

/// What a calculation takes and gives (`computes`, Section 5.9.5).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Computes {
    /// Named inputs, each with the kind it must measure.
    pub inputs: Vec<(String, Cid)>,
    /// Named outputs, each with the kind it measures.
    pub outputs: Vec<(String, Cid)>,
    /// How a result that is not exact is rounded.
    pub rounding: Option<String>,
    /// A simulation's seed.
    pub seed: Option<u64>,
}

impl Computes {
    /// Read a `computes` field.
    ///
    /// # Errors
    ///
    /// Returns [`GraphError::BadField`] if `inputs` or `outputs` is not an
    /// array of `{name, kind}` with a CID for each kind, a name repeats
    /// within one of them, or `rounding` or `seed` is ill-typed.
    pub fn from_value(value: &Value) -> Result<Self, GraphError> {
        let Value::Map(_) = value else {
            return Err(bad("computes", "a map"));
        };
        Ok(Self {
            inputs: signature(value.get("inputs"), "computes.inputs")?,
            outputs: signature(value.get("outputs"), "computes.outputs")?,
            rounding: match value.get("rounding") {
                None => None,
                Some(Value::Text(t)) => Some(t.clone()),
                Some(_) => return Err(bad("computes.rounding", "a text string")),
            },
            seed: match value.get("seed") {
                None => None,
                Some(Value::Uint(n)) => Some(*n),
                Some(_) => return Err(bad("computes.seed", "an unsigned integer")),
            },
        })
    }

    /// Every kind the calculation names, inputs first.
    pub fn kinds(&self) -> impl Iterator<Item = &Cid> {
        self.inputs
            .iter()
            .chain(&self.outputs)
            .map(|(_, kind)| kind)
    }
}

/// Whether `text` is a decimal string: an optional minus sign, digits, and
/// an optional fraction. No exponent, no leading `+`, no bare point.
pub(crate) fn is_decimal(text: &str) -> bool {
    let unsigned = text.strip_prefix('-').unwrap_or(text);
    let (whole, fraction) = match unsigned.split_once('.') {
        Some((w, f)) => (w, Some(f)),
        None => (unsigned, None),
    };
    !whole.is_empty()
        && whole.bytes().all(|b| b.is_ascii_digit())
        && fraction.is_none_or(|f| !f.is_empty() && f.bytes().all(|b| b.is_ascii_digit()))
}

fn required_text(value: &Value, key: &str, field: &'static str) -> Result<String, GraphError> {
    value
        .get(key)
        .and_then(Value::as_text)
        .filter(|t| !t.is_empty())
        .map(ToOwned::to_owned)
        .ok_or(bad(field, "a non-empty text string"))
}

fn symbol(value: &Value) -> Result<String, GraphError> {
    let s = required_text(value, "symbol", "defines.symbol")?;
    let wrapped = |open: char, close: char| {
        s.len() > 2
            && s.starts_with(open)
            && s.ends_with(close)
            && s.get(1..s.len() - 1)
                .is_some_and(|inner| !inner.contains(['{', '}', '[', ']']))
    };
    if wrapped('{', '}') || wrapped('[', ']') {
        Ok(s)
    } else {
        Err(bad(
            "defines.symbol",
            "a brace annotation such as `{tray}` or a bracketed atom such as `[EUR]`",
        ))
    }
}

fn dimension(value: Option<&Value>) -> Result<BTreeMap<String, i64>, GraphError> {
    let Some(Value::Map(map)) = value else {
        return Err(bad("defines.dimension", "a map from base to exponent"));
    };
    let mut out = BTreeMap::new();
    for (base, exponent) in map {
        let n = match exponent {
            Value::Uint(n) => i64::try_from(*n).ok(),
            // CBOR stores -1 - n.
            Value::Nint(n) => i64::try_from(*n).ok().map(|n| -1 - n),
            _ => None,
        }
        .ok_or(bad("defines.dimension", "integer exponents"))?;
        if base.is_empty() {
            return Err(bad("defines.dimension", "non-empty base symbols"));
        }
        if n != 0 {
            out.insert(base.clone(), n);
        }
    }
    Ok(out)
}

fn parameters(value: Option<&Value>) -> Result<Vec<Parameter>, GraphError> {
    let Some(Value::Array(items)) = value else {
        return Err(bad(
            "defines.parameters",
            "an array of {name, type, meaning}",
        ));
    };
    let mut out: Vec<Parameter> = Vec::with_capacity(items.len());
    for item in items {
        let name = required_text(item, "name", "defines.parameters.name")?;
        if out.iter().any(|p| p.name == name) {
            return Err(bad("defines.parameters.name", "unique within the measure"));
        }
        let kind = match item.get("type").and_then(Value::as_text) {
            Some("quantity") => ParameterType::Quantity,
            Some("fraction") => ParameterType::Fraction,
            Some("count") => ParameterType::Count,
            Some("blob") => ParameterType::Blob,
            _ => {
                return Err(bad(
                    "defines.parameters.type",
                    "`quantity`, `fraction`, `count`, or `blob`",
                ));
            }
        };
        out.push(Parameter {
            name,
            kind,
            meaning: required_text(item, "meaning", "defines.parameters.meaning")?,
        });
    }
    if out.is_empty() {
        return Err(bad("defines.parameters", "at least one parameter"));
    }
    Ok(out)
}

fn signature(value: Option<&Value>, field: &'static str) -> Result<Vec<(String, Cid)>, GraphError> {
    let items = match value {
        None => return Ok(Vec::new()),
        Some(Value::Array(items)) => items,
        Some(_) => return Err(bad(field, "an array of {name, kind}")),
    };
    let mut out: Vec<(String, Cid)> = Vec::with_capacity(items.len());
    for item in items {
        let name = item
            .get("name")
            .and_then(Value::as_text)
            .filter(|n| !n.is_empty())
            .ok_or(bad(field, "entries with a non-empty `name`"))?;
        if out.iter().any(|(n, _)| n == name) {
            return Err(bad(field, "unique names"));
        }
        let kind = item
            .get("kind")
            .and_then(Value::as_text)
            .and_then(|t| t.parse::<Cid>().ok())
            .ok_or(bad(
                field,
                "entries whose `kind` is the CID of a kind claim",
            ))?;
        out.push((name.to_owned(), kind));
    }
    Ok(out)
}

fn bad(field: &'static str, expected: &'static str) -> GraphError {
    GraphError::BadField { field, expected }
}

#[cfg(test)]
mod tests {
    use super::*;

    const KIND: &str = "pub:sha2-256:z7uu6enmjz5gfxa5jtqjx4kynsm3chepcvqtv5s5g7zfj4y2iwra";

    fn map(pairs: Vec<(&str, Value)>) -> Value {
        Value::Map(pairs.into_iter().map(|(k, v)| (k.to_owned(), v)).collect())
    }

    fn text(s: &str) -> Value {
        Value::Text(s.to_owned())
    }

    #[test]
    fn a_dimension_is_named_by_a_braced_or_bracketed_symbol() {
        for good in ["{tray}", "[EUR]"] {
            let d = Definition::from_value(&map(vec![
                ("sort", text("dimension")),
                ("symbol", text(good)),
            ]))
            .unwrap();
            assert_eq!(d.term(), good);
        }
        for bad in ["tray", "{}", "{a}{b}", "kg"] {
            assert!(
                Definition::from_value(&map(vec![
                    ("sort", text("dimension")),
                    ("symbol", text(bad)),
                ]))
                .is_err(),
                "{bad}"
            );
        }
    }

    #[test]
    fn a_kind_reads_signed_exponents() {
        let d = Definition::from_value(&map(vec![
            ("sort", text("kind")),
            ("name", text("climate impact per tray")),
            (
                "dimension",
                map(vec![
                    ("g", Value::Uint(1)),
                    ("{CO2e}", Value::Uint(1)),
                    ("{tray}", Value::Nint(0)),
                ]),
            ),
            ("units", Value::Array(vec![text("kg{CO2e}/{tray}")])),
        ]))
        .unwrap();
        let Definition::Kind {
            dimension, units, ..
        } = d
        else {
            panic!("not a kind");
        };
        assert_eq!(dimension.get("{tray}"), Some(&-1));
        assert_eq!(units, ["kg{CO2e}/{tray}"]);
    }

    #[test]
    fn a_measure_names_typed_unique_parameters() {
        let param = |name: &str, kind: &str| {
            map(vec![
                ("name", text(name)),
                ("type", text(kind)),
                ("meaning", text("a bound")),
            ])
        };
        let measure = |params: Vec<Value>| {
            Definition::from_value(&map(vec![
                ("sort", text("measure")),
                ("name", text("three-point estimate")),
                ("describes", text("uncertainty")),
                ("parameters", Value::Array(params)),
            ]))
        };
        let d = measure(vec![
            param("low", "quantity"),
            param("likely", "quantity"),
            param("high", "quantity"),
        ])
        .unwrap();
        let Definition::Measure {
            parameters,
            describes,
            ..
        } = d
        else {
            panic!("not a measure");
        };
        assert_eq!(describes, Describes::Uncertainty);
        assert_eq!(parameters.len(), 3);
        assert!(measure(vec![param("low", "quantity"), param("low", "quantity")]).is_err());
        assert!(measure(vec![param("low", "float")]).is_err());
        assert!(measure(vec![]).is_err());
    }

    #[test]
    fn a_unit_is_a_decimal_multiple() {
        let unit = |value: &str| {
            Definition::from_value(&map(vec![
                ("sort", text("unit")),
                ("symbol", text("{flat}")),
                ("value", text(value)),
                ("unit", text("{tray}")),
            ]))
        };
        assert!(unit("6").is_ok());
        assert!(unit("0.125").is_ok());
        for bad in ["6e1", "+6", ".5", "5.", "six"] {
            assert!(unit(bad).is_err(), "{bad}");
        }
    }

    #[test]
    fn an_unknown_sort_is_refused() {
        assert!(Definition::from_value(&map(vec![("sort", text("currency"))])).is_err());
        assert!(Definition::from_value(&text("unit")).is_err());
    }

    #[test]
    fn a_calculation_names_its_kinds() {
        let entry = |name: &str| map(vec![("name", text(name)), ("kind", text(KIND))]);
        let c = Computes::from_value(&map(vec![
            (
                "inputs",
                Value::Array(vec![entry("energy"), entry("intensity")]),
            ),
            ("outputs", Value::Array(vec![entry("climate cost")])),
            ("rounding", text("half to even, 2 places")),
        ]))
        .unwrap();
        assert_eq!(c.kinds().count(), 3);
        assert_eq!(c.seed, None);
        assert!(
            Computes::from_value(&map(vec![(
                "inputs",
                Value::Array(vec![entry("energy"), entry("energy")])
            )]))
            .is_err()
        );
    }
}
