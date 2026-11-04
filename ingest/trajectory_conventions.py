#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-08-10
# SCALE-EXEMPT: this script's purpose IS to vary the convention. It computes
# finding (iii) under each plausible rule so the choice could be measured
# rather than argued, and it was the measurement that settled it. A table of
# its own is the instrument, not a second scale.
"""Finding (iii) under each plausible answer to Q3.

The manuscript reports post-listing status trajectories as 23 stable / 11
improved / 9 deteriorated. That tally depends entirely on how pre-2001 Red List
categories were handled, and 25 of 43 species have a legacy baseline. This computes
the tally under each rule, so the effect of the choice is explicit.

Baseline = earliest GLOBAL assessment. Current = latest GLOBAL assessment.
Scope is pinned global because the is_latest flag points at a European regional
assessment for 17 of 43 species.
"""
import os
import psycopg2

SCALE = {"LC": 0, "NT": 1, "VU": 2, "EN": 3, "CR": 4}

# Rule A: map legacy categories onto the modern scale where a defensible
# equivalent exists. K, T, NR, NA, N/A describe knowledge or an unresolved
# threat level, not a rank, so they stay unrankable under every rule.
MAP_A = {"LR/lc": "LC", "LR/nt": "NT", "LR/cd": "NT", "V": "VU", "E": "EN"}
LEGACY = {"LR/lc", "LR/nt", "LR/cd", "V", "E", "K", "T", "NR", "NA", "N/A"}


def rank(status, rule):
    if status in SCALE:
        return SCALE[status]
    if rule == "A" and status in MAP_A:
        return SCALE[MAP_A[status]]
    return None


def main():
    conn = psycopg2.connect(os.environ["ARCTIC_DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("""
        select s.scientific_name, a.status, a.year_published
        from arctic_v2.iucn_assessments a
        join arctic_v2.species s on s.id = a.species_id
        where coalesce(a.scope_code,'1') = '1' and a.year_published is not null
        order by s.scientific_name, a.year_published, a.assessment_id
    """)
    by_sp = {}
    for name, status, year in cur.fetchall():
        by_sp.setdefault(name, []).append((year, status))

    print(f"{len(by_sp)} species with at least one global assessment\n")

    for rule, label in [
        ("A", "RULE A - legacy categories MAPPED onto the modern scale"),
        ("B", "RULE B - species with ANY legacy baseline EXCLUDED"),
    ]:
        improved = stable = declined = 0
        dropped = []
        for name, rows in by_sp.items():
            base_year, base = rows[0]
            cur_year, curr = rows[-1]

            if rule == "B" and base in LEGACY:
                dropped.append((name, base, "legacy baseline"))
                continue

            rb, rc = rank(base, rule), rank(curr, rule)
            if rb is None or rc is None:
                dropped.append((name, base if rb is None else curr,
                                "unrankable category"))
                continue

            if rc < rb:
                improved += 1
            elif rc > rb:
                declined += 1
            else:
                stable += 1

        scored = improved + stable + declined
        print(f"{label}")
        print(f"  scored:      {scored} species")
        print(f"  improved:    {improved}")
        print(f"  stable:      {stable}")
        print(f"  deteriorated:{declined}")
        print(f"  excluded:    {len(dropped)}")
        if scored:
            print(f"  shares:      {round(100*stable/scored)}% stable, "
                  f"{round(100*improved/scored)}% improved, "
                  f"{round(100*declined/scored)}% deteriorated")
        print()

    print("MANUSCRIPT CLAIM: 23 stable (53%), 11 improved (26%), 9 deteriorated (21%)")
    print("                  = 43 species scored, i.e. NO species excluded.\n")

    n_legacy_base = sum(1 for rows in by_sp.values() if rows[0][1] in LEGACY)
    print(f"Species whose FIRST global assessment is a legacy category: {n_legacy_base} of {len(by_sp)}")
    unrankable = sum(1 for rows in by_sp.values()
                     if rows[0][1] in {"K", "T", "NR", "NA", "N/A"})
    print(f"  of which the baseline is not a risk rank at all (K/T/NR/NA): {unrankable}")
    conn.close()


if __name__ == "__main__":
    main()
