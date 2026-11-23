"""Cleaning and enrichment: raw offers (DuckDB) -> data/offers.csv (job-description text is NOT exported).

Usage: python -m painel.transform
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import duckdb
import pandas as pd

from .db import DB_PATH

OUT = Path(__file__).resolve().parents[2] / "data" / "offers.csv"

# Display name -> regex, applied to title + description snippet (case-insensitive).
# The patterns include Spanish keywords on purpose: the offers are written in Spanish.
SKILLS: dict[str, str] = {
    "SQL": r"\bsql\b|mysql|postgres|t-sql|oracle sql",
    "Python": r"\bpython\b",
    "Power BI": r"power ?bi",
    "Excel": r"\bexcel\b",
    "Tableau": r"\btableau\b",
    "Qlik": r"\bqlik",
    "Looker": r"\blooker\b",
    "R": r"(?<![\w])R(?![\w+#])",  # case-sensitive, handled separately below
    "Spark": r"\bspark\b|pyspark",
    "Databricks": r"databricks",
    "Snowflake": r"snowflake",
    "Azure": r"\bazure\b",
    "AWS": r"\baws\b|amazon web services",
    "GCP": r"\bgcp\b|google cloud|bigquery",
    "Airflow": r"airflow",
    "dbt": r"\bdbt\b",
    "Docker": r"\bdocker\b",
    "Git": r"\bgit\b|github|gitlab",
    "ETL": r"\betl\b|\belt\b",
    "Machine Learning": r"machine learning|aprendizaje autom|\bml\b",
    "SAP": r"\bsap\b",
    "Java": r"\bjava\b(?!script)",
    "JavaScript": r"javascript|typescript",
    "Kafka": r"\bkafka\b",
    "English": r"\bingl[eé]s\b|\benglish\b",
}
_SKILL_RE = {k: re.compile(v, re.I) for k, v in SKILLS.items() if k != "R"}
_R_RE = re.compile(SKILLS["R"])

_JUNIOR = re.compile(
    r"\bjunior\b|\bjúnior\b|\bjr\b|prácticas|practicas|becari|trainee|internship|sin experiencia|\bbeca\b", re.I
)
_SENIOR = re.compile(
    r"\bsenior\b|\bsénior\b|\bsr\b|\blead\b|\bhead\b|responsable|manager|director|principal|arquitect", re.I
)
_REMOTE = re.compile(r"remot|teletrabaj|trabajo en casa|work from home|100% online|fully remote", re.I)
_HYBRID = re.compile(r"h[ií]brid|hybrid|semipresencial", re.I)
_DATA_ROLE = re.compile(
    r"\bdat(a|os)\b|\bbi\b|business intelligence|analytic|anal[ií]tic|\bbbdd\b|power ?bi|machine learning|"
    r"\bml\b|\bsql\b|\betl\b|big data|cient[ií]fic[oa] de datos|estad[ií]stic",
    re.I,
)
# Known false positives for the data-role filter
_NOT_DATA = re.compile(r"data cent(er|re)|centro de datos|data[- ]driven", re.I)


def extract_skills(text: str) -> list[str]:
    found = [name for name, rx in _SKILL_RE.items() if rx.search(text)]
    if _R_RE.search(text):
        found.append("R")
    return sorted(found)


def seniority(title: str) -> str:
    if _JUNIOR.search(title):
        return "junior"
    if _SENIOR.search(title):
        return "senior"
    return "unspecified"


def work_mode(text: str) -> str:
    if _REMOTE.search(text):
        return "remote"
    if _HYBRID.search(text):
        return "hybrid"
    return "not stated"


def is_data_role(title: str) -> bool:
    return bool(_DATA_ROLE.search(title)) and not _NOT_DATA.search(title)


def _area(area: object, idx: int) -> str | None:
    return area[idx] if isinstance(area, list) and len(area) > idx else None


def build(db_path: Path = DB_PATH) -> pd.DataFrame:
    con = duckdb.connect(str(db_path), read_only=True)
    rows = [json.loads(r[0]) for r in con.execute("SELECT payload FROM raw_offers").fetchall()]
    df = pd.json_normalize(rows)

    # De-duplication: the same employer re-posts one ad across cities/languages
    desc_key = df["company.display_name"].fillna("") + "|" + df["description"].fillna("").str.lower().str[:120]
    title_key = df["company.display_name"].fillna("") + "|" + df["title"].fillna("").str.lower().str.strip()
    df = df[~desc_key.duplicated() & ~title_key.duplicated()].reset_index(drop=True)

    text = df["title"].fillna("") + ". " + df["description"].fillna("")
    area = df["location.area"]
    out = pd.DataFrame(
        {
            "id": df["id"].astype(str),
            "title": df["title"],
            "company": df.get("company.display_name"),
            "region": area.apply(lambda a: _area(a, 1)),
            "province": area.apply(lambda a: _area(a, 2)),
            "city": area.apply(lambda a: a[-1] if isinstance(a, list) and a else None),
            "location": df["location.display_name"],
            "published": pd.to_datetime(df["created"], utc=True).dt.tz_localize(None).dt.date,
            "salary_min": df["salary_min"],
            "salary_max": df["salary_max"],
            "contract": df.get("contract_time"),
            "category": df["category.label"],
            "url": df["redirect_url"].str.split("?").str[0],  # drop tracking params (they embed the app id)
            "seniority": df["title"].fillna("").apply(seniority),
            "work_mode": text.apply(work_mode),
            "is_data_role": df["title"].fillna("").apply(is_data_role),
            "skills": text.apply(lambda t: "|".join(extract_skills(t))),
        }
    )
    out["salary_mid"] = out[["salary_min", "salary_max"]].mean(axis=1)
    # keep only plausible annual salaries (drops monthly values / data-entry errors)
    out.loc[~out["salary_mid"].between(10_000, 200_000), ["salary_min", "salary_max", "salary_mid"]] = pd.NA
    out.attrs["duplicates_dropped"] = len(rows) - len(df)
    return out.sort_values("published", ascending=False).reset_index(drop=True)


def main() -> None:
    df = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"{len(df)} unique offers (dropped {df.attrs.get('duplicates_dropped')} duplicates) -> {OUT}")
    print("data roles:", int(df.is_data_role.sum()), "| published:", df.published.min(), "to", df.published.max())


if __name__ == "__main__":
    main()
