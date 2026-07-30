# LAND Section Writer Skill: Quick Start

## What This Skill Does

Generates the **LAND section** of monthly MBRs by:
1. Extracting insights from Optimal reporting decks (Google Slides)
2. Mapping data to LAND framework: Highlights (performance analysis) + What's Coming (future initiatives, fuel or fill)
3. Writing in the assigned team member's voice (Michael, Armando, or Val)

Output: Two subsections totaling 300-500 words, ready for Confluence MBR page.

---

## Fastest Path: Use with Claude Now

### Step 1: Extract Deck Data

1. Open your Optimal reporting deck (Google Slides link) to LAND section slides
2. Copy the key data into a text file or Confluence snippet:
   ```
   # BD1-6 Metrics
   Target: 0.7
   May: 0.7 (achieved)
   April: 0.65
   
   # Volume Sources
   Paid: 72%
   Organic: 28%
   
   # Efficiency Metrics
   CAC: $72 (up 8% MoM)
   LTV: 35x CAC
   
   # Competitive Context
   Three new entrants, estimated $1.5M spend each
   
   # Planned Initiatives
   - Launch two new audiences June 3 (Sarah owns)
   - Creative refresh (pending)
   - Lookalike audience untested (5K volume)
   ```

3. Save as `land-extract.md` in your workspace

### Step 2: Call the Skill

**In VS Code Copilot Chat or Claude:**

```
@tofu-mbr-writer

Month: May 2026
Product: Base Product
Writer: Michael
Subsection: Highlights

Deck data:
[paste your extracted data]
```

Or for What's Coming subsection:

```
@tofu-mbr-writer

Month: June 2026
Product: Base Product
Writer: Armando
Subsection: What's Coming

Deck data:
[paste your extracted data]
```

### Step 3: Get Output

Copilot generates the LAND Highlights or What's Coming subsection in the writer's voice. Copy to Confluence MBR page.

---

## Longer Path: Integrate with Automation

### Setup (Optional)

If you want to run the Python CLI locally:

```bash
# Extract LAND deck data to markdown
cat land-extract.md

# Generate Highlights subsection (Michael's voice, May 2026, Base Product)
python tofu_mbr_writer.py \
  --deck-file land-extract.md \
  --writer michael \
  --subsection highlights \
  --month "May 2026" \
  --product "Base Product"

# Generate What's Coming subsection (Armando's voice, June 2026, Base Product)
python tofu_mbr_writer.py \
  --deck-file land-extract.md \
  --writer armando \
  --subsection what-coming \
  --month "June 2026" \
  --product "Base Product"

# Save to file
python tofu_mbr_writer.py \
  --deck-file land-extract.md \
  --writer michael \
  --subsection highlights \
  --month "May 2026" \
  --product "Base Product" \
  --output land-highlights-may-baseproduct.md
```

---

## Example Workflows

### Workflow 1: LAND Highlights Only (15 min)

1. Extract LAND metrics section from Optimal deck to `land-may.md`
2. In Copilot: `@tofu-mbr-writer month="May 2026" product="Base Product" writer=michael subsection=highlights deck=land-may.md`
3. Copilot generates Highlights subsection (150-250 words, root cause analysis)
4. Copy to Confluence LAND section
5. Done

### Workflow 2: Both LAND Subsections (25 min)

1. Extract full LAND data (metrics, initiatives, competitive context) to `land-may.md`
2. Generate Highlights (Michael): `@tofu-mbr-writer month="May 2026" product="Base Product" writer=michael subsection=highlights deck=land-may.md`
3. Generate What's Coming (Armando): `@tofu-mbr-writer month="June 2026" product="Base Product" writer=armando subsection=what-coming deck=land-may.md`
4. Combine both subsections on Confluence page
5. Manual review (3 min): verify numbers, confirm gates and contingencies, check for em-dashes
6. Publish

### Workflow 3: Multi-voice LAND Section (35 min)

Same as Workflow 2, but generate three versions for comparison:

1. Highlights: Michael's analytical voice (May 2026, Base Product, root causes, confidence)
2. Highlights: Val's risk voice (May 2026, Base Product, competitive threats, scenarios)
3. What's Coming: Armando's operational voice (June 2026, Base Product, actions, owners, trade-offs)
4. Pick the most appropriate voice for final LAND section or blend approaches
5. One team review and publish

---

## How to Use Each Writer

### Michael (Strategic Analyst) for LAND Highlights
Use when you need root cause analysis of performance and projections.

**Strengths:** Connects metrics to trends, explains why CAC/LTV moved, confidence levels on projections.

**Example prompt:**
```
@tofu-mbr-writer
Month: May 2026
Product: Base Product
Writer: Michael
Subsection: Highlights
Data: [BD1-6 0.7, CAC up 8%, LTV stable, 3 competitors entered]
Task: Why did CAC rise? What's the outlook? Confidence level?
```

### Armando (Operational Lead) for LAND What's Coming
Use when you need action items, budget allocation, ownership clarity.

**Strengths:** Clear budget shifts, specific owners, deadlines, trade-off framing.

**Example prompt:**
```
@tofu-mbr-writer
Month: June 2026
Product: Base Product
Writer: Armando
Subsection: What's Coming
Initiatives: [new audiences June 3, creative pending, lookalike test opportunity]
Task: Who owns each? What budget? What trade-offs? What if CAC spikes?
```

### Val (Risk Strategist) for LAND Highlights or What's Coming
Use when you need scenario planning, contingencies, second-order effect analysis.

**Strengths:** Surfaces competitive threats, flags if/then scenarios, defines gates.

**Example prompt:**
```
@tofu-mbr-writer
Month: May 2026
Product: Base Product
Writer: Val
Subsection: Highlights
Data: [3 new competitors, CAC +8%, market share stable]
Task: What happens if competitors sustain spend? When do we escalate? What's the gate?
```

---

## Tone Reference: Quick Cheat Sheet

| Writer | Best For | Key Phrases |
|--------|----------|-------------|
| Michael | Highlights (analysis) | Root cause, Expected trajectory, Confidence level, LTV signals |
| Armando | What's Coming (action) | Owns by [date], Allocate, Hold contingency, Trade-off |
| Val | Highlights (risk) or What's Coming (scenario) | If/then, Confidence, Second-order effect, Watch for, Gate |

---

## Validation Checklist (Before Publishing LAND Section)

- [ ] Month is specified correctly (e.g., "May 2026")
- [ ] Product is specified correctly (e.g., "Base Product", "Paid Search")
- [ ] BD1-6 target and actual numbers match Optimal deck
- [ ] Volume source percentages add to 100%
- [ ] CAC and LTV metrics are correct and sourced
- [ ] Competitive moves are named specifically (not "market conditions")
- [ ] All action items in What's Coming have owner and deadline
- [ ] Gates and contingencies use specific thresholds (e.g., "if CAC hits $85", not "if pressure rises")
- [ ] No em-dashes ("—"); use . or , or : instead
- [ ] Tone matches assigned writer voice
- [ ] Total length 300-500 words (Highlights + What's Coming combined)

---

## Prompt Templates

### Basic LAND Highlights Request
```
@tofu-mbr-writer

Month: May 2026
Product: Base Product
Writer: michael
Subsection: Highlights
Deck: [Google Slides URL or extracted data]

Key data:
- BD1-6: Target 0.7, Actual 0.7
- Volume sources: Paid 72%, Organic 28%
- CAC: $72 (up 8% MoM)
- LTV: 35x CAC
- Competitive: 3 new entrants, ~$1.5M spend each
```

### Basic LAND What's Coming Request
```
@tofu-mbr-writer

Month: June 2026
Product: Paid Search
Writer: armando
Subsection: What's Coming
Deck: [URL or extracted data]

Planned initiatives:
- New audiences launch June 3 (Sarah owns)
- Creative refresh (pending)
- Lookalike testing opportunity (5K volume)

Context:
- Competitive pressure on CAC
- Budget constraints or opportunities
- Risk gates or contingencies
```

### Full LAND Section Request (Both Subsections)
```
@tofu-mbr-writer

Month: May 2026
Product: Base Product

Generate full LAND section:

Highlights (Michael's voice): Analyze BD1-6 performance, volume sources, efficiency metrics, root causes, confidence levels

What's Coming (Armando's voice): Forward-looking initiatives, budget allocation, ownership, trade-offs, gates

Deck data:
[your complete LAND extract]

Target: 300-500 words total, ready for Confluence
```

---

## Troubleshooting

### Problem: Output doesn't sound like the writer

**Solution:** Add more examples or context. Include a sample from the writer's past reports if available. Example:
```
@tofu-mbr-writer
Writer: Armando
Reference style: [paste 1-2 sentences from a past Armando report]
[your request]
```

### Problem: Numbers are missing or wrong

**Solution:** Copy exact numbers from the Optimal deck into your extract. Include units (%, $, count). Example:
```
Bad: Spend went up
Good: Spend increased $18K to $340K (18% increase week-over-week)
```

### Problem: Output has em-dashes or banned words

**Solution:** In your request, add: "Apply @writing-style.md rules: no em-dashes, no 'delve/leverage/robust/streamline', no 'let's unpack'."

---

## Next Steps

1. **Immediate:** Use the skill in Copilot Chat to generate LAND Highlights for this month's MBR
2. **Short-term:** Build both Highlights and What's Coming subsections; combine on Confluence LAND section
3. **Medium-term:** Automate Optimal deck LAND slide extraction via Google Slides API
4. **Long-term:** Create Confluence template with LAND section pre-populated by skill output

---

## Support & Feedback

Questions about voice or output quality?
- Review the voice profiles: `references/voice-[writer].md`
- Check the LAND template: `references/mbr-template.md`
- Cross-reference @writing-style.md for tone rules

Feedback or updates?
- Update the relevant `voice-[writer].md` file with new LAND examples
- Modify `mbr-template.md` if LAND structure changes
- Flag in #product-reporting Slack channel

---

## Files in This Skill

```
skills/tofu-mbr-writer/
├── SKILL.md                          (LAND skill overview; data mapping; examples)
├── QUICKSTART.md                     (this file / workflows; templates; troubleshooting)
├── tofu_mbr_writer.py                (Python CLI for batch generation)
├── references/
│   ├── voice-michael.md              (Michael Wong voice profile + examples)
│   ├── voice-armando.md              (Armando Serrano voice profile + examples)
│   ├── voice-val.md                  (Val Keeranan voice profile + examples)
│   └── mbr-template.md               (LAND structure; checklist; tone rules)
```

---

## Writer Profiles at a Glance (LAND-Specific)

- **Michael Wong (Highlights):** Explain why BD1-6 performed as it did. Root causes, CAC/LTV trends, confidence levels.
- **Armando Serrano (What's Coming):** Tell us what to execute. Budget allocation, new initiatives, owners, deadlines, trade-offs.
- **Val Keeranan (Highlights or What's Coming):** Flag the risks. Competitive threat scenarios, CAC gates, contingencies, second-order effects.

Pick the voice that matches the LAND subsection and decision at hand.
