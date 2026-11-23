"""Market snapshot: a few hand-picked searches (Adzuna free plan = tiny quota).

Usage: python -m painel.snapshot
Total: 16 API calls (50 results each). The counter in adzuna.py protects the quota.
"""
from __future__ import annotations

from . import adzuna, db

# (search term, location, pages)
PLAN = [
    ("analista de datos", None, 2),
    ("data analyst", None, 2),
    ("business intelligence", None, 1),
    ("power bi", None, 1),
    ("data scientist", None, 1),
    ("data engineer", None, 1),
    ("analista datos junior", None, 1),
    ("científico de datos", None, 1),
    ("python sql", None, 1),
    ("datos", "alicante", 1),
    ("data", "alicante", 1),
    ("analista", "alicante", 1),
    ("power bi", "alicante", 1),
    ("datos", "elche", 1),
]


def main() -> None:
    con = db.connect()
    for what, where, pages in PLAN:
        offers = list(adzuna.search(what, where, max_pages=pages))
        db.upsert_offers(con, "adzuna", f"{what}|{where or ''}", offers)
        total = con.execute("SELECT count(*) FROM raw_offers").fetchone()[0]
        print(f"{what!r} @ {where or 'Spain'}: {len(offers)} offers | unique in DB: {total}", flush=True)


if __name__ == "__main__":
    main()
