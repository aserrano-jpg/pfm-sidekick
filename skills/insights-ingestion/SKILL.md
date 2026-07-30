# Insights Ingestion Skill

## Purpose

Ingests raw data from Optimal decks and Socrates queries, normalizes it into a
standard insights block, and hands it off to `@skills/tofu-mbr-writer/SKILL.md`
for narrative generation. Covers both weekly TOFU reports and monthly MBR LAND
sections.

---

## When to Use

- Before generating any TOFU weekly report
- Before generating any MBR LAND section (Highlights or What's Coming)
- When you have data in multiple places (deck + Socrates) and need to combine it
- When you want a repeatable, consistent intake step before writing

---

## Report Types

| Report | Cadence | Primary Output |
|---|---|---|
| TOFU Weekly | Weekly | 4-6 bullet summary of paid + organic performance |
| MBR LAND | Monthly | Highlights + What's Coming narrative (300-500 words) |

---

## Inputs

### Required
- **Report type:** `tofu-weekly` or `mbr-land`
- **Period:** Week ending date (e.g., "week ending June 13 2026") or month (e.g., "May 2026")
- **Product:** Product or channel in scope (e.g., "Base Product", "Paid Search", "JPD")

### Optional (provide at least one data source)
- **Optimal deck URL:** Google Slides link to the reporting deck
- **Socrates query results:** Paste query output directly, or request that the agent run standard queries
- **Prior period data:** Previous week or month metrics for trend context
- **Writer:** Michael, Armando, or Val (defaults to Michael if not specified)

---

## Step-by-Step Workflow

### Step 1: Determine data sources

Check which sources are available:

```
[ ] Optimal deck URL provided
[ ] Socrates query results available (paste or request)
[ ] Prior period data available
```

If no Optimal deck is provided, skip deck extraction and work from Socrates only.
If no Socrates data is provided, extract from deck only and flag gaps.

---

### Step 2: Extract from Optimal deck (if URL provided)

Open the deck and extract the following by section:

| Section to find | Data to extract |
|---|---|
| BD1-6 / Activations | Actuals, target, prior period, MoM or WoW delta |
| Paid channel performance | Spend, volume, CPBD1-6, CAC, by channel |
| Organic / email | Volume, share of total, WoW trend |
| Competitors | Named competitors, actions taken, estimated impact |
| Opportunities | Planned initiatives, new audiences, budget shifts |
| Risks / blockers | Named blockers, owners, estimated impact |

Flag any section where data is missing or ambiguous. Do not invent numbers.

---

### Step 3: Pull Socrates data (if requested or deck is incomplete)

Load `@skills/analyst/SKILL.md` to route queries correctly. Use the routing
table in `references/source-routing.md` to select the right table.

Standard queries to run based on report type:

**For TOFU weekly:**
- WoW BD1-6 trend (paid.md query: WoW BD1-6 trend)
- Channel mix overview (gtm.md query: channel mix overview)
- Paid vs. organic split (gtm.md query: paid vs. organic split)

**For MBR LAND:**
- BD1-6 actuals by product monthly (paid.md query: BD1-6 by month)
- Land vs. xflow motion breakdown (paid.md query)
- Channel group breakdown (bd1-6.md query)
- YoY comparison (bd1-6.md query: if month is quarter-end)

See `references/socrates-queries.md` for ready-to-run SQL templates.

Always flag: BD1-6 has a 7-day bake lag. Data from the last 7 days will be
understated. Note this in the insights block.

---

### Step 4: Normalize into insights block

After extraction, produce a structured insights block in this exact format.
This is the handoff to the MBR writer skill.

```
INSIGHTS BLOCK
==============
Period: [month or week ending date]
Product: [product name]
Report type: [tofu-weekly | mbr-land]
Writer: [Michael | Armando | Val]
Data sources: [Optimal deck URL, Socrates, or both]

METRICS
-------
BD1-6 actuals: [number or range]
BD1-6 target: [number]
BD1-6 vs. target: [+/- delta and %]
BD1-6 prior period: [number]
BD1-6 MoM or WoW delta: [+/- delta and %]
Paid channel volume share: [%]
Organic volume share: [%]
Spend: [$amount] (directional)
CAC: [$amount]
LTV to CAC ratio: [Xx]
CPBD1-6: [$amount]
Data lag flag: [yes/no - flag if last 7 days understated]

CHANNEL BREAKDOWN
-----------------
[Channel]: [BD1-6 volume] | [spend] | [CPBD1-6] | [WoW or MoM delta]
(repeat for each material channel)

COMPETITIVE
-----------
[Named competitor]: [action] | [estimated impact on CAC or volume]
(or: No material competitive signals this period)

OPPORTUNITIES
-------------
- [Initiative]: [owner if known] | [expected lift] | [timeline]
(list up to 3)

RISKS AND BLOCKERS
------------------
- [Risk]: [owner if known] | [estimated impact] | [gate or threshold]
(or: No material risks flagged this period)

MISSING DATA
------------
- [List any metrics that could not be sourced, and where to find them]
(or: None)
```

Do not invent any number. If a field cannot be filled from available sources,
write `[not available - check [source]]`.

---

### Step 5: Hand off to report writer

Once the insights block is complete, pass it to the appropriate writer skill:

**For MBR LAND section:**
Load `@skills/tofu-mbr-writer/SKILL.md` and provide:
- The full insights block as input
- Writer name
- Subsection: Highlights, What's Coming, or both

**For TOFU weekly:**
Load `@skills/tofu-mbr-writer/SKILL.md` and request TOFU format (4-6 bullets,
data-forward, no narrative padding).

---

## TOFU Weekly Format

TOFU weekly is shorter and more punchy than MBR. Target: 4-6 bullets, each one
sentence. Lead with the number, then the "so what".

```
TOFU: Week ending [date] - [Product]

- BD1-6: [actuals] vs. [target] ([delta]). [One-line root cause or trend note.]
- Paid volume: [%] of total. [Top channel] drove [X%]; [channel] down [X%] WoW.
- Spend: [$amount] ([WoW delta]). CPBD1-6: [$amount] ([WoW delta]).
- [Key opportunity or initiative]: [owner] targeting [launch date].
- [Key risk or watch item]: [threshold or gate].
- [Optional: competitive signal if material.]
```

No prose padding. No "it's worth noting". No em dashes. Numbers in every bullet.

---

## Quality Checks Before Handoff

Run through this list before passing the insights block to the writer:

- [ ] All numbers have a source (deck slide number or Socrates query name)
- [ ] BD1-6 lag flag noted if reporting last 7 days
- [ ] Spend marked as directional (not precise)
- [ ] No fields invented - missing data flagged explicitly
- [ ] Competitors named specifically (not "a competitor")
- [ ] Opportunities have owner or "owner: TBD" if unknown
- [ ] Risks have a threshold or gate (not vague "could be an issue")
- [ ] No em dashes, no AI tropes, no banned vocabulary from writing-style.md

---

## Related Skills

- `@skills/analyst/SKILL.md` - Routes Socrates queries to the right table
- `@skills/tofu-mbr-writer/SKILL.md` - Generates narrative from the insights block
- `@skills/confluence-writer/SKILL.md` - Formats the draft for Confluence (after review)

---

## Constraints

- Never publish directly. This skill produces a draft for human review only.
- Never invent data. If a number is missing, say so and name the correct source.
- Spend figures are directional. Flag them as such every time.
- BD1-6 has a 7-day bake lag. Always note this when reporting recent periods.
