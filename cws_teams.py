"""
CWS team data for all tournament rounds, 2014-2025.

Supports flexible comparison groups:
  - Final Four (last 4 teams in CWS)
  - Finalists (championship series participants)
  - All CWS 8 teams
  - Super Regional losers (teams eliminated in supers)

NCAA team name normalization handles common mismatches between
how stats.ncaa.org names teams vs how we refer to them.
"""

# ============================================================
# CWS RESULTS BY YEAR
# ============================================================

# Format: {year: {"champion": str, "runner_up": str, 
#                  "semi_3": str, "semi_4": str,
#                  "cws_5th" through "cws_8th": str,
#                  "super_regional_losers": [str, ...]}}

CWS_DATA = {
    2025: {
        "champion": "LSU",
        "runner_up": "Coastal Carolina",
        "semi_3": "Arkansas",
        "semi_4": "Louisville",
        "cws_5th": "Oregon State",
        "cws_6th": "UCLA",
        "cws_7th": "Murray State",
        "cws_8th": "Arizona",
    },
    2024: {
        "champion": "Tennessee",
        "runner_up": "Texas A&M",
        "semi_3": "Florida State",
        "semi_4": "Florida",
        "cws_5th": "North Carolina",
        "cws_6th": "Virginia",
        "cws_7th": "Kentucky",
        "cws_8th": "NC State",
    },
    2023: {
        "champion": "LSU",
        "runner_up": "Florida",
        "semi_3": "Wake Forest",
        "semi_4": "Oral Roberts",
        "cws_5th": "Stanford",
        "cws_6th": "Virginia",
        "cws_7th": "TCU",
        "cws_8th": "Tennessee",
    },
    2022: {
        "champion": "Ole Miss",
        "runner_up": "Oklahoma",
        "semi_
