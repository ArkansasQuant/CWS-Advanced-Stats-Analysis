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
        "semi_3": "Arkansas",
        "semi_4": "Texas A&M",
        "cws_5th": "Auburn",
        "cws_6th": "Stanford",
        "cws_7th": "Notre Dame",
        "cws_8th": "Texas",
    },
    2021: {
        "champion": "Mississippi State",
        "runner_up": "Vanderbilt",
        "semi_3": "NC State",
        "semi_4": "Texas",
        "cws_5th": "Stanford",
        "cws_6th": "Arizona",
        "cws_7th": "Tennessee",
        "cws_8th": "Virginia",
    },
    # 2020: cancelled (COVID)
    2019: {
        "champion": "Vanderbilt",
        "runner_up": "Michigan",
        "semi_3": "Texas Tech",
        "semi_4": "Louisville",
        "cws_5th": "Mississippi State",
        "cws_6th": "Auburn",
        "cws_7th": "Arkansas",
        "cws_8th": "Florida State",
    },
    2018: {
        "champion": "Oregon State",
        "runner_up": "Arkansas",
        "semi_3": "Mississippi State",
        "semi_4": "North Carolina",
        "cws_5th": "Texas Tech",
        "cws_6th": "Florida",
        "cws_7th": "Texas",
        "cws_8th": "Washington",
    },
    2017: {
        "champion": "Florida",
        "runner_up": "LSU",
        "semi_3": "Oregon State",
        "semi_4": "Louisville",
        "cws_5th": "TCU",
        "cws_6th": "Texas A&M",
        "cws_7th": "Cal State Fullerton",
        "cws_8th": "Missouri State",
    },
    2016: {
        "champion": "Coastal Carolina",
        "runner_up": "Arizona",
        "semi_3": "TCU",
        "semi_4": "Oklahoma State",
        "cws_5th": "Texas Tech",
        "cws_6th": "Miami",
        "cws_7th": "UC Santa Barbara",
        "cws_8th": "Louisville",
    },
    2015: {
        "champion": "Virginia",
        "runner_up": "Vanderbilt",
        "semi_3": "TCU",
        "semi_4": "Florida",
        "cws_5th": "Arkansas",
        "cws_6th": "LSU",
        "cws_7th": "Miami",
        "cws_8th": "Cal State Fullerton",
    },
    2014: {
        "champion": "Vanderbilt",
        "runner_up": "Virginia",
        "semi_3": "Texas",
        "semi_4": "Ole Miss",
        "cws_5th": "UC Irvine",
        "cws_6th": "Louisville",
        "cws_7th": "TCU",
        "cws_8th": "Texas Tech",
    },
}


# ============================================================
# TEAM NAME ALIASES
# ============================================================
# Maps our standard names to possible NCAA stats.ncaa.org variations.
# The scraper will try fuzzy matching, but these help with exact matches.

NAME_ALIASES = {
    "Ole Miss": ["Mississippi", "Ole Miss", "Miss."],
    "Mississippi State": ["Mississippi St.", "Mississippi State", "Miss. State"],
    "NC State": ["N.C. State", "NC State", "North Carolina St."],
    "LSU": ["LSU", "La.-Lafayette", "Louisiana State"],
    "TCU": ["TCU", "Texas Christian"],
    "UCF": ["UCF", "Central Florida"],
    "USC": ["USC", "Southern California", "Southern Cal"],
    "Miami": ["Miami (FL)", "Miami", "Miami (Fla.)"],
    "Cal State Fullerton": ["Cal St. Fullerton", "CS Fullerton", "CSUF"],
    "UC Irvine": ["UC Irvine", "California-Irvine", "Cal-Irvine"],
    "UC Santa Barbara": ["UC Santa Barbara", "UCSB", "California-Santa Barbara"],
    "Texas A&M": ["Texas A&M", "Texas A&M University"],
    "Oral Roberts": ["Oral Roberts"],
    "Murray State": ["Murray St.", "Murray State"],
    "Coastal Carolina": ["Coastal Car.", "Coastal Carolina"],
    "Florida State": ["Florida St.", "Florida State"],
    "Oregon State": ["Oregon St.", "Oregon State"],
    "Oklahoma State": ["Oklahoma St.", "Oklahoma State"],
    "Wake Forest": ["Wake Forest"],
    "North Carolina": ["North Carolina", "UNC"],
    "Missouri State": ["Missouri St.", "Missouri State"],
}


# ============================================================
# COMPARISON GROUP BUILDERS
# ============================================================

def get_teams(group="final_four", years=None):
    """
    Get team-year pairs for a comparison group.
    
    Groups:
        "final_four"  - Last 4 teams (champion, runner_up, semi_3, semi_4)
        "finalists"   - Championship series only (champion, runner_up)
        "champion"    - Champion only
        "all_cws"     - All 8 CWS teams
        "cws_5_to_8"  - Teams eliminated in first CWS round
    
    Args:
        group: Which subset of teams
        years: List of years (None = all available)
    
    Returns:
        List of (year, team_name) tuples
    """
    if years is None:
        years = sorted(CWS_DATA.keys())
    
    GROUP_KEYS = {
        "champion":    ["champion"],
        "finalists":   ["champion", "runner_up"],
        "final_four":  ["champion", "runner_up", "semi_3", "semi_4"],
        "all_cws":     ["champion", "runner_up", "semi_3", "semi_4",
                        "cws_5th", "cws_6th", "cws_7th", "cws_8th"],
        "cws_5_to_8":  ["cws_5th", "cws_6th", "cws_7th", "cws_8th"],
    }
    
    keys = GROUP_KEYS.get(group, GROUP_KEYS["final_four"])
    
    result = []
    for year in years:
        if year not in CWS_DATA:
            continue
        data = CWS_DATA[year]
        for key in keys:
            if key in data:
                result.append((year, data[key]))
    
    return result


def get_comparison(
    target_group="final_four",
    target_years=None,
    baseline_group="final_four", 
    baseline_years=None,
):
    """
    Build two comparison sets for analysis.
    
    Example usages:
        # 2024-2025 Final Four vs 2014-2023 Final Four (default)
        get_comparison(target_years=[2024,2025], baseline_years=[2014,...,2023])
        
        # 2023-2025 all CWS teams vs 2014-2022
        get_comparison("all_cws", [2023,2024,2025], "all_cws", [2014,...,2022])
        
        # Finalists vs teams eliminated in CWS first round (same years)
        get_comparison("finalists", None, "cws_5_to_8", None)
    
    Returns:
        dict with "target" and "baseline" lists of (year, team) tuples
    """
    return {
        "target": get_teams(target_group, target_years),
        "baseline": get_teams(baseline_group, baseline_years),
    }


def normalize_team_name(name):
    """Normalize a team name for matching against scraped data."""
    # Strip common suffixes/formatting
    clean = name.strip()
    clean = clean.replace("University of ", "").replace("University", "")
    clean = clean.strip()
    return clean


def find_team_in_data(team_name, available_teams):
    """
    Find the best match for a team name in a list of scraped team names.
    Returns the matched name or None.
    """
    # Exact match
    if team_name in available_teams:
        return team_name
    
    # Check aliases
    aliases = NAME_ALIASES.get(team_name, [team_name])
    for alias in aliases:
        if alias in available_teams:
            return alias
        # Case-insensitive
        for avail in available_teams:
            if alias.lower() == avail.lower():
                return avail
    
    # Substring match (last resort)
    for avail in available_teams:
        if team_name.lower() in avail.lower() or avail.lower() in team_name.lower():
            return avail
    
    return None


# ============================================================
# PRESET SCENARIOS
# ============================================================

SCENARIOS = {
    "default": {
        "name": "2024-2025 Final Four vs 2014-2023 Final Four",
        "target_group": "final_four",
        "target_years": [2024, 2025],
        "baseline_group": "final_four",
        "baseline_years": [2014, 2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023],
    },
    "recent_3yr": {
        "name": "2023-2025 Final Four vs 2014-2022 Final Four",
        "target_group": "final_four",
        "target_years": [2023, 2024, 2025],
        "baseline_group": "final_four",
        "baseline_years": [2014, 2015, 2016, 2017, 2018, 2019, 2021, 2022],
    },
    "all_cws_2yr": {
        "name": "2024-2025 All CWS vs 2014-2023 All CWS",
        "target_group": "all_cws",
        "target_years": [2024, 2025],
        "baseline_group": "all_cws",
        "baseline_years": [2014, 2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023],
    },
    "finalists_vs_early_exits": {
        "name": "CWS Finalists vs First-Round CWS Exits (all years)",
        "target_group": "finalists",
        "target_years": None,  # all years
        "baseline_group": "cws_5_to_8",
        "baseline_years": None,
    },
    "champions_vs_field": {
        "name": "CWS Champions vs Non-Champion CWS Teams (all years)",
        "target_group": "champion",
        "target_years": None,
        "baseline_group": "all_cws",  # will filter out champions in analysis
        "baseline_years": None,
    },
}


if __name__ == "__main__":
    # Quick diagnostic
    print("Available scenarios:")
    for key, scenario in SCENARIOS.items():
        comp = get_comparison(
            scenario["target_group"], scenario["target_years"],
            scenario["baseline_group"], scenario["baseline_years"],
        )
        print(f"\n  {key}: {scenario['name']}")
        print(f"    Target:   {len(comp['target'])} team-seasons")
        print(f"    Baseline: {len(comp['baseline'])} team-seasons")
