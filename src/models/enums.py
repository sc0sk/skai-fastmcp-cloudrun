"""Enum types for MCP tool parameters."""

from typing import Literal

# Australian political parties represented in the dataset
PartyEnum = Literal[
    "Liberal",      # Liberal Party of Australia
    "Labor",        # Australian Labor Party (note: "Labor" not "Labour")
    "Greens",       # Australian Greens
    "National",     # National Party of Australia
    "Independent"   # Independent MPs
]

# Australian Parliament chambers
ChamberEnum = Literal[
    "REPS",    # House of Representatives
    "SENATE"   # Senate
]
