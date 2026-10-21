"""
xpert_legacy/faraid.py
Islamic inheritance (Faraid / Mirath) calculation engine.

Madhhab: Hanafi (the school followed by the majority in Pakistan).
Pure standard library — no Django, no third-party packages, so it can be
unit-tested standalone and imported from any Django view.

IMPORTANT
---------
This is a calculation tool, not a fatwa. Distribution of a real estate must be
confirmed by a qualified scholar and recorded by a lawyer. Handled here:
  * Spouse (husband / wives)
  * Father, mother (including the two "Umariyyatan" cases)
  * Sons, daughters, grandsons, granddaughters
  * Paternal grandfather / grandmother, maternal grandmother
  * Full, consanguine (paternal) and uterine (maternal) siblings
  * 'Awl  (fixed shares exceed 1 -> proportional reduction)
  * Radd (fixed shares below 1 and no residuary -> proportional return)

Combinations outside this scope raise a warning in `notes` so the caller can
route the case to a scholar instead of silently returning a wrong number.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Dict, List, Optional


# --------------------------------------------------------------------------- #
# Input model
# --------------------------------------------------------------------------- #
@dataclass
class Heirs:
    """Presence/count of each heir. All optional, all default to absent."""

    husband: bool = False
    wives: int = 0

    father: bool = False
    mother: bool = False

    sons: int = 0
    daughters: int = 0

    # Children of a son (they only inherit when there is no child)
    grandsons: int = 0
    granddaughters: int = 0

    paternal_grandfather: bool = False
    paternal_grandmother: bool = False
    maternal_grandmother: bool = False

    full_brothers: int = 0
    full_sisters: int = 0
    paternal_brothers: int = 0      # consanguine (same father)
    paternal_sisters: int = 0       # consanguine
    maternal_siblings: int = 0      # uterine (same mother)

    full_nephews: int = 0           # son of a full brother

    def any(self) -> bool:
        return any(
            [
                self.husband,
                self.wives,
                self.father,
                self.mother,
                self.sons,
                self.daughters,
                self.grandsons,
                self.granddaughters,
                self.paternal_grandfather,
                self.paternal_grandmother,
                self.maternal_grandmother,
                self.full_brothers,
                self.full_sisters,
                self.paternal_brothers,
                self.paternal_sisters,
                self.maternal_siblings,
                self.full_nephews,
            ]
        )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _frac(value) -> Fraction:
    """Convert int/float/str/Decimal to an exact Fraction."""
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    return Fraction(str(value))


def _ratio(numerator: Fraction) -> str:
    return f"{numerator.numerator}/{numerator.denominator}"


@dataclass
class Result:
    heir: str
    share: Fraction
    count: int = 1

    @property
    def share_str(self) -> str:
        return _ratio(self.share)

    @property
    def percent(self) -> float:
        return round(float(self.share) * 100, 4)

    def amount(self, estate: Fraction) -> float:
        return round(float(self.share * estate), 2)


# --------------------------------------------------------------------------- #
# Core engine
# --------------------------------------------------------------------------- #
def calculate(estate, heirs: Heirs) -> Dict:
    """
    Return a distribution table for `estate` (net of debts and wasiyyah)
    among `heirs`.

    Result shape::

        {
          "estate": 1000000.0,
          "results": [
             {"heir": "Wife", "share": "1/8", "percent": 12.5,
              "count": 1, "amount": 125000.0},
             ...
          ],
          "distributed": 1000000.0,
          "notes": ["'Awl applied: ..."],
          "warnings": []
        }
    """
    if not heirs.any():
        raise ValueError("At least one heir is required.")

    estate_f = _frac(estate)
    if estate_f <= 0:
        raise ValueError("Estate must be greater than zero.")

    notes: List[str] = []
    warnings: List[str] = []

    # ---- Structural facts ------------------------------------------------ #
    has_children = heirs.sons + heirs.daughters > 0
    has_grandchildren = heirs.grandsons + heirs.granddaughters > 0
    has_descendant = has_children or has_grandchildren
    has_male_descendant = heirs.sons + heirs.grandsons > 0

    siblings_total = (
        heirs.full_brothers
        + heirs.full_sisters
        + heirs.paternal_brothers
        + heirs.paternal_sisters
        + heirs.maternal_siblings
    )

    # ---------------------------------------------------------------- #
    # Phase 1 — fixed shares (Fardh)
    # ---------------------------------------------------------------- #
    fardh: Dict[str, Fraction] = {}
    counts: Dict[str, int] = {}

    # --- Spouse ---
    if heirs.husband and heirs.wives:
        raise ValueError("A person cannot have both a husband and wives.")

    if heirs.husband:
        fardh["Husband"] = Fraction(1, 2) if not has_descendant else Fraction(1, 4)
        counts["Husband"] = 1

    if heirs.wives > 0:
        fardh["Wife"] = Fraction(1, 4) if not has_descendant else Fraction(1, 8)
        counts["Wife"] = heirs.wives

    spouse_total = sum(
        (fardh.get("Husband", Fraction(0)), fardh.get("Wife", Fraction(0))),
        Fraction(0),
    )

    # --- Mother ---
    # Two classic exceptions (Umariyyatan): spouse + mother + father only.
    umariyyatan = (
        not has_descendant
        and siblings_total == 0
        and heirs.father
        and (heirs.husband or heirs.wives > 0)
    )

    if heirs.mother:
        if has_descendant or siblings_total >= 2:
            fardh["Mother"] = Fraction(1, 6)
        elif umariyyatan:
            # 1/3 of what remains after the spouse -> 1/6 or 1/4 of total
            fardh["Mother"] = (Fraction(1) - spouse_total) / 3
            notes.append(
                "Umariyyatan case: mother receives 1/3 of the remainder "
                "after the spouse's share."
            )
        else:
            fardh["Mother"] = Fraction(1, 3)
        counts["Mother"] = 1

    # --- Father (fixed part) ---
    if heirs.father and has_descendant:
        fardh["Father"] = Fraction(1, 6)
        counts["Father"] = 1
    elif heirs.father:
        counts["Father"] = 1  # pure residuary, handled in Phase 2

    # --- Children (fixed part for daughters with no sons) ---
    if heirs.sons > 0:
        counts["Son"] = heirs.sons
        if heirs.daughters:
            counts["Daughter"] = heirs.daughters
    elif heirs.daughters > 0:
        fardh["Daughter"] = (
            Fraction(1, 2) if heirs.daughters == 1 else Fraction(2, 3)
        )
        counts["Daughter"] = heirs.daughters
    elif heirs.grandsons > 0:
        counts["Grandson"] = heirs.grandsons
        if heirs.granddaughters:
            counts["Granddaughter"] = heirs.granddaughters
    elif heirs.granddaughters > 0:
        fardh["Granddaughter"] = (
            Fraction(1, 2) if heirs.granddaughters == 1 else Fraction(2, 3)
        )
        counts["Granddaughter"] = heirs.granddaughters

    # --- Paternal grandfather (only when father is absent) ---
    grandfather_active = heirs.paternal_grandfather and not heirs.father
    if grandfather_active:
        counts["Paternal Grandfather"] = 1
        if has_descendant:
            fardh["Paternal Grandfather"] = Fraction(1, 6)

    # --- Grandmothers (blocked by mother) ---
    grandmothers: List[str] = []
    if not heirs.mother:
        gm_count = int(heirs.maternal_grandmother) + int(heirs.paternal_grandmother)
        if gm_count:
            fardh["Grandmother"] = Fraction(1, 6)
            counts["Grandmother"] = gm_count
            if heirs.maternal_grandmother and heirs.paternal_grandmother:
                notes.append("Two grandmothers share the single 1/6 equally.")

    # --- Siblings ---
    # Uterine siblings: blocked by any descendant, father or grandfather.
    uterine_ok = not has_descendant and not heirs.father and not grandfather_active
    if heirs.maternal_siblings > 0 and uterine_ok:
        fardh["Maternal Siblings"] = (
            Fraction(1, 6) if heirs.maternal_siblings == 1 else Fraction(1, 3)
        )
        counts["Maternal Siblings"] = heirs.maternal_siblings

    # Full / consanguine siblings: blocked by a male descendant, father or
    # paternal grandfather, but NOT by daughters.
    siblings_ok = not has_male_descendant and not heirs.father and not grandfather_active

    full_active = siblings_ok and (heirs.full_brothers + heirs.full_sisters) > 0
    consanguine_ok = (
        siblings_ok
        and not full_active            # full siblings block consanguine ones
        and (heirs.paternal_brothers + heirs.paternal_sisters) > 0
    )

    if full_active:
        if heirs.full_brothers > 0:
            counts["Full Brother"] = heirs.full_brothers
            if heirs.full_sisters:
                counts["Full Sister"] = heirs.full_sisters
        else:
            # Sisters only: fixed share, or residuary alongside daughters.
            if has_children:
                counts["Full Sister"] = heirs.full_sisters
                notes.append(
                    "Full sisters inherit as residuary alongside daughters "
                    "(al-ukht ma'a al-bint)."
                )
            else:
                fardh["Full Sister"] = (
                    Fraction(1, 2) if heirs.full_sisters == 1 else Fraction(2, 3)
                )
                counts["Full Sister"] = heirs.full_sisters

    elif consanguine_ok:
        if heirs.paternal_brothers > 0:
            counts["Paternal Brother"] = heirs.paternal_brothers
            if heirs.paternal_sisters:
                counts["Paternal Sister"] = heirs.paternal_sisters
        else:
            fardh["Paternal Sister"] = (
                Fraction(1, 2) if heirs.paternal_sisters == 1 else Fraction(2, 3)
            )
            counts["Paternal Sister"] = heirs.paternal_sisters
    elif full_active is False and siblings_ok and heirs.full_nephews > 0 and not (
        heirs.full_brothers or heirs.full_sisters
    ):
        counts["Full Nephew"] = heirs.full_nephews

    # ---------------------------------------------------------------- #
    # Phase 2 — residuary (Asabah)
    # ---------------------------------------------------------------- #
    asabah_groups: List[List[str]] = []

    if heirs.sons > 0:
        asabah_groups.append(["Son", "Daughter"])
    elif heirs.grandsons > 0:
        asabah_groups.append(["Grandson", "Granddaughter"])
    elif heirs.father and not has_male_descendant:
        asabah_groups.append(["Father"])
    elif grandfather_active and not has_male_descendant:
        asabah_groups.append(["Paternal Grandfather"])
    elif full_active and heirs.full_brothers > 0:
        asabah_groups.append(["Full Brother", "Full Sister"])
    elif full_active and heirs.full_sisters > 0 and has_children:
        asabah_groups.append(["Full Sister"])
    elif consanguine_ok and heirs.paternal_brothers > 0:
        asabah_groups.append(["Paternal Brother", "Paternal Sister"])
    elif consanguine_ok and heirs.paternal_sisters > 0 and has_children:
        asabah_groups.append(["Paternal Sister"])
    elif heirs.full_nephews > 0 and siblings_ok:
        asabah_groups.append(["Full Nephew"])

    # ---------------------------------------------------------------- #
    # Phase 3 — 'Awl (shares exceed the estate)
    # ---------------------------------------------------------------- #
    total_fardh = sum(fardh.values(), Fraction(0))

    if total_fardh > 1:
        notes.append(
            f"'Awl applied: fixed shares total {_ratio(total_fardh)} "
            f"(more than the whole estate), so every share is reduced "
            f"proportionally to {_ratio(Fraction(1, 1))}."
        )
        for key in list(fardh.keys()):
            fardh[key] = fardh[key] / total_fardh
        total_fardh = Fraction(1)

    remainder = Fraction(1) - total_fardh

    # ---------------------------------------------------------------- #
    # Phase 4 — distribute the remainder
    # ---------------------------------------------------------------- #
    if remainder > 0 and asabah_groups:
        group = asabah_groups[0]
        weights: List[tuple[str, Fraction]] = []
        for name in group:
            if counts.get(name):
                # male gets twice the female share
                w = Fraction(2) if name in (
                    "Son",
                    "Grandson",
                    "Full Brother",
                    "Paternal Brother",
                ) else Fraction(1)
                weights.append((name, w * counts[name]))

        total_weight = sum((w for _, w in weights), Fraction(0))
        if total_weight > 0:
            for name, w in weights:
                fardh[name] = fardh.get(name, Fraction(0)) + remainder * w / total_weight
            notes.append(
                "Remainder distributed to the residuary heirs "
                f"({', '.join(group)}), with a male share equal to twice a "
                "female share."
            )

    elif remainder > 0:
        # Radd — return the surplus to the fixed-share heirs, spouse excluded.
        radd_keys = [k for k in fardh if k not in ("Husband", "Wife")]
        radd_total = sum((fardh[k] for k in radd_keys), Fraction(0))
        if radd_total > 0:
            for k in radd_keys:
                fardh[k] = fardh[k] + remainder * fardh[k] / radd_total
            notes.append(
                "Radd applied: no residuary heir exists, so the surplus is "
                "returned to the fixed-share heirs in proportion to their "
                "shares (the spouse does not take part)."
            )
        else:
            warnings.append(
                "Only the spouse inherits; the surplus would go to the "
                "Bait-ul-Maal under Hanafi rules. Confirm with a scholar."
            )

    # ---------------------------------------------------------------- #
    # Phase 5 — per-person figures
    # ---------------------------------------------------------------- #
    results: List[Result] = []
    for name in sorted(fardh, key=lambda n: (-fardh[n], n)):
        total_share = fardh[name]
        n = counts.get(name, 1) or 1
        results.append(Result(heir=name, share=total_share, count=n))

    distributed = sum((r.share for r in results), Fraction(0))
    if abs(distributed - 1) > Fraction(1, 10**9):
        warnings.append(
            f"Shares total {_ratio(distributed)} instead of 1 — please review "
            "the input combination."
        )

    if heirs.full_nephews and (heirs.full_brothers or heirs.full_sisters):
        notes.append("Nephews are excluded because the brothers/sisters are present.")

    return {
        "estate": float(estate_f),
        "results": [
            {
                "heir": r.heir,
                "share": r.share_str,
                "percent": r.percent,
                "count": r.count,
                "amount": r.amount(estate_f),
                "per_person": round(r.amount(estate_f) / r.count, 2),
            }
            for r in results
        ],
        "distributed": round(float(distributed * estate_f), 2),
        "notes": notes,
        "warnings": warnings,
    }


# --------------------------------------------------------------------------- #
# Convenience
# --------------------------------------------------------------------------- #
def quick(estate, **kwargs) -> Dict:
    """`quick(1000000, wives=1, sons=1, daughters=1, mother=True)`"""
    return calculate(estate, Heirs(**kwargs))
