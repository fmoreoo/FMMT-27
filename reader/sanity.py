"""Guards against a game patch silently breaking the reader.

The reader finds players by class name, but the field offsets inside a player are
hard-coded. After a patch they may point at the wrong bytes and still return
plausible-looking numbers. Two guards catch that:

1. KNOWN_BUILDS: the engine builds the offsets were solved and checked on.
2. check_rows(): impossible values (a pass rate above 100%, more shots on target than
   shots, a rating outside 1-10 ...). One odd row can be a quirk of the game's own data,
   so a check only warns when it fires on at least MIN_SHARE of the rows with minutes.

After solving the offsets for a new build, add its id (printed by `python game.py`,
shown in the page banner) to KNOWN_BUILDS and a Profile to fm27.py.
"""

KNOWN_BUILDS = {"6A229F1E-1D8D3000", "6ADFB11C-19E69000", "6AE563A1-175DA000", "6AE8CF77-17969000"}  # FM26 26.3.2, FM27, FM27 0.9.2409, FM27 0.9.2435

MIN_SHARE = 0.02   # warn when a check fires on >= 2% of rows
MIN_ROWS = 20      # below this many rows the shares are too noisy to judge

PCT_COLUMNS = ["Pas %", "Cr C/A", "OP-Cr %", "Tck R", "Hdr %", "Sv %", "xSv %", "Pens Saved Ratio"]


def _num(v):
    return v if isinstance(v, (int, float)) and v == v else None


def _violations(r: dict) -> list[str]:
    """Names of the checks this one row fails (only for rows that have minutes)."""
    bad = []
    for c in PCT_COLUMNS:
        v = _num(r.get(c))
        if v is not None and not (0 <= v <= 100.0001):
            bad.append("percentage outside 0-100")
            break
    shots, sot = _num(r.get("Shots")), _num(r.get("ShT"))
    if shots is not None and sot is not None and sot > shots:
        bad.append("more shots on target than shots")
    rat = _num(r.get("Av Rat"))
    if rat is not None and not (1 <= rat <= 10):
        bad.append("average rating outside 1-10")
    mins, apps = _num(r.get("Mins")), _num(r.get("Apps"))
    if mins is not None and mins > 8000:
        bad.append("over 8000 minutes in a season")
    if mins is not None and apps and mins > apps * 130:
        bad.append("more than 130 minutes per appearance")
    age = _num(r.get("Age"))
    if age is not None and not (14 <= age <= 60):
        bad.append("age outside 14-60")
    dist = _num(r.get("Dist/90"))
    if dist is not None and not (0 <= dist <= 25):
        bad.append("distance per 90 outside 0-25 km")
    for c, hi in (("NP-xG/90", 3), ("xA/90", 3), ("Shot/90", 20), ("Pres A/90", 80), ("Poss Lost/90", 120)):
        v = _num(r.get(c))
        if v is not None and not (0 <= v <= hi):
            bad.append(f"{c} outside 0-{hi}")
    if r.get("Name") in (None, "", "?"):
        bad.append("player with no readable name")
    return bad


def check_rows(rows: list[dict]) -> list[str]:
    full = [r for r in rows if r.get("Mins")]
    if len(full) < MIN_ROWS:
        return []
    counts: dict[str, int] = {}
    for r in full:
        for name in set(_violations(r)):
            counts[name] = counts.get(name, 0) + 1
    out = []
    for name, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        if n / len(full) >= MIN_SHARE:
            out.append(f"{n} of {len(full)} players show {name}.")
    return out


def check(rows: list[dict], build_id: str, unlisted: int = 0) -> list[str]:
    """Warnings to show the user; an empty list means nothing looks wrong."""
    warnings = []
    if build_id not in KNOWN_BUILDS:
        known = ", ".join(sorted(KNOWN_BUILDS))
        warnings.append(
            f"This game build ({build_id}) is not one the reader was checked on ({known}). "
            "The game may have been patched: treat the numbers with caution until the offsets are re-checked.")
    if unlisted:
        warnings.append(f"{unlisted:,} players on club squad lists could not be read, so they are missing from the tool.")
    bad = check_rows(rows)
    if bad:
        warnings.extend(bad)
        warnings.append("Impossible values like these usually mean a game patch moved some fields.")
    return warnings


def main() -> int:
    """`python sanity.py` with the game running and a save loaded. Beyond check(), this catches stats landing
    on the wrong player, which looks perfectly plausible row by row: every player's stats object must carry that
    player's id, and goals conceded must land on keepers."""
    from export import to_row
    from fm27 import ENTRY, Game, P_ID

    g = Game()
    print(f"Game build {g.build.id} ({g.prof.name}{'' if g.known_build else ', unknown build'})")
    ps = g.players(refresh=True)
    if len(ps) < 1000:
        print(f"Only {len(ps)} players found. Load a save and run this again.")
        return 1
    today, raw = g.read_all("competitive", require_minutes=False)
    print(f"{len(ps):,} players, in-game date {today}")
    failed = 0

    linked = [a for a in ps if g.stats_object(a)]
    ids = sum(g.p.u32(g.stats_object(a) + 0x40) == g.p.u32(a + P_ID) for a in linked)
    ok = ids >= 0.99 * max(len(linked), 1)
    failed += not ok
    print(f"{'OK  ' if ok else 'FAIL'}  stats object belongs to its player: {ids:,} of {len(linked):,}")

    keepers = [r for r in raw if r["pos"][0] >= 15 and max(r["pos"]) == r["pos"][0] and r["season"] and r["season"]["minutes"] >= 450]
    others = [r for r in raw if r["pos"][0] < 15 and r["season"] and r["season"]["minutes"] >= 450]
    if len(keepers) >= 20 and len(others) >= 20:
        share = lambda rows: sum(r["season"]["conceded"] > 0 for r in rows) / len(rows)
        ok = share(keepers) > 0.5 and share(others) < 0.05
        failed += not ok
        print(f"{'OK  ' if ok else 'FAIL'}  goals conceded land on keepers: keepers {share(keepers):.0%}, others {share(others):.0%}")
    else:
        print("SKIP  goals conceded land on keepers: too few players with 450+ minutes yet")

    # attributes: every value on the 1-20 scale (x5), and a shifted map would lose the keepers' lead in their own attributes
    from fm27 import SHOWN_ATTRS
    att = [r for r in raw if r.get("attrs") and len(r["attrs"]) == len(SHOWN_ATTRS)]
    inrange = sum(all(1 <= v <= 100 for v in r["attrs"]) for r in att)
    gk = [r for r in att if r["pos"][0] >= 15 and max(r["pos"]) == r["pos"][0]]
    out = [r for r in att if r["pos"][0] < 15]
    mean = lambda rows, a: sum(r["attrs"][SHOWN_ATTRS.index(a)] for r in rows) / max(len(rows), 1)
    lead = all(mean(gk, a) > mean(out, a) + 25 for a in ("Handling", "Reflexes", "One On Ones")) and mean(out, "Finishing") > mean(gk, "Finishing") + 15
    ok = len(att) >= 0.99 * len(raw) and inrange >= 0.999 * len(att) and lead
    failed += not ok
    print(f"{'OK  ' if ok else 'FAIL'}  attributes: {inrange:,} of {len(att):,} in range; keepers' Handling {mean(gk, 'Handling') / 5:.1f} vs outfielders' {mean(out, 'Handling') / 5:.1f}")

    warnings = check([to_row(r) for r in raw], g.build.id, g.unlisted)
    failed += bool(warnings)
    for w in warnings:
        print("FAIL  " + w)
    if not warnings:
        print("OK    no impossible values")
    print("All checks passed." if not failed else f"{failed} check(s) failed: offsets in fm27.py probably need updating.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
