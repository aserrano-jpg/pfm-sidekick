# PFM Sidekick

A personal AI assistant config built for performance marketers at Atlassian. It gives Rovo Dev (the AI) the right context, skills, and rules to help you do your job — writing Confluence pages, querying data, communicating with leadership, and more.

This is not a software project. You do not need to know how to code to use it.

---

## What this is

When you chat with Rovo Dev, it starts with no knowledge of who you are, how you like to work, or what your job is. This repo fixes that. It tells the AI:

- Who you are and what you own
- How you like to write
- What tools and data sources to use for specific tasks
- How to format Confluence pages, talk to executives, query Socrates, and more

Think of it as a briefing document the AI reads before every conversation.

---

## How it works — the file structure

```
pfm-sidekick/
├── AGENTS.md               ← The AI reads this first, every session
├── writing-style.md        ← Your writing rules, applied to everything
├── skills/
│   ├── analyst/                  ← Data and metrics questions
│   ├── confluence-writer/        ← Confluence page building
│   ├── executive-communication/  ← Writing up to leadership
│   ├── skill-builder/            ← Building or improving other skills
│   └── slack-gif-creator/        ← Making custom Slack emoji and GIFs
```

---

## The key files

### `AGENTS.md`

The master briefing. The AI reads this at the start of every session. It contains:

- Your name, role, team, and manager
- What products you own
- How you like to communicate
- Which skills to load for which tasks
- Your Atlassian site URL and account ID

**This is the first file you should personalise.** Replace the placeholder fields (`[Your Name]`, `[Your Role]`, etc.) with your actual details.

### `writing-style.md`

Your personal writing rulebook. The AI applies this to every piece of content it writes for you — Confluence pages, Slack messages, Atlas updates, emails.

It covers:

- Core principles (lead with the answer, be specific, be short)
- Tone by content type (Atlas vs. MBR vs. Slack vs. email)
- A list of AI writing tropes to never use (the "delve", "tapestry", "it's worth noting" patterns)
- An example of what good reporting language actually looks like

---

## Skills — what they are and when to use them

Skills are instruction sets the AI loads on demand. They give the AI deep, specific knowledge for a particular task. You do not need to load them manually — the AI knows when to use each one based on what you ask.

### `skills/analyst/`

Load this for any data or metrics question.

Covers three dashboards:

- **Paid Performance** (`go/paiddash`) — paid channel spend, CPBD1-6, channel efficiency
- **GTM Dashboard** (`go/newgtmdash`) — page-level funnel, all-channel signups, entrances
- **Biz D1-6AI** (`go/fy26d16`) — OKR pacing, actuals vs. target, YoY

The skill routes your question to the right reference file automatically, writes the correct Socrates/Databricks SQL, and flags known data quirks (like the 7-day bake lag on BD1-6).

Contains three reference files in `skills/analyst/references/`:

- `paid.md` — paid channel table schema and query patterns
- `gtm.md` — GTM dashboard table schema and query patterns
- `bd1-6.md` — BD1-6 tracking table schema and OKR pacing logic

### `skills/confluence-writer/`

Load this when you want the AI to build or format a Confluence page.

Covers:

- Every Confluence component (panels, tables, status lozenges, layout sections, expands, smart links, task lists, emojis)
- When to use each component and when not to
- Four page architecture templates (review page, project update, decision page, reference page)
- Quality rules for structure, information density, and consistency
- Anti-patterns to avoid (wall of text, rainbow page, hidden critical info, mega-table)

Contains a reference file in `skills/confluence-writer/references/`:

- `adf-mechanics.md` — technical guide for building pages programmatically via the Confluence API

### `skills/executive-communication/`

Load this when writing to or about senior leaders — a Slack message to your VP, a pitch for a new budget, a tricky conversation with your manager, an MBR section.

Covers:

- The RLC framework (Recipient, Logic, Cognitive load)
- Written communication rules by format
- How to be direct without being a jerk
- How to present to executives (before, during, after)
- How to manage up and share a point of view
- A script bank for common situations (framing upfront, pushing back, asking for something, sharing bad news)

### `skills/skill-builder/`

Load this when you want to create a new skill, audit an existing one, or have the AI interview you to produce a `SKILL.md` from scratch.

Covers:

- The CIAO framework (Context, Instructions, Avoid, Output) for writing well-scoped skills
- How to interview yourself (or the user) to surface the inputs, rules, and output format a new skill needs
- How to register a new skill in the `AGENTS.md` Skills table so it loads automatically
- How to spot and rewrite weak skills (too vague, missing triggers, no examples)

Use this any time the AI keeps getting something wrong in the same way. That's a signal a skill is missing or under-specified.

### `skills/slack-gif-creator/`

Load this when you want to make a custom Slack emoji or animated GIF from scratch.

Covers:

- Slack's exact size and file requirements for emoji and GIFs
- A Python toolkit for building and optimising frames
- Animation concepts (easing, fade in/out, motion)
- Utilities for building, validating, and compressing GIFs

This skill has actual Python code in `skills/slack-gif-creator/core/` that the AI can run.

---

## How to set it up for yourself

1. **Download or clone this folder** to your local machine
2. **Open `AGENTS.md`** and replace every `[placeholder]` with your actual details
3. **Open `writing-style.md`** and adjust anything that does not match how you write
4. **Point Rovo Dev at this folder** as your workspace — it will find the files automatically

That's it. The AI reads the files at the start of every session. No installation, no code to run.

### Prefer to let Rovo Dev do the setup for you?

Once you have the folder open in Rovo Dev, paste this prompt and it will walk through the configuration with you:

```
I just downloaded the PFM Sidekick. Please read AGENTS.md and writing-style.md,
then ask me the questions needed to fill in all the placeholder fields
([Your Name], [Your Role], [Your Team], [Your Manager], [Add yours], and any others).
Once I answer, update both files with my real details.
```

Rovo Dev will ask you each question, then make the edits itself. You just answer.

---

## Let the agent build your AGENTS.md from scratch

If you'd rather not edit files at all, you can have Rovo Dev interview you and write your entire `AGENTS.md` from the ground up — including your role, what you own, how you like to work, and which skills to load.

### Step 1 — Bootstrap it

Paste this to start:

```
I want to set up my AGENTS.md from scratch. Don't use the placeholder template —
start fresh. Interview me to understand: who I am, my role and team, what products
or areas I own, how I like to communicate, what I want the AI to prioritise,
and which skills I'll use most. Ask one question at a time. Once you have
everything, write the AGENTS.md file.
```

The agent will ask you questions one at a time — role, team, what you own, how you like to work, what to prioritise. When you're done answering, it writes the file.

### Step 2 — Iterate on it

Once the first version exists, you can refine it through conversation. Some prompts to try:

```
Read my AGENTS.md and tell me what's missing or could be more specific.
```

```
My role has changed — I now own [X]. Update AGENTS.md to reflect this.
```

```
I want the agent to always flag when I'm spending time on low-priority work.
Add that as an instruction in AGENTS.md.
```

```
Add a new skill to AGENTS.md — it's called [skill name] and should load when I ask about [topic].
```

### Step 3 — Keep it alive

`AGENTS.md` works best when it reflects how you actually work right now, not how you worked six months ago. Run this every few months:

```
Read my AGENTS.md. Ask me if anything has changed — my role, my priorities,
my products, or how I like to work. Update the file based on my answers.
```

Think of it as a living document the AI helps you maintain, not a config file you set once and forget.

---

## How to customise it


| What you want to change            | File to edit                                |
| ---------------------------------- | ------------------------------------------- |
| Your name, role, or what you own   | `AGENTS.md`                                 |
| How the AI writes for you          | `writing-style.md`                          |
| How the AI queries your data       | `skills/analyst/references/`                |
| How the AI builds Confluence pages | `skills/confluence-writer/SKILL.md`         |
| How the AI writes for executives   | `skills/executive-communication/SKILL.md`   |
| How the AI builds new skills       | `skills/skill-builder/SKILL.md`             |
| Which skills load automatically    | `AGENTS.md`, the Skills table at the bottom |


---

## Adding a new skill

If you want the AI to have deep knowledge of something new (a new dashboard, a new content type, a new workflow), create a new folder inside `skills/` and add a `SKILL.md` file. Then add a row to the Skills table in `AGENTS.md` telling the AI when to load it.

You do not need to write code. Skills are plain text instruction files.

---

## Connecting external tools (MCP)

Rovo Dev connects to external tools — Slack, Jira, Confluence, Google Calendar, Gmail, and more — through something called MCP (Model Context Protocol). Most of these are available out of the box via the slash command version of Rovo Dev. But if you need a tool that isn't available, or if a connection isn't working, you can configure it manually using an `mcp.json` file.

### What is mcp.json?

It's a config file that tells Rovo Dev which external tools it can access and how to connect to them. You don't need to write it yourself — the agent can build it for you.

### Step 1 — Check what's already connected

Before adding anything, ask the agent what it can already see:

```
What MCP tools do you currently have access to? List them out.
```

This shows you what's already connected so you don't duplicate anything.

### Step 2 — Add a new MCP connection

If there's a tool you want to connect that isn't available, paste this:

```
I want to connect [tool name] to Rovo Dev via MCP. Help me create or update
my mcp.json file to add this connection. Ask me for any credentials or config
values you need, then write the file.
```

Common tools people add this way:

- **Exa** — web search and URL browsing (get a free API key at exa.ai)
- **GitHub** — if your code lives in GitHub rather than Bitbucket
- **Notion** — if your team uses Notion alongside Confluence
- **Linear** — if your team uses Linear instead of Jira
- **Airtable** — for connecting to tracking spreadsheets

### Step 3 — If a connection isn't working

If a tool is connected but not behaving correctly — wrong permissions, authentication errors, not returning data — just describe the problem to the agent:

```
My [tool name] MCP connection isn't working. Here's what's happening: [describe the error].
Help me troubleshoot and fix it.
```

The agent can read your mcp.json, identify the issue, and walk you through fixing it.

### Where mcp.json lives


| Setup type              | Location                          |
| ----------------------- | --------------------------------- |
| Global (all workspaces) | `~/.rovodev/mcp.json`             |
| Project-specific        | `mcp.json` in your workspace root |


If you're not sure which one to use, ask:

```
Where should I put my mcp.json — globally or in my project folder?
What's the difference and which makes more sense for what I'm trying to do?
```

---

## Questions

If something is not working the way you expect, the most likely cause is one of three things:

1. `AGENTS.md` has placeholder text the AI is reading literally — fill in your real details
2. The AI is not loading the right skill — check the Skills table in `AGENTS.md`
3. The writing style is not matching your voice — edit `writing-style.md` and be more specific

---

## Where to take this next

This repo is a starting point. The more context you give the AI, the better it performs. Here are the highest-value things to add — and a prompt you can paste into Rovo Dev to build each one without doing it manually.

---

### Real page templates

Save actual Confluence pages you're proud of as examples. The AI will match your structure instead of inventing its own.

**To build this, paste:**

```
I want to create a templates/ folder in my PFM Sidekick with real page examples
the AI can reference. Interview me about the page types I create most often
(weekly updates, MBR sections, OKR check-ins, channel briefs, etc.), ask me
to describe what good looks like for each, then create the folder structure
and a starter template file for each one.
```

---

### A contacts file

A `contacts.md` with the names, roles, and communication preferences of the people you work with most. The AI uses this to tailor tone when you're writing to specific people.

**To build this, paste:**

```
I want to create a contacts.md file in my PFM Sidekick. Ask me about the key
people I work with — my manager, my stakeholders, my data partners, my skip-level.
For each person, ask me: how they prefer to receive information, what to avoid,
and the best format for async communication. Then create the file.
```

---

### Product-specific reference files

A reference file per product you own, covering the key metrics, targets, channel mix, and known quirks. Keeps the AI accurate when you switch between products in the same session.

**To build this, paste:**

```
I want to create a products/ folder in my PFM Sidekick with one reference file
per product I own. For each product, interview me about: the BD1-6 target,
the paid channel mix, the primary acquisition motion, known seasonality or
data quirks, and the key stakeholders. Then create the files.
```

---

### A decisions log

A running `decisions.md` where you record calls you've made and why. Useful when the AI needs context on existing setup, or when you need to brief someone new.

**To build this, paste:**

```
I want to create a decisions.md file in my PFM Sidekick to track key calls
I've made. Ask me about recent decisions — budget moves, channel strategy,
test prioritisation, anything worth documenting. For each one, capture:
what the decision was, why I made it, and what the alternative was.
Then create the file.
```

---

### New skills

Skills are the highest-leverage thing to add. Each one makes the AI dramatically better at a specific recurring task.

**To build a new skill, paste:**

```
I want to build a new skill for my PFM Sidekick called [skill name].
Here's what it should do: [one sentence description].
Interview me about how I currently do this task — the inputs I start with,
the output format I want, the rules I follow, and any common mistakes to avoid.
Then create the skill folder, SKILL.md, and any reference files it needs.
Finally, add it to the Skills table in AGENTS.md.
```

**Highest-value skills to build next:**


| Skill           | What it does                                                                              | Prompt name to use    |
| --------------- | ----------------------------------------------------------------------------------------- | --------------------- |
| `atlas-update`  | Pulls pacing data and writes your KR narrative in one shot, in your exact format          | "atlas-update skill"  |
| `mbr-writer`    | Knows your MBR section structure, applies your voice, formats for exec consumption        | "mbr-writer skill"    |
| `brief-builder` | Turns a campaign idea into a structured brief with audience, message, and success metrics | "brief-builder skill" |
| `channel-audit` | Takes 4 weeks of channel data and writes a structured assessment with a recommendation    | "channel-audit skill" |


---

### Write better skills (the CIAO framework)

Weak skills are vague. The AI doesn't know when to load them, what to do, or how to format the output — so it guesses. The CIAO framework fixes this. Every skill you write should have four sections:


| Section              | What goes here                                                                                |
| -------------------- | --------------------------------------------------------------------------------------------- |
| **C — Context**      | Who you are, what this skill is for, when it applies                                          |
| **I — Instructions** | Step-by-step or rule-based guidance on how to do the task                                     |
| **A — Avoid**        | Explicit list of what not to do — bad patterns, wrong formats, things that sound AI-generated |
| **O — Output**       | Exactly what the final output should look like — format, length, structure, examples          |


**What good looks like:**

```markdown
---
name: channel-audit
description: >
  Load when asked to audit a paid channel, assess performance, or write a
  channel recommendation. Triggers on: audit [channel], how is [channel]
  performing, should we change [channel] spend, write up [channel] results.
---

## Context
You are writing a structured channel assessment for a performance marketing
manager at Atlassian. The audience is internal — the manager, their lead,
and occasionally a VP. Assume familiarity with paid channel mechanics.

## Instructions
1. Start with the bottom line — is the channel working or not, in one sentence
2. Pull the last 4 weeks of data: spend, BD1-6, CPBD1-6, vs. target
3. Identify the primary signal (efficiency, volume, or conversion issue)
4. State one recommendation with a clear rationale
5. Flag any data gaps or caveats

## Avoid
- Do not editorialize — stick to what the data shows
- Do not use "it's worth noting", "notably", "importantly"
- Do not hedge every statement — be direct, flag uncertainty separately
- Do not write more than one page

## Output
A structured markdown doc with four sections:
Bottom line / Performance snapshot (table) / Signal / Recommendation
```

**What bad looks like (and why it fails):**

```markdown
# Channel Audit Skill
This skill helps you audit paid channels and understand performance.
Use it when you want to know how a channel is doing.
```

This fails because: no trigger phrases (AI won't know when to load it), no instructions (AI will invent a format), no avoid list (AI will use its defaults), no output spec (every audit will look different).

**To audit and improve an existing skill, paste:**

```
Read [skill name]/SKILL.md and evaluate it against the CIAO framework:
Context, Instructions, Avoid, Output. Tell me what's missing or weak in
each section, then rewrite it to be tighter and more actionable.
Keep it under 300 lines — if it's longer, something can be cut.
```

**To build a new skill from scratch using CIAO, paste:**

```
I want to build a new skill called [skill name] for my PFM Sidekick.
Use the CIAO framework: Context, Instructions, Avoid, Output.
Interview me about this task — what triggers it, how I do it step by step,
what I hate seeing in the output, and what a perfect result looks like.
Then write the SKILL.md. Keep it tight — no padding, no fractal summaries,
no section that doesn't earn its place.
```

---

### A daily/weekly briefing skill

One of the highest-value things you can build is a briefing skill — one prompt that pulls your calendar, Slack, Confluence, Jira, and email into a single "here's what matters today" summary.

**What it covers:**


| Source          | What the AI checks                                                      |
| --------------- | ----------------------------------------------------------------------- |
| Google Calendar | Meetings today/this week, any prep needed                               |
| Slack           | Unread mentions, threads you're in, anything flagged urgent             |
| Jira            | Tickets assigned to you, overdue items, recent comments                 |
| Confluence      | Pages you've been mentioned on, recent edits to pages you own           |
| Gmail           | Emails requiring a response, anything from your manager or stakeholders |
| Atlas           | KR update deadlines, project status changes                             |


**To build this skill, paste:**

```
I want to build a morning briefing skill for my PFM Sidekick. It should pull
context from my calendar, Slack, Jira, Confluence, and email, then give me
a single structured summary of: what I have on today, what needs a response,
what's at risk, and what I should do first.

Interview me about: how I like to start my day, what "urgent" means to me,
which sources I check most, and what I want to be reminded about that I
usually forget. Then build the skill using the CIAO framework and add it
to AGENTS.md.
```

