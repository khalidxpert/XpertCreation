"""
xpert_legacy/test_faraid.py
Verification cases for the Faraid engine. Run:  python3 test_faraid.py
Each expected value is the textbook (Hanafi) answer.
"""
from fractions import Fraction

from faraid import Heirs, calculate, quick

PASS, FAIL = "\033[92mPASS\033[0m", "\033[91mFAIL\033[0m"
failures = []


def check(name, estate, kwargs, expected: dict):
    """expected = {"Heir": "3/4", ...}"""
    out = quick(estate, **kwargs)
    got = {r["heir"]: r["share"] for r in out["results"]}
    ok = True
    for heir, share in expected.items():
        if Fraction(got.get(heir, "0")) != Fraction(share):
            ok = False
            print(f"   expected {heir}={share}, got {got.get(heir)}")
    extra = set(got) - set(expected)
    if extra:
        print(f"   unexpected heirs: {extra} -> {[got[e] for e in extra]}")
        ok = False
    print(("  " + PASS if ok else "  " + FAIL), name, "->", got)
    if not ok:
        failures.append(name)


print("\n=== 1. Spouse + children (classic residuary) ===")
# Wife 1/8; rest 7/8 split 2:1 -> son 7/12, daughter 7/24
check("wife + son + daughter", 1_000_000,
      dict(wives=1, sons=1, daughters=1),
      {"Wife": "1/8", "Son": "7/12", "Daughter": "7/24"})

print("\n=== 2. Umariyyatan (spouse + parents) ===")
# Husband 1/2, mother 1/3 of remainder = 1/6, father 1/3
check("husband + mother + father", 1_000_000,
      dict(husband=True, mother=True, father=True),
      {"Husband": "1/2", "Mother": "1/6", "Father": "1/3"})

# Wife 1/4, mother 1/3 of 3/4 = 1/4, father 1/2
check("wife + mother + father", 1_000_000,
      dict(wives=1, mother=True, father=True),
      {"Wife": "1/4", "Mother": "1/4", "Father": "1/2"})

print("\n=== 3. Daughters only -> Radd ===")
# 2 daughters take 2/3, remainder returns -> each 1/2
check("2 daughters only", 1_000_000,
      dict(daughters=2),
      {"Daughter": "1"})

print("\n=== 4. 'Awl case: wife + 2 daughters + father + mother (27 parts) ===")
# 1/8 + 2/3 + 1/6 + 1/6 = 27/24 -> awl to 27
check("awl 27", 1_000_000,
      dict(wives=1, daughters=2, father=True, mother=True),
      {"Wife": "3/27", "Daughter": "16/27",
       "Father": "4/27", "Mother": "4/27"})

print("\n=== 5. Mother + 1 daughter -> Radd proportional ===")
# Mother 1/6, daughter 1/2, remainder 1/3 returned 1:3 -> mother 1/4, daughter 3/4
check("mother + 1 daughter", 1_000_000,
      dict(mother=True, daughters=1),
      {"Mother": "1/4", "Daughter": "3/4"})

print("\n=== 6. Husband + daughter + father ===")
check("husband + daughter + father", 1_000_000,
      dict(husband=True, daughters=1, father=True),
      {"Husband": "1/4", "Daughter": "1/2", "Father": "1/4"})

print("\n=== 7. Full brother + full sister (2:1) with mother ===")
check("mother + brother + sister", 1_000_000,
      dict(mother=True, full_brothers=1, full_sisters=1),
      {"Mother": "1/6", "Full Brother": "5/9", "Full Sister": "5/18"})

print("\n=== 8. Uterine siblings (with radd on the surplus) ===")
# Wife 1/4, mother 1/6, uterine 1/3 -> 3/4, remainder 1/4 returns 1:2 -> 1/2 each group
check("wife + 2 maternal siblings + mother", 1_000_000,
      dict(wives=1, maternal_siblings=2, mother=True),
      {"Wife": "1/4", "Maternal Siblings": "1/2", "Mother": "1/4"})

print("\n=== 9. Father as pure residuary (no descendants) ===")
check("husband + father", 1_000_000,
      dict(husband=True, father=True),
      {"Husband": "1/2", "Father": "1/2"})

print("\n=== 10. Grandchildren inherit when no children ===")
check("wife + grandson + granddaughter", 1_000_000,
      dict(wives=1, grandsons=1, granddaughters=1),
      {"Wife": "1/8", "Grandson": "7/12", "Granddaughter": "7/24"})

print("\n=== 11. Siblings blocked by son ===")
out = quick(1_000_000, wives=1, sons=1, full_brothers=2)
got = {r["heir"] for r in out["results"]}
ok = "Full Brother" not in got and "Wife" in got
print(("  " + PASS if ok else "  " + FAIL), "son blocks full brothers ->", got)
if not ok:
    failures.append("hajb by son")

print("\n=== 12. Every case distributes 100% ===")
cases = [
    dict(wives=1, sons=2, daughters=1, mother=True, father=True),
    dict(husband=True, daughters=3, mother=True),
    dict(mother=True, full_brothers=2, full_sisters=1),
    dict(wives=2, sons=1, grandsons=1),
    dict(daughters=1, granddaughters=1),
    dict(husband=True, full_sisters=2),
    dict(wives=1, maternal_siblings=1, full_brothers=1),
    dict(father=True, mother=True, sons=1, daughters=1, wives=1),
]
for case in cases:
    out = quick(1_000_000, **case)
    total = sum(Fraction(r["share"]) for r in out["results"])
    ok = total == 1
    label = ", ".join(f"{k}={v}" for k, v in case.items())
    print(("  " + PASS if ok else "  " + FAIL), f"sum={total}", "|", label)
    if not ok:
        failures.append("sum " + label)

print("\n" + "=" * 60)
if failures:
    print(f"\033[91m{len(failures)} FAILED\033[0m: {failures}")
    raise SystemExit(1)
print("\033[92mALL TESTS PASSED\033[0m")
