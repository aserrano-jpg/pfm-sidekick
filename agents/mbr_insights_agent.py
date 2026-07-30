#!/usr/bin/env python3
"""
MBR Insights Agent
==================
Ingests data from Optimal deck extracts and Socrates query results,
normalizes everything into a standard insights block, and prints a
draft report (TOFU weekly or MBR LAND) to stdout for human review.

No data is auto-published. All output is draft-only.

Usage
-----
# From a JSON insights file (Socrates results pre-exported):
python agents/mbr_insights_agent.py \\
    --insights-file insights_june2026.json \\
    --report-type mbr-land \\
    --period "June 2026" \\
    --product "Base Product" \\
    --writer michael

# From a deck extract markdown file:
python agents/mbr_insights_agent.py \\
    --deck-file deck_extract_june2026.md \\
    --report-type tofu-weekly \\
    --period "week ending June 13 2026" \\
    --product "Jira" \\
    --writer armando

# Combining both sources:
python agents/mbr_insights_agent.py \\
    --deck-file deck_extract.md \\
    --insights-file socrates_results.json \\
    --report-type mbr-land \\
    --period "June 2026" \\
    --product "Base Product" \\
    --writer val \\
    --output draft_mbr_june2026.txt
"""

from __future__ import annotations

import json
import logging
import sys
from argparse import ArgumentParser
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("mbr_insights_agent")

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ChannelRow:
    """One row of channel-level performance data."""
    channel: str
    bd1_6: Optional[float] = None
    spend: Optional[float] = None        # directional; always flag as such
    cpbd1_6: Optional[float] = None      # cost per BD1-6 (spend / bd1_6)
    wow_delta: Optional[float] = None    # week-over-week delta in bd1_6
    mom_delta: Optional[float] = None    # month-over-month delta in bd1_6
    share_of_total: Optional[float] = None  # fraction of total bd1_6


@dataclass
class CompetitorSignal:
    name: str
    action: str
    estimated_impact: Optional[str] = None


@dataclass
class Opportunity:
    description: str
    owner: Optional[str] = None
    expected_lift: Optional[str] = None
    timeline: Optional[str] = None


@dataclass
class Risk:
    description: str
    owner: Optional[str] = None
    estimated_impact: Optional[str] = None
    gate_or_threshold: Optional[str] = None


@dataclass
class InsightsBlock:
    """
    Normalized insights block produced by the ingestion step.
    This is the handoff object to the MBR writer.
    """
    # Metadata
    period: str = ""
    product: str = ""
    report_type: str = ""           # "tofu-weekly" or "mbr-land"
    writer: str = "michael"
    data_sources: List[str] = field(default_factory=list)

    # Top-level metrics
    bd1_6_actuals: Optional[float] = None
    bd1_6_target: Optional[float] = None
    bd1_6_vs_target_pct: Optional[float] = None   # e.g. 1.05 = 5% above target
    bd1_6_prior_period: Optional[float] = None
    bd1_6_period_delta_pct: Optional[float] = None  # MoM or WoW
    paid_share: Optional[float] = None              # fraction of total bd1_6
    organic_share: Optional[float] = None
    spend: Optional[float] = None                   # directional
    cac: Optional[float] = None
    ltv_to_cac_ratio: Optional[float] = None
    cpbd1_6: Optional[float] = None
    data_lag_flag: bool = False       # True if last 7 days included (understated)

    # Breakdowns
    channels: List[ChannelRow] = field(default_factory=list)

    # Qualitative signals
    competitors: List[CompetitorSignal] = field(default_factory=list)
    opportunities: List[Opportunity] = field(default_factory=list)
    risks: List[Risk] = field(default_factory=list)

    # Audit
    missing_fields: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Source parsers
# ---------------------------------------------------------------------------

def parse_deck_file(path: Path) -> Dict[str, Any]:
    """
    Parse a markdown deck extract into a raw dict.

    Expected format (sections delimited by ## headers):

        ## BD1-6 Metrics
        actuals: 0.72
        target: 0.70
        prior_period: 0.65

        ## Spend
        amount: 1500000

        ## Channels
        Paid Search: bd1_6=0.45, spend=800000
        Paid Social: bd1_6=0.15, spend=300000

        ## Competitors
        Acme Corp: launched new free tier; estimated +15% CAC pressure

        ## Opportunities
        - Mid-market audience expansion; Sarah; +15-20% volume; Jun 30

        ## Risks
        - CAC inflation if Acme sustains spend; CAC team; +$15 CAC; gate: CAC > $85

    All fields are optional. Missing fields are collected and reported.
    """
    raw: Dict[str, Any] = {}
    if not path.exists():
        raise FileNotFoundError(f"Deck file not found: {path}")

    content = path.read_text()
    current_section = None

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("## "):
            current_section = stripped[3:].strip().lower().replace(" ", "_").replace("-", "_")
            raw.setdefault(current_section, [])
            continue

        if current_section is not None:
            raw[current_section].append(stripped)

    return raw


def parse_insights_file(path: Path) -> Dict[str, Any]:
    """
    Parse a JSON file containing pre-run Socrates query results.

    Expected top-level keys (all optional):
        bd1_6_actuals, bd1_6_target, bd1_6_prior_period,
        spend, cac, ltv_to_cac_ratio, cpbd1_6,
        paid_share, organic_share,
        channels: [{channel, bd1_6, spend, cpbd1_6, wow_delta, mom_delta, share_of_total}],
        data_lag_flag: true/false
    """
    if not path.exists():
        raise FileNotFoundError(f"Insights file not found: {path}")
    with path.open() as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def _safe_float(value: Any, field_name: str, missing: List[str]) -> Optional[float]:
    """Convert value to float, or record as missing."""
    if value is None:
        missing.append(field_name)
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        missing.append(field_name)
        return None


def _parse_kv_lines(lines: List[str]) -> Dict[str, str]:
    """Parse 'key: value' lines into a dict."""
    result = {}
    for line in lines:
        if ":" in line:
            k, _, v = line.partition(":")
            result[k.strip().lower().replace(" ", "_")] = v.strip()
    return result


def normalize(
    deck_raw: Optional[Dict[str, Any]],
    insights_raw: Optional[Dict[str, Any]],
    period: str,
    product: str,
    report_type: str,
    writer: str,
) -> InsightsBlock:
    """
    Merge deck extract and Socrates results into a single InsightsBlock.
    Socrates data takes priority for quantitative metrics. Deck data fills
    qualitative fields (competitors, opportunities, risks) and any gaps.
    """
    block = InsightsBlock(
        period=period,
        product=product,
        report_type=report_type,
        writer=writer,
    )
    missing: List[str] = []

    # --- Quantitative metrics: Socrates first, deck as fallback ---

    # Socrates JSON
    if insights_raw:
        block.data_sources.append("Socrates")
        block.bd1_6_actuals = _safe_float(
            insights_raw.get("bd1_6_actuals"), "bd1_6_actuals", missing
        )
        block.bd1_6_target = _safe_float(
            insights_raw.get("bd1_6_target"), "bd1_6_target", missing
        )
        block.bd1_6_prior_period = _safe_float(
            insights_raw.get("bd1_6_prior_period"), "bd1_6_prior_period", missing
        )
        block.spend = _safe_float(insights_raw.get("spend"), "spend", missing)
        block.cac = _safe_float(insights_raw.get("cac"), "cac", missing)
        block.ltv_to_cac_ratio = _safe_float(
            insights_raw.get("ltv_to_cac_ratio"), "ltv_to_cac_ratio", missing
        )
        block.cpbd1_6 = _safe_float(insights_raw.get("cpbd1_6"), "cpbd1_6", missing)
        block.paid_share = _safe_float(
            insights_raw.get("paid_share"), "paid_share", missing
        )
        block.organic_share = _safe_float(
            insights_raw.get("organic_share"), "organic_share", missing
        )
        block.data_lag_flag = bool(insights_raw.get("data_lag_flag", False))

        # Channel rows
        for ch in insights_raw.get("channels", []):
            block.channels.append(
                ChannelRow(
                    channel=ch.get("channel", "Unknown"),
                    bd1_6=ch.get("bd1_6"),
                    spend=ch.get("spend"),
                    cpbd1_6=ch.get("cpbd1_6"),
                    wow_delta=ch.get("wow_delta"),
                    mom_delta=ch.get("mom_delta"),
                    share_of_total=ch.get("share_of_total"),
                )
            )

    # Deck fallback for metrics not in Socrates results
    if deck_raw:
        block.data_sources.append("Optimal deck")
        bd1_6_section = deck_raw.get("bd1_6_metrics", [])
        kv = _parse_kv_lines(bd1_6_section)

        if block.bd1_6_actuals is None and "actuals" in kv:
            block.bd1_6_actuals = _safe_float(kv["actuals"], "bd1_6_actuals", missing)
        if block.bd1_6_target is None and "target" in kv:
            block.bd1_6_target = _safe_float(kv["target"], "bd1_6_target", missing)
        if block.bd1_6_prior_period is None and "prior_period" in kv:
            block.bd1_6_prior_period = _safe_float(
                kv["prior_period"], "bd1_6_prior_period", missing
            )

        spend_section = deck_raw.get("spend", [])
        spend_kv = _parse_kv_lines(spend_section)
        if block.spend is None and "amount" in spend_kv:
            block.spend = _safe_float(spend_kv["amount"], "spend", missing)

        # Qualitative: competitors
        for comp_line in deck_raw.get("competitors", []):
            if ":" in comp_line:
                name, _, rest = comp_line.partition(":")
                parts = rest.split(";")
                action = parts[0].strip() if parts else rest.strip()
                impact = parts[1].strip() if len(parts) > 1 else None
                block.competitors.append(
                    CompetitorSignal(name=name.strip(), action=action, estimated_impact=impact)
                )

        # Qualitative: opportunities (format: desc; owner; lift; timeline)
        for opp_line in deck_raw.get("opportunities", []):
            opp_line = opp_line.lstrip("- ").strip()
            parts = [p.strip() for p in opp_line.split(";")]
            block.opportunities.append(
                Opportunity(
                    description=parts[0] if len(parts) > 0 else opp_line,
                    owner=parts[1] if len(parts) > 1 else None,
                    expected_lift=parts[2] if len(parts) > 2 else None,
                    timeline=parts[3] if len(parts) > 3 else None,
                )
            )

        # Qualitative: risks (format: desc; owner; impact; gate)
        for risk_line in deck_raw.get("risks", []):
            risk_line = risk_line.lstrip("- ").strip()
            parts = [p.strip() for p in risk_line.split(";")]
            block.risks.append(
                Risk(
                    description=parts[0] if len(parts) > 0 else risk_line,
                    owner=parts[1] if len(parts) > 1 else None,
                    estimated_impact=parts[2] if len(parts) > 2 else None,
                    gate_or_threshold=parts[3] if len(parts) > 3 else None,
                )
            )

    # --- Derived metrics ---
    if block.bd1_6_actuals and block.bd1_6_target:
        block.bd1_6_vs_target_pct = block.bd1_6_actuals / block.bd1_6_target

    if block.bd1_6_actuals and block.bd1_6_prior_period and block.bd1_6_prior_period != 0:
        block.bd1_6_period_delta_pct = (
            (block.bd1_6_actuals - block.bd1_6_prior_period) / block.bd1_6_prior_period
        )

    if block.paid_share and block.organic_share is None:
        block.organic_share = 1.0 - block.paid_share

    # Remove duplicate missing fields (could appear from both sources)
    seen = set()
    block.missing_fields = [
        f for f in missing if f not in seen and not seen.add(f)
    ]

    return block


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------

def _fmt_pct(value: Optional[float], decimals: int = 1) -> str:
    if value is None:
        return "[not available]"
    return f"{value * 100:.{decimals}f}%"


def _fmt_num(value: Optional[float], prefix: str = "", suffix: str = "", decimals: int = 0) -> str:
    if value is None:
        return "[not available]"
    return f"{prefix}{value:,.{decimals}f}{suffix}"


def render_insights_block(block: InsightsBlock) -> str:
    """Render the normalized InsightsBlock as a structured text block."""
    lines = [
        "INSIGHTS BLOCK",
        "==============",
        f"Period:       {block.period}",
        f"Product:      {block.product}",
        f"Report type:  {block.report_type}",
        f"Writer:       {block.writer}",
        f"Data sources: {', '.join(block.data_sources) if block.data_sources else '[none provided]'}",
        "",
        "METRICS",
        "-------",
        f"BD1-6 actuals:          {_fmt_num(block.bd1_6_actuals, decimals=2)}",
        f"BD1-6 target:           {_fmt_num(block.bd1_6_target, decimals=2)}",
        f"BD1-6 vs. target:       {_fmt_pct(block.bd1_6_vs_target_pct)} of target",
        f"BD1-6 prior period:     {_fmt_num(block.bd1_6_prior_period, decimals=2)}",
        f"BD1-6 period delta:     {_fmt_pct(block.bd1_6_period_delta_pct)} MoM/WoW",
        f"Paid volume share:      {_fmt_pct(block.paid_share)}",
        f"Organic volume share:   {_fmt_pct(block.organic_share)}",
        f"Spend (directional):    {_fmt_num(block.spend, prefix='$')}",
        f"CAC:                    {_fmt_num(block.cac, prefix='$', decimals=2)}",
        f"LTV to CAC ratio:       {_fmt_num(block.ltv_to_cac_ratio, suffix='x', decimals=1)}",
        f"CPBD1-6:                {_fmt_num(block.cpbd1_6, prefix='$', decimals=2)}",
        f"Data lag flag:          {'YES - last 7 days understated' if block.data_lag_flag else 'No'}",
    ]

    # Channel breakdown
    lines += ["", "CHANNEL BREAKDOWN", "-----------------"]
    if block.channels:
        for ch in block.channels:
            delta_str = ""
            if ch.wow_delta is not None:
                delta_str = f" | WoW: {_fmt_pct(ch.wow_delta)}"
            elif ch.mom_delta is not None:
                delta_str = f" | MoM: {_fmt_pct(ch.mom_delta)}"
            share_str = f" | share: {_fmt_pct(ch.share_of_total)}" if ch.share_of_total else ""
            lines.append(
                f"  {ch.channel}: bd1_6={_fmt_num(ch.bd1_6)}"
                f" | spend={_fmt_num(ch.spend, prefix='$')}"
                f" | cpbd1_6={_fmt_num(ch.cpbd1_6, prefix='$', decimals=2)}"
                f"{share_str}{delta_str}"
            )
    else:
        lines.append("  [not available - run TW-1 or MBR-1 from socrates-queries.md]")

    # Competitive
    lines += ["", "COMPETITIVE", "-----------"]
    if block.competitors:
        for comp in block.competitors:
            impact_str = f" | impact: {comp.estimated_impact}" if comp.estimated_impact else ""
            lines.append(f"  {comp.name}: {comp.action}{impact_str}")
    else:
        lines.append("  No material competitive signals this period")

    # Opportunities
    lines += ["", "OPPORTUNITIES", "-------------"]
    if block.opportunities:
        for opp in block.opportunities:
            owner_str = f" | owner: {opp.owner}" if opp.owner else " | owner: TBD"
            lift_str = f" | lift: {opp.expected_lift}" if opp.expected_lift else ""
            timeline_str = f" | by: {opp.timeline}" if opp.timeline else ""
            lines.append(f"  - {opp.description}{owner_str}{lift_str}{timeline_str}")
    else:
        lines.append("  [not available - extract from Optimal deck forward-looking slides]")

    # Risks
    lines += ["", "RISKS AND BLOCKERS", "------------------"]
    if block.risks:
        for risk in block.risks:
            owner_str = f" | owner: {risk.owner}" if risk.owner else ""
            impact_str = f" | impact: {risk.estimated_impact}" if risk.estimated_impact else ""
            gate_str = f" | gate: {risk.gate_or_threshold}" if risk.gate_or_threshold else ""
            lines.append(f"  - {risk.description}{owner_str}{impact_str}{gate_str}")
    else:
        lines.append("  No material risks flagged this period")

    # Missing data
    lines += ["", "MISSING DATA", "------------"]
    if block.missing_fields:
        for f in block.missing_fields:
            lines.append(f"  - {f} [not available - check Optimal deck or Socrates]")
    else:
        lines.append("  None")

    return "\n".join(lines)


def render_tofu_draft(block: InsightsBlock) -> str:
    """
    Render a TOFU weekly draft (4-6 bullets).
    This is a scaffold. The agent populates what it can from the insights block
    and marks gaps for the human reviewer to fill before publishing.
    """
    bullets = []

    # BD1-6 headline
    bd_str = _fmt_num(block.bd1_6_actuals, decimals=2)
    tgt_str = _fmt_num(block.bd1_6_target, decimals=2)
    delta_str = _fmt_pct(block.bd1_6_period_delta_pct)
    bullets.append(
        f"BD1-6: {bd_str} vs. target {tgt_str} ({delta_str} WoW)."
        " [Add: one-line root cause or trend note]"
    )

    # Paid vs. organic split
    if block.paid_share is not None:
        paid_pct = _fmt_pct(block.paid_share)
        org_pct = _fmt_pct(block.organic_share)
        bullets.append(
            f"Channel mix: paid drove {paid_pct} of BD1-6; organic {org_pct}."
            " [Add: top channel name and WoW delta if available]"
        )
    else:
        bullets.append(
            "Channel mix: [not available - run TW-3 from socrates-queries.md]"
        )

    # Spend
    spend_str = _fmt_num(block.spend, prefix="$")
    cpbd_str = _fmt_num(block.cpbd1_6, prefix="$", decimals=2)
    lag_note = " Note: last 7 days understated (bake lag)." if block.data_lag_flag else ""
    bullets.append(f"Spend: {spend_str} (directional). CPBD1-6: {cpbd_str}.{lag_note}")

    # Top opportunity
    if block.opportunities:
        opp = block.opportunities[0]
        owner = opp.owner or "TBD"
        lift = opp.expected_lift or "[lift TBD]"
        timeline = opp.timeline or "[date TBD]"
        bullets.append(
            f"{opp.description}: {owner} targeting {timeline}, expected lift {lift}."
        )
    else:
        bullets.append(
            "Upcoming initiative: [not available - extract from Optimal deck]"
        )

    # Top risk
    if block.risks:
        risk = block.risks[0]
        gate = risk.gate_or_threshold or "[threshold TBD]"
        bullets.append(
            f"Watch: {risk.description}. Gate: {gate}."
        )
    else:
        bullets.append("Watch items: none flagged this period")

    # Competitive (only if material)
    if block.competitors:
        comp = block.competitors[0]
        impact = comp.estimated_impact or "[impact TBD]"
        bullets.append(f"Competitive: {comp.name} {comp.action}. Impact: {impact}.")

    header = (
        f"TOFU: {block.period} - {block.product}\n"
        + "-" * 40
    )
    return header + "\n" + "\n".join(f"- {b}" for b in bullets)


def render_mbr_draft(block: InsightsBlock) -> str:
    """
    Render an MBR LAND section scaffold.
    Populates the structure from the insights block and marks gaps for review.
    The human reviewer (or tofu-mbr-writer skill) fills narrative around the data.
    """
    delta_str = _fmt_pct(block.bd1_6_period_delta_pct)
    prior_str = _fmt_num(block.bd1_6_prior_period, decimals=2)
    actuals_str = _fmt_num(block.bd1_6_actuals, decimals=2)
    target_str = _fmt_num(block.bd1_6_target, decimals=2)
    vs_target_str = _fmt_pct(block.bd1_6_vs_target_pct)
    paid_str = _fmt_pct(block.paid_share)
    organic_str = _fmt_pct(block.organic_share)
    spend_str = _fmt_num(block.spend, prefix="$")
    cac_str = _fmt_num(block.cac, prefix="$", decimals=2)
    ltv_str = _fmt_num(block.ltv_to_cac_ratio, suffix="x", decimals=1)
    lag_note = "\nNote: last 7 days understated due to BD1-6 bake lag." if block.data_lag_flag else ""

    highlights = f"""LAND: {block.period} Performance
{'=' * 40}

--- Highlights ---

{block.product} BD1-6 reached {actuals_str} in {block.period} ({vs_target_str} of {target_str} target), \
{"up" if (block.bd1_6_period_delta_pct or 0) >= 0 else "down"} from {prior_str} prior period ({delta_str} MoM/WoW). \
Paid channels drove {paid_str} of volume; organic {organic_str}.{lag_note}

CAC: {cac_str}. LTV to CAC: {ltv_str}. Spend: {spend_str} (directional).

[Add: root cause of performance. What drove the delta? Competitor pressure, product change, market shift?]
[Add: confidence level on trajectory: Confidence: high/medium/low. Reason.]
"""

    # Channel table
    if block.channels:
        channel_lines = ["Channel performance:"]
        for ch in block.channels:
            channel_lines.append(
                f"  {ch.channel}: BD1-6 {_fmt_num(ch.bd1_6)}"
                f" | spend {_fmt_num(ch.spend, prefix='$')}"
                f" | CPBD1-6 {_fmt_num(ch.cpbd1_6, prefix='$', decimals=2)}"
            )
        highlights += "\n".join(channel_lines) + "\n"
    else:
        highlights += "[Channel breakdown not available - run MBR-1 from socrates-queries.md]\n"

    whats_coming = "\n--- What's Coming ---\n\n"

    if block.opportunities:
        for opp in block.opportunities:
            owner = opp.owner or "TBD"
            lift = opp.expected_lift or "[lift TBD]"
            timeline = opp.timeline or "[date TBD]"
            whats_coming += (
                f"- {opp.description}: {owner} by {timeline}, expected lift {lift}.\n"
            )
    else:
        whats_coming += "[Opportunities not available - extract from Optimal deck]\n"

    whats_coming += "\n"

    if block.competitors:
        whats_coming += "Competitive landscape:\n"
        for comp in block.competitors:
            impact = comp.estimated_impact or "[impact TBD]"
            whats_coming += f"  - {comp.name}: {comp.action}. Estimated impact: {impact}.\n"
    else:
        whats_coming += "Competitive: no material signals this period.\n"

    whats_coming += "\n"

    if block.risks:
        whats_coming += "Risks and contingencies:\n"
        for risk in block.risks:
            gate = risk.gate_or_threshold or "[threshold TBD]"
            impact = risk.estimated_impact or "[impact TBD]"
            owner = risk.owner or "TBD"
            whats_coming += (
                f"  - {risk.description} ({owner}). Impact: {impact}. Gate: {gate}.\n"
            )
    else:
        whats_coming += "Risks: none flagged this period.\n"

    footer = (
        "\n[DRAFT - human review required before publishing]\n"
        "[Pass this draft to tofu-mbr-writer skill with writer="
        f"{block.writer} to apply voice and finalize narrative]\n"
    )

    if block.missing_fields:
        footer += "\nMissing data (resolve before publishing):\n"
        for f in block.missing_fields:
            footer += f"  - {f}\n"

    return highlights + whats_coming + footer


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = ArgumentParser(
        description=(
            "Ingest Optimal deck extracts and Socrates results into a normalized "
            "insights block and generate a TOFU or MBR draft for review."
        )
    )
    parser.add_argument(
        "--deck-file",
        type=Path,
        default=None,
        help="Path to markdown file with Optimal deck extract",
    )
    parser.add_argument(
        "--insights-file",
        type=Path,
        default=None,
        help="Path to JSON file with pre-run Socrates query results",
    )
    parser.add_argument(
        "--report-type",
        required=True,
        choices=["tofu-weekly", "mbr-land"],
        help="Type of report to generate",
    )
    parser.add_argument(
        "--period",
        required=True,
        help="Reporting period (e.g. 'June 2026' or 'week ending June 13 2026')",
    )
    parser.add_argument(
        "--product",
        required=True,
        help="Product in scope (e.g. 'Base Product', 'Jira', 'Confluence')",
    )
    parser.add_argument(
        "--writer",
        default="michael",
        choices=["michael", "armando", "val"],
        help="Writer voice profile (default: michael)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--dump-insights",
        action="store_true",
        help="Also print the normalized insights block before the draft",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )

    args = parser.parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(levelname)s: %(message)s")

    if not args.deck_file and not args.insights_file:
        parser.error("Provide at least one of --deck-file or --insights-file")

    # Parse sources
    deck_raw = None
    if args.deck_file:
        try:
            deck_raw = parse_deck_file(args.deck_file)
            logger.info("Parsed deck file: %s", args.deck_file)
        except FileNotFoundError as exc:
            logger.error("%s", exc)
            sys.exit(1)

    insights_raw = None
    if args.insights_file:
        try:
            insights_raw = parse_insights_file(args.insights_file)
            logger.info("Parsed insights file: %s", args.insights_file)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logger.error("Could not parse insights file: %s", exc)
            sys.exit(1)

    # Normalize
    block = normalize(
        deck_raw=deck_raw,
        insights_raw=insights_raw,
        period=args.period,
        product=args.product,
        report_type=args.report_type,
        writer=args.writer,
    )

    # Render
    output_parts = []

    if args.dump_insights:
        output_parts.append(render_insights_block(block))
        output_parts.append("\n" + "=" * 40 + "\n")

    if args.report_type == "tofu-weekly":
        output_parts.append(render_tofu_draft(block))
    else:
        output_parts.append(render_mbr_draft(block))

    output_text = "\n".join(output_parts)

    if args.output:
        args.output.write_text(output_text)
        print(f"Draft written to {args.output}")
    else:
        print(output_text)


if __name__ == "__main__":
    main()
