"""National rental price index (Mietpreisindex, part of the LIK/CPI) --
context series only, never compared across cantons since BFS does not
publish it below national level.

Unlike the other three sources, no bulk CSV/API endpoint for this specific
sub-index could be confirmed within this project's scope: it isn't on the
BFS STAT-TAB/PxWeb catalog (checked, no px-x-05xx cube matches), and
opendata.swiss's package API returned HTTP 403 to automated requests during
the audit (Cloudflare-protected — same as it did for several dataset pages
during the Step 1 audit). Per the project's "document the manual step, don't
scrape" rule, this table is intentionally left unpopulated; the schema slot
(fact_mietpreisindex_national) still exists for anyone who wants to wire it
up later. Manual source: https://www.bfs.admin.ch/bfs/de/home/statistiken/preise/mieten/index.html
"""


def run() -> int:
    print(
        "mietpreisindex_bfs: skipped -- no confirmed bulk/API source in scope, "
        "see module docstring and DATA_AUDIT.md for the manual source."
    )
    return 0


if __name__ == "__main__":
    run()
