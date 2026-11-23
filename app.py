"""Spain data job market dashboard. Run: streamlit run app.py"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA = Path(__file__).parent / "data" / "offers.csv"
WINDOW_DAYS = 90
ACCENT = "#1f5fa8"

st.set_page_config(page_title="Data job market in Spain", page_icon="📊", layout="wide")


@st.cache_data
def load() -> tuple[pd.DataFrame, pd.Timestamp]:
    df = pd.read_csv(DATA, parse_dates=["published"])
    snapshot = df["published"].max()
    df = df[df["is_data_role"] & (df["published"] >= snapshot - pd.Timedelta(days=WINDOW_DAYS))].copy()
    df["skills"] = df["skills"].fillna("")
    return df, snapshot


def skills_long(df: pd.DataFrame) -> pd.Series:
    s = df["skills"].str.split("|").explode()
    return s[s != ""]


def style(fig, height=380):
    fig.update_layout(height=height, margin=dict(l=0, r=10, t=10, b=0), plot_bgcolor="rgba(0,0,0,0)",
                      showlegend=False, font=dict(size=13))
    fig.update_xaxes(gridcolor="rgba(128,128,128,.15)")
    fig.update_yaxes(gridcolor="rgba(128,128,128,.15)")
    return fig


def euros(value: float) -> str:
    return f"€{value:,.0f}"


base, snapshot = load()

st.title("📊 Data job market in Spain")
st.caption(f"Snapshot of {snapshot:%d %b %Y} · offers published in the last {WINDOW_DAYS} days · "
           "Data: [Jobs by Adzuna](https://www.adzuna.es)")

with st.sidebar:
    st.header("Filters")
    provs = st.multiselect("Province", base["province"].value_counts().index.tolist(), placeholder="All")
    levels = st.multiselect("Seniority", ["junior", "unspecified", "senior"], placeholder="All")
    modes = st.multiselect("Work mode", ["remote", "hybrid", "not stated"], placeholder="All")
    only_salary = st.checkbox("Only offers with salary")

df = base
if provs:
    df = df[df["province"].isin(provs)]
if levels:
    df = df[df["seniority"].isin(levels)]
if modes:
    df = df[df["work_mode"].isin(modes)]
if only_salary:
    df = df[df["salary_mid"].notna()]

if df.empty:
    st.warning("No offers match these filters.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Offers", f"{len(df):,}")
sal = df["salary_mid"].dropna()
c2.metric("Median salary", euros(sal.median()) if len(sal) else "—",
          help=f"Gross annual salary, computed over the {len(sal)} offers that publish one.")
c3.metric("Salary published", f"{len(sal) / len(df):.0%}")
c4.metric("Mention remote", f"{(df['work_mode'] == 'remote').mean():.0%}",
          help="Detected in the title and the 500-character description snippet, so it is a lower bound.")

st.subheader("Most requested skills")
sk = skills_long(df).value_counts().head(15)
pct = (sk / len(df) * 100).round(1).iloc[::-1]
fig = px.bar(x=pct.values, y=pct.index, orientation="h", labels={"x": "% of offers", "y": ""},
             color_discrete_sequence=[ACCENT])
st.plotly_chart(style(fig, 440), use_container_width=True)

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Offers by province")
    prov = df["province"].value_counts().head(8).iloc[::-1]
    fig = px.bar(x=prov.values, y=prov.index, orientation="h", labels={"x": "offers", "y": ""},
                 color_discrete_sequence=[ACCENT])
    st.plotly_chart(style(fig), use_container_width=True)
with col_b:
    st.subheader("Gross annual salary by province")
    top = df["province"].value_counts().head(5).index
    d = df[df["province"].isin(top) & df["salary_mid"].notna()]
    fig = px.box(d, x="province", y="salary_mid", labels={"salary_mid": "€ / year", "province": ""},
                 color_discrete_sequence=[ACCENT], points="outliers")
    st.plotly_chart(style(fig), use_container_width=True)

st.subheader("Alicante and Elche")
local = base[(base["province"] == "Alicante") | base["city"].fillna("").str.contains("Elche|Elx")]
local_sal = local["salary_mid"].dropna()
l1, l2, l3, l4 = st.columns(4)
l1.metric("Offers in the province", len(local))
l2.metric("In Elche", int(base["city"].fillna("").str.contains("Elche|Elx").sum()))
l3.metric("Mention remote", f"{(local['work_mode'] == 'remote').mean():.0%}" if len(local) else "—")
l4.metric("Median salary", euros(local_sal.median()) if len(local_sal) else "—",
          help=f"Over {len(local_sal)} offers with a published salary.")
st.caption("Descriptive cut, ignoring the sidebar filters. It is deliberately not compared with the rest of Spain: "
           "the sample was built with different searches in each area (see methodology).")

col_c, col_d = st.columns(2)
with col_c:
    st.subheader("Seniority")
    n = df["seniority"].value_counts().reindex(["junior", "unspecified", "senior"]).dropna()
    fig = px.bar(x=n.index, y=n.values, labels={"x": "", "y": "offers"}, color_discrete_sequence=[ACCENT])
    st.plotly_chart(style(fig, 300), use_container_width=True)
    st.caption("Only counts offers that state it in the title.")
with col_d:
    st.subheader("Work mode")
    m = df["work_mode"].value_counts()
    fig = px.bar(x=m.index, y=m.values, labels={"x": "", "y": "offers"}, color_discrete_sequence=[ACCENT])
    st.plotly_chart(style(fig, 300), use_container_width=True)

st.subheader("Offers")
df = df.assign(city=df["city"].fillna("—"), province=df["province"].fillna("—"))
table = df[["title", "company", "city", "province", "seniority", "salary_mid", "skills", "published", "url"]].rename(
    columns={"title": "Title", "company": "Company", "city": "City", "province": "Province",
             "seniority": "Seniority", "salary_mid": "Avg. salary (€)", "skills": "Skills",
             "published": "Published", "url": "Link"})
st.dataframe(table, hide_index=True, use_container_width=True,
             column_config={"Link": st.column_config.LinkColumn("Link", display_text="View offer"),
                            "Avg. salary (€)": st.column_config.NumberColumn(format="%d")})

with st.expander("Methodology and limitations"):
    st.markdown(
        """
- **Source:** Adzuna API (free plan, very small quota). This is a **sample** of ~570 unique offers (after removing
  repeated ads) collected with 16 hand-picked searches (data-related terms across Spain and in Alicante/Elche),
  **not a census** of the market.
- **Sample bias:** searching for terms such as "Power BI" or "SQL" makes those tools appear more often than they would
  in the full market, and the Alicante/Elche searches were more generic than the national ones, so areas are not
  compared with each other.
- **Skills:** detected with regular expressions on the title and the first 500 characters of the description (the
  maximum the API returns). This is a **lower bound**: an offer may ask for more than what is visible.
- **Salaries:** only offers that publish one, filtered to €10,000–€200,000 per year.
- **Data role:** the title contains terms such as *data, datos, BI, SQL, ETL, analytics…*
        """
    )
