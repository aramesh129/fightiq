import os, time, logging, requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from supabase import create_client
from dotenv import load_dotenv
from backfill import make_driver, get_page, upsert_event, scrape_event, prime_cache, db

load_dotenv()
log = logging.getLogger("scraper")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
BASE    = "http://www.ufcstats.com"
API_URL = os.environ.get("HF_SPACE_URL", "")


def load_upcoming(driver):
    log.info("Scraping upcoming events from ufcstats...")
    prime_cache()
    soup = get_page(driver, f"{BASE}/statistics/events/upcoming",
                    wait_class="b-statistics__table-row")
    added = 0
    events = []
    for row in soup.select("tr.b-statistics__table-row"):
        a = row.select_one("a.b-link")
        if not a: continue
        d  = row.select_one("span.b-statistics__date")
        ls = row.select("td.b-statistics__table-col")
        events.append({
            "name":     a.get_text(strip=True),
            "url":      a["href"],
            "date":     d.get_text(strip=True) if d else None,
            "location": ls[1].get_text(strip=True) if len(ls) > 1 else None,
        })
    log.info(f"Found {len(events)} upcoming events")
    for ev in events:
        existing = db.table("events").select("event_id").eq(
            "event_name", ev["name"]).execute()
        if existing.data:
            log.info(f"SKIP (exists): {ev['name']}")
            continue
        log.info(f"Loading: {ev['name']}")
        eid    = upsert_event(ev, False)
        driver = scrape_event(driver, ev["url"], eid)
        added += 1
    log.info(f"Added {added} new upcoming events")
    return driver


def settle_recent(driver):
    log.info("Checking for recently completed events...")
    prime_cache()
    pending = db.table("events").select(
        "event_id,event_name").eq("is_completed", False).execute().data
    if not pending:
        log.info("No pending events to settle")
        return driver

    soup = get_page(driver,
                    f"{BASE}/statistics/events/completed?page=all",
                    wait_class="b-statistics__table-row")
    completed_map = {}
    for row in soup.select("tr.b-statistics__table-row"):
        a = row.select_one("a.b-link")
        if a and a.get("href"):
            completed_map[a.get_text(strip=True).lower()] = a["href"]

    settled = 0
    for ev in pending:
        url = completed_map.get(ev["event_name"].lower())
        if not url:
            continue
        log.info(f"Settling: {ev['event_name']}")
        driver = scrape_event(driver, url, ev["event_id"])
        db.table("events").update({"is_completed": True}).eq(
            "event_id", ev["event_id"]).execute()
        settled += 1
    log.info(f"Settled {settled} events")
    return driver


def trigger_predictions():
    if not API_URL:
        log.warning("HF_SPACE_URL not set - skipping prediction trigger")
        return
    try:
        r = requests.post(f"{API_URL}/api/generate-predictions", timeout=120)
        log.info(f"Predictions triggered: HTTP {r.status_code} - {r.text}")
    except Exception as e:
        log.warning(f"Could not reach prediction API: {e}")


def main():
    driver = make_driver()
    log.info("Browser started.")
    try:
        driver = settle_recent(driver)
        driver = load_upcoming(driver)
    finally:
        try: driver.quit()
        except: pass
        log.info("Browser closed.")
    trigger_predictions()
    log.info("Scraper complete.")


if __name__ == "__main__":
    main()
