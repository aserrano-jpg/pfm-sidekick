import json
import pytest
from pathlib import Path
from agents.mbr_insights_agent import (
    normalize,
    parse_deck_file,
    parse_insights_file,
    render_insights_block,
    render_tofu_draft,
    render_mbr_draft,
    InsightsBlock,
    ChannelRow,
    CompetitorSignal,
    Opportunity,
    Risk,
    _fmt_num,
    _fmt_pct,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_INSIGHTS_RAW = {
    "bd1_6_actuals": 0.72,
    "bd1_6_target": 0.70,
    "bd1_6_prior_period": 0.65,
    "spend": 1500000,
    "cac": 72.0,
    "ltv_to_cac_ratio": 35.0,
    "cpbd1_6": 208.33,
    "paid_share": 0.72,
    "data_lag_flag": False,
    "channels": [
        {
            "channel": "Paid Search",
            "bd1_6": 450,
            "spend": 800000,
            "cpbd1_6": 177.78,
            "share_of_total": 0.45,
        },
        {
            "channel": "Paid Social",
            "bd1_6": 270,
            "spend": 400000,
            "cpbd1_6": 148.15,
            "share_of_total": 0.27,
        },
    ],
}

SAMPLE_DECK_RAW = {
    "bd1_6_metrics": ["actuals: 0.72", "target: 0.70", "prior_period: 0.65"],
    "spend": ["amount: 1500000"],
    "competitors": ["Acme Corp: launched new free tier; estimated +15% CAC pressure"],
    "opportunities": ["Mid-market expansion; Sarah; +15% volume; Jun 30"],
    "risks": ["CAC inflation; CAC team; +$15 CAC; gate: CAC > 85"],
}


def make_block(report_type="mbr-land", writer="michael", insights=None, deck=None):
    return normalize(
        deck_raw=deck or SAMPLE_DECK_RAW,
        insights_raw=insights or SAMPLE_INSIGHTS_RAW,
        period="June 2026",
        product="Base Product",
        report_type=report_type,
        writer=writer,
    )


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def test_fmt_num_basic():
    assert _fmt_num(1500000, prefix="$") == "$1,500,000"


def test_fmt_num_decimals():
    assert _fmt_num(0.72, decimals=2) == "0.72"


def test_fmt_num_none():
    assert _fmt_num(None) == "[not available]"


def test_fmt_pct_basic():
    assert _fmt_pct(0.728) == "72.8%"


def test_fmt_pct_none():
    assert _fmt_pct(None) == "[not available]"


# ---------------------------------------------------------------------------
# normalize: Socrates-only
# ---------------------------------------------------------------------------

def test_normalize_socrates_only_metrics():
    block = normalize(
        deck_raw=None,
        insights_raw=SAMPLE_INSIGHTS_RAW,
        period="June 2026",
        product="Base Product",
        report_type="mbr-land",
        writer="michael",
    )
    assert block.bd1_6_actuals == pytest.approx(0.72)
    assert block.bd1_6_target == pytest.approx(0.70)
    assert block.bd1_6_prior_period == pytest.approx(0.65)
    assert block.spend == pytest.approx(1500000)
    assert block.cac == pytest.approx(72.0)
    assert block.ltv_to_cac_ratio == pytest.approx(35.0)
    assert block.cpbd1_6 == pytest.approx(208.33)
    assert block.paid_share == pytest.approx(0.72)
    assert block.data_lag_flag is False


def test_normalize_socrates_derived_vs_target():
    block = normalize(
        deck_raw=None,
        insights_raw=SAMPLE_INSIGHTS_RAW,
        period="June 2026",
        product="Base Product",
        report_type="mbr-land",
        writer="michael",
    )
    # 0.72 / 0.70 = 1.0285...
    assert block.bd1_6_vs_target_pct == pytest.approx(0.72 / 0.70, rel=1e-4)


def test_normalize_socrates_derived_period_delta():
    block = normalize(
        deck_raw=None,
        insights_raw=SAMPLE_INSIGHTS_RAW,
        period="June 2026",
        product="Base Product",
        report_type="mbr-land",
        writer="michael",
    )
    # (0.72 - 0.65) / 0.65
    expected = (0.72 - 0.65) / 0.65
    assert block.bd1_6_period_delta_pct == pytest.approx(expected, rel=1e-4)


def test_normalize_socrates_organic_share_derived():
    block = normalize(
        deck_raw=None,
        insights_raw=SAMPLE_INSIGHTS_RAW,
        period="June 2026",
        product="Base Product",
        report_type="mbr-land",
        writer="michael",
    )
    # organic_share not in insights_raw, so derived as 1 - paid_share
    assert block.organic_share == pytest.approx(1.0 - 0.72)


def test_normalize_socrates_channels():
    block = normalize(
        deck_raw=None,
        insights_raw=SAMPLE_INSIGHTS_RAW,
        period="June 2026",
        product="Base Product",
        report_type="mbr-land",
        writer="michael",
    )
    assert len(block.channels) == 2
    assert block.channels[0].channel == "Paid Search"
    assert block.channels[0].bd1_6 == 450
    assert block.channels[1].channel == "Paid Social"


def test_normalize_socrates_data_sources():
    block = normalize(
        deck_raw=None,
        insights_raw=SAMPLE_INSIGHTS_RAW,
        period="June 2026",
        product="Base Product",
        report_type="mbr-land",
        writer="michael",
    )
    assert "Socrates" in block.data_sources
    assert "Optimal deck" not in block.data_sources


def test_normalize_data_lag_flag_true():
    raw = dict(SAMPLE_INSIGHTS_RAW)
    raw["data_lag_flag"] = True
    block = normalize(
        deck_raw=None,
        insights_raw=raw,
        period="week ending June 13 2026",
        product="Jira",
        report_type="tofu-weekly",
        writer="armando",
    )
    assert block.data_lag_flag is True


# ---------------------------------------------------------------------------
# normalize: deck-only
# ---------------------------------------------------------------------------

def test_normalize_deck_only_metrics():
    block = normalize(
        deck_raw=SAMPLE_DECK_RAW,
        insights_raw=None,
        period="June 2026",
        product="Base Product",
        report_type="mbr-land",
        writer="michael",
    )
    assert block.bd1_6_actuals == pytest.approx(0.72)
    assert block.bd1_6_target == pytest.approx(0.70)
    assert block.bd1_6_prior_period == pytest.approx(0.65)
    assert block.spend == pytest.approx(1500000)


def test_normalize_deck_only_qualitative():
    block = normalize(
        deck_raw=SAMPLE_DECK_RAW,
        insights_raw=None,
        period="June 2026",
        product="Base Product",
        report_type="mbr-land",
        writer="michael",
    )
    assert len(block.competitors) == 1
    assert block.competitors[0].name == "Acme Corp"
    assert "free tier" in block.competitors[0].action

    assert len(block.opportunities) == 1
    assert block.opportunities[0].owner == "Sarah"
    assert block.opportunities[0].timeline == "Jun 30"

    assert len(block.risks) == 1
    assert block.risks[0].owner == "CAC team"


def test_normalize_deck_only_data_sources():
    block = normalize(
        deck_raw=SAMPLE_DECK_RAW,
        insights_raw=None,
        period="June 2026",
        product="Base Product",
        report_type="mbr-land",
        writer="michael",
    )
    assert "Optimal deck" in block.data_sources
    assert "Socrates" not in block.data_sources


# ---------------------------------------------------------------------------
# normalize: both sources, Socrates takes priority for quant metrics
# ---------------------------------------------------------------------------

def test_normalize_socrates_overrides_deck_for_actuals():
    # Deck says 0.72, Socrates says 0.80: Socrates wins
    raw = dict(SAMPLE_INSIGHTS_RAW)
    raw["bd1_6_actuals"] = 0.80
    block = normalize(
        deck_raw=SAMPLE_DECK_RAW,
        insights_raw=raw,
        period="June 2026",
        product="Base Product",
        report_type="mbr-land",
        writer="michael",
    )
    assert block.bd1_6_actuals == pytest.approx(0.80)


def test_normalize_both_sources_listed():
    block = make_block()
    assert "Socrates" in block.data_sources
    assert "Optimal deck" in block.data_sources


def test_normalize_both_has_qualitative_from_deck():
    block = make_block()
    assert len(block.competitors) == 1
    assert len(block.opportunities) == 1
    assert len(block.risks) == 1


# ---------------------------------------------------------------------------
# normalize: missing data tracking
# ---------------------------------------------------------------------------

def test_normalize_missing_fields_when_no_sources():
    # Minimal insights with no cac/ltv/cpbd1_6 to confirm missing tracking
    raw = {
        "bd1_6_actuals": 0.72,
        "bd1_6_target": 0.70,
        "paid_share": 0.72,
    }
    block = normalize(
        deck_raw=None,
        insights_raw=raw,
        period="June 2026",
        product="Base Product",
        report_type="mbr-land",
        writer="michael",
    )
    assert "bd1_6_prior_period" in block.missing_fields
    assert "spend" in block.missing_fields
    assert "cac" in block.missing_fields


def test_normalize_no_missing_when_all_provided():
    block = make_block(deck=None)
    # Socrates sample has all quantitative fields; organic_share is derived
    quant_fields = [
        "bd1_6_actuals", "bd1_6_target", "bd1_6_prior_period",
        "spend", "cac", "ltv_to_cac_ratio", "cpbd1_6", "paid_share",
    ]
    for f in quant_fields:
        assert f not in block.missing_fields, f"{f} should not be missing"


# ---------------------------------------------------------------------------
# normalize: edge cases
# ---------------------------------------------------------------------------

def test_normalize_zero_prior_period_no_crash():
    raw = dict(SAMPLE_INSIGHTS_RAW)
    raw["bd1_6_prior_period"] = 0
    block = normalize(
        deck_raw=None,
        insights_raw=raw,
        period="June 2026",
        product="Base Product",
        report_type="mbr-land",
        writer="michael",
    )
    # No division by zero; delta should be None
    assert block.bd1_6_period_delta_pct is None


def test_normalize_zero_target_no_crash():
    raw = dict(SAMPLE_INSIGHTS_RAW)
    raw["bd1_6_target"] = 0
    block = normalize(
        deck_raw=None,
        insights_raw=raw,
        period="June 2026",
        product="Base Product",
        report_type="mbr-land",
        writer="michael",
    )
    assert block.bd1_6_vs_target_pct is None


def test_normalize_empty_channels():
    raw = dict(SAMPLE_INSIGHTS_RAW)
    raw["channels"] = []
    block = normalize(
        deck_raw=None,
        insights_raw=raw,
        period="June 2026",
        product="Base Product",
        report_type="mbr-land",
        writer="michael",
    )
    assert block.channels == []


def test_normalize_no_competitors_in_deck():
    deck = dict(SAMPLE_DECK_RAW)
    deck.pop("competitors", None)
    block = normalize(
        deck_raw=deck,
        insights_raw=None,
        period="June 2026",
        product="Base Product",
        report_type="mbr-land",
        writer="michael",
    )
    assert block.competitors == []


def test_normalize_metadata():
    block = make_block(report_type="tofu-weekly", writer="val")
    assert block.period == "June 2026"
    assert block.product == "Base Product"
    assert block.report_type == "tofu-weekly"
    assert block.writer == "val"


# ---------------------------------------------------------------------------
# parse_deck_file
# ---------------------------------------------------------------------------

def test_parse_deck_file(tmp_path):
    deck_md = tmp_path / "deck.md"
    deck_md.write_text(
        "## BD1-6 Metrics\n"
        "actuals: 0.72\n"
        "target: 0.70\n\n"
        "## Spend\n"
        "amount: 1500000\n\n"
        "## Competitors\n"
        "Acme: new product; 10% CAC lift\n\n"
        "## Opportunities\n"
        "- New audience; Sarah; +10%; Jul 1\n\n"
        "## Risks\n"
        "- Spend spike; ops; +$10 CAC; gate: CAC > 90\n"
    )
    raw = parse_deck_file(deck_md)
    assert "bd1_6_metrics" in raw
    assert any("actuals: 0.72" in line for line in raw["bd1_6_metrics"])
    assert "competitors" in raw
    assert "opportunities" in raw
    assert "risks" in raw


def test_parse_deck_file_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_deck_file(tmp_path / "nonexistent.md")


def test_parse_deck_file_empty_sections(tmp_path):
    deck_md = tmp_path / "empty.md"
    deck_md.write_text("## BD1-6 Metrics\n\n## Spend\n")
    raw = parse_deck_file(deck_md)
    # Sections exist but are empty lists
    assert raw.get("bd1_6_metrics", []) == []
    assert raw.get("spend", []) == []


# ---------------------------------------------------------------------------
# parse_insights_file
# ---------------------------------------------------------------------------

def test_parse_insights_file(tmp_path):
    f = tmp_path / "insights.json"
    f.write_text(json.dumps(SAMPLE_INSIGHTS_RAW))
    raw = parse_insights_file(f)
    assert raw["bd1_6_actuals"] == pytest.approx(0.72)
    assert len(raw["channels"]) == 2


def test_parse_insights_file_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_insights_file(tmp_path / "nonexistent.json")


def test_parse_insights_file_invalid_json(tmp_path):
    import json as _json
    f = tmp_path / "bad.json"
    f.write_text("not valid json {{{")
    with pytest.raises(_json.JSONDecodeError):
        parse_insights_file(f)


# ---------------------------------------------------------------------------
# render_insights_block
# ---------------------------------------------------------------------------

def test_render_insights_block_contains_key_fields():
    block = make_block()
    rendered = render_insights_block(block)
    assert "INSIGHTS BLOCK" in rendered
    assert "0.72" in rendered
    assert "0.70" in rendered
    assert "$1,500,000" in rendered
    assert "72.0%" in rendered
    assert "Paid Search" in rendered
    assert "Acme Corp" in rendered
    assert "Sarah" in rendered


def test_render_insights_block_lag_flag_shown():
    raw = dict(SAMPLE_INSIGHTS_RAW)
    raw["data_lag_flag"] = True
    block = normalize(
        deck_raw=None, insights_raw=raw,
        period="week ending June 13 2026", product="Jira",
        report_type="tofu-weekly", writer="armando",
    )
    rendered = render_insights_block(block)
    assert "understated" in rendered


def test_render_insights_block_missing_data_section():
    raw = {"bd1_6_actuals": 0.72, "bd1_6_target": 0.70, "paid_share": 0.60}
    block = normalize(
        deck_raw=None, insights_raw=raw,
        period="June 2026", product="Base Product",
        report_type="mbr-land", writer="michael",
    )
    rendered = render_insights_block(block)
    assert "MISSING DATA" in rendered
    assert "spend" in rendered


def test_render_insights_block_no_em_dashes():
    block = make_block()
    rendered = render_insights_block(block)
    assert "\u2014" not in rendered
    assert "\u2013" not in rendered


# ---------------------------------------------------------------------------
# render_tofu_draft
# ---------------------------------------------------------------------------

def test_render_tofu_draft_structure():
    block = make_block(report_type="tofu-weekly", writer="armando")
    rendered = render_tofu_draft(block)
    assert "TOFU:" in rendered
    assert "BD1-6:" in rendered
    assert "Spend:" in rendered
    assert "directional" in rendered


def test_render_tofu_draft_bd1_6_values():
    block = make_block(report_type="tofu-weekly")
    rendered = render_tofu_draft(block)
    assert "0.72" in rendered
    assert "0.70" in rendered


def test_render_tofu_draft_lag_note():
    raw = dict(SAMPLE_INSIGHTS_RAW)
    raw["data_lag_flag"] = True
    block = normalize(
        deck_raw=None, insights_raw=raw,
        period="week ending June 13 2026", product="Jira",
        report_type="tofu-weekly", writer="armando",
    )
    rendered = render_tofu_draft(block)
    assert "bake lag" in rendered


def test_render_tofu_draft_opportunity_shown():
    block = make_block(report_type="tofu-weekly")
    rendered = render_tofu_draft(block)
    assert "Sarah" in rendered


def test_render_tofu_draft_no_opportunities_placeholder():
    raw = dict(SAMPLE_INSIGHTS_RAW)
    block = normalize(
        deck_raw=None, insights_raw=raw,
        period="June 2026", product="Base Product",
        report_type="tofu-weekly", writer="michael",
    )
    rendered = render_tofu_draft(block)
    assert "not available" in rendered or "Sarah" in rendered


def test_render_tofu_draft_no_em_dashes():
    block = make_block(report_type="tofu-weekly")
    rendered = render_tofu_draft(block)
    assert "\u2014" not in rendered
    assert "\u2013" not in rendered


# ---------------------------------------------------------------------------
# render_mbr_draft
# ---------------------------------------------------------------------------

def test_render_mbr_draft_structure():
    block = make_block()
    rendered = render_mbr_draft(block)
    assert "LAND:" in rendered
    assert "Highlights" in rendered
    assert "What's Coming" in rendered
    assert "DRAFT" in rendered


def test_render_mbr_draft_metrics_present():
    block = make_block()
    rendered = render_mbr_draft(block)
    assert "0.72" in rendered
    assert "0.70" in rendered
    assert "72.0%" in rendered
    assert "$1,500,000" in rendered
    assert "35.0x" in rendered


def test_render_mbr_draft_channels_present():
    block = make_block()
    rendered = render_mbr_draft(block)
    assert "Paid Search" in rendered
    assert "Paid Social" in rendered


def test_render_mbr_draft_competitive_present():
    block = make_block()
    rendered = render_mbr_draft(block)
    assert "Acme Corp" in rendered


def test_render_mbr_draft_writer_instruction():
    block = make_block(writer="val")
    rendered = render_mbr_draft(block)
    assert "val" in rendered


def test_render_mbr_draft_missing_data_listed():
    raw = {"bd1_6_actuals": 0.72, "bd1_6_target": 0.70}
    block = normalize(
        deck_raw=None, insights_raw=raw,
        period="June 2026", product="Base Product",
        report_type="mbr-land", writer="michael",
    )
    rendered = render_mbr_draft(block)
    assert "Missing data" in rendered


def test_render_mbr_draft_no_em_dashes():
    block = make_block()
    rendered = render_mbr_draft(block)
    assert "\u2014" not in rendered
    assert "\u2013" not in rendered


def test_render_mbr_draft_period_delta_up():
    block = make_block()
    rendered = render_mbr_draft(block)
    assert "up from" in rendered


def test_render_mbr_draft_period_delta_down():
    raw = dict(SAMPLE_INSIGHTS_RAW)
    raw["bd1_6_actuals"] = 0.60   # below prior of 0.65
    block = normalize(
        deck_raw=None, insights_raw=raw,
        period="June 2026", product="Base Product",
        report_type="mbr-land", writer="michael",
    )
    rendered = render_mbr_draft(block)
    assert "down from" in rendered


# ---------------------------------------------------------------------------
# CLI integration (main)
# ---------------------------------------------------------------------------

def test_main_mbr_land_from_json(tmp_path):
    from agents.mbr_insights_agent import main

    insights_file = tmp_path / "insights.json"
    insights_file.write_text(json.dumps(SAMPLE_INSIGHTS_RAW))
    output_file = tmp_path / "draft.txt"

    main([
        "--insights-file", str(insights_file),
        "--report-type", "mbr-land",
        "--period", "June 2026",
        "--product", "Base Product",
        "--writer", "michael",
        "--output", str(output_file),
    ])

    content = output_file.read_text()
    assert "LAND:" in content
    assert "0.72" in content


def test_main_tofu_weekly_from_json(tmp_path):
    from agents.mbr_insights_agent import main

    insights_file = tmp_path / "insights.json"
    insights_file.write_text(json.dumps(SAMPLE_INSIGHTS_RAW))
    output_file = tmp_path / "tofu.txt"

    main([
        "--insights-file", str(insights_file),
        "--report-type", "tofu-weekly",
        "--period", "week ending June 13 2026",
        "--product", "Jira",
        "--writer", "armando",
        "--output", str(output_file),
    ])

    content = output_file.read_text()
    assert "TOFU:" in content
    assert "0.72" in content


def test_main_dump_insights_flag(tmp_path):
    from agents.mbr_insights_agent import main

    insights_file = tmp_path / "insights.json"
    insights_file.write_text(json.dumps(SAMPLE_INSIGHTS_RAW))
    output_file = tmp_path / "full.txt"

    main([
        "--insights-file", str(insights_file),
        "--report-type", "mbr-land",
        "--period", "June 2026",
        "--product", "Base Product",
        "--writer", "michael",
        "--output", str(output_file),
        "--dump-insights",
    ])

    content = output_file.read_text()
    assert "INSIGHTS BLOCK" in content
    assert "LAND:" in content


def test_main_from_deck_file(tmp_path):
    from agents.mbr_insights_agent import main

    deck_file = tmp_path / "deck.md"
    deck_file.write_text(
        "## BD1-6 Metrics\nactuals: 0.72\ntarget: 0.70\nprior_period: 0.65\n\n"
        "## Spend\namount: 1200000\n\n"
        "## Competitors\nRival Co: new free tier; 10% CAC pressure\n\n"
        "## Opportunities\n- Expand mid-market; Sarah; +15%; Jul 1\n\n"
        "## Risks\n- Spend spike; Ops; +$10 CAC; gate: CAC > 90\n"
    )
    output_file = tmp_path / "draft.txt"

    main([
        "--deck-file", str(deck_file),
        "--report-type", "mbr-land",
        "--period", "June 2026",
        "--product", "Base Product",
        "--writer", "michael",
        "--output", str(output_file),
    ])

    content = output_file.read_text()
    assert "LAND:" in content
    assert "0.72" in content


def test_main_no_source_exits(tmp_path):
    from agents.mbr_insights_agent import main
    import sys

    with pytest.raises(SystemExit):
        main([
            "--report-type", "mbr-land",
            "--period", "June 2026",
            "--product", "Base Product",
        ])
