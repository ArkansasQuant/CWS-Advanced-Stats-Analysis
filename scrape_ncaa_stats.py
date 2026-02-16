"""
Scrape NCAA D1 baseball team stats using ncaa_bbStats package.

This pulls team-level batting, pitching, and fielding stats 
for all D1 teams from 2014-2025, then saves to data/ directory.

The ncaa_bbStats package wraps stats.ncaa.org with built-in
caching and rate limiting.
"""

import os
import sys
import json
import logging
from pathlib import Path

import pandas as pd
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Years to scrape (2020 cancelled)
YEARS = [2014, 2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025]
OUTPUT_DIR = "data"

# Stats we want to pull per team
# These are the stat abbreviation keys used by ncaa_bbStats
BATTING_STATS = [
    "ba", "obp", "slg", "hr", "r", "sb", "bb", "so", 
    "hbp", "rbi", "2b", "3b", "tb", "gp"
]
PITCHING_STATS = [
    "era", "ip", "so", "bb", "ha", "hra", "er", "wp", 
    "bk", "sho", "sv", "gp"
]
FIELDING_STATS = ["fpct", "e", "dp", "tp"]


def scrape_with_ncaa_bbstats():
    """
    Pull team stats using ncaa_bbStats package.
    
    ncaa_bbStats provides:
      - get_team_stat(stat_name, team_name, year, division)
      - It also has ranking functions
    
    However, the most efficient approach is to pull the full 
    ranking/leaderboard for each stat, which gives us all teams at once.
    """
    try:
        from ncaa_bbStats import get_team_stat, display_all_team_stats
    except ImportError:
        logger.error("ncaa_bbStats not installed. Run: pip install ncaa_bbStats")
        sys.exit(1)
    
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    for year in YEARS:
        logger.info(f"\n{'='*50}")
        logger.info(f"Processing {year}")
        logger.info(f"{'='*50}")
        
        outfile = os.path.join(OUTPUT_DIR, f"team_stats_{year}.csv")
        if os.path.exists(outfile):
            logger.info(f"  Already exists: {outfile}, skipping")
            continue
        
        try:
            # ncaa_bbStats can return all team stats for a year
            # The function varies by version - try the bulk approach first
            all_stats = display_all_team_stats(year=year, division=1)
            if all_stats is not None and not all_stats.empty:
                all_stats["year"] = year
                all_stats.to_csv(outfile, index=False)
                logger.info(f"  Saved {len(all_stats)} teams to {outfile}")
                continue
        except Exception as e:
            logger.info(f"  Bulk pull not available ({e}), falling back to per-team")
        
        # Fallback: if bulk doesn't work, we'll try the ranking approach
        logger.info("  Using fallback scraping method...")
        scrape_fallback_rankings(year)


def scrape_fallback_rankings(year):
    """
    Fallback: scrape NCAA team ranking pages directly.
    Each ranking page lists all ~300 D1 teams for one stat.
    """
    import requests
    from bs4 import BeautifulSoup
    import time
    
    # NCAA ranking page stat IDs for team-level stats
    STAT_IDS = {
        # Batting
        "batting_avg": 211, "on_base_pct": 216, "slugging_pct": 217,
        "home_runs_pg": 215, "scoring_rpg": 228, "stolen_bases_pg": 218,
        "doubles_pg": 223, "triples_pg": 226, "strikeouts_pg": 220,
        # Pitching
        "era": 212, "whip": 239, "k_per_nine": 219,
        "bb_per_nine": 238, "hits_per_nine": 214, "k_bb_ratio": 229,
        # Fielding
        "fielding_pct": 213, "double_plays_pg": 224,
    }
    
    # Map year -> NCAA academic year season ID
    # NOTE: These need to be verified - check stats.ncaa.org dropdown
    # You can find them by inspecting the year selector on the rankings page
    SEASON_LOOKUP = {
        2014: "12560", 2015: "12900", 2016: "13220",
        2017: "13523", 2018: "14781", 2019: "15204",
        2021: "15860", 2022: "16340", 2023: "16820",
        2024: "17300", 2025: "17780",
    }
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; CWS-Research/1.0)"
    })
    
    all_rows = []
    season_id = SEASON_LOOKUP.get(year, "")
    
    for stat_name, stat_id in tqdm(STAT_IDS.items(), desc=f"  Stats for {year}"):
        url = "https://stats.ncaa.org/rankings"
        params = {
            "academic_year": season_id,
            "division": "1",
            "sport_code": "MBA",
            "stat_seq": str(stat_id),
        }
        
        try:
            resp = session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, "lxml")
            table = soup.find("table", {"id": "rankings_table"})
            if not table:
                tables = soup.find_all("table")
                table = tables[-1] if tables else None
            
            if table:
                for tr in table.find_all("tr")[1:]:
                    cells = tr.find_all("td")
                    if len(cells) >= 3:
                        try:
                            rank = int(cells[0].get_text(strip=True))
                            team = cells[1].get_text(strip=True)
                            value = float(cells[-1].get_text(strip=True))
                            all_rows.append({
                                "year": year,
                                "team": team,
                                "stat_name": stat_name,
                                "stat_value": value,
                                "rank": rank,
                            })
                        except (ValueError, IndexError):
                            continue
            
            time.sleep(3)  # Be polite
            
        except Exception as e:
            logger.warning(f"    Failed {stat_name}: {e}")
            continue
    
    if all_rows:
        df = pd.DataFrame(all_rows)
        # Pivot to wide format
        wide = df.pivot_table(
            index=["year", "team"],
            columns="stat_name",
            values="stat_value",
            aggfunc="first"
        ).reset_index()
        
        outfile = os.path.join(OUTPUT_DIR, f"team_stats_{year}.csv")
        wide.to_csv(outfile, index=False)
        logger.info(f"  Saved {len(wide)} teams to {outfile}")
    else:
        logger.error(f"  No data collected for {year}")


def scrape_with_collegebaseball_pkg():
    """
    Alternative: Use nathanblumenfeld's collegebaseball package.
    Install: pip install git+https://github.com/nathanblumenfeld/collegebaseball
    """
    try:
        from collegebaseball import ncaa_scraper
    except ImportError:
        logger.error("collegebaseball not installed.")
        logger.error("Install: pip install git+https://github.com/nathanblumenfeld/collegebaseball")
        return
    
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    for year in YEARS:
        logger.info(f"Scraping {year} via collegebaseball package...")
        outfile = os.path.join(OUTPUT_DIR, f"team_stats_{year}.csv")
        if os.path.exists(outfile):
            logger.info(f"  Skipping (already exists)")
            continue
        
        try:
            # This package can pull team-level aggregated stats
            df = ncaa_scraper.ncaa_team_stats(year=year, division=1)
            if df is not None and not df.empty:
                df["year"] = year
                df.to_csv(outfile, index=False)
                logger.info(f"  Saved {len(df)} teams")
        except Exception as e:
            logger.error(f"  Failed: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", default="ncaa_bbstats",
                        choices=["ncaa_bbstats", "collegebaseball", "direct"],
                        help="Which scraping method to use")
    args = parser.parse_args()
    
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    if args.method == "ncaa_bbstats":
        scrape_with_ncaa_bbstats()
    elif args.method == "collegebaseball":
        scrape_with_collegebaseball_pkg()
    else:
        for year in YEARS:
            scrape_fallback_rankings(year)
    
    logger.info("\nDone! Data saved to data/ directory.")
