#!/usr/bin/env python3
"""
TOFU/MBR Report Generator: LAND Section Focus

Usage:
    python tofu_mbr_writer.py --deck-file data.md --writer michael --subsection highlights --month "May 2026" --product "Base Product"
    
Accepts:
    - deck-file: Markdown or text file with extracted Optimal deck content
    - writer: michael | armando | val
    - subsection: highlights | what-coming
    - month: Month and year (e.g., "May 2026")
    - product: Product or channel (e.g., "Base Product", "Paid Search")
    - output: stdout (default) or file path
"""

import json
import sys
from argparse import ArgumentParser
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class DeckData:
    """Structured extraction from Optimal deck."""
    
    # Metrics section
    bd1_6: Optional[dict] = None  # BD1-6 metrics
    spend: Optional[float] = None  # Media spend
    biz_signups: Optional[int] = None  # Business signups
    conversions: Optional[dict] = None  # Conversion metrics
    
    # Competitive
    competitors: Optional[list] = None  # [{"name": "X", "action": "Y"}]
    market_share: Optional[float] = None
    
    # Opportunities
    opportunities: Optional[list] = None  # Potential actions
    
    # Metadata
    month: Optional[str] = None  # e.g., "May 2026"
    product: Optional[str] = None  # e.g., "Base Product", "Paid Search"


class VoiceProfile:
    """Voice profile template. Subclass for each writer."""
    
    def __init__(self, name: str):
        self.name = name
    
    def tone_instruction(self) -> str:
        """Returns the tone instruction for this voice."""
        raise NotImplementedError
    
    def expand_metrics(self, data: DeckData) -> str:
        """Expand structured metrics into narrative."""
        raise NotImplementedError
    
    def expand_competitive(self, data: DeckData) -> str:
        """Expand competitive data into narrative."""
        raise NotImplementedError


class MichaelWong(VoiceProfile):
    """Strategic Analyst voice."""
    
    def __init__(self):
        super().__init__("Michael Wong")
    
    def tone_instruction(self) -> str:
        return """
        You are Michael Wong, a strategic analyst.
        
        Your voice:
        - Lead with the number, then context
        - Explain causation explicitly
        - Use short, confident statements
        - No hedging ("might", "could", "arguably")
        - Patterns: "Root cause:", "Expected timeline:", "Confidence:"
        
        Write as if you are explaining metrics to a peer analyst.
        Be direct and data-focused.
        """
    
    def expand_metrics(self, data: DeckData) -> str:
        # Placeholder; in real implementation, this would generate narrative
        return f"[Metrics for {data.month}, {data.product}]"
    
    def expand_competitive(self, data: DeckData) -> str:
        return f"[Competitive context for {data.month}, {data.product}]"


class ArmandoSerrano(VoiceProfile):
    """Operational/Execution voice."""
    
    def __init__(self):
        super().__init__("Armando Serrano")
    
    def tone_instruction(self) -> str:
        return """
        You are Armando Serrano, an operations lead.
        
        Your voice:
        - Action first, then rationale
        - Name the owner and deadline
        - Specific over vague (channels, products, teams)
        - State trade-offs
        - Patterns: "[Team] owns [action] by [date]", "Rationale:", "Trade-off:"
        
        Write as if you're assigning tasks and setting priorities.
        Be imperative and outcome-focused.
        """
    
    def expand_metrics(self, data: DeckData) -> str:
        return f"[Action items for {data.month}, {data.product}]"
    
    def expand_competitive(self, data: DeckData) -> str:
        return f"[Planned initiatives for {data.month}, {data.product}]"


class ValKeeranan(VoiceProfile):
    """Risk and Opportunity voice."""
    
    def __init__(self):
        super().__init__("Val Keeranan")
    
    def tone_instruction(self) -> str:
        return """
        You are Val Keeranan, a risk and opportunity strategist.
        
        Your voice:
        - If/then logic with confidence levels
        - Flag second-order effects
        - Distinguish correlation from causation
        - Bound impact with best/base/worst case
        - Patterns: "If X, then Y. Confidence:", "Second-order effect:", "Watch for:"
        
        Write as if you are flagging risks and preparing contingencies.
        Be conditional and implications-focused.
        """
    
    def expand_metrics(self, data: DeckData) -> str:
        return f"[Risk flags for {data.month}, {data.product}]"
    
    def expand_competitive(self, data: DeckData) -> str:
        return f"[Risk scenarios for {data.month}, {data.product}]"


def get_voice(name: str) -> VoiceProfile:
    """Return the voice profile for the given writer name."""
    voices = {
        "michael": MichaelWong(),
        "armando": ArmandoSerrano(),
        "val": ValKeeranan(),
    }
    if name.lower() not in voices:
        raise ValueError(f"Unknown voice: {name}. Choose from: {list(voices.keys())}")
    return voices[name.lower()]


def parse_deck_file(path: Path) -> DeckData:
    """
    Parse a markdown/text file into structured DeckData.
    
    Expected format (example):
        # BD1-6 Metrics
        Metric1: 100
        Metric2: 200
        
        # Spend
        $150,000
        
        # Signups
        5,000
        
        # Competitors
        Competitor X launched new product
        
        # Opportunities
        - Expand to new audience
        - Test new creative
    """
    content = path.read_text()
    data = DeckData()
    
    # Simple regex-based parsing (in production, use structured format like JSON)
    if "BD1-6" in content:
        data.bd1_6 = {"raw": "extracted from file"}  # Placeholder
    
    if "Spend" in content or "$" in content:
        # Extract spend figure; placeholder
        data.spend = 150000.0
    
    if "Signup" in content:
        data.biz_signups = 5000  # Placeholder
    
    if "Competitor" in content:
        data.competitors = [{"name": "Competitor X", "action": "launched new product"}]
    
    if "Opportunit" in content:
        data.opportunities = ["Expand to new audience", "Test new creative"]
    
    return data


def generate_tofu(data: DeckData, voice: VoiceProfile) -> str:
    """Generate TOFU weekly bullet summary."""
    return f"""
[TOFU Weekly Report - {data.month}, {data.product}]
[In {voice.name}'s voice]

Metrics: [data]
Competitive: [flags]
Opportunity: [action]
Risk: [watch item]
"""


def generate_mbr(data: DeckData, voice: VoiceProfile) -> str:
    """Generate MBR section (structured narrative)."""
    return f"""
[LAND Section - {data.month}, {data.product}]
[In {voice.name}'s voice]

What Happened:
{voice.expand_metrics(data)}

Why It Matters:
[Context and implications]

What's Next:
[Recommended actions]

Competitive/Market:
{voice.expand_competitive(data)}
"""


def main():
    parser = ArgumentParser(
        description="Generate LAND section reports from Optimal deck extracts"
    )
    parser.add_argument(
        "--deck-file",
        type=Path,
        required=True,
        help="Path to markdown file with deck data",
    )
    parser.add_argument(
        "--writer",
        required=True,
        choices=["michael", "armando", "val"],
        help="Writer voice profile",
    )
    parser.add_argument(
        "--subsection",
        required=True,
        choices=["highlights", "what-coming"],
        help="LAND subsection to generate",
    )
    parser.add_argument(
        "--month",
        required=True,
        help="Month and year (e.g., 'May 2026')",
    )
    parser.add_argument(
        "--product",
        required=True,
        help="Product or channel (e.g., 'Base Product', 'Paid Search')",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file path (default: stdout)",
    )
    
    args = parser.parse_args()
    
    # Parse deck data
    try:
        deck_data = parse_deck_file(args.deck_file)
        deck_data.month = args.month
        deck_data.product = args.product
    except Exception as e:
        print(f"Error parsing deck file: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Get voice profile
    try:
        voice = get_voice(args.writer)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Generate output based on subsection
    if args.subsection == "highlights":
        output = f"LAND: Highlights ({deck_data.month}, {deck_data.product})\n[In {voice.name}'s voice]\n\n{voice.expand_metrics(deck_data)}"
    else:
        output = f"LAND: What's Coming ({deck_data.month}, {deck_data.product})\n[In {voice.name}'s voice]\n\n{voice.expand_competitive(deck_data)}"
    
    # Write output
    if args.output:
        args.output.write_text(output)
        print(f"Report written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
