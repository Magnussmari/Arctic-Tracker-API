#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-28
"""Canonical unit normalization for CITES trade quantities.

WHY THIS EXISTS
---------------
`cites_trade_records.quantity` is a bare number whose meaning depends entirely
on `unit`, and the corpus contains 26 distinct units spanning mass, volume,
area, length, and several kinds of count. Summing that column without regard to
unit is not an approximation, it is meaningless, and it silently inverts
magnitude rankings because the smallest unit dominates the total.

Measured on the 43-species corpus (2026-07-28), raw sums by unit:

    mg      19,617 rows   sum 2,391,996,696   =      2.4 tonnes
    kg      87,270 rows   sum    74,196,188   = 74,196.2 tonnes

A naive SUM(quantity) makes the milligram rows look ~32x larger than the
kilogram rows, when they represent ~0.003% of the mass. Three rows also exceed
`numeric(10,2)` and were dropped at load time purely because they are recorded
in tiny units (1e8 mg and 1.23e8 / 3.3e8 microgrammes, all Acipenser baerii),
which is the overflow that has bitten this pipeline before.

THE RULE
--------
Quantities are only comparable within a DIMENSION. This module converts each
quantity to the canonical unit of its dimension and refuses to cross dimensions.
Callers aggregate per dimension and report per dimension. There is deliberately
no "total quantity" function, because there is no such quantity.

COUNT and PACKAGING are kept separate on purpose. A blank unit in the CITES
trade database means the quantity counts the term itself (88,284 blank-unit
"live" rows are 88,284 counts of live animals), which is a true count.
"sets", "pairs", "flasks", "cartons" and friends are countable but not
interconvertible and not comparable to specimen counts, so they get their own
dimension rather than being quietly folded into COUNT.
"""
from decimal import Decimal, ROUND_HALF_UP

# Dimensions. Values are the canonical unit each dimension normalizes to.
MASS = "mass"          # -> kg
VOLUME = "volume"      # -> L
AREA = "area"          # -> m2
LENGTH = "length"      # -> m
COUNT = "count"        # -> specimens (dimensionless count of the term)
PACKAGING = "packaging"  # -> discrete containers, NOT interconvertible
UNKNOWN = "unknown"    # unit present but unrecognised: never aggregated

CANONICAL = {
    MASS: "kg",
    VOLUME: "L",
    AREA: "m2",
    LENGTH: "m",
    COUNT: "specimens",
    PACKAGING: "containers",
    UNKNOWN: None,
}

# unit string (lowercased, stripped) -> (dimension, factor to canonical unit)
# Factors are exact Decimals; float factors would reintroduce the rounding
# drift that table_spec.py already had to fix once.
UNIT_TABLE = {
    # mass -> kg
    "microgrammes": (MASS, Decimal("1e-9")),
    "microgrames": (MASS, Decimal("1e-9")),   # observed spelling variant
    "ug": (MASS, Decimal("1e-9")),
    "mg": (MASS, Decimal("1e-6")),
    "g": (MASS, Decimal("1e-3")),
    "kg": (MASS, Decimal("1")),
    # volume -> L
    "ml": (VOLUME, Decimal("1e-3")),
    "l": (VOLUME, Decimal("1")),
    "cm3": (VOLUME, Decimal("1e-3")),         # 1 cm3 == 1 ml
    "m3": (VOLUME, Decimal("1000")),
    # area -> m2
    "cm2": (AREA, Decimal("1e-4")),
    "m2": (AREA, Decimal("1")),
    # length -> m
    "cm": (LENGTH, Decimal("1e-2")),
    "m": (LENGTH, Decimal("1")),
    # count -> specimens
    "number of specimens": (COUNT, Decimal("1")),
    "": (COUNT, Decimal("1")),                # CITES: blank unit == count of term
    # packaging: countable, not interconvertible, never merged with COUNT
    "sets": (PACKAGING, Decimal("1")),
    "pairs": (PACKAGING, Decimal("1")),
    "flasks": (PACKAGING, Decimal("1")),
    "bags": (PACKAGING, Decimal("1")),
    "shipments": (PACKAGING, Decimal("1")),
    "cans": (PACKAGING, Decimal("1")),
    "bottles": (PACKAGING, Decimal("1")),
    "boxes": (PACKAGING, Decimal("1")),
    "pieces": (PACKAGING, Decimal("1")),
    "sides": (PACKAGING, Decimal("1")),
    "cases": (PACKAGING, Decimal("1")),
    "cartons": (PACKAGING, Decimal("1")),
}


def classify(unit: str | None) -> str:
    """Return the dimension for a raw unit string. Unrecognised -> UNKNOWN."""
    key = (unit or "").strip().lower()
    entry = UNIT_TABLE.get(key)
    return entry[0] if entry else UNKNOWN


def normalize(quantity, unit: str | None):
    """Convert a quantity to its dimension's canonical unit.

    Returns (dimension, canonical_unit, value) where value is a Decimal, or
    (UNKNOWN, None, None) when the unit is unrecognised or the quantity is
    missing. An unrecognised unit is never silently coerced: a row that cannot
    be placed in a dimension must be reported, not folded into a total.
    """
    if quantity is None:
        return (UNKNOWN, None, None)
    key = (unit or "").strip().lower()
    entry = UNIT_TABLE.get(key)
    if entry is None:
        return (UNKNOWN, None, None)
    dimension, factor = entry
    value = Decimal(str(quantity)) * factor
    return (dimension, CANONICAL[dimension], value)


def aggregate(rows):
    """Sum an iterable of (quantity, unit) per dimension.

    Deliberately returns a mapping keyed by dimension. There is no scalar
    return value and no "total": summing across dimensions is the bug this
    module exists to prevent.

    Unrecognised units are counted under UNKNOWN with a row count only, so that
    a caller can see and report what it could not place.
    """
    out = {}
    for quantity, unit in rows:
        dimension, canonical, value = normalize(quantity, unit)
        slot = out.setdefault(
            dimension, {"unit": canonical, "total": Decimal("0"), "rows": 0, "unplaced_rows": 0}
        )
        slot["rows"] += 1
        if value is None:
            slot["unplaced_rows"] += 1
        else:
            slot["total"] += value
    for slot in out.values():
        slot["total"] = slot["total"].quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    return out


def sql_normalized_quantity(qty_col: str = "quantity", unit_col: str = "unit") -> str:
    """Emit the SQL CASE expression that mirrors UNIT_TABLE, for use in views.

    Generated from the same table the Python path uses, so the two cannot drift.
    Rows whose unit is unrecognised yield NULL rather than an unconverted
    number, which makes a missed unit visible as a NULL instead of a wrong sum.
    """
    whens = []
    for unit, (_dimension, factor) in sorted(UNIT_TABLE.items()):
        whens.append(
            f"    when lower(coalesce({unit_col}, '')) = '{unit}' "
            f"then {qty_col}::numeric * {factor:f}"
        )
    body = "\n".join(whens)
    return f"case\n{body}\n    else null\nend"


def sql_dimension(unit_col: str = "unit") -> str:
    """Emit the SQL CASE expression assigning each row its dimension."""
    whens = []
    for unit, (dimension, _factor) in sorted(UNIT_TABLE.items()):
        whens.append(f"    when lower(coalesce({unit_col}, '')) = '{unit}' then '{dimension}'")
    body = "\n".join(whens)
    return f"case\n{body}\n    else '{UNKNOWN}'\nend"
