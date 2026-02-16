"""
CWS Final Four teams by year, plus NCAA stats.ncaa.org team IDs.

"Final Four" = the last 4 teams remaining in the CWS each year:
  - The 2 finalists (championship series participants)
  - The last team eliminated from each bracket (lost the bracket semifinal/if-necessary game)

NCAA team IDs sourced from stats.ncaa.org. These are needed to pull 
team-level stats from the NCAA website or via the collegebaseball/baseballr packages.
"""

# CWS Final Four teams by year
# Format: {year: [champion, runner_up, semi_3, semi_4]}
CWS_FINAL_FOUR = {
    # === RECENT ERA (2024-2025) ===
    2024: ["Tennessee", "Texas A&M", "Florida State", "Florida"],
    2025: ["LSU", "Coastal Carolina", "Arkansas", "Louisville"],

    # === HISTORICAL ERA (2014-2023) ===
    2014: ["Vanderbilt", "Virginia", "Texas", "Ole Miss"],
    2015: ["Virginia", "Vanderbilt", "TCU", "Florida"],
    2016: ["Coastal Carolina", "Arizona", "TCU", "Oklahoma State"],
    2017: ["Florida", "LSU", "Oregon State", "Louisville"],
    2018: ["Oregon State", "Arkansas", "Mississippi State", "North Carolina"],
    2019: ["Vanderbilt", "Michigan", "Texas Tech", "Louisville"],
    # 2020: cancelled (COVID)
    2021: ["Mississippi State", "Vanderbilt", "NC State", "Texas"],
    2022: ["Ole Miss", "Oklahoma", "Arkansas", "Texas A&M"],
    2023: ["LSU", "Florida", "Wake Forest", "Oral Roberts"],
}

# All 8 CWS teams by year (for expanded analysis if desired)
CWS_ALL_EIGHT = {
    2024: ["Tennessee", "Texas A&M", "Florida State", "Florida",
           "North Carolina", "Virginia", "Kentucky", "NC State"],
    2025: ["LSU", "Coastal Carolina", "Arkansas", "Louisville",
           "Oregon State", "UCLA", "Murray State", "Arizona"],
    2014: ["Vanderbilt", "Virginia", "Texas", "Ole Miss",
           "UC Irvine", "Louisville", "TCU", "Texas Tech"],
    2015: ["Virginia", "Vanderbilt", "TCU", "Florida",
           "Arkansas", "LSU", "Miami (FL)", "Cal State Fullerton"],
    2016: ["Coastal Carolina", "Arizona", "TCU", "Oklahoma State",
           "Texas Tech", "Miami (FL)", "UC Santa Barbara", "Louisville"],
    2017: ["Florida", "LSU", "Oregon State", "Louisville",
           "TCU", "Texas A&M", "Cal State Fullerton", "Missouri State"],
    2018: ["Oregon State", "Arkansas", "Mississippi State", "North Carolina",
           "Texas Tech", "Florida", "Texas", "Washington"],
    2019: ["Vanderbilt", "Michigan", "Texas Tech", "Louisville",
           "Mississippi State", "Auburn", "Arkansas", "Florida State"],
    2021: ["Mississippi State", "Vanderbilt", "NC State", "Texas",
           "Stanford", "Arizona", "Tennessee", "Virginia"],
    2022: ["Ole Miss", "Oklahoma", "Arkansas", "Texas A&M",
           "Auburn", "Stanford", "Notre Dame", "Texas"],
    2023: ["LSU", "Florida", "Wake Forest", "Oral Roberts",
           "Stanford", "Virginia", "TCU", "Tennessee"],
}

# NCAA stats.ncaa.org team IDs
# These are used to construct URLs like:
#   https://stats.ncaa.org/teams/{season_id}
# The team_id is stable across years; the season_id changes.
# Use the lookup approach below to find season-specific IDs.
NCAA_TEAM_IDS = {
    "Tennessee": 694,
    "Texas A&M": 697,
    "Florida State": 234,
    "Florida": 235,
    "LSU": 365,
    "Coastal Carolina": 157,
    "Arkansas": 31,
    "Louisville": 367,
    "Vanderbilt": 736,
    "Virginia": 746,
    "Texas": 703,
    "Ole Miss": 433,
    "TCU": 698,
    "Arizona": 29,
    "Oklahoma State": 459,
    "Oregon State": 468,
    "Michigan": 418,
    "Texas Tech": 700,
    "Mississippi State": 430,
    "North Carolina": 457,
    "NC State": 490,
    "Oklahoma": 458,
    "Wake Forest": 749,
    "Oral Roberts": 464,
    "UC Irvine": 300,
    "Miami (FL)": 415,
    "Cal State Fullerton": 107,
    "Missouri State": 441,
    "Texas Tech": 700,
    "Auburn": 37,
    "Stanford": 674,
    "Washington": 756,
    "UC Santa Barbara": 676,
    "UCLA": 684,
    "Murray State": 447,
    "Notre Dame": 490,
    "Kentucky": 334,
}

RECENT_YEARS = [2024, 2025]
HISTORICAL_YEARS = [2014, 2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023]
ALL_YEARS = HISTORICAL_YEARS + RECENT_YEARS


def get_all_final_four_teams():
    """Return flat list of (year, team) tuples for all Final Four teams."""
    teams = []
    for year, team_list in CWS_FINAL_FOUR.items():
        for team in team_list:
            teams.append((year, team))
    return teams


def get_final_four_by_era():
    """Return dict with 'recent' and 'historical' lists of (year, team)."""
    recent = []
    historical = []
    for year, team_list in CWS_FINAL_FOUR.items():
        for team in team_list:
            if year in RECENT_YEARS:
                recent.append((year, team))
            else:
                historical.append((year, team))
    return {"recent": recent, "historical": historical}
