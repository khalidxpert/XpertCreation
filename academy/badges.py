# The badge engine. Pure: takes the numbers, gives back role and medals.
# Kept free of Django so it can be tested on its own, and so the rules
# live in one readable place.

TIERS = ["bronze", "silver", "gold", "diamond"]

# Each family is one medallion. It shows the best tier reached and how far
# the next one is - seven medals that grow, rather than thirty that clutter.
FAMILIES = [
    {"id": "lessons",  "icon": "\U0001F4D6", "title": "Lessons",
     "desc": "Lessons finished", "steps": [1, 10, 50, 100]},
    {"id": "certs",    "icon": "\U0001F3C5", "title": "Certificates",
     "desc": "Courses passed", "steps": [1, 3, 5, 10]},
    {"id": "streak",   "icon": "\U0001F525", "title": "Streak",
     "desc": "Days in a row with a lesson", "steps": [3, 7, 14, 30]},
    {"id": "videos",   "icon": "\U0001F3AC", "title": "Creator",
     "desc": "Videos published", "steps": [1, 5, 10, 20]},
    {"id": "helpful",  "icon": "\U0001F44D", "title": "Helpful",
     "desc": "Helpful votes on your videos", "steps": [10, 50, 100, 200]},
    {"id": "reviews",  "icon": "\u270D\uFE0F", "title": "Reviewer",
     "desc": "Courses reviewed", "steps": [1, 3, 6, 10]},
    {"id": "polyglot", "icon": "\U0001F30D", "title": "Polyglot",
     "desc": "Language courses passed", "steps": [1, 2, 3, 5]},
]

ROLES = {
    "learner": {"title": "Learner", "icon": "\U0001F393"},
    "scholar": {"title": "Scholar", "icon": "\U0001F4DA"},
    "creator": {"title": "Content Creator", "icon": "\U0001F3AC"},
    "mentor":  {"title": "Mentor", "icon": "\U0001F31F"},
}


def best_streak(days):
    """Longest run of consecutive dates. days: iterable of date objects."""
    ds = sorted(set(days))
    best = run = 0
    prev = None
    for d in ds:
        run = run + 1 if (prev is not None and (d - prev).days == 1) else 1
        best = max(best, run)
        prev = d
    return best


def role_for(s):
    # Highest earned wins. Creating is worth more than collecting, and
    # being found helpful by others is worth most of all.
    if s["videos"] >= 1 and s["helpful"] >= 25:
        key = "mentor"
    elif s["videos"] >= 1:
        key = "creator"
    elif s["certs"] >= 3:
        key = "scholar"
    else:
        key = "learner"

    nxt = None
    if key == "learner":
        nxt = {"role": "scholar", "hint": "Pass %d more course%s"
               % (3 - s["certs"], "" if 3 - s["certs"] == 1 else "s")}
    elif key == "scholar":
        nxt = {"role": "creator", "hint": "Get one video published on a course"}
    elif key == "creator":
        left = 25 - s["helpful"]
        nxt = {"role": "mentor", "hint": "%d more helpful vote%s on your videos"
               % (left, "" if left == 1 else "s")}

    out = dict(ROLES[key], key=key)
    if nxt:
        out["next"] = dict(ROLES[nxt["role"]], key=nxt["role"], hint=nxt["hint"])
    return out


def families_for(s):
    out = []
    for f in FAMILIES:
        v = s.get(f["id"], 0)
        reached = [i for i, n in enumerate(f["steps"]) if v >= n]
        tier = TIERS[reached[-1]] if reached else None
        nxt_i = (reached[-1] + 1) if reached else 0
        nxt = None
        if nxt_i < len(f["steps"]):
            nxt = {"tier": TIERS[nxt_i], "goal": f["steps"][nxt_i]}
        out.append({"id": f["id"], "icon": f["icon"], "title": f["title"],
                    "desc": f["desc"], "value": v, "tier": tier, "next": nxt})
    return out


def summary(s):
    fams = families_for(s)
    return {"role": role_for(s), "families": fams,
            "earned": sum(1 for f in fams if f["tier"])}
