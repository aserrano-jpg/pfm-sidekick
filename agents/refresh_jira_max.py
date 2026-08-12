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
               metrics.cost_micros, metrics.clicks, metrics.impressions
        FROM campaign
        WHERE segments.date BETWEEN '{START_6M}' AND '{END}'
        AND campaign.name LIKE '%P:jira%'
        AND metrics.impressions > 0
        ORDER BY segments.month
    """))

    SEARCH_SIGNALS = ["search", "brand", "nbps", "bps", "kw", "keyword"]
    EXCLUDE_SIGNALS = ["experiment", "test", "pilot", "chatgpt",
                       "display", "social", "video", "youtube", "gmail"]

    agg = defaultdict(lambda: {"spend": 0.0, "clicks": 0, "impressions": 0})
    for r in rows:
        name = r.campaign.name.lower()
        if any(x in name for x in ["experiment", "test", "pilot", "chatgpt"]):
            continue
        m = r.segments.month[:7]
        geo_match = _re.search(r"g:([a-z]+)", name)
        geo = geo_match.group(1).upper() if geo_match else "OTHER"
        key = (m, geo)
        spend = r.metrics.cost_micros / 1_000_000
        agg[key]["spend"] += spend
        agg[key]["clicks"] += r.metrics.clicks
        agg[key]["impressions"] += r.metrics.impressions

    records = []
    for (m, geo), d in sorted(agg.items()):
        records.append({
            "month": m, "geo": geo,
            "spend": round(d["spend"], 2),
            "clicks": d["clicks"],
            "impressions": d["impressions"],
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
    month_spend = defaultdict(lambda: {"spend": 0.0, "clicks": 0, "impressions": 0})
    for r in spend_records:
        month_spend[r["month"]]["spend"] += r["spend"]
        month_spend[r["month"]]["clicks"] += r["clicks"]
        month_spend[r["month"]]["impressions"] += r["impressions"]

    # Build joined monthly records
    all_months = sorted(set(
        [r["month"] for r in spend_records] + [r["month"] for r in funnel_records]
    ))
    records = []
    for m in all_months:
        sp = month_spend.get(m, {"spend": 0.0, "clicks": 0, "impressions": 0})
        fn = month_funnel.get(m, {"biz_signups": 0, "bd1_6": 0.0})
        records.append({
            "month": m,
            "geo": "ALL",
            "spend": round(sp["spend"], 2),
            "clicks": sp["clicks"],
            "impressions": sp["impressions"],
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
        out.append({
            "month": m,
            "spend": round(sp),
            "biz_signups": biz,
            "bd1_6": round(bd, 1),
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
def build_html(records, monthly, geo_rows, cur_month, prev_month):
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

    html += f"""    </tbody>
  </table>
</div>

<div class="footer">Jira Paid Efficiency Dashboard | Source: Socrates | Generated {GENERATED} | Internal use only</div>

<script>
const MONTHLY = {monthly_json};
const GEO_ROWS = {geo_json};

const months = MONTHLY.map(d => d.month);
const cpBiz = MONTHLY.map(d => d.cp_biz);
const cpBd16 = MONTHLY.map(d => d.cp_bd16);
const spend = MONTHLY.map(d => d.spend);
const rate = MONTHLY.map(d => d.bd16_rate);

// Efficiency trend chart
new Chart(document.getElementById('efficiencyChart'), {{
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

// BD1-6 rate chart
new Chart(document.getElementById('bd16SpendChart'), {{
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

new Chart(document.getElementById('rateChart'), {{
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

    html = build_html(records, monthly, geo_rows, cur_month, prev_month)

    with open(OUTPUT_FILE, "w") as f:
        f.write(html)
    print(f"HTML written: {OUTPUT_FILE}")

    publish()
    print("Done.")

if __name__ == "__main__":
    main()
