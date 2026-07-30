# Optimal Deck Extract Template

Use this file as your monthly/weekly starting point. Fill in values from the
Optimal reporting deck, then pass to `mbr_insights_agent.py` via `--deck-file`.

Copy this file for each report. Name it:
- MBR: `deck_extract_MMMYYYY.md` (e.g. `deck_extract_jun2026.md`)
- TOFU: `deck_extract_week_YYYYMMDD.md` (e.g. `deck_extract_week_20260613.md`)

Delete placeholder comments before running the agent.
All fields are optional. Leave a section empty if data is not in the deck.

---

## BD1-6 Metrics
actuals: [e.g. 0.72]
target: [e.g. 0.70]
prior_period: [e.g. 0.65 - prior month for MBR, prior week for TOFU]

---

## Spend
amount: [e.g. 1500000 - USD, no commas, no $ sign]

---

## Channels
[One line per material channel. Format: Channel Name: bd1_6=X, spend=Y]
[Example: Paid Search: bd1_6=450, spend=800000]
[Example: Paid Social: bd1_6=270, spend=400000]
[Leave blank if pulling channel data from Socrates instead]

---

## Competitors
[One line per competitor. Format: Competitor Name: action taken; estimated impact]
[Example: Acme Corp: launched new free tier; estimated +15% CAC pressure]
[Example: Rival Inc: increased spend 2x in paid search; watching CPC impact]
[Write "None" if no material competitive signals this period]

---

## Opportunities
[One line per initiative. Format: - Description; Owner; Expected lift; Timeline]
[Example: - Mid-market audience expansion; Sarah; +15-20% volume; Jun 30]
[Example: - Creative refresh for paid social; Design team; +5% CVR; Jul 7]
[Write "None" if no initiatives to flag]

---

## Risks
[One line per risk. Format: - Description; Owner; Estimated impact; Gate or threshold]
[Example: - CAC inflation if Acme sustains spend; CAC team; +$15 CAC; gate: CAC > $85]
[Example: - Creative delay blocking paid social launch; Sarah; -10% volume; gate: miss Jul 7]
[Write "None" if no risks to flag]
