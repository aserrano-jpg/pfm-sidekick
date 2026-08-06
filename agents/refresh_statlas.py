#!/usr/bin/env python3
"""
refresh_statlas.py
Pulls fresh IS data from Google Ads API and republishes the Statlas dashboard.

Usage:
    python3 agents/refresh_statlas.py

Requirements:
    - agents/config.yaml with google_ads credentials
    - atlas CLI with statlas + slauth plugins installed
    - atlassian-staff AD group membership

Published to:
    https://statlas.prod.atl-paas.net/aserrano-pfm/bps_is_dashboard.html
"""

import json
import os
import re
import subprocess
import sys
import yaml
from collections import defaultdict
from datetime import datetime, timedelta

try:
    from google.ads.googleads.client import GoogleAdsClient
except ImportError:
    print("ERROR: google-ads package not installed. Run: pip install google-ads")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
STATLAS_NAMESPACE = "aserrano-pfm"
STATLAS_AUTH_GROUP = "atlassian-staff"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "bps_is_dashboard.html")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")

TODAY = datetime.today()
START_13M = (TODAY - timedelta(days=395)).strftime("%Y-%m-%d")
START_56D = (TODAY - timedelta(days=56)).strftime("%Y-%m-%d")
END = TODAY.strftime("%Y-%m-%d")
GENERATED = TODAY.strftime("%b %d, %Y")


# ── Google Ads client ─────────────────────────────────────────────────────────
def load_ga_client():
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
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


def run_query(service, customer_id, q):
    return list(service.search(customer_id=customer_id, query=q))


# ── Data pulls ────────────────────────────────────────────────────────────────
def pull_tmp_monthly_by_keyword(service, customer_id):
    """TMP monthly IS/spend/clicks broken out by keyword text (exact match)."""
    print("Pulling TMP monthly IS by keyword...")
    rows = run_query(service, customer_id, f"""
        SELECT segments.month,
               ad_group_criterion.keyword.text,
               metrics.search_impression_share,
               metrics.impressions, metrics.clicks, metrics.cost_micros
        FROM keyword_view
        WHERE segments.date BETWEEN '{START_13M}' AND '{END}'
        AND ad_group.name LIKE '%S:brand-trademark%'
        AND ad_group.name NOT LIKE '%trello%'
        AND ad_group_criterion.keyword.match_type = 'EXACT'
        AND metrics.impressions > 0
        ORDER BY segments.month
    """)
    agg = defaultdict(lambda: defaultdict(lambda: {"is_w": 0.0, "imp": 0, "clicks": 0, "cost": 0.0}))
    def normalize_kw(kw):
        kw = kw.lower().strip()
        if kw == "atlassian jira":
            kw = "jira atlassian"
        return kw

    for r in rows:
        m = r.segments.month[:7]
        kw = normalize_kw(r.ad_group_criterion.keyword.text)
        imp = r.metrics.impressions
        is_v = r.metrics.search_impression_share or 0
        if is_v > 0 and imp > 0:
            agg[m][kw]["is_w"] += is_v * imp
            agg[m][kw]["imp"] += imp
        agg[m][kw]["clicks"] += r.metrics.clicks
        agg[m][kw]["cost"] += r.metrics.cost_micros / 1_000_000
    records = []
    for m in sorted(agg.keys()):
        for kw, d in agg[m].items():
            records.append({
                "month": m,
                "keyword": kw,
                "spend": round(d["cost"]),
                "clicks": d["clicks"],
                "is": round(d["is_w"] / d["imp"] * 100, 1) if d["imp"] > 0 else 0,
                "imp": d["imp"],
            })
    print(f"  {len(records)} keyword-month rows")
    return records


def pull_tmp_monthly(service, customer_id):
    print("Pulling TMP monthly IS (13 months)...")
    rows = run_query(service, customer_id, f"""
        SELECT segments.month, metrics.search_impression_share,
               metrics.impressions, metrics.clicks, metrics.cost_micros
        FROM keyword_view
        WHERE segments.date BETWEEN '{START_13M}' AND '{END}'
        AND ad_group.name LIKE '%S:brand-trademark%'
        AND ad_group.name NOT LIKE '%trello%'
        AND ad_group_criterion.keyword.match_type = 'EXACT'
        AND metrics.impressions > 0
        ORDER BY segments.month
    """)
    agg = defaultdict(lambda: {"is_w": 0.0, "imp": 0, "clicks": 0, "cost": 0.0})
    for r in rows:
        m = r.segments.month[:7]
        imp = r.metrics.impressions
        is_v = r.metrics.search_impression_share or 0
        if is_v > 0 and imp > 0:
            agg[m]["is_w"] += is_v * imp
            agg[m]["imp"] += imp
        agg[m]["clicks"] += r.metrics.clicks
        agg[m]["cost"] += r.metrics.cost_micros / 1_000_000
    result = [{"month": m, "is": round(d["is_w"] / d["imp"] * 100, 1) if d["imp"] > 0 else 0,
               "spend": round(d["cost"]), "clicks": d["clicks"]}
              for m, d in sorted(agg.items())]
    print(f"  {len(result)} months")
    return result


def pull_geo_monthly(service, customer_id):
    print("Pulling TMP IS by geo (13 months, campaign level)...")
    import re as _re
    rows = run_query(service, customer_id, f"""
        SELECT segments.month, campaign.name,
               metrics.search_impression_share, metrics.impressions,
               metrics.cost_micros, metrics.clicks
        FROM campaign
        WHERE segments.date BETWEEN '{START_13M}' AND '{END}'
        AND campaign.name LIKE '%S:brand-trademark%'
        AND campaign.name NOT LIKE '%trello%'
        AND metrics.impressions > 0
        ORDER BY segments.month
    """)
    geo_agg = defaultdict(lambda: {"is_w": 0.0, "imp": 0, "cost": 0.0, "clicks": 0})
    for r in rows:
        m = r.segments.month[:7]
        name = r.campaign.name
        match = _re.search(r"G:([a-z]+)", name)
        geo = match.group(1).upper() if match else "OTHER"
        imp = r.metrics.impressions
        is_v = r.metrics.search_impression_share or 0
        key = (m, geo)
        if is_v > 0 and imp > 0:
            geo_agg[key]["is_w"] += is_v * imp
            geo_agg[key]["imp"] += imp
        geo_agg[key]["cost"] += r.metrics.cost_micros / 1_000_000
        geo_agg[key]["clicks"] += r.metrics.clicks

    # Top 6 geos by total impressions
    geo_totals = defaultdict(int)
    for (m, g), d in geo_agg.items():
        geo_totals[g] += d["imp"]
    top_geos = [g for g, _ in sorted(geo_totals.items(), key=lambda x: -x[1])[:6]]

    result = [{"month": k[0], "geo": k[1],
               "is": round(d["is_w"] / d["imp"] * 100, 1) if d["imp"] > 0 else 0,
               "spend": round(d["cost"]), "clicks": d["clicks"]}
              for k, d in sorted(geo_agg.items()) if k[1] in top_geos]
    print(f"  {len(result)} geo-month rows | top geos: {top_geos}")
    return result, top_geos


def pull_nontmp_monthly(service, customer_id):
    """nonTMP (Brand-General) monthly aggregated IS, spend, clicks, lost IS."""
    print("Pulling nonTMP monthly IS (13 months, ad_group level)...")
    ag_rows = run_query(service, customer_id, f"""
        SELECT segments.month, ad_group.name,
               metrics.search_impression_share,
               metrics.impressions, metrics.clicks, metrics.cost_micros
        FROM ad_group
        WHERE segments.date BETWEEN '{START_13M}' AND '{END}'
        AND metrics.impressions > 0
        ORDER BY segments.month
    """)
    agg_is = defaultdict(lambda: {"is_w": 0.0, "imp": 0, "clicks": 0, "cost": 0.0})
    for r in ag_rows:
        name = r.ad_group.name
        if "S:brand-general" not in name or "trello" in name.lower():
            continue
        m = r.segments.month[:7]
        imp = r.metrics.impressions
        is_v = r.metrics.search_impression_share or 0
        if is_v > 0 and imp > 0:
            agg_is[m]["is_w"] += is_v * imp
            agg_is[m]["imp"] += imp
        agg_is[m]["clicks"] += r.metrics.clicks
        agg_is[m]["cost"] += r.metrics.cost_micros / 1_000_000

    camp_rows = run_query(service, customer_id, f"""
        SELECT segments.month,
               metrics.search_budget_lost_impression_share,
               metrics.search_rank_lost_impression_share,
               metrics.impressions
        FROM campaign
        WHERE segments.date BETWEEN '{START_13M}' AND '{END}'
        AND campaign.name LIKE '%S:brand-trademark%'
        AND campaign.name NOT LIKE '%trello%'
        AND metrics.impressions > 0
        ORDER BY segments.month
    """)
    agg_lost = defaultdict(lambda: {"budget_w": 0.0, "rank_w": 0.0, "imp": 0})
    for r in camp_rows:
        m = r.segments.month[:7]
        imp = r.metrics.impressions
        if imp > 0:
            agg_lost[m]["budget_w"] += (r.metrics.search_budget_lost_impression_share or 0) * imp
            agg_lost[m]["rank_w"] += (r.metrics.search_rank_lost_impression_share or 0) * imp
            agg_lost[m]["imp"] += imp

    result = []
    for m in sorted(set(list(agg_is.keys()) + list(agg_lost.keys()))):
        di = agg_is.get(m, {"is_w": 0, "imp": 0, "clicks": 0, "cost": 0})
        dl = agg_lost.get(m, {"budget_w": 0, "rank_w": 0, "imp": 0})
        result.append({
            "month": m,
            "is": round(di["is_w"] / di["imp"] * 100, 1) if di["imp"] > 0 else 0,
            "lost_budget": round(dl["budget_w"] / dl["imp"] * 100, 1) if dl["imp"] > 0 else 0,
            "lost_rank": round(dl["rank_w"] / dl["imp"] * 100, 1) if dl["imp"] > 0 else 0,
            "clicks": di["clicks"],
            "spend": round(di["cost"]),
        })
    print(f"  {len(result)} months")
    return result


def pull_nontmp_weekly(service, customer_id):
    print("Pulling nonTMP weekly IS (8 weeks, ad_group level)...")
    # IS at ad_group level, filtered client-side
    ag_rows = run_query(service, customer_id, f"""
        SELECT segments.week, ad_group.name,
               metrics.search_impression_share,
               metrics.impressions, metrics.clicks, metrics.cost_micros
        FROM ad_group
        WHERE segments.date BETWEEN '{START_56D}' AND '{END}'
        AND metrics.impressions > 0
        ORDER BY segments.week
    """)
    agg_is = defaultdict(lambda: {"is_w": 0.0, "imp": 0, "clicks": 0, "cost": 0.0})
    for r in ag_rows:
        name = r.ad_group.name
        if "S:brand-general" not in name or "trello" in name.lower():
            continue
        w = r.segments.week[:10]
        imp = r.metrics.impressions
        is_v = r.metrics.search_impression_share or 0
        if is_v > 0 and imp > 0:
            agg_is[w]["is_w"] += is_v * imp
            agg_is[w]["imp"] += imp
        agg_is[w]["clicks"] += r.metrics.clicks
        agg_is[w]["cost"] += r.metrics.cost_micros / 1_000_000

    # Lost IS at campaign level (only available there)
    camp_rows = run_query(service, customer_id, f"""
        SELECT segments.week,
               metrics.search_budget_lost_impression_share,
               metrics.search_rank_lost_impression_share,
               metrics.impressions
        FROM campaign
        WHERE segments.date BETWEEN '{START_56D}' AND '{END}'
        AND campaign.name LIKE '%S:brand-trademark%'
        AND campaign.name NOT LIKE '%trello%'
        AND metrics.impressions > 0
        ORDER BY segments.week
    """)
    agg_lost = defaultdict(lambda: {"budget_w": 0.0, "rank_w": 0.0, "imp": 0})
    for r in camp_rows:
        w = r.segments.week[:10]
        imp = r.metrics.impressions
        if imp > 0:
            agg_lost[w]["budget_w"] += (r.metrics.search_budget_lost_impression_share or 0) * imp
            agg_lost[w]["rank_w"] += (r.metrics.search_rank_lost_impression_share or 0) * imp
            agg_lost[w]["imp"] += imp

    result = []
    for w in sorted(set(list(agg_is.keys()) + list(agg_lost.keys()))):
        di = agg_is.get(w, {"is_w": 0, "imp": 0, "clicks": 0, "cost": 0})
        dl = agg_lost.get(w, {"budget_w": 0, "rank_w": 0, "imp": 0})
        result.append({
            "week": w,
            "is": round(di["is_w"] / di["imp"] * 100, 1) if di["imp"] > 0 else 0,
            "lost_budget": round(dl["budget_w"] / dl["imp"] * 100, 1) if dl["imp"] > 0 else 0,
            "lost_rank": round(dl["rank_w"] / dl["imp"] * 100, 1) if dl["imp"] > 0 else 0,
            "clicks": di["clicks"],
            "spend": round(di["cost"]),
        })
    print(f"  {len(result)} weeks")
    return result


# ── HTML builder ──────────────────────────────────────────────────────────────
def build_html(tmp_monthly, nontmp_weekly, geo_out=None, top_geos=None, tmp_by_kw=None, nontmp_monthly=None):
    print("Building HTML...")
    tmp_latest = tmp_monthly[-1] if tmp_monthly else {}
    tmp_prev = tmp_monthly[-2] if len(tmp_monthly) >= 2 else tmp_latest
    nontmp_latest = nontmp_weekly[-1] if nontmp_weekly else {}
    nontmp_prev = nontmp_weekly[-2] if len(nontmp_weekly) >= 2 else nontmp_latest

    def delta_class(a, b):
        return "up" if a >= b else "down"

    def delta_arrow(a, b):
        return "▲" if a >= b else "▼"

    tmp_is_now = tmp_latest.get("is", 0)
    tmp_is_prev = tmp_prev.get("is", 0)
    nontmp_is_now = nontmp_latest.get("is", 0)
    nontmp_is_prev = nontmp_prev.get("is", 0)
    nontmp_rank_now = nontmp_latest.get("lost_rank", 0)

    tmp_table_rows = ""
    for r in reversed(tmp_monthly):
        tmp_table_rows += (
            f'<tr><td>{r["month"]}</td><td><strong>{r["is"]}%</strong></td>'
            f'<td><div class="bar-wrap"><div class="bar-fill bar-tmp" style="width:{r["is"]}%"></div></div></td>'
            f'<td>${r["spend"]:,}</td><td>{r["clicks"]:,}</td></tr>\n'
        )

    nontmp_table_rows = ""
    for r in reversed(nontmp_weekly):
        nontmp_table_rows += (
            f'<tr><td>{r["week"]}</td><td><strong>{r["is"]}%</strong></td>'
            f'<td><div class="bar-wrap"><div class="bar-fill bar-nontmp" style="width:{r["is"]}%"></div></div></td>'
            f'<td style="color:#E76F51">{r["lost_rank"]}%</td>'
            f'<td>{r["lost_budget"]}%</td>'
            f'<td>{r["clicks"]:,}</td><td>${r["spend"]:,}</td></tr>\n'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Jira BPS: TMP vs nonTMP IS Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; margin: 0; padding: 24px; background: #f4f6f8; color: #111; }}
    .header {{ margin-bottom: 28px; }}
    .title {{ font-size: 26px; font-weight: 700; color: #0052CC; }}
    .subtitle {{ color: #666; margin-top: 6px; font-size: 14px; }}
    .badge {{ display: inline-block; background: #E3FCEF; color: #006644; border-radius: 6px; padding: 3px 10px; font-size: 12px; font-weight: 600; margin-left: 10px; vertical-align: middle; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 28px; }}
    .card {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); border-top: 4px solid #4688EC; }}
    .card.green {{ border-top-color: #2ABB7F; }}
    .card label {{ color: #777; display: block; margin-bottom: 6px; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }}
    .card .value {{ font-size: 32px; font-weight: 700; line-height: 1.1; }}
    .card .delta {{ font-size: 13px; margin-top: 6px; }}
    .delta.up {{ color: #006644; }}
    .delta.down {{ color: #BF2600; }}
    .delta.flat {{ color: #666; }}
    .section {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
    .section h2 {{ font-size: 17px; font-weight: 700; margin: 0 0 6px; }}
    .section .desc {{ font-size: 13px; color: #666; margin-bottom: 20px; }}
    .chart-wrap {{ position: relative; height: 280px; }}
    .tabs {{ display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }}
    .tab {{ padding: 7px 16px; border-radius: 20px; border: 1px solid #ddd; background: white; cursor: pointer; font-size: 13px; font-weight: 500; color: #444; transition: all 0.15s; }}
    .tab.active {{ background: #0052CC; color: white; border-color: #0052CC; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th {{ background: #f4f6f8; color: #444; font-weight: 600; padding: 10px 12px; text-align: left; border-bottom: 2px solid #e8eaed; }}
    td {{ padding: 9px 12px; border-bottom: 1px solid #f0f0f0; }}
    tr:last-child td {{ border-bottom: none; }}
    .bar-wrap {{ background: #e8eaed; border-radius: 999px; height: 10px; min-width: 80px; }}
    .bar-fill {{ height: 100%; border-radius: 999px; }}
    .bar-tmp {{ background: #4688EC; }}
    .bar-nontmp {{ background: #2ABB7F; }}
    .note {{ font-size: 13px; color: #444; background: #F0F4FF; border-left: 3px solid #4688EC; padding: 12px 16px; border-radius: 6px; margin-top: 20px; }}
    .footer {{ font-size: 12px; color: #999; margin-top: 32px; text-align: center; }}
    @media (max-width: 600px) {{ .cards {{ grid-template-columns: 1fr 1fr; }} }}
  </style>
</head>
<body>
<div class="header">
  <div class="title">Jira BPS: TMP vs nonTMP IS Dashboard <span class="badge">Internal</span></div>
  <div class="subtitle">Brand paid search impression share, spend, and click trends | Google Ads API | All geos excl. Trello | As of {GENERATED}</div>
</div>

<div class="cards">
  <div class="card">
    <label>TMP IS (latest month)</label>
    <div class="value">{tmp_is_now}%</div>
    <div class="delta {delta_class(tmp_is_now, tmp_is_prev)}">
      {delta_arrow(tmp_is_now, tmp_is_prev)} {abs(round(tmp_is_now - tmp_is_prev, 1))}pp vs prior month
    </div>
  </div>
  <div class="card green">
    <label>nonTMP IS (latest week)</label>
    <div class="value">{nontmp_is_now}%</div>
    <div class="delta {delta_class(nontmp_is_now, nontmp_is_prev)}">
      {delta_arrow(nontmp_is_now, nontmp_is_prev)} {abs(round(nontmp_is_now - nontmp_is_prev, 1))}pp vs prior week
    </div>
  </div>
  <div class="card">
    <label>TMP Lost IS</label>
    <div class="value" style="font-size:26px;">~5%</div>
    <div class="delta flat">Rank-constrained, budget healthy</div>
  </div>
  <div class="card green">
    <label>nonTMP Lost IS (Rank)</label>
    <div class="value" style="font-size:26px;">{nontmp_rank_now}%</div>
    <div class="delta down">Rank-constrained, bid lever available</div>
  </div>
</div>

<div class="section">
  <h2>TMP (Brand-Trademark) Monthly IS</h2>
  <div class="desc">Exact match keywords only. Impressions-weighted IS. 13-month trend.</div>
  <div id="kw-filter" style="margin-bottom:12px;display:flex;flex-wrap:wrap;gap:4px;align-items:center;padding:10px;background:#f8f9fa;border-radius:6px;border:1px solid #e0e0e0"></div>
  <div class="chart-wrap"><canvas id="tmpMonthlyChart"></canvas></div>
  <div class="note">Latest month at {tmp_is_now}% IS. Jun dip driven by conversion outage and account suspension in May. Recovery through Jul-Aug on spend step-up.</div>
</div>

<div class="section">
  <h2>nonTMP (Brand-General) Weekly IS</h2>
  <div class="desc">All match types, S:brand-general ad groups. Last 8 weeks. Lost IS breakdown below.</div>
  <div class="chart-wrap"><canvas id="nontmpChart"></canvas></div>
  <div class="note">IS is rank-constrained (20-28% lost to rank vs near-zero budget loss). Spend step-up in late July bought IS back. Bid strategy is the primary lever.</div>
</div>

<div class="section">
  <h2>nonTMP (Brand-General) Monthly IS</h2>
  <div class="desc">All match types | All geos | Excl. Trello | 13-month trend. Lost IS at campaign level.</div>
  <div class="chart-wrap"><canvas id="nontmpMonthlyChart"></canvas></div>
</div>

<div class="section">
  <h2>nonTMP Monthly Lost IS Breakdown</h2>
  <div class="desc">Budget vs rank loss by month. Shows structural IS constraints over time.</div>
  <div class="chart-wrap"><canvas id="nontmpMonthlyLostChart"></canvas></div>
</div>

<div class="section">
  <h2>nonTMP Lost IS Breakdown</h2>
  <div class="desc">Budget vs rank loss by week. Budget loss is minimal; rank loss is the structural constraint.</div>
  <div class="chart-wrap"><canvas id="lostIsChart"></canvas></div>
</div>

<div class="section">
  <h2>Raw Data</h2>
  <div class="tabs">
    <div class="tab active" onclick="showTab('tmp')">TMP Monthly</div>
    <div class="tab" onclick="showTab('nontmp')">nonTMP Weekly</div>
  </div>
  <div id="tab-tmp">
    <table>
      <thead><tr><th>Month</th><th>IS%</th><th>IS Bar</th><th>Spend</th><th>Clicks</th></tr></thead>
      <tbody>{tmp_table_rows}</tbody>
    </table>
  </div>
  <div id="tab-nontmp" style="display:none">
    <table>
      <thead><tr><th>Week</th><th>IS%</th><th>IS Bar</th><th>Lost Rank%</th><th>Lost Budget%</th><th>Clicks</th><th>Spend</th></tr></thead>
      <tbody>{nontmp_table_rows}</tbody>
    </table>
  </div>
</div>

<div class="footer">Jira BPS Dashboard | Data: Google Ads API | Generated {GENERATED} | Internal use only</div>

<script>
const TMP_MONTHLY = {json.dumps(tmp_monthly)};
const NONTMP_WEEKLY = {json.dumps(nontmp_weekly)};
const TMP_BY_KW = {json.dumps(tmp_by_kw or [])};
const NONTMP_MONTHLY = {json.dumps(nontmp_monthly or [])};

// ── Keyword filter setup ──
const allKeywords = [...new Set(TMP_BY_KW.map(d => d.keyword))].sort();
let selectedKeywords = new Set(allKeywords);

function buildKwFilter() {{
  const wrap = document.getElementById('kw-filter');
  if (!allKeywords.length) {{ wrap.style.display = 'none'; return; }}
  wrap.innerHTML = '<strong style="font-size:13px;color:#333">Filter keywords:</strong> ' +
    '<label style="margin-left:8px;font-size:12px;cursor:pointer">' +
    '<input type="checkbox" id="kw-all" checked onchange="toggleAllKw(this.checked)"> All</label> ' +
    allKeywords.map(kw =>
      `<label style="margin-left:8px;font-size:12px;cursor:pointer;white-space:nowrap">` +
      `<input type="checkbox" class="kw-cb" value="${{kw}}" checked onchange="updateKwFilter()"> ${{kw}}</label>`
    ).join('');
}}

function toggleAllKw(checked) {{
  document.querySelectorAll('.kw-cb').forEach(cb => cb.checked = checked);
  selectedKeywords = checked ? new Set(allKeywords) : new Set();
  renderTmpChart();
}}

function updateKwFilter() {{
  selectedKeywords = new Set([...document.querySelectorAll('.kw-cb:checked')].map(cb => cb.value));
  const allChecked = selectedKeywords.size === allKeywords.length;
  document.getElementById('kw-all').checked = allChecked;
  renderTmpChart();
}}

function getRolledUp() {{
  // Roll up keyword-level data to monthly totals for selected keywords
  const filtered = TMP_BY_KW.filter(d => selectedKeywords.has(d.keyword));
  const byMonth = {{}};
  filtered.forEach(d => {{
    if (!byMonth[d.month]) byMonth[d.month] = {{is_w: 0, imp: 0, spend: 0, clicks: 0}};
    byMonth[d.month].is_w += d.is * d.imp;
    byMonth[d.month].imp += d.imp;
    byMonth[d.month].spend += d.spend;
    byMonth[d.month].clicks += d.clicks;
  }});
  // Fall back to full TMP_MONTHLY if no keyword data
  if (!filtered.length) return TMP_MONTHLY;
  const months = Object.keys(byMonth).sort();
  return months.map(m => ({{
    month: m,
    is: byMonth[m].imp > 0 ? Math.round(byMonth[m].is_w / byMonth[m].imp * 10) / 10 : 0,
    spend: byMonth[m].spend,
    clicks: byMonth[m].clicks,
  }}));
}}

let tmpChart = null;
function renderTmpChart() {{
  const data = getRolledUp();
  if (tmpChart) tmpChart.destroy();
  tmpChart = new Chart(document.getElementById('tmpMonthlyChart'), {{
    type: 'line',
    data: {{
      labels: data.map(d => d.month),
      datasets: [{{ label: 'TMP IS%', data: data.map(d => d.is),
        borderColor: '#4688EC', backgroundColor: 'rgba(70,136,236,0.08)',
        borderWidth: 3, pointRadius: 5, pointBackgroundColor: '#4688EC', fill: true, tension: 0.3 }}]
    }},
    options: {{ responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }}, tooltip: {{ callbacks: {{ label: ctx => ctx.parsed.y + '%' }} }} }},
      scales: {{ y: {{ min: 75, max: 100, ticks: {{ callback: v => v + '%' }}, grid: {{ color: '#f0f0f0' }} }},
                 x: {{ grid: {{ display: false }} }} }} }}
  }});
}}

buildKwFilter();
renderTmpChart();

if (NONTMP_MONTHLY.length) {{
  new Chart(document.getElementById('nontmpMonthlyChart'), {{
    type: 'line',
    data: {{
      labels: NONTMP_MONTHLY.map(d => d.month),
      datasets: [{{ label: 'nonTMP IS%', data: NONTMP_MONTHLY.map(d => d.is),
        borderColor: '#2ABB7F', backgroundColor: 'rgba(42,187,127,0.08)',
        borderWidth: 3, pointRadius: 5, pointBackgroundColor: '#2ABB7F', fill: true, tension: 0.3 }}]
    }},
    options: {{ responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }}, tooltip: {{ callbacks: {{ label: ctx => ctx.parsed.y + '%' }} }} }},
      scales: {{ y: {{ min: 40, max: 80, ticks: {{ callback: v => v + '%' }}, grid: {{ color: '#f0f0f0' }} }},
                 x: {{ grid: {{ display: false }} }} }} }}
  }});

  new Chart(document.getElementById('nontmpMonthlyLostChart'), {{
    type: 'bar',
    data: {{
      labels: NONTMP_MONTHLY.map(d => d.month),
      datasets: [
        {{ label: 'Lost (Rank)', data: NONTMP_MONTHLY.map(d => d.lost_rank), backgroundColor: '#F4A261' }},
        {{ label: 'Lost (Budget)', data: NONTMP_MONTHLY.map(d => d.lost_budget), backgroundColor: '#E76F51' }},
        {{ label: 'IS Won', data: NONTMP_MONTHLY.map(d => d.is), backgroundColor: '#2ABB7F' }},
      ]
    }},
    options: {{ responsive: true, maintainAspectRatio: false,
      plugins: {{ tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y + '%' }} }} }},
      scales: {{ x: {{ stacked: true, grid: {{ display: false }} }},
                 y: {{ stacked: true, max: 100, ticks: {{ callback: v => v + '%' }}, grid: {{ color: '#f0f0f0' }} }} }} }}
  }});
}}

new Chart(document.getElementById('nontmpChart'), {{
  type: 'line',
  data: {{
    labels: NONTMP_WEEKLY.map(d => d.week),
    datasets: [{{ label: 'nonTMP IS%', data: NONTMP_WEEKLY.map(d => d.is),
      borderColor: '#2ABB7F', backgroundColor: 'rgba(42,187,127,0.08)',
      borderWidth: 3, pointRadius: 5, pointBackgroundColor: '#2ABB7F', fill: true, tension: 0.3 }}]
  }},
  options: {{ responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }}, tooltip: {{ callbacks: {{ label: ctx => ctx.parsed.y + '%' }} }} }},
    scales: {{ y: {{ min: 40, max: 75, ticks: {{ callback: v => v + '%' }}, grid: {{ color: '#f0f0f0' }} }},
               x: {{ grid: {{ display: false }} }} }} }}
}});

new Chart(document.getElementById('lostIsChart'), {{
  type: 'bar',
  data: {{
    labels: NONTMP_WEEKLY.map(d => d.week),
    datasets: [
      {{ label: 'Lost (Rank)', data: NONTMP_WEEKLY.map(d => d.lost_rank), backgroundColor: '#F4A261' }},
      {{ label: 'Lost (Budget)', data: NONTMP_WEEKLY.map(d => d.lost_budget), backgroundColor: '#E76F51' }},
      {{ label: 'IS Won', data: NONTMP_WEEKLY.map(d => d.is), backgroundColor: '#2ABB7F' }},
    ]
  }},
  options: {{ responsive: true, maintainAspectRatio: false,
    plugins: {{ tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y + '%' }} }} }},
    scales: {{ x: {{ stacked: true, grid: {{ display: false }} }},
               y: {{ stacked: true, max: 100, ticks: {{ callback: v => v + '%' }}, grid: {{ color: '#f0f0f0' }} }} }} }}
}});

function showTab(name) {{
  document.getElementById('tab-tmp').style.display = name === 'tmp' ? '' : 'none';
  document.getElementById('tab-nontmp').style.display = name === 'nontmp' ? '' : 'none';
  document.querySelectorAll('.tab').forEach((t, i) =>
    t.classList.toggle('active', (name === 'tmp' && i === 0) || (name === 'nontmp' && i === 1)));
}}
</script>
</body>
</html>"""


# ── Publish ───────────────────────────────────────────────────────────────────
def publish():
    print(f"Publishing to Statlas namespace: {STATLAS_NAMESPACE}...")
    result = subprocess.run(
        ["atlas", "statlas", "put",
         "-n", STATLAS_NAMESPACE,
         "-f", os.path.basename(OUTPUT_FILE),
         "--auth-group", STATLAS_AUTH_GROUP],
        capture_output=True, text=True,
        cwd=os.path.dirname(OUTPUT_FILE),
    )
    if result.returncode == 0:
        url = f"https://statlas.prod.atl-paas.net/{STATLAS_NAMESPACE}/bps_is_dashboard.html"
        print(f"Published: {url}")
    else:
        print(f"ERROR publishing: {result.stderr}")
        sys.exit(1)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"Refreshing BPS IS Dashboard | {GENERATED}")
    print("-" * 50)

    service, customer_id = load_ga_client()
    tmp_monthly = pull_tmp_monthly(service, customer_id)
    tmp_by_kw = pull_tmp_monthly_by_keyword(service, customer_id)
    nontmp_monthly = pull_nontmp_monthly(service, customer_id)
    nontmp_weekly = pull_nontmp_weekly(service, customer_id)
    geo_out, top_geos = pull_geo_monthly(service, customer_id)

    html = build_html(tmp_monthly, nontmp_weekly, geo_out, top_geos, tmp_by_kw=tmp_by_kw, nontmp_monthly=nontmp_monthly)
    with open(OUTPUT_FILE, "w") as f:
        f.write(html)
    print(f"HTML written: {OUTPUT_FILE}")

    publish()
    print("Done.")


if __name__ == "__main__":
    main()
