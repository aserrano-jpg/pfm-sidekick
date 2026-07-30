# TOFU/MBR Weekly Report Writer

## Purpose

Automates the generation of the **LAND section** of monthly MBRs by:
1. Extracting performance and forward-looking data from Optimal reporting decks (Google Slides)
2. Mapping data to the LAND framework: Highlights (performance analysis) + What's Coming (future fuel and fill)
3. Generating narrative subsections using the assigned team member's voice and writing style

LAND focuses on customer acquisition, new logos (Base Product), and paid channel performance. The skill applies precise tone, structure, and word choice based on the writer's profile (Michael Wong, Armando Serrano, or Val Keeranan), ensuring consistency with team standards.

---

## When to Use

- Monthly MBR LAND section generation (Highlights subsection)
- Monthly MBR LAND section generation (What's Coming subsection)
- Rapid Optimal deck to LAND narrative conversion with voice consistency
- Competitive or market context for LAND (customer acquisition landscape)
- Base Product and paid channel performance narrative

---

## Inputs

### Required
- **Deck URL:** Public or shareable Google Slides link to Optimal reporting deck (LAND section slides)
- **Assigned Writer:** Michael Wong, Armando Serrano, or Val Keeranan
- **LAND Subsection:** Highlights or What's Coming
- **Month:** Month and year reporting period (e.g., "May 2026")
- **Product:** Product or channel being analyzed (e.g., "Base Product", "Paid Search")

### Optional
- **Prior Period Data:** Previous month metrics for trend context
- **Target Metrics:** BD1-6 target (e.g., 0.7) or other KPIs to reference

---

## Outputs

### LAND Highlights Subsection
Performance analysis (150-250 words) with why metrics performed as they did:
- Lead metric: Base Product BD1-6 or customer acquisition volume
- Supporting metrics: Paid channel performance, CAC, LTV, ROI
- Period comparison and trend analysis
- Root causes or drivers of performance
- Confidence level on projections

**Example:**
```
LAND: Highlights
Base Product BD1-6 reached 0.7 target in May, up from 0.65 in April. Paid channels drove 72% of volume; organic email contributed 28%. CAC rose 8% month-over-month due to increased competition on paid search; however, LTV held steady at 35x CAC, indicating sustainable unit economics. If paid channel spend holds, we expect June to exceed target by 5-10% (confidence: high).
```

### LAND What's Coming Subsection
Forward-looking narrative (150-250 words) focused on fueling growth or filling gaps:
- Upcoming paid channel initiatives (new audiences, creative, targeting)
- Product or positioning changes that affect acquisition
- Market or competitive changes affecting LAND dynamics
- Recommended budget allocation or strategy shifts
- Risks or opportunities in pipeline

**Example:**
```
LAND: What's Coming
We're launching two new paid audiences in June targeting mid-market, expected to add 15-20% volume. Pending: creative refresh (delayed one week; Sarah owns). Competitive landscape is heating up; we're seeing three new entrants. Risk: if they match our spend, CAC could rise another 10-15%. Recommendation: reserve $75K contingency budget for aggressive bidding if needed. Opportunity: our existing customer base offers 5K lookalike volume untested; recommend 10% test allocation.
```

---

## Team Voice Profiles

All outputs adhere to the shared writing standards in @writing-style.md. Per-writer profiles below:

### Michael Wong
- **Style:** Strategic analyst voice. Lead with data, then narrative context
- **Strengths:** Connects metrics to business outcomes, identifies root causes
- **Sentence Pattern:** Short, confident statements. No hedging
- **Vocabulary:** Precise technical language; avoids corporate jargon
- **Example Phrasing:** "Spend increased 12%. Root cause: CPC inflation from competitor bid escalation."
- **See:** references/voice-michael.md

### Armando Serrano
- **Style:** Operational/execution voice. Focus on what to do and why
- **Strengths:** Clear action items, structured priorities, process clarity
- **Sentence Pattern:** Direct imperatives or outcome-focused statements
- **Vocabulary:** Action-oriented, specific (names channels, products, teams)
- **Example Phrasing:** "We need to shift budget from Channel A to Channel B. Rationale: ROI improved 18% on B this week."
- **See:** references/voice-armando.md

### Val Keeranan
- **Style:** Risk and opportunity voice. Flags implications and second-order effects
- **Strengths:** Surfaces non-obvious connections, identifies threats and upside early
- **Sentence Pattern:** Causality-driven (if X, then Y); conditional reasoning
- **Vocabulary:** Precise; distinguishes between correlation and causation
- **Example Phrasing:** "If competitor launches in Q3, our CAC will likely rise 20-30%. Recommend contingency reserve now."
- **See:** references/voice-val.md

---

## Usage Examples

### Example 1: LAND Highlights (Michael's voice)
**Input:**
```
Optimal Deck: [slide 12-15, LAND section]
Writer: Michael
Subsection: Highlights
Period: May 2026
Data: BD1-6 0.7 (target met), Paid volume 72%, CAC +8%, LTV 35x CAC
```

**Output (Michael's voice):**
"Base Product BD1-6 reached 0.7 target in May, up from 0.65 in April. Paid channels drove 72% of volume; organic email contributed 28%. CAC rose 8% month-over-month due to increased competition on paid search; however, LTV held steady at 35x CAC, indicating sustainable unit economics. Root cause of CAC increase: three competitors entered the market, each deploying $1.5M spend. Expected CAC trajectory: plateau in June as competitive intensity stabilizes. Confidence: medium (depends on competitive spend levels). Recommendation: monitor CPC weekly; if CAC exceeds $85 (current $72), trigger contingency bid reduction strategy."

### Example 2: LAND What's Coming (Armando's voice)
**Input:**
```
Optimal Deck: [slide 16, LAND forward plans]
Writer: Armando
Subsection: What's Coming
Period: June 2026 forecast
Data: New audiences launching, creative refresh pending, contingency budget needed
```

**Output (Armando's voice):**
"Launching two new paid audiences in June targeting mid-market; expected volume: 15-20% lift. Sarah owns creative variants; launch timeline: June 3. Pending: creative refresh (delayed one week due to design cycle; Michael owns). Allocate $30K of June budget to new audiences; hold $50K contingency if competitive pressure spikes. If CAC rises above $85, trigger bid reduction on low-funnel terms (saves $12K/month, costs 8% volume). Trade-off: we preserve margin at cost of growth rate. Gate: if new audiences convert 10% below existing average, scale back to 5% budget allocation. Competitive threat: three new entrants entered market; recommend daily spend tracking through end of June."

### Example 3: LAND Highlights (Val's voice)
**Input:**
```
Optimal Deck: [metrics and market data]
Writer: Val
Subsection: Highlights
Period: May 2026
Data: BD1-6 target met, CAC rising, market saturation signals
```

**Output (Val's voice):**
"Base Product reached target (0.7 BD1-6), but underlying dynamics signal caution. CAC rose 8% despite flat volume; causation: competitive spend influx, not audience depletion. If competitors sustain spend levels, expect CAC +15-20% in Q3 (confidence: high based on cohort entry patterns). Second-order effect: higher CAC compresses unit economics, requiring either LTV improvement or price increase to maintain 35x CAC ratio. Watch for: if LTV declines below 30x CAC in June, this signals conversion efficiency loss. Gate for escalation: LTV drops below 30x or CAC hits $85. Contingency: reserve $75K competitive response budget; recommend quarterly review of acquisition strategy mix (paid vs. organic). Best case: competitors reduce spend, CAC normalizes. Base case: CAC holds +8-12%. Worst case: CAC +25%, forcing budget reallocation."

---

## Technical Notes

### Google Slides Extraction
- Uses Google Slides API or public deck export (PDF/HTML)
- Extracts text and tables from specified slide ranges
- Maps slide titles/sections to predefined data categories: Metrics, Spend, Biz-signups, Competitors, Opportunities
- Validates numeric extraction (checks for currency, percentages, variance formats)

### Data Mapping
Standard extraction map for LAND section:

| Optimal Section | LAND Highlights | LAND What's Coming |
|---|---|---|
| BD1-6 metrics | Primary metric, performance vs. target | Target forecast |
| Paid channel performance | Volume source, CAC, ROI | Planned initiatives |
| Organic/email metrics | Secondary volume source | Pipeline or audience expansion |
| Competitor activity | Market context / pressure on CAC | Competitive threat or budget reserve |
| Product/positioning changes | (if applicable) | Upcoming launches or pivots |
| Customer cohort analysis | LTV, retention signals | Upsell or cross-sell opportunities |
| Blockers or risks | (if applicable) | Risks or contingencies |

### Voice Application
1. Extract structured data (numbers, trends, risks)
2. Select writer voice profile
3. Expand into narrative using writer's sentence patterns and vocabulary
4. Apply @writing-style.md rules (no em-dashes, no fluff, specific over vague)
5. Validate for tone consistency before output

---

## Examples & Templates

See references/:
- `voice-michael.md`: Michael Wong voice examples and templates
- `voice-armando.md`: Armando Serrano voice examples and templates
- `voice-val.md`: Val Keeranan voice examples and templates
- `mbr-template.md`: Standard MBR section structure

---

## Constraints & Limitations

- **Data Quality:** Extraction accuracy depends on Optimal deck structure consistency. Semi-structured decks may require manual cleanup
- **Voice Fallback:** If writer profile is unknown, defaults to neutral analytical voice (Michael pattern)
- **Context Limit:** Provides narrative only for extracted deck data. Does not invent metrics or make external API calls for validation
- **Manual Review:** Recommend 5-minute review of output before publishing to confirm data accuracy and tone fit

---

## Related Skills

- `@skills/analyst/SKILL.md` - For deeper CAC, LTV, ROI analysis and trend interpretation
- `@skills/confluence-writer/SKILL.md` - For formatting LAND sections in Confluence MBR pages
- `@skills/executive-communication/SKILL.md` - For escalating LAND risks or opportunities to leadership
