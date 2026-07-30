"""
Jira BPS Interactive Dashboard
Pulls live data from Google Ads API + Socrates/Databricks.

Run with:
    /Users/aserrano/Library/Python/3.9/bin/streamlit run agents/dashboard.py
"""

import yaml
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from collections import defaultdict
from google.ads.googleads.client import GoogleAdsClient
import requests
import time

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Jira BPS Dashboard",
    page_icon="📊",
    layout="wide",
)

COLORS = {
    "TMP": "#4688EC",
    "nonTMP": "#2ABB7F",
    "FY26": "#F4A261",
    "FY27": "#E76F51",
}

GEO_COLORS = {
    "us": "#4688EC",
    "uk": "#2ABB7F",
    "au": "#F4A261",
    "in": "#E76F51",
    "row": "#9B5DE5",
    "es": "#F15BB5",
    "unknown": "#adb5bd",
}

# ── Socrates config ───────────────────────────────────────────────────────────
SOCRATES_HOST = "https://socrates-workbench-01.cloud.databricks.com"
SOCRATES_TIMEOUT = 45  # seconds


def _load_socrates_token():
    """Load Socrates PAT from Streamlit secrets or local config."""
    try:
        return st.secrets["socrates"]["token"]
    except Exception:
        pass
    try:
        with open("agents/config.yaml") as f:
            cfg = yaml.safe_load(f)
        return cfg.get("socrates", {}).get("token", None)
    except Exception:
        return None


SOCRATES_MONTHLY_SEED = [
    ["2025-06", 378004, 53648, 8654, 581968],
    ["2025-07", 417000, 50879, 9299, 594951],
    ["2025-08", 397919, 54351, 9700, 477689],
    ["2025-09", 455445, 67154, 11924, 450408],
    ["2025-10", 473299, 70075, 11530, 547843],
    ["2025-11", 452369, 69825, 11368, 553788],
    ["2025-12", 391116, 56317, 9216, 347640],
    ["2026-01", 476595, 69689, 13376, 544580],
    ["2026-02", 557728, 60413, 14334, 817039],
    ["2026-03", 655877, 64904, 15024, 956226],
    ["2026-04", 632554, 64669, 14179, 1295107],
    ["2026-05", 561790, 32488, 11243, 614473],
    ["2026-06", 585832, 26554, 9346, 666816],
]

SOCRATES_DAILY_SEED = [
    ["2026-07-13", 27659, 1157, 392],
    ["2026-07-14", 24583, 963, 320],
    ["2026-07-15", 24878, 1226, 379],
    ["2026-07-16", 24480, 1267, 355],
    ["2026-07-17", 21201, 1080, 265],
    ["2026-07-18", 6287, 295, 101],
    ["2026-07-19", 5751, 290, 111],
    ["2026-07-20", 28228, 1555, 436],
    ["2026-07-21", 28279, 1637, 436],
    ["2026-07-22", 27131, 1434, 405],
    ["2026-07-23", 27201, 1283, 355],
    ["2026-07-24", 22801, 949, 276],
    ["2026-07-25", 7257, 385, 118],
    ["2026-07-26", 7466, 305, 92],
    ["2026-07-27", 30086, 1443, 323],
    ["2026-07-28", 28431, 1179, 241],
    ["2026-07-29", 26243, 407, 0],
]


@st.cache_data(ttl=3600)
def fetch_socrates_monthly(start_date, end_date):
    """Pull BPS signups, biz_signups, BD1-6 monthly from Socrates.
    Uses seed data when PAT token is unavailable (PATs disabled by IT policy).
    Returns empty DataFrame with correct columns on any failure."""
    empty = pd.DataFrame(columns=["Month", "Signups", "BizSignups", "BD1_6", "CPBD1_6"])
    token = _load_socrates_token()
    if not token or token == "PASTE_DATABRICKS_PAT_HERE":
        # Use seed data (PATs disabled by IT policy - refreshed via Rovo Dev MCP)
        df = pd.DataFrame(SOCRATES_MONTHLY_SEED, columns=["Month", "Signups", "BizSignups", "BD1_6", "Spend"])
        df["CPBD1_6"] = (df["Spend"] / df["BD1_6"].replace(0, 1)).round(0).astype(int)
        df = df[["Month", "Signups", "BizSignups", "BD1_6", "CPBD1_6"]]
        return df, "Using cached data (last refreshed Jul 30 2026). PATs disabled by IT policy."

    sql = f"""
        SELECT
            date_trunc('month', date) as month,
            SUM(entrances) as signups,
            SUM(evaluations_with_business_domain) as biz_signups,
            SUM(business_domain_d1to6) as bd1_6,
            SUM(spend) as spend
        FROM marketing_paid_performance.paid_performance_campaigns
        WHERE channel = 'paid-search-branded'
        AND advertised_product = 'Jira'
        AND campaign_subject = 'brand-trademark'
        AND date >= '{start_date}'
        AND date <= '{end_date}'
        GROUP BY 1
        ORDER BY 1
    """
    try:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        r = requests.post(
            f"{SOCRATES_HOST}/api/2.0/sql/statements",
            headers=headers,
            json={"statement": sql, "wait_timeout": "30s", "on_wait_timeout": "CONTINUE"},
            timeout=SOCRATES_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()

        # Poll if still running
        stmt_id = data.get("statement_id")
        for _ in range(6):
            state = data.get("status", {}).get("state", "")
            if state in ("SUCCEEDED", "FAILED", "CANCELED", "CLOSED"):
                break
            time.sleep(5)
            poll = requests.get(
                f"{SOCRATES_HOST}/api/2.0/sql/statements/{stmt_id}",
                headers=headers, timeout=SOCRATES_TIMEOUT)
            data = poll.json()

        if data.get("status", {}).get("state") != "SUCCEEDED":
            err = data.get("status", {}).get("error", {}).get("message", "Unknown error")
            return empty, f"Socrates query failed: {err}"

        cols = [c["name"] for c in data["manifest"]["schema"]["columns"]]
        rows = data.get("result", {}).get("data_array", [])
        df = pd.DataFrame(rows, columns=cols)
        df.columns = ["Month", "Signups", "BizSignups", "BD1_6", "Spend"]
        df["Month"] = df["Month"].str[:7]
        for col in ["Signups", "BizSignups", "BD1_6", "Spend"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        df["CPBD1_6"] = (df["Spend"] / df["BD1_6"]).round(0).astype(int)
        return df[["Month", "Signups", "BizSignups", "BD1_6", "CPBD1_6"]], None

    except Exception as e:
        return empty, f"Socrates unavailable: {str(e)[:120]}"


@st.cache_data(ttl=3600)
def fetch_socrates_daily(start_date, end_date):
    """Pull BPS signups, biz_signups, BD1-6 daily from Socrates."""
    empty = pd.DataFrame(columns=["Date", "Signups", "BizSignups", "BD1_6"])
    token = _load_socrates_token()
    if not token or token == "PASTE_DATABRICKS_PAT_HERE":
        # Use seed data (PATs disabled by IT policy - refreshed via Rovo Dev MCP)
        df = pd.DataFrame(SOCRATES_DAILY_SEED, columns=["Date", "Signups", "BizSignups", "BD1_6"])
        return df, "Using cached data (last refreshed Jul 30 2026). PATs disabled by IT policy."

    sql = f"""
        SELECT
            date,
            SUM(entrances) as signups,
            SUM(evaluations_with_business_domain) as biz_signups,
            SUM(business_domain_d1to6) as bd1_6
        FROM marketing_paid_performance.paid_performance_campaigns
        WHERE channel = 'paid-search-branded'
        AND advertised_product = 'Jira'
        AND campaign_subject = 'brand-trademark'
        AND date >= '{start_date}'
        AND date <= '{end_date}'
        GROUP BY 1
        ORDER BY 1
    """
    try:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        r = requests.post(
            f"{SOCRATES_HOST}/api/2.0/sql/statements",
            headers=headers,
            json={"statement": sql, "wait_timeout": "30s", "on_wait_timeout": "CONTINUE"},
            timeout=SOCRATES_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()

        stmt_id = data.get("statement_id")
        for _ in range(6):
            state = data.get("status", {}).get("state", "")
            if state in ("SUCCEEDED", "FAILED", "CANCELED", "CLOSED"):
                break
            time.sleep(5)
            poll = requests.get(
                f"{SOCRATES_HOST}/api/2.0/sql/statements/{stmt_id}",
                headers=headers, timeout=SOCRATES_TIMEOUT)
            data = poll.json()

        if data.get("status", {}).get("state") != "SUCCEEDED":
            err = data.get("status", {}).get("error", {}).get("message", "Unknown error")
            return empty, f"Socrates query failed: {err}"

        cols = [c["name"] for c in data["manifest"]["schema"]["columns"]]
        rows = data.get("result", {}).get("data_array", [])
        df = pd.DataFrame(rows, columns=cols)
        df.columns = ["Date", "Signups", "BizSignups", "BD1_6"]
        for col in ["Signups", "BizSignups", "BD1_6"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        return df, None

    except Exception as e:
        return empty, f"Socrates unavailable: {str(e)[:120]}"


# ── Load Google Ads client ────────────────────────────────────────────────────
@st.cache_resource
def load_client():
    # Try Streamlit Cloud secrets first, fall back to local config.yaml
    try:
        ga = st.secrets["google_ads"]
        cids = ga.get("client_customer_ids", ["5374304580"])
    except Exception:
        with open("agents/config.yaml") as f:
            cfg = yaml.safe_load(f)
        ga = cfg["google_ads"]
        cids = ga.get("client_customer_ids", ["5374304580"])

    client = GoogleAdsClient.load_from_dict({
        "developer_token": ga["developer_token"],
        "client_id": ga["client_id"],
        "client_secret": ga["client_secret"],
        "refresh_token": ga["refresh_token"],
        "login_customer_id": str(ga["login_customer_id"]),
        "use_proto_plus": True,
    })
    customer_id = str(cids[0]).replace("-", "")
    return client, customer_id


def run_query(query):
    client, customer_id = load_client()
    service = client.get_service("GoogleAdsService")
    return list(service.search(customer_id=customer_id, query=query))


def weighted_is(rows_dict):
    return rows_dict["is_w"] / rows_dict["imp"] * 100 if rows_dict["imp"] > 0 else 0


# ── Data fetchers ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def fetch_tmp_monthly(start_date, end_date):
    """TMP (Brand-Trademark) exact match IS monthly."""
    rows = run_query(f"""
        SELECT segments.month, metrics.search_impression_share,
               metrics.impressions, metrics.clicks, metrics.cost_micros
        FROM keyword_view
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
        AND campaign.name LIKE '%S:brand-trademark%'
        AND campaign.name NOT LIKE '%trello%'
        AND ad_group.name LIKE '%Brand-Trademark%'
        AND ad_group_criterion.keyword.match_type = 'EXACT'
        AND metrics.impressions > 0
        ORDER BY segments.month
    """)
    agg = defaultdict(lambda: {"is_w": 0.0, "imp": 0, "clicks": 0, "cost": 0.0})
    for r in rows:
        m = r.segments.month
        imp = r.metrics.impressions
        is_v = r.metrics.search_impression_share or 0
        if is_v > 0 and imp > 0:
            agg[m]["is_w"] += is_v * imp
            agg[m]["imp"] += imp
        agg[m]["clicks"] += r.metrics.clicks
        agg[m]["cost"] += r.metrics.cost_micros / 1_000_000
    return pd.DataFrame([{
        "Month": m[:7],
        "Spend": round(d["cost"]),
        "Clicks": d["clicks"],
        "IS": round(weighted_is(d), 1),
    } for m, d in sorted(agg.items())])


@st.cache_data(ttl=3600)
def fetch_nontmp_weekly(start_date, end_date):
    """nonTMP (Brand-General) all match types, weekly aggregated."""
    rows = run_query(f"""
        SELECT segments.week, metrics.search_impression_share,
               metrics.search_budget_lost_impression_share,
               metrics.search_rank_lost_impression_share,
               metrics.impressions, metrics.clicks, metrics.cost_micros
        FROM campaign
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
        AND campaign.name LIKE '%S:brand-trademark%'
        AND campaign.name NOT LIKE '%trello%'
        AND metrics.impressions > 0
        ORDER BY segments.week
    """)
    agg = defaultdict(lambda: {"is_w": 0.0, "budget_w": 0.0, "rank_w": 0.0,
                                "imp": 0, "clicks": 0, "cost": 0.0})
    for r in rows:
        w = r.segments.week
        imp = r.metrics.impressions
        is_v = r.metrics.search_impression_share or 0
        bud_v = r.metrics.search_budget_lost_impression_share or 0
        rank_v = r.metrics.search_rank_lost_impression_share or 0
        if imp > 0:
            agg[w]["is_w"] += is_v * imp
            agg[w]["budget_w"] += bud_v * imp
            agg[w]["rank_w"] += rank_v * imp
            agg[w]["imp"] += imp
        agg[w]["clicks"] += r.metrics.clicks
        agg[w]["cost"] += r.metrics.cost_micros / 1_000_000
    return pd.DataFrame([{
        "Week": w[:10],
        "Spend": round(d["cost"]),
        "Clicks": d["clicks"],
        "IS": round(weighted_is(d), 1),
        "Lost_Budget": round(d["budget_w"] / d["imp"] * 100 if d["imp"] > 0 else 0, 1),
        "Lost_Rank": round(d["rank_w"] / d["imp"] * 100 if d["imp"] > 0 else 0, 1),
    } for w, d in sorted(agg.items())])


@st.cache_data(ttl=3600)
def fetch_daily_tmp(start_date, end_date):
    """TMP daily: IS, spend, clicks."""
    rows = run_query(f"""
        SELECT segments.date, metrics.search_impression_share,
               metrics.impressions, metrics.clicks, metrics.cost_micros
        FROM keyword_view
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
        AND campaign.name LIKE '%S:brand-trademark%'
        AND campaign.name NOT LIKE '%trello%'
        AND ad_group.name LIKE '%Brand-Trademark%'
        AND ad_group_criterion.keyword.match_type = 'EXACT'
        AND metrics.impressions > 0
        ORDER BY segments.date
    """)
    agg = defaultdict(lambda: {"is_w": 0.0, "imp": 0, "clicks": 0, "cost": 0.0})
    for r in rows:
        d = r.segments.date
        imp = r.metrics.impressions
        is_v = r.metrics.search_impression_share or 0
        if is_v > 0 and imp > 0:
            agg[d]["is_w"] += is_v * imp
            agg[d]["imp"] += imp
        agg[d]["clicks"] += r.metrics.clicks
        agg[d]["cost"] += r.metrics.cost_micros / 1_000_000
    return pd.DataFrame([{
        "Date": dt,
        "Spend": round(d["cost"]),
        "Clicks": d["clicks"],
        "IS": round(weighted_is(d), 1),
    } for dt, d in sorted(agg.items())])


@st.cache_data(ttl=3600)
def fetch_is_by_geo(start_date, end_date):
    """TMP IS broken out by geo (parsed from campaign name G:xx)."""
    rows = run_query(f"""
        SELECT segments.month, campaign.name,
               metrics.search_impression_share, metrics.impressions,
               metrics.cost_micros, metrics.clicks
        FROM keyword_view
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
        AND campaign.name LIKE '%S:brand-trademark%'
        AND campaign.name NOT LIKE '%trello%'
        AND ad_group.name LIKE '%Brand-Trademark%'
        AND ad_group_criterion.keyword.match_type = 'EXACT'
        AND metrics.impressions > 0
        ORDER BY segments.month
    """)
    import re
    agg = defaultdict(lambda: {"is_w": 0.0, "imp": 0, "cost": 0.0, "clicks": 0})
    for r in rows:
        m = r.segments.month[:7]
        name = r.campaign.name
        match = re.search(r"G:([a-z]+)", name)
        geo = match.group(1) if match else "unknown"
        imp = r.metrics.impressions
        is_v = r.metrics.search_impression_share or 0
        key = (m, geo)
        if is_v > 0 and imp > 0:
            agg[key]["is_w"] += is_v * imp
            agg[key]["imp"] += imp
        agg[key]["cost"] += r.metrics.cost_micros / 1_000_000
        agg[key]["clicks"] += r.metrics.clicks
    return pd.DataFrame([{
        "Month": k[0],
        "Geo": k[1].upper(),
        "IS": round(weighted_is(d), 1),
        "Spend": round(d["cost"]),
        "Clicks": d["clicks"],
    } for k, d in sorted(agg.items())])


@st.cache_data(ttl=3600)
def fetch_yoy_is(fy26_start, fy26_end, fy27_start, fy27_end):
    """YoY IS + Spend: FY26 vs FY27 monthly."""
    def fetch_year(start, end, label):
        rows = run_query(f"""
            SELECT segments.month, metrics.search_impression_share,
                   metrics.impressions, metrics.cost_micros, metrics.clicks
            FROM keyword_view
            WHERE segments.date BETWEEN '{start}' AND '{end}'
            AND campaign.name LIKE '%S:brand-trademark%'
            AND campaign.name NOT LIKE '%trello%'
            AND ad_group.name LIKE '%Brand-Trademark%'
            AND ad_group_criterion.keyword.match_type = 'EXACT'
            AND metrics.impressions > 0
            ORDER BY segments.month
        """)
        agg = defaultdict(lambda: {"is_w": 0.0, "imp": 0, "cost": 0.0, "clicks": 0})
        for r in rows:
            m = r.segments.month[:7]
            imp = r.metrics.impressions
            is_v = r.metrics.search_impression_share or 0
            if is_v > 0 and imp > 0:
                agg[m]["is_w"] += is_v * imp
                agg[m]["imp"] += imp
            agg[m]["cost"] += r.metrics.cost_micros / 1_000_000
            agg[m]["clicks"] += r.metrics.clicks
        df = pd.DataFrame([{
            "Month": m,
            "IS": round(weighted_is(d), 1),
            "Spend": round(d["cost"]),
            "Clicks": d["clicks"],
            "Year": label,
        } for m, d in sorted(agg.items())])
        # Normalize month to MMM for display
        df["MonthLabel"] = pd.to_datetime(df["Month"]).dt.strftime("%b")
        return df
    fy26 = fetch_year(fy26_start, fy26_end, "FY26")
    fy27 = fetch_year(fy27_start, fy27_end, "FY27")
    return pd.concat([fy26, fy27], ignore_index=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("📊 Jira BPS")
st.sidebar.markdown("Google Ads API | All geos | Excl. Trello")

view = st.sidebar.radio("View", [
    "1. MoM TMP Overview",
    "2. WoW Daily TMP",
    "3. nonTMP Pulse",
    "4. IS by Geo",
    "5. YoY Comparison",
])

today = datetime.today()

if view == "1. MoM TMP Overview":
    start = st.sidebar.date_input("Start", value=today - timedelta(days=395))
    end = st.sidebar.date_input("End", value=today)

elif view == "2. WoW Daily TMP":
    start = st.sidebar.date_input("Start", value=today - timedelta(days=28))
    end = st.sidebar.date_input("End", value=today)

elif view == "3. nonTMP Pulse":
    start = st.sidebar.date_input("Start", value=today - timedelta(days=28))
    end = st.sidebar.date_input("End", value=today)

elif view == "4. IS by Geo":
    start = st.sidebar.date_input("Start", value=today - timedelta(days=395))
    end = st.sidebar.date_input("End", value=today)
    geo_options = ["US", "UK", "AU", "IN", "ROW", "ES"]
    selected_geos = st.sidebar.multiselect("Geos", geo_options, default=geo_options)

elif view == "5. YoY Comparison":
    st.sidebar.markdown("**FY26 range:**")
    fy26_start = st.sidebar.date_input("FY26 Start", value=datetime(2025, 6, 1))
    fy26_end = st.sidebar.date_input("FY26 End", value=datetime(2026, 1, 31))
    st.sidebar.markdown("**FY27 range:**")
    fy27_start = st.sidebar.date_input("FY27 Start", value=datetime(2026, 2, 1))
    fy27_end = st.sidebar.date_input("FY27 End", value=today)

st.sidebar.markdown("---")
st.sidebar.caption("Data refreshes every 60 min. IS = Search Impression Share. BD1-6 has 7-day maturity lag.")

# ── Main ──────────────────────────────────────────────────────────────────────
st.title("📊 Jira BPS: TMP vs nonTMP Dashboard")
st.caption(f"As of {today.strftime('%b %d, %Y')} | Google Ads API | All geos | Excl. Trello")

# ────────────────────────────────────────────────────────────────────────────
# VIEW 1: MoM TMP Overview
# ────────────────────────────────────────────────────────────────────────────
if view == "1. MoM TMP Overview":
    st.subheader("MoM TMP (Brand-Trademark) Overview")
    st.caption("Exact match keywords | All geos | Excl. Trello")

    with st.spinner("Pulling TMP monthly data..."):
        df = fetch_tmp_monthly(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    if df.empty:
        st.warning("No data for this range.")
        st.stop()

    # KPI cards
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("IS (latest)", f"{latest['IS']}%",
              f"{latest['IS'] - prev['IS']:+.1f}pp MoM")
    c2.metric("Spend (latest)", f"${latest['Spend']:,}",
              f"{((latest['Spend'] - prev['Spend']) / prev['Spend'] * 100):+.0f}% MoM")
    c3.metric("Clicks (latest)", f"{latest['Clicks']:,}",
              f"{((latest['Clicks'] - prev['Clicks']) / prev['Clicks'] * 100):+.0f}% MoM")
    c4.metric("Months of data", len(df))

    # IS trend
    fig_is = px.line(df, x="Month", y="IS", markers=True,
                     title="Monthly Search IS (%)",
                     color_discrete_sequence=[COLORS["TMP"]])
    fig_is.update_layout(yaxis_range=[0, 100], hovermode="x unified")
    fig_is.add_hline(y=88, line_dash="dot", line_color="gray",
                     annotation_text="FY26 avg (88%)", annotation_position="top left")
    st.plotly_chart(fig_is, use_container_width=True)

    # Spend bar
    fig_spend = px.bar(df, x="Month", y="Spend",
                       title="Monthly Spend ($)",
                       color_discrete_sequence=[COLORS["TMP"]])
    fig_spend.update_layout(hovermode="x unified")
    st.plotly_chart(fig_spend, use_container_width=True)

    # Clicks line
    fig_clicks = px.line(df, x="Month", y="Clicks", markers=True,
                         title="Monthly Clicks",
                         color_discrete_sequence=[COLORS["TMP"]])
    fig_clicks.update_layout(hovermode="x unified")
    st.plotly_chart(fig_clicks, use_container_width=True)

    # Socrates BD1-6 + Biz Signups
    st.markdown("---")
    st.markdown("#### BD1-6 and Biz Signups (Databricks)")
    with st.spinner("Pulling BD1-6 and Biz Signups from Databricks..."):
        sdf, serr = fetch_socrates_monthly(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    if serr:
        st.warning(f"Databricks: {serr}")
    elif not sdf.empty:
        sc1, sc2, sc3, sc4 = st.columns(4)
        sl = sdf.iloc[-1]
        sp = sdf.iloc[-2] if len(sdf) > 1 else sl
        sc1.metric("BD1-6 (latest)", f"{sl['BD1_6']:,}",
                   f"{((sl['BD1_6'] - sp['BD1_6']) / max(sp['BD1_6'], 1) * 100):+.0f}% MoM")
        sc2.metric("Biz Signups (latest)", f"{sl['BizSignups']:,}",
                   f"{((sl['BizSignups'] - sp['BizSignups']) / max(sp['BizSignups'], 1) * 100):+.0f}% MoM")
        sc3.metric("Signups (latest)", f"{sl['Signups']:,}",
                   f"{((sl['Signups'] - sp['Signups']) / max(sp['Signups'], 1) * 100):+.0f}% MoM")
        sc4.metric("CPBD1-6 (latest)", f"${sl['CPBD1_6']:,}",
                   f"{((sl['CPBD1_6'] - sp['CPBD1_6']) / max(sp['CPBD1_6'], 1) * 100):+.0f}% MoM")

        fig_bd = px.bar(sdf, x="Month", y="BD1_6",
                        title="Monthly BD1-6",
                        color_discrete_sequence=[COLORS["TMP"]])
        fig_bd.update_layout(hovermode="x unified")
        st.plotly_chart(fig_bd, use_container_width=True)

        fig_suf = go.Figure()
        fig_suf.add_trace(go.Bar(x=sdf["Month"], y=sdf["Signups"],
                                 name="Total Signups", marker_color=COLORS["nonTMP"]))
        fig_suf.add_trace(go.Bar(x=sdf["Month"], y=sdf["BizSignups"],
                                 name="Biz Signups", marker_color=COLORS["TMP"]))
        fig_suf.update_layout(barmode="overlay", title="Monthly Signups vs Biz Signups",
                               hovermode="x unified")
        st.plotly_chart(fig_suf, use_container_width=True)

        fig_cp = px.line(sdf, x="Month", y="CPBD1_6", markers=True,
                         title="Monthly CPBD1-6 ($)",
                         color_discrete_sequence=[COLORS["TMP"]])
        fig_cp.update_layout(hovermode="x unified")
        st.plotly_chart(fig_cp, use_container_width=True)

        with st.expander("BD1-6 Raw data"):
            st.dataframe(sdf, use_container_width=True)

    with st.expander("Google Ads Raw data"):
        st.dataframe(df, use_container_width=True)


# ────────────────────────────────────────────────────────────────────────────
# VIEW 2: WoW Daily TMP
# ────────────────────────────────────────────────────────────────────────────
elif view == "2. WoW Daily TMP":
    st.subheader("WoW Daily TMP (Brand-Trademark)")
    st.caption("Exact match keywords | All geos | BD1-6 has 7-day maturity lag")

    with st.spinner("Pulling daily TMP data..."):
        df = fetch_daily_tmp(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    if df.empty:
        st.warning("No data for this range.")
        st.stop()

    # WoW metrics
    if len(df) >= 14:
        mid = len(df) // 2
        prior = df.iloc[:mid]
        curr = df.iloc[mid:]
        c1, c2, c3 = st.columns(3)
        c1.metric("IS WoW", f"{curr['IS'].mean():.1f}%",
                  f"{curr['IS'].mean() - prior['IS'].mean():+.1f}pp")
        c2.metric("Spend WoW", f"${curr['Spend'].sum():,}",
                  f"{((curr['Spend'].sum() - prior['Spend'].sum()) / prior['Spend'].sum() * 100):+.0f}%")
        c3.metric("Clicks WoW", f"{curr['Clicks'].sum():,}",
                  f"{((curr['Clicks'].sum() - prior['Clicks'].sum()) / prior['Clicks'].sum() * 100):+.0f}%")

    st.info("BD1-6 has a 7-day maturity lag. Last 7 days of conversion data are understated. Use Biz Signups as directional signal.")

    fig_is = px.line(df, x="Date", y="IS", markers=True,
                     title="Daily Search IS (%)",
                     color_discrete_sequence=[COLORS["TMP"]])
    fig_is.update_layout(yaxis_range=[0, 100], hovermode="x unified")
    st.plotly_chart(fig_is, use_container_width=True)

    fig_spend = px.bar(df, x="Date", y="Spend",
                       title="Daily Spend ($)",
                       color_discrete_sequence=[COLORS["TMP"]])
    fig_spend.update_layout(hovermode="x unified")
    st.plotly_chart(fig_spend, use_container_width=True)

    fig_clicks = px.line(df, x="Date", y="Clicks", markers=True,
                         title="Daily Clicks",
                         color_discrete_sequence=[COLORS["TMP"]])
    fig_clicks.update_layout(hovermode="x unified")
    st.plotly_chart(fig_clicks, use_container_width=True)

    # Socrates daily BD1-6 + Biz Signups
    st.markdown("---")
    st.markdown("#### BD1-6 and Biz Signups (Databricks) - 7 day maturity lag applies")
    with st.spinner("Pulling daily BD1-6 from Databricks..."):
        sdf_d, serr_d = fetch_socrates_daily(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    if serr_d:
        st.warning(f"Databricks: {serr_d}")
    elif not sdf_d.empty:
        # WoW cards
        if len(sdf_d) >= 14:
            mid = len(sdf_d) // 2
            prior_s = sdf_d.iloc[:mid]
            curr_s = sdf_d.iloc[mid:]
            sd1, sd2, sd3 = st.columns(3)
            sd1.metric("BD1-6 WoW", f"{curr_s['BD1_6'].sum():,}",
                       f"{((curr_s['BD1_6'].sum() - prior_s['BD1_6'].sum()) / max(prior_s['BD1_6'].sum(), 1) * 100):+.0f}% (immature)")
            sd2.metric("Biz Signups WoW", f"{curr_s['BizSignups'].sum():,}",
                       f"{((curr_s['BizSignups'].sum() - prior_s['BizSignups'].sum()) / max(prior_s['BizSignups'].sum(), 1) * 100):+.0f}%")
            sd3.metric("Total Signups WoW", f"{curr_s['Signups'].sum():,}",
                       f"{((curr_s['Signups'].sum() - prior_s['Signups'].sum()) / max(prior_s['Signups'].sum(), 1) * 100):+.0f}%")

        fig_bd_d = px.bar(sdf_d, x="Date", y="BD1_6",
                          title="Daily BD1-6 (last 7 days understated due to maturity lag)",
                          color_discrete_sequence=[COLORS["TMP"]])
        fig_bd_d.update_layout(hovermode="x unified")
        st.plotly_chart(fig_bd_d, use_container_width=True)

        fig_suf_d = go.Figure()
        fig_suf_d.add_trace(go.Bar(x=sdf_d["Date"], y=sdf_d["Signups"],
                                   name="Total Signups", marker_color=COLORS["nonTMP"]))
        fig_suf_d.add_trace(go.Bar(x=sdf_d["Date"], y=sdf_d["BizSignups"],
                                   name="Biz Signups", marker_color=COLORS["TMP"]))
        fig_suf_d.update_layout(barmode="overlay", title="Daily Signups vs Biz Signups",
                                 hovermode="x unified")
        st.plotly_chart(fig_suf_d, use_container_width=True)

        with st.expander("BD1-6 Raw data"):
            st.dataframe(sdf_d, use_container_width=True)

    with st.expander("Google Ads Raw data"):
        st.dataframe(df, use_container_width=True)


# ────────────────────────────────────────────────────────────────────────────
# VIEW 3: nonTMP Pulse
# ────────────────────────────────────────────────────────────────────────────
elif view == "3. nonTMP Pulse":
    st.subheader("nonTMP (Brand-General) Pulse")
    st.caption("All match types | All geos | Excl. Trello | Campaign level for Lost IS")
    st.markdown("""
    **Lost IS explained:** IS + Lost IS (Budget) + Lost IS (Rank) = 100%.
    Budget loss = missed auctions because daily budget ran out (fix: more spend).
    Rank loss = missed auctions because a competitor outbid us (fix: higher bids or better quality score).
    """)

    with st.spinner("Pulling nonTMP pulse data..."):
        df = fetch_nontmp_weekly(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    if df.empty:
        st.warning("No data for this range.")
        st.stop()

    # KPI row
    if len(df) >= 2:
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("IS (latest week)", f"{curr['IS']}%",
                  f"{curr['IS'] - prev['IS']:+.1f}pp WoW")
        c2.metric("Spend (latest week)", f"${curr['Spend']:,}",
                  f"{((curr['Spend'] - prev['Spend']) / prev['Spend'] * 100):+.0f}%")
        c3.metric("Clicks (latest week)", f"{curr['Clicks']:,}",
                  f"{((curr['Clicks'] - prev['Clicks']) / prev['Clicks'] * 100):+.0f}%")
        c4.metric("Lost (Budget)", f"{curr['Lost_Budget']}%",
                  f"{curr['Lost_Budget'] - prev['Lost_Budget']:+.1f}pp")
        c5.metric("Lost (Rank)", f"{curr['Lost_Rank']}%",
                  f"{curr['Lost_Rank'] - prev['Lost_Rank']:+.1f}pp")

    # IS trend
    fig_is = px.line(df, x="Week", y="IS", markers=True,
                     title="Weekly Search IS (%) - nonTMP",
                     color_discrete_sequence=[COLORS["nonTMP"]])
    fig_is.update_layout(yaxis_range=[0, 100], hovermode="x unified")
    st.plotly_chart(fig_is, use_container_width=True)

    # Lost IS stacked bar
    fig_lost = go.Figure()
    fig_lost.add_trace(go.Bar(
        x=df["Week"], y=df["Lost_Budget"],
        name="Lost IS (Budget)", marker_color="#F4A261"))
    fig_lost.add_trace(go.Bar(
        x=df["Week"], y=df["Lost_Rank"],
        name="Lost IS (Rank)", marker_color="#E76F51"))
    fig_lost.add_trace(go.Bar(
        x=df["Week"], y=df["IS"],
        name="IS Won", marker_color=COLORS["nonTMP"]))
    fig_lost.update_layout(
        barmode="stack", title="IS Breakdown: Won vs Lost (Budget vs Rank)",
        yaxis_range=[0, 100], hovermode="x unified",
        yaxis_title="% of eligible impressions")
    st.plotly_chart(fig_lost, use_container_width=True)

    # Spend bar
    fig_spend = px.bar(df, x="Week", y="Spend",
                       title="Weekly Spend ($) - nonTMP",
                       color_discrete_sequence=[COLORS["nonTMP"]])
    fig_spend.update_layout(hovermode="x unified")
    st.plotly_chart(fig_spend, use_container_width=True)

    with st.expander("Raw data"):
        st.dataframe(df, use_container_width=True)


# ────────────────────────────────────────────────────────────────────────────
# VIEW 4: IS by Geo
# ────────────────────────────────────────────────────────────────────────────
elif view == "4. IS by Geo":
    st.subheader("TMP IS by Geo")
    st.caption("Exact match keywords | Brand-Trademark ad group | Excl. Trello")

    with st.spinner("Pulling geo IS data..."):
        df = fetch_is_by_geo(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    if df.empty:
        st.warning("No data for this range.")
        st.stop()

    # Filter to selected geos
    df_filtered = df[df["Geo"].isin([g.upper() for g in selected_geos])]

    # IS by geo line chart
    fig_geo = px.line(df_filtered, x="Month", y="IS", color="Geo",
                      markers=True,
                      title="Monthly IS (%) by Geo - TMP Brand-Trademark",
                      color_discrete_map={g.upper(): c for g, c in GEO_COLORS.items()})
    fig_geo.update_layout(yaxis_range=[0, 100], hovermode="x unified")
    st.plotly_chart(fig_geo, use_container_width=True)

    # Spend by geo
    fig_spend_geo = px.bar(df_filtered, x="Month", y="Spend", color="Geo",
                           barmode="group",
                           title="Monthly Spend ($) by Geo",
                           color_discrete_map={g.upper(): c for g, c in GEO_COLORS.items()})
    fig_spend_geo.update_layout(hovermode="x unified")
    st.plotly_chart(fig_spend_geo, use_container_width=True)

    # Latest IS by geo heatmap-style table
    latest_month = df_filtered["Month"].max()
    latest_geo = df_filtered[df_filtered["Month"] == latest_month][["Geo", "IS", "Spend", "Clicks"]]
    st.markdown(f"**Latest month ({latest_month}) snapshot:**")
    st.dataframe(latest_geo.sort_values("IS", ascending=False), use_container_width=True)

    with st.expander("Full raw data"):
        st.dataframe(df_filtered, use_container_width=True)


# ────────────────────────────────────────────────────────────────────────────
# VIEW 5: YoY Comparison
# ────────────────────────────────────────────────────────────────────────────
elif view == "5. YoY Comparison":
    st.subheader("YoY IS + Spend Comparison: FY26 vs FY27")
    st.caption("Exact match keywords | All geos | Brand-Trademark ad group | Excl. Trello")
    st.info("Context: From Feb 2026, Brand-General was consolidated under Brand-Trademark as an ad group (BPS consolidation). IS is at exact match keyword level throughout for consistency.")

    with st.spinner("Pulling YoY data..."):
        df = fetch_yoy_is(
            fy26_start.strftime("%Y-%m-%d"), fy26_end.strftime("%Y-%m-%d"),
            fy27_start.strftime("%Y-%m-%d"), fy27_end.strftime("%Y-%m-%d"),
        )

    if df.empty:
        st.warning("No data for this range.")
        st.stop()

    # IS comparison line chart
    fig_is = px.line(df, x="MonthLabel", y="IS", color="Year",
                     markers=True,
                     title="IS (%) YoY: FY26 vs FY27",
                     color_discrete_map={"FY26": COLORS["FY26"], "FY27": COLORS["FY27"]},
                     category_orders={"MonthLabel": ["Jun","Jul","Aug","Sep","Oct","Nov","Dec","Jan","Feb","Mar","Apr","May"]})
    fig_is.update_layout(yaxis_range=[0, 100], hovermode="x unified")
    st.plotly_chart(fig_is, use_container_width=True)

    # Spend comparison bar chart
    fig_spend = px.bar(df, x="MonthLabel", y="Spend", color="Year",
                       barmode="group",
                       title="Spend ($) YoY: FY26 vs FY27",
                       color_discrete_map={"FY26": COLORS["FY26"], "FY27": COLORS["FY27"]},
                       category_orders={"MonthLabel": ["Jun","Jul","Aug","Sep","Oct","Nov","Dec","Jan","Feb","Mar","Apr","May"]})
    fig_spend.update_layout(hovermode="x unified")
    st.plotly_chart(fig_spend, use_container_width=True)

    # YoY IS gap table
    fy26_df = df[df["Year"] == "FY26"][["MonthLabel", "IS", "Spend"]].rename(
        columns={"IS": "FY26 IS", "Spend": "FY26 Spend"})
    fy27_df = df[df["Year"] == "FY27"][["MonthLabel", "IS", "Spend"]].rename(
        columns={"IS": "FY27 IS", "Spend": "FY27 Spend"})
    merged = fy26_df.merge(fy27_df, on="MonthLabel", how="outer")
    merged["IS Gap (pp)"] = (merged["FY27 IS"] - merged["FY26 IS"]).round(1)
    merged["Spend Change"] = (
        (merged["FY27 Spend"] - merged["FY26 Spend"]) / merged["FY26 Spend"] * 100
    ).round(0).astype(str) + "%"
    st.markdown("**YoY Gap Summary:**")
    st.dataframe(merged, use_container_width=True)

    with st.expander("Full raw data"):
        st.dataframe(df, use_container_width=True)
