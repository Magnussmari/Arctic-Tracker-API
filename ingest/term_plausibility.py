#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-28
"""Deterministic term-plausibility gate for CITES trade records.

A CITES record says a quantity of some TERM (baleen, tusks, caviar, feathers)
was traded for some TAXON. Nothing in the CITES pipeline checks that the term is
anatomically possible for that taxon, so the public record contains items that
cannot exist: narwhal baleen, sturgeon baleen, bird teeth.

This gate flags those. It is the same defect class as the species-identity gate
in reference_gate.py, applied to a third surface.

DESIGN CONSTRAINTS (identical to reference_gate.py, and load-bearing)
---------------------------------------------------------------------
1. NO MODEL IN THE AUTHORITY PATH. Every verdict comes from an explicit rule
   keyed on taxonomic rank. A language model may help draft rules; it never
   decides a record's fate. This is the direct answer to R2.
2. RULES KEY ON RANK, NOT SPECIES LISTS. Rules are written against class,
   order and family so they generalise to taxa outside the current 43 rather
   than encoding a lookup of today's data.
3. UNCERTAIN NEVER AUTO-REJECTS. Anything short of anatomical impossibility
   returns REVIEW for a human. A gate that quietly discards ambiguous records
   would repeat the failure it exists to catch.
4. NOTHING IS DELETED. The gate labels; disposition is a human decision. The
   recommendation on this project is retain-and-flag, not drop.

VERDICTS
--------
  ACCEPT  term is possible for this taxon (or no rule constrains it)
  REVIEW  suspicious but not impossible; a human decides
  REJECT  anatomically impossible; cannot be a true record as filed
"""
from dataclasses import dataclass

ACCEPT = "ACCEPT"
REVIEW = "REVIEW"
REJECT = "REJECT"

# Mysticetes (baleen whales) by family. Everything else in Cetacea is an
# odontocete (toothed whale) and has no baleen.
MYSTICETE_FAMILIES = {"Balaenidae", "Balaenopteridae", "Eschrichtiidae", "Neobalaenidae"}

# The only families in scope that bear true tusks: walrus and narwhal.
TUSKED_FAMILIES = {"Odobenidae", "Monodontidae"}

# Families whose teeth are traded as worked ivory. Sperm whale teeth are
# legitimately worked as scrimshaw ivory, so Physeteridae belongs here.
IVORY_FAMILIES = {"Odobenidae", "Monodontidae", "Physeteridae"}

PLANT_CLASSES = {"Magnoliopsida", "Liliopsida", "Pinopsida", "Polypodiopsida"}
BIRD_CLASSES = {"Aves"}
MAMMAL_CLASSES = {"Mammalia"}
# Chondrichthyes are cartilaginous fish: no swim bladder, no true bone.
CARTILAGINOUS_CLASSES = {"Chondrichthyes"}
BONY_FISH_CLASSES = {"Actinopterygii", "Sarcopterygii"}
FISH_CLASSES = CARTILAGINOUS_CLASSES | BONY_FISH_CLASSES


def _norm(term: str) -> str:
    return (term or "").strip().lower()


@dataclass(frozen=True)
class Verdict:
    verdict: str
    rule: str
    reason: str

    @property
    def is_impossible(self) -> bool:
        return self.verdict == REJECT


@dataclass(frozen=True)
class Taxon:
    """The taxonomic ranks a rule may key on."""
    scientific_name: str
    class_name: str
    order_name: str
    family: str

    @property
    def is_cetacean(self) -> bool:
        return self.order_name == "Cetacea"

    @property
    def is_mysticete(self) -> bool:
        return self.is_cetacean and self.family in MYSTICETE_FAMILIES

    @property
    def is_odontocete(self) -> bool:
        return self.is_cetacean and self.family not in MYSTICETE_FAMILIES

    @property
    def is_bird(self) -> bool:
        return self.class_name in BIRD_CLASSES

    @property
    def is_mammal(self) -> bool:
        return self.class_name in MAMMAL_CLASSES

    @property
    def is_plant(self) -> bool:
        return self.class_name in PLANT_CLASSES

    @property
    def is_fish(self) -> bool:
        return self.class_name in FISH_CLASSES


# Each rule: (rule_id, set of terms, predicate on Taxon -> True when IMPOSSIBLE,
#             verdict, human-readable reason)
# Predicates state impossibility positively so the rule reads as the claim it makes.
RULES = [
    (
        "R1-baleen-requires-mysticete",
        {"baleen", "baleen carvings", "baleen products"},
        lambda t: not t.is_mysticete,
        REJECT,
        "baleen is the keratin filter structure of mysticete whales; this taxon has none",
    ),
    (
        "R2-teeth-absent-in-mysticetes",
        {"teeth", "tooth"},
        lambda t: t.is_mysticete,
        REJECT,
        "mysticete whales have baleen, not teeth",
    ),
    (
        "R3-teeth-absent-in-birds",
        {"teeth", "tooth"},
        lambda t: t.is_bird,
        REJECT,
        "extant birds have no teeth",
    ),
    (
        "R4-tusks-require-tusked-family",
        {"tusks", "tusk"},
        lambda t: t.family not in TUSKED_FAMILIES,
        REJECT,
        "tusks occur only in Odobenidae (walrus) and Monodontidae (narwhal) in this dataset",
    ),
    (
        "R5a-feathers-require-birds",
        {"feathers", "down"},
        lambda t: not t.is_bird,
        REJECT,
        "feathers occur only in birds",
    ),
    (
        # NOT bird-exclusive. Fish, reptiles and amphibians all lay eggs, and
        # sturgeon eggs are the single largest legitimate egg trade in this
        # corpus (caviar is sturgeon roe). An earlier version of this rule
        # bundled eggs with feathers and falsely rejected 10,129 Acipenser
        # baerii records. Only mammals are excluded: no mammal in scope is a
        # monotreme, so a mammalian egg record is impossible.
        "R5b-eggs-absent-in-mammals",
        {"eggs", "eggshell", "eggs (live)"},
        lambda t: t.is_mammal,
        REJECT,
        "no mammal in scope lays eggs (no monotremes present)",
    ),
    (
        "R6-caviar-requires-sturgeon",
        {"caviar"},
        lambda t: t.order_name != "Acipenseriformes",
        REJECT,
        "caviar is sturgeon and paddlefish roe (Acipenseriformes)",
    ),
    (
        "R7-plant-parts-require-plants",
        {"roots", "flowers", "dried plants", "leaves", "seeds", "stems", "bark"},
        lambda t: not t.is_plant,
        REJECT,
        "plant structures cannot come from an animal taxon",
    ),
    (
        "R8-swim-bladder-requires-bony-fish",
        {"swim bladders", "swim bladder"},
        lambda t: t.class_name not in BONY_FISH_CLASSES,
        REJECT,
        "swim bladders occur in bony fish; cartilaginous fish and non-fish have none",
    ),
    (
        "R9-hair-requires-mammal",
        {"hair", "hair products", "fur product (small)", "fur products (large)", "wool"},
        lambda t: not t.is_mammal,
        REJECT,
        "hair and fur occur only in mammals",
    ),
    (
        "R10-horns-absent-in-all-scope-taxa",
        {"horns", "horn carvings", "horn products", "horn pieces"},
        lambda t: True,
        REJECT,
        "no taxon in scope bears true horns; walrus and narwhal bear tusks, not horns",
    ),
    # --- REVIEW tier: suspicious, not impossible. A human decides. ---
    (
        "R11-ivory-outside-ivory-bearing-families",
        {"ivory carvings", "ivory pieces", "ivory scraps", "jewellery - ivory ", "jewellery - ivory"},
        lambda t: t.family not in IVORY_FAMILIES,
        REVIEW,
        "worked ivory normally derives from walrus, narwhal or sperm whale dentition",
    ),
    (
        "R12-fins-outside-fish",
        {"fins", "fin (dried)"},
        lambda t: not t.is_fish,
        REVIEW,
        "'fins' normally denotes shark fin; on a cetacean this may mean flipper and needs a human read",
    ),
    (
        "R13-scales-in-mammals-or-birds",
        {"scales"},
        lambda t: t.is_mammal or t.is_bird,
        REVIEW,
        "scales are not a mammalian or avian structure in this trade context",
    ),
    (
        # "fibres" is ambiguous: plant fibre, but also baleen fibre and other
        # animal fibres. Not impossible on an animal, so REVIEW rather than
        # the REJECT an earlier version of R7 gave it.
        "R14-fibres-on-animal",
        {"fibres"},
        lambda t: not t.is_plant,
        REVIEW,
        "'fibres' usually denotes plant fibre but animal fibre exists; needs a human read",
    ),
]


def check(term: str, taxon: Taxon) -> Verdict:
    """Return the verdict for one (term, taxon) pair.

    Rules are evaluated in order; the first REJECT wins, otherwise the first
    REVIEW. A term no rule constrains is ACCEPT: this gate makes positive
    claims about impossibility only, and silence is not suspicion.
    """
    normalized = _norm(term)
    pending_review = None
    for rule_id, terms, is_impossible, verdict, reason in RULES:
        if normalized not in {_norm(t) for t in terms}:
            continue
        if not is_impossible(taxon):
            continue
        if verdict == REJECT:
            return Verdict(REJECT, rule_id, reason)
        if pending_review is None:
            pending_review = Verdict(REVIEW, rule_id, reason)
    if pending_review is not None:
        return pending_review
    return Verdict(ACCEPT, "no-rule-applies", "no rule constrains this term for this taxon")
