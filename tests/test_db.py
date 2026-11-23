from painel import db


def test_upsert_does_not_duplicate(tmp_path):
    con = db.connect(tmp_path / "t.duckdb")
    offer = {"id": "abc", "title": "Data Analyst"}
    db.upsert_offers(con, "adzuna", "datos", [offer])
    db.upsert_offers(con, "adzuna", "datos", [offer])
    assert con.execute("SELECT count(*) FROM raw_offers").fetchone()[0] == 1
