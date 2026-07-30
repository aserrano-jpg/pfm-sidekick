"""
Generate a static HTML preview for the BPS Databricks dashboard.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

PREVIEW_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>BPS Impression Share Dashboard Preview</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; padding: 24px; background: #f4f6f8; color: #111; }}
    .header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }}
    .title {{ font-size: 28px; font-weight: 700; }}
    .subtitle {{ color: #555; margin-top: 4px; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }}
    .card {{ background: white; border-radius: 12px; padding: 18px; box-shadow: 0 1px 3px rgba(16, 24, 40, 0.08); }}
    .card label {{ color: #777; display: block; margin-bottom: 8px; font-size: 0.9rem; }}
    .card .value {{ font-size: 28px; font-weight: 700; }}
    .section {{ margin-bottom: 24px; }}
    .section h2 {{ font-size: 20px; margin-bottom: 16px; }}
    .table-wrapper {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; }}
    th, td {{ padding: 12px 14px; text-align: left; }}
    th {{ background: #f4f6f8; color: #333; font-weight: 600; }}
    tr:nth-child(even) {{ background: #fafbfc; }}
    .bar-cell {{ min-width: 140px; }}
    .bar {{ height: 14px; border-radius: 999px; background: #e4e8f0; overflow: hidden; }}
    .bar-fill {{ height: 100%; background: #2563eb; border-radius: 999px; }}
    .note {{ font-size: 0.95rem; color: #444; background: #e8f0ff; border-left: 4px solid #3b82f6; padding: 14px 18px; border-radius: 8px; }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <div class="title">BPS Paid Search Dashboard</div>
      <div class="subtitle">Brand paid search performance, impression share, spend efficiency, and source mix.</div>
    </div>
    <div class="note">Dataset: Google Ads + internal paid performance | Daily refresh | BPS only</div>
  </div>

  <div class="cards">
    <div class="card"><label>Impression Share</label><div class="value">{impression_share_pct:.1f}%</div><div style="color:#555; margin-top:8px;">Share of eligible impressions captured</div></div>
    <div class="card"><label>Spend</label><div class="value">${spend:,.0f}</div><div style="color:#555; margin-top:8px;">Last 7-day total</div></div>
    <div class="card"><label>CPM</label><div class="value">${cpm:,.1f}</div><div style="color:#555; margin-top:8px;">Cost per thousand impressions</div></div>
    <div class="card"><label>Lost Impression Share</label><div class="value">{lost_impr_pct:.1f}%</div><div style="color:#555; margin-top:8px;">Eligible impressions not won</div></div>
  </div>

  <div class="section">
    <h2>Weekly Trend</h2>
    <div class="card" style="padding: 24px;">
      <svg width="100%" height="220" viewBox="0 0 700 220" xmlns="http://www.w3.org/2000/svg">
        <polyline fill="none" stroke="#2563eb" stroke-width="4" points="40,170 120,140 200,118 280,94 360,98 440,82 520,72 600,58" />
        <circle cx="40" cy="170" r="6" fill="#2563eb" />
        <circle cx="120" cy="140" r="6" fill="#2563eb" />
        <circle cx="200" cy="118" r="6" fill="#2563eb" />
        <circle cx="280" cy="94" r="6" fill="#2563eb" />
        <circle cx="360" cy="98" r="6" fill="#2563eb" />
        <circle cx="440" cy="82" r="6" fill="#2563eb" />
        <circle cx="520" cy="72" r="6" fill="#2563eb" />
        <circle cx="600" cy="58" r="6" fill="#2563eb" />
        <text x="40" y="190" fill="#555" font-size="12">Week 1</text>
        <text x="120" y="190" fill="#555" font-size="12">Week 2</text>
        <text x="200" y="190" fill="#555" font-size="12">Week 3</text>
        <text x="280" y="190" fill="#555" font-size="12">Week 4</text>
        <text x="360" y="190" fill="#555" font-size="12">Week 5</text>
        <text x="440" y="190" fill="#555" font-size="12">Week 6</text>
        <text x="520" y="190" fill="#555" font-size="12">Week 7</text>
        <text x="600" y="190" fill="#555" font-size="12">Week 8</text>
      </svg>
    </div>
  </div>

  <div class="section">
    <h2>Top BPS Campaigns</h2>
    <div class="table-wrapper">
      <table>
        <thead>
          <tr><th>Campaign</th><th>Impr Share</th><th>Spend</th><th>Impressions</th><th>Lost IS</th></tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
      </table>
    </div>
  </div>

  <div class="section">
    <h2>Insights</h2>
    <div class="note">Brand search impression share is strong, but lost share remains concentrated in two lower-ranked campaigns. Consider bid or copy updates for campaigns below 80% share.</div>
  </div>
</body>
</html>"""


def build_row(name: str, share: float, spend: float, impressions: int, lost_pct: float) -> str:
    width = min(max(share, 0.0), 100.0)
    return f"""
    <tr>
      <td>{name}</td>
      <td>{share:.1f}%</td>
      <td>${spend:,.0f}</td>
      <td>{impressions:,}</td>
      <td class=\"bar-cell\"><div class=\"bar\"><div class=\"bar-fill\" style=\"width:{width:.1f}%\"></div></div></td>
    </tr>
    """


def generate_dashboard_html(path: Path) -> Path:
    metrics = {
        "impression_share_pct": 84.2,
        "spend": 258000,
        "cpm": 21.5,
        "lost_impr_pct": 15.8,
    }
    rows = "".join([
        build_row("Brand US Core", 89.4, 112000, 374000, 10.2),
        build_row("Brand EU", 78.6, 76000, 218000, 21.4),
        build_row("Brand APAC", 82.1, 45000, 134000, 18.7),
    ])

    html = PREVIEW_HTML.format(rows=rows, **metrics)
    path.write_text(html, encoding="utf-8")
    return path


if __name__ == "__main__":
    out_path = Path(__file__).resolve().parent / "dashboard_preview.html"
    generated = generate_dashboard_html(out_path)
    print(f"Dashboard preview generated at: {generated}")
