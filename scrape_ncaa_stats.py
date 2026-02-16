"""
Scrape NCAA D1 baseball team stats from stats.ncaa.org using Playwright.

Uses a real browser to avoid 403 blocks from cloud IPs.

Debug mode: python scrape_ncaa_stats.py --debug
Test mode:  python scrape_ncaa_stats.py --test (only scrapes 2024-2025)
"""

import os
import sys
import time
import json
import argparse
import logging
import traceback
from pathlib import Path
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm

LOG_DIR = "data"
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(LOG_DIR, "scrape_log.txt"), mode="w"),
    ]
)
logger = logging.getLogger(__name__)

ALL_YEARS = [2014, 2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025]

STAT_CATEGORIES = {
    "batting_avg":       {"id": 211, "type": "batting", "lower_is_better": False},
    "on_base_pct":       {"id": 216, "type": "batting", "lower_is_better": False},
    "slugging_pct":      {"id": 217, "type": "batting", "lower_is_better": False},
    "home_runs_pg":      {"id": 215, "type": "batting", "lower_is_better": False},
    "runs_pg":           {"id": 228, "type": "batting", "lower_is_better": False},
    "stolen_bases_pg":   {"id": 218, "type": "batting", "lower_is_better": False},
    "doubles_pg":        {"id": 223, "type": "batting", "lower_is_better": False},
    "triples_pg":        {"id": 226, "type": "batting", "lower_is_better": False},
    "base_on_balls_pg":  {"id": 222, "type": "batting", "lower_is_better": False},
    "era":               {"id": 212, "type": "pitching", "lower_is_better": True},
    "whip":              {"id": 239, "type": "pitching", "lower_is_better": True},
    "k_per_nine":        {"id": 219, "type": "pitching", "lower_is_better": False},
    "bb_per_nine":       {"id": 238, "type": "pitching", "lower_is_better": True},
    "hits_per_nine":     {"id": 214, "type": "pitching", "lower_is_better": True},
    "k_bb_ratio":        {"id": 229, "type": "pitching", "lower_is_better": False},
    "fielding_pct":      {"id": 213, "type": "fielding", "lower_is_better": False},
    "double_plays_pg":   {"id": 224, "type": "fielding", "lower_is_better": False},
}

STAT_META_FILE = os.path.join(LOG_DIR, "stat_metadata.json")


def setup_browser():
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
    )
    page = context.new_page()
    logger.info("Browser launched successfully")
    return pw, browser, context, page


def discover_season_id(year, page, debug=False):
    logger.info(f"  Discovering season ID for {year}...")
    try:
        page.goto(
            "https://stats.ncaa.org/rankings?sport_code=MBA&division=1",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        page.wait_for_timeout(2000)

        if debug:
            debug_dir = os.path.join(LOG_DIR, "debug_html")
            Path(debug_dir).mkdir(parents=True, exist_ok=True)
            with open(os.path.join(debug_dir, f"season_discovery_{year}.html"), "w") as f:
                f.write(page.content())

        html = page.content()
        soup = BeautifulSoup(html, "lxml")

        select = soup.find("select", {"name": "academic_year"})
        if not select:
            select = soup.find("select", {"id": "academic_year"})

        if select:
            target = f"{year-1}-{str(year)[2:]}"
            for option in select.find_all("option"):
                text = option.get_text(strip=True)
                value = option.get("value", "")
                if target in text:
                    logger.info(f"  Found season ID: {value} ({text})")
                    return value

        logger.warning(f"  Could not find season ID for {year}")
        return None
    except Exception as e:
        logger.error(f"  Error discovering season ID: {e}")
        return None


def scrape_ranking_page(stat_name, stat_config, year, season_id, page, debug=False):
    stat_id = stat_config["id"]
    url = f"https://stats.ncaa.org/rankings?sport_code=MBA&division=1&stat_seq={stat_id}"
    if season_id:
        url += f"&academic_year={season_id}"

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        # Wait for table to appear
        try:
            page.wait_for_selector("table", timeout=10000)
        except Exception:
            logger.warning(f"    No table loaded for {stat_name} {year}")
            return []

        if debug:
            debug_dir = os.path.join(LOG_DIR, "debug_html")
            Path(debug_dir).mkdir(parents=True, exist_ok=True)
            with open(os.path.join(debug_dir, f"{year}_{stat_name}.html"), "w") as f:
                f.write(page.content())

        html = page.content()
        soup = BeautifulSoup(html, "lxml")

        table = soup.find("table", {"id": "rankings_table"})
        if not table:
            table = soup.find("table", class_="dataTable")
        if not table:
            tables = soup.find_all("table")
            if tables:
                table = max(tables, key=lambda t: len(t.find_all("tr")))
        if not table:
            logger.warning(f"    No table found in HTML for {stat_name} {year}")
            return []

        rows = []
        for tr in table.find_all("tr")[1:]:
            cells = tr.find_all("td")
            if len(cells) < 3:
                continue
            try:
                rank_text = cells[0].get_text(strip=True)
                team_text = cells[1].get_text(strip=True)
                value_text = cells[-1].get_text(strip=True)
                team_clean = team_text.split("(")[0].strip()
                value_clean = value_text.replace(",", "")
                rank_num = int(rank_text) if rank_text.isdigit() else None
                value_num = float(value_clean)
                rows.append({
                    "team": team_clean,
                    "rank": rank_num,
                    "value": value_num,
                })
            except (ValueError, IndexError):
                continue

        return rows

    except Exception as e:
        logger.error(f"    Error for {stat_name} {year}: {e}")
        if debug:
            traceback.print_exc()
        return []


def scrape_year(year, page, debug=False):
    outfile = os.path.join(LOG_DIR, f"team_stats_{year}.csv")
    if os.path.exists(outfile):
        logger.info(f"  Already exists: {outfile}, loading from cache")
        return pd.read_csv(outfile)

    season_id = discover_season_id(year, page, debug)
    if not season_id:
        logger.warning(f"  No season ID for {year}, trying without it")

    all_stat_data = {}
    stats_scraped = 0
    stats_failed = 0

    for stat_name, stat_config in tqdm(STAT_CATEGORIES.items(), desc=f"  {year}"):
        rows = scrape_ranking_page(stat_name, stat_config, year, season_id, page, debug)
        if rows:
            all_stat_data[stat_name] = {r["team"]: r["value"] for r in rows}
            stats_scraped += 1
            logger.info(f"    {stat_name}: {len(rows)} teams")
        else:
            stats_failed += 1
            logger.warning(f"    {stat_name}: FAILED")
        time.sleep(2)

    logger.info(f"  Year {year} summary: {stats_scraped} stats OK, {stats_failed} failed")

    if not all_stat_data:
        logger.error(f"  No data collected for {year}!")
        return pd.DataFrame()

    all_teams = set()
    for stat_teams in all_stat_data.values():
        all_teams.update(stat_teams.keys())

    records = []
    for team in sorted(all_teams):
        record = {"year": year, "team": team}
        for sn, tv in all_stat_data.items():
            record[sn] = tv.get(team)
        records.append(record)

    df = pd.DataFrame(records)
    if "slugging_pct" in df.columns and "batting_avg" in df.columns:
        df["iso"] = df["slugging_pct"] - df["batting_avg"]
    if "on_base_pct" in df.columns and "slugging_pct" in df.columns:
        df["ops"] = df["on_base_pct"] + df["slugging_pct"]

    df.to_csv(outfile, index=False)
    logger.info(f"  Saved {len(df)} teams x {len(df.columns)} cols to {outfile}")
    return df


def scrape_all(years=None, debug=False):
    if years is None:
        years = ALL_YEARS

    # Save stat metadata
    meta = {}
    for stat_name, config in STAT_CATEGORIES.items():
        meta[stat_name] = {
            "type": config["type"],
            "lower_is_better": config["lower_is_better"],
        }
    meta["iso"] = {"type": "batting", "lower_is_better": False}
    meta["ops"] = {"type": "batting", "lower_is_better": False}
    with open(STAT_META_FILE, "w") as f:
        json.dump(meta, f, indent=2)
    logger.info(f"Saved stat metadata to {STAT_META_FILE}")

    # Launch browser
    pw, browser, context, page = setup_browser()

    try:
        all_dfs = []
        for year in years:
            logger.info(f"\n{'='*60}")
            logger.info(f"SCRAPING {year}")
            logger.info(f"{'='*60}")
            df = scrape_year(year, page, debug)
            if not df.empty:
                all_dfs.append(df)

        if all_dfs:
            master = pd.concat(all_dfs, ignore_index=True)
            master_file = os.path.join(LOG_DIR, "all_team_stats.csv")
            master.to_csv(master_file, index=False)
            logger.info(f"\n{'='*60}")
            logger.info(f"MASTER DATASET: {len(master)} rows x {len(master.columns)} cols")
            logger.info(f"Years: {sorted(master['year'].unique())}")
            logger.info(f"Teams per year: ~{len(master) // len(master['year'].unique())}")
            logger.info(f"Saved to {master_file}")
            logger.info(f"{'='*60}")
            logger.info("\nData completeness by stat:")
            for col in sorted(master.columns):
                if col in ("year", "team"):
                    continue
                pct = master[col].notna().mean() * 100
                logger.info(f"  {col:25s}: {pct:5.1f}% complete")
        else:
            logger.error("No data collected for any year!")
            sys.exit(1)
    finally:
        context.close()
        browser.close()
        pw.stop()
        logger.info("Browser closed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape NCAA D1 baseball team stats")
    parser.add_argument("--debug", action="store_true",
                        help="Save raw HTML and extra logging")
    parser.add_argument("--test", action="store_true",
                        help="Only scrape 2024-2025 (quick test)")
    parser.add_argument("--years", type=str, default=None,
                        help="Comma-separated years (e.g. 2023,2024,2025)")
    args = parser.parse_args()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    years = None
    if args.test:
        years = [2024, 2025]
    elif args.years:
        years = [int(y.strip()) for y in args.years.split(",")]
    logger.info(f"Starting scrape at {datetime.now().isoformat()}")
    logger.info(f"Years: {years or ALL_YEARS}")
    logger.info(f"Debug: {args.debug}")
    scrape_all(years=years, debug=args.debug)
```

---

Also update `requirements.txt` — replace entirely:
```
pandas>=1.5.0
numpy>=1.23.0
scipy>=1.9.0
scikit-learn>=1.1.0
matplotlib>=3.6.0
seaborn>=0.12.0
requests>=2.28.0
beautifulsoup4>=4.11.0
lxml>=4.9.0
tqdm>=4.64.0
openpyxl>=3.0.0
playwright>=1.40.0
