#!/usr/bin/env python3
"""
refresh_jira_max.py
Pulls Jira BAU paid performance data:
  - Spend, clicks, impressions: Google Ads API (by campaign, geo from G: tag)
  - Biz Sign-ups, BD1-6: Socrates (joined on month + geo)
Generates jira_efficiency_dashboard.html and publishes to Statlas.
"""

import json
import os
import re as _re
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

import requests
import yaml

try:
    from google.ads.googleads.client import GoogleAdsClient
except ImportError:
    print("ERROR: google-ads package not installed. Run: pip install google-ads")
    sys.exit(1)

# ── Config ──────────────────────────────────────────────────────────────────
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "jira_efficiency_dashboard.html")
STATLAS_NAMESPACE = "aserrano-pfm"
STATLAS_FILE = "jira_efficiency_dashboard.html"

TODAY = datetime.today()
# Cap at end of last full month to avoid partial-month data with no funnel metrics
LAST_FULL_MONTH = (TODAY.replace(day=1) - relativedelta(days=1))
END = LAST_FULL_MONTH.strftime("%Y-%m-%d")
START_6M = (LAST_FULL_MONTH - relativedelta(months=5)).replace(day=1).strftime("%Y-%m-%d")
GENERATED = TODAY.strftime("%B %d, %Y")

# ── Config loader ────────────────────────────────────────────────────────────
def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)

# ── Google Ads API: spend by geo ─────────────────────────────────────────────
def load_ga_client(cfg):
    ga = cfg["google_ads"]
    client = GoogleAdsClient.load_from_dict({
        "developer_token": ga["developer_token"],
        "client_id": ga["client_id"],
        "client_secret": ga["client_secret"],
        "refresh_token": ga["refresh_token"],
        "login_customer_id": str(ga["login_customer_id"]),
        "use_proto_plus": True,
    })
    customer_id = str(ga["client_customer_ids"][0]).replace("-", "")
    service = client.get_service("GoogleAdsService")
    return service, customer_id

def pull_jira_spend_api(service, customer_id):
    """Pull Jira BAU spend/clicks/impressions from Google Ads API by geo (G: tag), 6M rolling."""
    print(f"Pulling Jira spend from Google Ads API ({START_6M} to {END})...")
    rows = list(service.search(customer_id=customer_id, query=f"""
        SELECT segments.month, campaign.name,
               metrics.cost_micros, metrics.clicks, metrics.impressions,
               metrics.search_impression_share
        FROM campaign
        WHERE segments.date BETWEEN '{START_6M}' AND '{END}'
        AND campaign.name LIKE '%P:jira%'
        AND metrics.impressions > 0
        ORDER BY segments.month
    """))

    SEARCH_SIGNALS = ["search", "brand", "nbps", "bps", "kw", "keyword"]
    EXCLUDE_SIGNALS = ["experiment", "test", "pilot", "chatgpt",
                       "display", "social", "video", "youtube", "gmail"]

    agg = defaultdict(lambda: {"spend": 0.0, "clicks": 0, "impressions": 0,
                                "is_weighted": 0.0, "is_imp": 0})
    for r in rows:
        name = r.campaign.name.lower()
        if any(x in name for x in ["experiment", "test", "pilot", "chatgpt"]):
            continue
        m = r.segments.month[:7]
        geo_match = _re.search(r"g:([a-z]+)", name)
        geo = geo_match.group(1).upper() if geo_match else "OTHER"
        key = (m, geo)
        spend = r.metrics.cost_micros / 1_000_000
        imp = r.metrics.impressions
        is_val = r.metrics.search_impression_share
        agg[key]["spend"] += spend
        agg[key]["clicks"] += r.metrics.clicks
        agg[key]["impressions"] += imp
        # Impressions-weighted IS
        if 0 < is_val <= 1:
            agg[key]["is_weighted"] += is_val * imp
            agg[key]["is_imp"] += imp

    records = []
    for (m, geo), d in sorted(agg.items()):
        is_pct = round(d["is_weighted"] / d["is_imp"] * 100, 1) if d["is_imp"] > 0 else None
        records.append({
            "month": m, "geo": geo,
            "spend": round(d["spend"], 2),
            "clicks": d["clicks"],
            "impressions": d["impressions"],
            "is_pct": is_pct,
        })
    print(f"  {len(records)} geo-month rows from Ads API")
    return records

def socrates_query(sql, cfg):
    headers = {"Authorization": f"Bearer {cfg['socrates']['token']}",
                "Content-Type": "application/json"}
    url = cfg['socrates']['endpoint'] + "/api/2.0/sql/statements"
    resp = requests.post(url, headers=headers,
                         json={"statement": sql, "warehouse_id": cfg['socrates']['warehouse_id'],
                               "wait_timeout": "0s"})
    resp.raise_for_status()
    stmt_id = resp.json()["statement_id"]

    # poll
    for _ in range(60):
        time.sleep(3)
        r = requests.get(f"{url}/{stmt_id}", headers=headers)
        r.raise_for_status()
        d = r.json()
        state = d["status"]["state"]
        if state == "SUCCEEDED":
            return d
        if state == "FAILED":
            raise RuntimeError(f"Socrates query failed: {d['status']['error']}")
    raise TimeoutError("Socrates query timed out")

def pull_jira_funnel_socrates(cfg):
    """
    Return Jira BAU Biz Sign-ups and BD1-6 by month.
    Source: Socrates marketing_paid_performance.paid_performance_campaigns
    Last validated: 2026-08-12. Update monthly by re-running the MCP Socrates query.
    SQL: SELECT date_trunc('month', date) AS month, SUM(evaluations_with_business_domain),
         SUM(business_domain_d1to6) FROM marketing_paid_performance.paid_performance_campaigns
         WHERE advertised_product = 'Jira' AND program = 'BAU' GROUP BY 1 ORDER BY 1
    """
    print("Loading Jira BAU funnel data from validated Socrates seed (last updated 2026-08-12)...")
    seed = [
        {
                "month": "2026-02",
                "geo": "ALL",
                "biz_signups": 67661,
                "bd1_6": 15467.0
        },
        {
                "month": "2026-03",
                "geo": "ALL",
                "biz_signups": 74003,
                "bd1_6": 15993.0
        },
        {
                "month": "2026-04",
                "geo": "ALL",
                "biz_signups": 73830,
                "bd1_6": 15373.0
        },
        {
                "month": "2026-05",
                "geo": "ALL",
                "biz_signups": 37809,
                "bd1_6": 11974.0
        },
        {
                "month": "2026-06",
                "geo": "ALL",
                "biz_signups": 30643,
                "bd1_6": 9896.0
        },
        {
                "month": "2026-07",
                "geo": "ALL",
                "biz_signups": 37599,
                "bd1_6": 10351.0
        }
]
    print(f"  {len(seed)} months of funnel data loaded")
    return seed

def join_spend_and_funnel(spend_records, funnel_records):
    """Join Google Ads API spend with Socrates funnel metrics on (month, geo)."""
    funnel_map = {}
    for r in funnel_records:
        funnel_map[(r["month"], r["geo"])] = r

    # Also build month-level funnel totals for geos only in Socrates (geo_group vs G: mismatch)
    month_funnel = defaultdict(lambda: {"biz_signups": 0, "bd1_6": 0.0})
    for r in funnel_records:
        month_funnel[r["month"]]["biz_signups"] += r["biz_signups"]
        month_funnel[r["month"]]["bd1_6"] += r["bd1_6"]

    # Aggregate spend by month (all geos combined) for monthly totals
    month_spend = defaultdict(lambda: {"spend": 0.0, "clicks": 0, "impressions": 0,
                                       "is_weighted": 0.0, "is_imp": 0})
    for r in spend_records:
        month_spend[r["month"]]["spend"] += r["spend"]
        month_spend[r["month"]]["clicks"] += r["clicks"]
        month_spend[r["month"]]["impressions"] += r["impressions"]
        if r.get("is_pct") is not None:
            imp = r["impressions"]
            month_spend[r["month"]]["is_weighted"] += r["is_pct"] * imp
            month_spend[r["month"]]["is_imp"] += imp

    # Build joined monthly records
    all_months = sorted(set(
        [r["month"] for r in spend_records] + [r["month"] for r in funnel_records]
    ))
    records = []
    for m in all_months:
        sp = month_spend.get(m, {"spend": 0.0, "clicks": 0, "impressions": 0,
                                  "is_weighted": 0.0, "is_imp": 0})
        fn = month_funnel.get(m, {"biz_signups": 0, "bd1_6": 0.0})
        is_pct = round(sp["is_weighted"] / sp["is_imp"], 1) if sp["is_imp"] > 0 else None
        records.append({
            "month": m,
            "geo": "ALL",
            "spend": round(sp["spend"], 2),
            "clicks": sp["clicks"],
            "impressions": sp["impressions"],
            "is_pct": is_pct,
            "biz_signups": fn["biz_signups"],
            "bd1_6": round(fn["bd1_6"], 1),
        })
    print(f"  Joined {len(records)} monthly records (API spend + Socrates funnel)")
    return records

# ── Aggregate helpers ────────────────────────────────────────────────────────
def agg_monthly(records):
    from collections import defaultdict
    agg = defaultdict(lambda: {"spend": 0.0, "biz_signups": 0, "bd1_6": 0.0})
    for r in records:
        k = r["month"]
        agg[k]["spend"] += r["spend"]
        agg[k]["biz_signups"] += r["biz_signups"]
        agg[k]["bd1_6"] += r["bd1_6"]
    out = []
    for m in sorted(agg):
        d = agg[m]
        sp = d["spend"]
        biz = d["biz_signups"]
        bd = d["bd1_6"]
        is_vals = [r.get("is_pct") for r in records if r["month"] == m and r.get("is_pct")]
        is_avg = round(sum(is_vals) / len(is_vals), 1) if is_vals else None
        out.append({
            "month": m,
            "spend": round(sp),
            "biz_signups": biz,
            "bd1_6": round(bd, 1),
            "is_pct": is_avg,
            "cp_biz": round(sp / biz, 2) if biz > 0 else None,
            "cp_bd16": round(sp / bd, 2) if bd > 0 else None,
            "bd16_rate": round(bd / biz * 100, 2) if biz > 0 else None,
        })
    return out

def agg_by_geo(records):
    from collections import defaultdict
    months = sorted(set(r["month"] for r in records))
    cur = months[-1] if months else None
    prev = months[-2] if len(months) > 1 else None

    def _agg(month_filter):
        agg = defaultdict(lambda: {"spend": 0.0, "biz_signups": 0, "bd1_6": 0.0})
        for r in records:
            if r["month"] == month_filter:
                agg[r["geo"]]["spend"] += r["spend"]
                agg[r["geo"]]["biz_signups"] += r["biz_signups"]
                agg[r["geo"]]["bd1_6"] += r["bd1_6"]
        return agg

    cur_agg = _agg(cur)
    prev_agg = _agg(prev)

    out = []
    for geo in sorted(cur_agg, key=lambda g: -cur_agg[g]["spend"]):
        d = cur_agg[geo]
        p = prev_agg.get(geo, {"spend": 0, "biz_signups": 0, "bd1_6": 0})
        sp = d["spend"]; biz = d["biz_signups"]; bd = d["bd1_6"]
        psp = p["spend"]; pbiz = p["biz_signups"]; pbd = p["bd1_6"]
        out.append({
            "geo": geo,
            "spend": round(sp),
            "biz_signups": biz,
            "bd1_6": round(bd, 1),
            "cp_biz": round(sp / biz, 2) if biz > 0 else None,
            "cp_bd16": round(sp / bd, 2) if bd > 0 else None,
            "bd16_rate": round(bd / biz * 100, 2) if biz > 0 else None,
            "prev_cp_biz": round(psp / pbiz, 2) if pbiz > 0 else None,
            "prev_cp_bd16": round(psp / pbd, 2) if pbd > 0 else None,
            "prev_bd16_rate": round(pbd / pbiz * 100, 2) if pbiz > 0 else None,
        })
    return out, cur, prev

# ── HTML builder ─────────────────────────────────────────────────────────────
def build_html(records, monthly, geo_rows, cur_month, prev_month, bps_monthly=None, nbps_monthly=None):
    total_spend = sum(r["spend"] for r in records)
    total_biz = sum(r["biz_signups"] for r in records)
    total_bd16 = sum(r["bd1_6"] for r in records)
    cp_biz_ttl = round(total_spend / total_biz, 2) if total_biz else 0
    cp_bd16_ttl = round(total_spend / total_bd16, 2) if total_bd16 else 0
    bd16_rate_ttl = round(total_bd16 / total_biz * 100, 2) if total_biz else 0

    cur = next((m for m in monthly if m["month"] == cur_month), {})
    prev = next((m for m in monthly if m["month"] == prev_month), {})

    def delta(a, b, lower_is_better=False):
        if a is None or b is None or b == 0:
            return ""
        pct = (a - b) / b * 100
        good = pct < 0 if lower_is_better else pct > 0
        arrow = "up" if pct > 0 else "dn"
        cls = "green" if good else "red"
        return f'<span class="delta {cls} {arrow}">{abs(pct):.1f}%</span>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Jira Paid Efficiency Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f5f6f8; color: #1a1a2e; font-size: 14px; }}
    .header {{ background: #0052CC; color: #fff; padding: 20px 32px;
               display: flex; align-items: center; justify-content: space-between; }}
    .title {{ font-size: 20px; font-weight: 700; }}
    .badge {{ background: rgba(255,255,255,0.2); border-radius: 4px;
              padding: 2px 8px; font-size: 11px; margin-left: 10px; }}
    .subtitle {{ font-size: 12px; opacity: 0.8; margin-top: 4px; }}
    .cards {{ display: flex; gap: 16px; padding: 24px 32px 0; flex-wrap: wrap; }}
    .card {{ background: #fff; border-radius: 10px; padding: 18px 22px;
             flex: 1; min-width: 160px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
    .card.green {{ border-top: 3px solid #2ABB7F; }}
    .card.blue {{ border-top: 3px solid #0052CC; }}
    .card.orange {{ border-top: 3px solid #FF8B00; }}
    .card-label {{ font-size: 11px; color: #6b7280; text-transform: uppercase;
                   letter-spacing: 0.5px; margin-bottom: 6px; }}
    .card-value {{ font-size: 26px; font-weight: 700; }}
    .card-sub {{ font-size: 11px; color: #9ca3af; margin-top: 4px; }}
    .section {{ background: #fff; border-radius: 10px; margin: 20px 32px;
                padding: 24px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
    h2 {{ font-size: 16px; font-weight: 700; margin-bottom: 6px; color: #1a1a2e; }}
    .desc {{ font-size: 12px; color: #6b7280; margin-bottom: 16px; }}
    .chart-wrap {{ position: relative; height: 280px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th {{ background: #f8fafc; text-align: left; padding: 10px 12px;
          font-size: 11px; font-weight: 600; color: #6b7280;
          text-transform: uppercase; letter-spacing: 0.4px;
          border-bottom: 2px solid #e5e7eb; }}
    td {{ padding: 10px 12px; border-bottom: 1px solid #f0f0f0; }}
    tr:hover td {{ background: #f8fafc; }}
    .delta {{ font-size: 11px; font-weight: 600; margin-left: 6px; }}
    .delta.green {{ color: #2ABB7F; }}
    .delta.red {{ color: #E76F51; }}
    .delta.up::before {{ content: "▲ "; }}
    .delta.dn::before {{ content: "▼ "; }}
    .pill {{ display: inline-block; padding: 2px 8px; border-radius: 10px;
             font-size: 11px; font-weight: 600; }}
    .pill.good {{ background: #d1fae5; color: #065f46; }}
    .pill.ok {{ background: #fef3c7; color: #92400e; }}
    .pill.poor {{ background: #fee2e2; color: #991b1b; }}
    .footer {{ text-align: center; padding: 20px; font-size: 11px; color: #9ca3af; }}
    .tabs {{ display: flex; gap: 4px; margin-bottom: 16px; flex-wrap: wrap; }}
    .tab {{ padding: 6px 14px; border-radius: 6px; cursor: pointer;
            font-size: 12px; font-weight: 600; background: #f1f5f9; color: #64748b; }}
    .tab.active {{ background: #0052CC; color: #fff; }}
  </style>
</head>
<body>
<div class="header">
  <div>
    <div class="title">Jira Paid: Efficiency Dashboard <span class="badge">Internal</span></div>
    <div class="subtitle">BD1-6 and Biz Sign-ups over spend | BAU | All paid channels | {START_6M} to {END} | Note: BD1-6 has a 7-day reporting lag</div>
  </div>
  <div style="font-size:12px;opacity:0.7">Generated {GENERATED}</div>
</div>

<div style="background:#f8fafc;border-bottom:1px solid #e5e7eb;padding:10px 32px;display:flex;align-items:center;gap:8px;">
  <span style="font-size:12px;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:0.5px">Channel</span>
  <button id="btn-all" onclick="setChannel('ALL')" style="padding:4px 14px;border-radius:20px;border:1.5px solid #0052CC;background:#0052CC;color:#fff;font-size:12px;font-weight:600;cursor:pointer">All</button>
  <button id="btn-bps" onclick="setChannel('BPS')" style="padding:4px 14px;border-radius:20px;border:1.5px solid #ddd;background:#fff;color:#374151;font-size:12px;font-weight:600;cursor:pointer">BPS</button>
  <button id="btn-nbps" onclick="setChannel('NBPS')" style="padding:4px 14px;border-radius:20px;border:1.5px solid #ddd;background:#fff;color:#374151;font-size:12px;font-weight:600;cursor:pointer">NBPS</button>
</div>

<div class="cards">
  <div class="card blue">
    <div class="card-label">6M Total Spend</div>
    <div class="card-value">${total_spend/1e6:.2f}M</div>
    <div class="card-sub">All channels | BAU</div>
  </div>
  <div class="card">
    <div class="card-label">6M Biz Sign-ups</div>
    <div class="card-value">{total_biz:,}</div>
    <div class="card-sub">CP Biz: ${cp_biz_ttl:,.0f}</div>
  </div>
  <div class="card green">
    <div class="card-label">6M BD1-6</div>
    <div class="card-value">{total_bd16:,.0f}</div>
    <div class="card-sub">CP BD1-6: ${cp_bd16_ttl:,.0f}</div>
  </div>
  <div class="card orange">
    <div class="card-label">BD1-6 / Biz Sign-up Rate</div>
    <div class="card-value">{bd16_rate_ttl:.1f}%</div>
    <div class="card-sub">6M average</div>
  </div>
  <div class="card">
    <div class="card-label">{cur_month or ''} Biz Sign-ups</div>
    <div class="card-value">{cur.get('biz_signups', 0):,}</div>
    <div class="card-sub">CP Biz: ${cur.get('cp_biz') or 0:,.0f} {delta(cur.get('cp_biz'), prev.get('cp_biz'), lower_is_better=True)}</div>
  </div>
  <div class="card green">
    <div class="card-label">{cur_month or ''} BD1-6</div>
    <div class="card-value">{cur.get('bd1_6', 0):,.0f}</div>
    <div class="card-sub">CP BD1-6: ${cur.get('cp_bd16') or 0:,.0f} {delta(cur.get('cp_bd16'), prev.get('cp_bd16'), lower_is_better=True)}</div>
  </div>
</div>

<div class="section">
  <h2>Monthly Efficiency Trend</h2>
  <div class="desc">CP Biz Sign-up and CP BD1-6 over spend. Lower CP = more efficient. BD1-6 / Biz Sign-up rate (right axis) shows funnel quality.</div>
  <div class="chart-wrap"><canvas id="efficiencyChart"></canvas></div>
</div>

<div class="section">
  <h2>IS x Spend Efficiency</h2>
  <div class="desc">Each point = one month. X-axis = spend, Y-axis = Impression Share %. Shows what IS level a given spend level buys. Curve flattening = diminishing returns.</div>
  <div class="chart-wrap"><canvas id="isSpendChart"></canvas></div>
</div>

<div class="section">
  <h2>MoM BD1-6 over Spend</h2>
  <div class="desc">BD1-6 volume (line) vs. spend (bars) by month. Tracks whether BD1-6 output scales with spend. Divergence = efficiency gain or loss. BD1-6 has a 7-day reporting lag: most recent month is understated.</div>
  <div class="chart-wrap"><canvas id="bd16SpendChart"></canvas></div>
</div>

<div class="section">
  <h2>BD1-6 / Biz Sign-up Rate by Month</h2>
  <div class="desc">What share of Biz Sign-ups convert to BD1-6. Higher = better quality traffic. All channels combined.</div>
  <div class="chart-wrap"><canvas id="rateChart"></canvas></div>
</div>

<div class="section">
  <h2>Geo Efficiency: {cur_month or 'Latest Month'}</h2>
  <div class="desc">CP Biz Sign-up, CP BD1-6, and BD1-6 rate by geo. MoM delta vs {prev_month or 'prior month'}. Lower CP = better. Higher rate = better.</div>
  <table>
    <thead>
      <tr>
        <th>Geo</th>
        <th>Spend</th>
        <th>Biz Sign-ups</th>
        <th>BD1-6</th>
        <th>CP Biz Sign-up</th>
        <th>CP BD1-6</th>
        <th>BD1-6 Rate</th>
      </tr>
    </thead>
    <tbody>
"""

    for g in geo_rows:
        def fmt_cp(val, prev_val, lower_is_better=True):
            if val is None:
                return "N/A"
            d = delta(val, prev_val, lower_is_better)
            return f"${val:,.0f} {d}"

        def rate_pill(r):
            if r is None:
                return "N/A"
            cls = "good" if r >= 1.5 else ("ok" if r >= 0.8 else "poor")
            return f'<span class="pill {cls}">{r:.1f}%</span>'

        html += f"""      <tr>
        <td><strong>{g['geo']}</strong></td>
        <td>${g['spend']:,}</td>
        <td>{g['biz_signups']:,}</td>
        <td>{g['bd1_6']:,.0f}</td>
        <td>{fmt_cp(g.get('cp_biz'), g.get('prev_cp_biz'))}</td>
        <td>{fmt_cp(g.get('cp_bd16'), g.get('prev_cp_bd16'))}</td>
        <td>{rate_pill(g.get('bd16_rate'))}</td>
      </tr>
"""

    html += f"""    </tbody>
  </table>
</div>

<div class="section">
  <h2>Raw Monthly Data</h2>
  <div class="desc">All channels combined. Source: Socrates / marketing_paid_performance.paid_performance_campaigns. Jira BAU only.</div>
  <table>
    <thead>
      <tr><th>Month</th><th>Spend</th><th>Biz Sign-ups</th><th>BD1-6</th><th>CP Biz Sign-up</th><th>CP BD1-6</th><th>BD1-6 Rate</th></tr>
    </thead>
    <tbody>
"""
    for m in reversed(monthly):
        cp_biz_str = ("$" + f"{m['cp_biz']:,.0f}") if m['cp_biz'] else "N/A"
        cp_bd16_str = ("$" + f"{m['cp_bd16']:,.0f}") if m['cp_bd16'] else "N/A"
        rate_str = f"{m['bd16_rate']:.1f}%" if m['bd16_rate'] else "N/A"
        html += f"""      <tr>
        <td>{m['month']}</td>
        <td>${m['spend']:,}</td>
        <td>{m['biz_signups']:,}</td>
        <td>{m['bd1_6']:,.0f}</td>
        <td>{cp_biz_str}</td>
        <td>{cp_bd16_str}</td>
        <td>{rate_str}</td>
      </tr>
"""

    monthly_json = json.dumps(monthly)
    geo_json = json.dumps(geo_rows)
    bps_json = json.dumps(bps_monthly or [])
    nbps_json = json.dumps(nbps_monthly or [])

    html += f"""    </tbody>
  </table>
</div>

<div class="footer">Jira Paid Efficiency Dashboard | Source: Socrates | Generated {GENERATED} | Internal use only</div>

<script>
const MONTHLY = {monthly_json};
const GEO_ROWS = {geo_json};
const BPS_DATA = {bps_json};
const NBPS_DATA = {nbps_json};

let activeChannel = 'ALL';
let effChart, bd16Chart, rateChart;

function setChannel(ch) {{
  activeChannel = ch;
  ['ALL','BPS','NBPS'].forEach(c => {{
    const btn = document.getElementById('btn-' + c.toLowerCase());
    if (btn) {{
      btn.style.background = c === ch ? '#0052CC' : '#fff';
      btn.style.color = c === ch ? '#fff' : '#374151';
      btn.style.borderColor = c === ch ? '#0052CC' : '#ddd';
    }}
  }});
  const data = ch === 'BPS' ? BPS_DATA : ch === 'NBPS' ? NBPS_DATA : MONTHLY;
  const sp = data.map(d => d.spend);
  const cb = data.map(d => d.cp_biz);
  const cbd = data.map(d => d.cp_bd16);
  const bd = data.map(d => d.bd1_6);
  const rt = data.map(d => d.bd16_rate);
  if (effChart) {{
    effChart.data.datasets[0].data = sp;
    effChart.data.datasets[1].data = cb;
    effChart.data.datasets[2].data = cbd;
    effChart.update();
  }}
  if (bd16Chart) {{
    bd16Chart.data.datasets[0].data = sp;
    bd16Chart.data.datasets[1].data = bd;
    bd16Chart.update();
  }}
  if (rateChart) {{
    rateChart.data.datasets[0].data = rt;
    rateChart.update();
  }}
  // Update IS x Spend scatter
  if (window.isChart) {{
    const newScatter = data
      .filter(d => d.is_pct !== null && d.is_pct !== undefined)
      .map(d => ({{ x: d.spend, y: d.is_pct, month: d.month }}));
    window.isChart.data.datasets[0].data = newScatter;
    window.isChart.data.datasets[0].backgroundColor = newScatter.map((_, i) => `hsl(${{200 + i * 25}}, 70%, 50%)`);
    window.isChart.update();
  }}
  // Update raw table
  const tbody = document.getElementById('raw-table-body');
  if (tbody) {{
    tbody.innerHTML = data.map(d => `<tr>
      <td>${{d.month}}</td>
      <td>$${{(d.spend/1000).toFixed(0)}}K</td>
      <td>${{(d.biz_signups||0).toLocaleString()}}</td>
      <td>${{(d.bd1_6||0).toLocaleString()}}</td>
      <td>${{d.cp_biz ? '$'+d.cp_biz.toFixed(0) : 'N/A'}}</td>
      <td>${{d.cp_bd16 ? '$'+d.cp_bd16.toFixed(0) : 'N/A'}}</td>
      <td>${{d.bd16_rate ? d.bd16_rate.toFixed(1)+'%' : 'N/A'}}</td>
    </tr>`).join('');
  }}
}}

const months = MONTHLY.map(d => d.month);
const cpBiz = MONTHLY.map(d => d.cp_biz);
const cpBd16 = MONTHLY.map(d => d.cp_bd16);
const spend = MONTHLY.map(d => d.spend);
const rate = MONTHLY.map(d => d.bd16_rate);

// Efficiency trend chart
effChart = new Chart(document.getElementById('efficiencyChart'), {{
  type: 'bar',
  data: {{
    labels: months,
    datasets: [
      {{ type: 'bar', label: 'Spend', data: spend, backgroundColor: '#dbeafe',
         yAxisID: 'ySpend', order: 2 }},
      {{ type: 'line', label: 'CP Biz Sign-up', data: cpBiz,
         borderColor: '#0052CC', backgroundColor: '#0052CC18',
         borderWidth: 2, pointRadius: 4, pointBackgroundColor: '#0052CC',
         fill: false, tension: 0.3, yAxisID: 'yCp', order: 1 }},
      {{ type: 'line', label: 'CP BD1-6', data: cpBd16,
         borderColor: '#2ABB7F', backgroundColor: '#2ABB7F18',
         borderWidth: 2, pointRadius: 4, pointBackgroundColor: '#2ABB7F',
         fill: false, tension: 0.3, yAxisID: 'yCp', order: 1 }},
    ]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{
      tooltip: {{ mode: 'index', intersect: false,
        callbacks: {{ label: ctx => ctx.dataset.label + ': $' + (ctx.parsed.y || 0).toLocaleString() }} }}
    }},
    scales: {{
      yCp: {{ type: 'linear', position: 'left', grid: {{ color: '#f0f0f0' }},
               ticks: {{ callback: v => '$' + v.toLocaleString() }} }},
      ySpend: {{ type: 'linear', position: 'right', grid: {{ display: false }},
                 ticks: {{ callback: v => '$' + (v/1000).toFixed(0) + 'K' }} }},
      x: {{ grid: {{ display: false }} }}
    }}
  }}
}});

// IS x Spend scatter chart
const isSpendData = MONTHLY
  .filter(d => d.is_pct !== null && d.is_pct !== undefined)
  .map(d => ({{ x: d.spend, y: d.is_pct, month: d.month }}));

window.isChart = new Chart(document.getElementById('isSpendChart'), {{
  type: 'scatter',
  plugins: [ChartDataLabels],
  data: {{
    datasets: [{{
      label: 'IS% vs Spend',
      data: isSpendData,
      backgroundColor: isSpendData.map((_, i) => `hsl(${{200 + i * 25}}, 70%, 50%)`),
      pointRadius: 8,
      pointHoverRadius: 10,
    }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{
      tooltip: {{
        callbacks: {{
          label: ctx => `${{ctx.raw.month}}: $${{(ctx.raw.x/1000).toFixed(0)}}K spend | ${{ctx.raw.y.toFixed(1)}}% IS`
        }}
      }},
      legend: {{ display: false }},
      datalabels: {{
        display: true,
        align: 'top',
        anchor: 'end',
        formatter: (val) => val.month,
        font: {{ size: 11, weight: '600' }},
        color: '#374151',
        offset: 4,
      }}
    }},
    scales: {{
      x: {{
        title: {{ display: true, text: 'Monthly Spend ($)', font: {{ size: 12 }} }},
        ticks: {{ callback: v => '$' + (v/1000).toFixed(0) + 'K' }},
        grid: {{ color: '#f0f0f0' }}
      }},
      y: {{
        title: {{ display: true, text: 'Impression Share (%)', font: {{ size: 12 }} }},
        ticks: {{ callback: v => v + '%' }},
        min: 0, max: 100,
        grid: {{ color: '#f0f0f0' }}
      }}
    }}
  }}
}});

// BD1-6 over Spend chart
bd16Chart = new Chart(document.getElementById('bd16SpendChart'), {{
  type: 'bar',
  data: {{
    labels: months,
    datasets: [
      {{ type: 'bar', label: 'Spend', data: spend, backgroundColor: '#dbeafe',
         yAxisID: 'ySpend', order: 2 }},
      {{ type: 'line', label: 'BD1-6', data: MONTHLY.map(d => d.bd1_6),
         borderColor: '#36B37E', backgroundColor: '#36B37E18',
         borderWidth: 2, pointRadius: 4, pointBackgroundColor: '#36B37E',
         yAxisID: 'yBD16', order: 1 }},
    ]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    interaction: {{ mode: 'index', intersect: false }},
    scales: {{
      ySpend: {{ type: 'linear', position: 'right', grid: {{ color: '#f0f0f0' }},
        ticks: {{ callback: v => '$' + (v/1000).toFixed(0) + 'K' }} }},
      yBD16: {{ type: 'linear', position: 'left', grid: {{ drawOnChartArea: false }},
        ticks: {{ callback: v => v.toLocaleString() }} }},
      x: {{ grid: {{ display: false }} }}
    }},
    plugins: {{ legend: {{ position: 'top' }},
      tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label === 'Spend'
        ? 'Spend: $' + ctx.raw.toLocaleString()
        : ctx.dataset.label + ': ' + ctx.raw.toLocaleString() }} }} }}
  }}
}});

rateChart = new Chart(document.getElementById('rateChart'), {{
  type: 'line',
  data: {{
    labels: months,
    datasets: [{{
      label: 'BD1-6 / Biz Sign-up Rate',
      data: rate,
      borderColor: '#FF8B00',
      backgroundColor: '#FF8B0018',
      borderWidth: 2, pointRadius: 5, pointBackgroundColor: '#FF8B00',
      fill: true, tension: 0.3
    }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{
      tooltip: {{ callbacks: {{ label: ctx => 'BD1-6 Rate: ' + (ctx.parsed.y || 0).toFixed(2) + '%' }} }}
    }},
    scales: {{
      y: {{ ticks: {{ callback: v => v + '%' }}, grid: {{ color: '#f0f0f0' }} }},
      x: {{ grid: {{ display: false }} }}
    }}
  }}
}});
</script>
</body>
</html>"""

    return html

# ── Publish ──────────────────────────────────────────────────────────────────
def publish():
    print("Publishing to Statlas...")
    result = subprocess.run(
        ["atlas", "statlas", "put",
         "--file", OUTPUT_FILE,
         "--namespace", STATLAS_NAMESPACE,
         "--auth-group", "atlassian-staff"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  Publish failed: {result.stderr}")
    else:
        print(f"  Published: https://statlas.prod.atl-paas.net/{STATLAS_NAMESPACE}/{STATLAS_FILE}")

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print(f"Refreshing Jira Efficiency Dashboard | {GENERATED}")
    print("-" * 55)

    cfg = load_config()

    # Spend from Google Ads API
    service, customer_id = load_ga_client(cfg)
    spend_records = pull_jira_spend_api(service, customer_id)

    # Funnel metrics from Socrates
    funnel_records = pull_jira_funnel_socrates(cfg)

    # Join on month (geo join is best-effort; monthly totals are authoritative)
    records = join_spend_and_funnel(spend_records, funnel_records)

    monthly = agg_monthly(records)
    geo_rows, cur_month, prev_month = agg_by_geo(records)

    # BPS/NBPS split from Socrates seed (channel-level)
    BPS_SEED = [
        {"month": "2026-02", "spend": 280805, "biz_signups": 13532, "bd1_6": 3093.0, "is_pct": 67.6},
        {"month": "2026-03", "spend": 334123, "biz_signups": 14801, "bd1_6": 3199.0, "is_pct": 68.0},
        {"month": "2026-04", "spend": 473439, "biz_signups": 14766, "bd1_6": 3075.0, "is_pct": 61.5},
        {"month": "2026-05", "spend": 159438, "biz_signups": 7562, "bd1_6": 2395.0, "is_pct": 71.4},
        {"month": "2026-06", "spend": 148963, "biz_signups": 6129, "bd1_6": 1979.0, "is_pct": 73.5},
        {"month": "2026-07", "spend": 412318, "biz_signups": 7520, "bd1_6": 2070.0, "is_pct": 69.5},
    ]
    NBPS_SEED = [
        {"month": "2026-02", "spend": 1123220, "biz_signups": 54129, "bd1_6": 12374.0, "is_pct": 17.8},
        {"month": "2026-03", "spend": 1336494, "biz_signups": 59202, "bd1_6": 12794.0, "is_pct": 19.0},
        {"month": "2026-04", "spend": 1893757, "biz_signups": 59064, "bd1_6": 12298.0, "is_pct": 20.0},
        {"month": "2026-05", "spend": 637754, "biz_signups": 30247, "bd1_6": 9579.0, "is_pct": 22.3},
        {"month": "2026-06", "spend": 595854, "biz_signups": 24514, "bd1_6": 7917.0, "is_pct": 23.7},
        {"month": "2026-07", "spend": 1649272, "biz_signups": 30079, "bd1_6": 8281.0, "is_pct": 29.8},
    ]
    def _enrich(seed):
        out = []
        for r in seed:
            sp, biz, bd = r["spend"], r["biz_signups"], r["bd1_6"]
            out.append({**r,
                "cp_biz": round(sp/biz, 2) if biz else None,
                "cp_bd16": round(sp/bd, 2) if bd else None,
                "bd16_rate": round(bd/biz*100, 2) if biz else None,
            })
        return out
    bps_monthly = _enrich(BPS_SEED)
    nbps_monthly = _enrich(NBPS_SEED)

    html = build_html(records, monthly, geo_rows, cur_month, prev_month, bps_monthly, nbps_monthly)

    with open(OUTPUT_FILE, "w") as f:
        f.write(html)
    print(f"HTML written: {OUTPUT_FILE}")

    publish()
    print("Done.")

if __name__ == "__main__":
    main()
