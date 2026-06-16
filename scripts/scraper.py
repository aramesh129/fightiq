"""
Weekly scraper — runs every Monday via GitHub Actions.
Imports helpers from backfill.py (must be in same directory).
"""
import os, requests, logging
from dotenv import load_dotenv
from backfill import (get_soup, get_or_create_fighter, scrape_event,
                      upsert_event, prime_cache, get_all_events, db)

load_dotenv()
log = logging.getLogger("scraper")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
API_URL = os.environ.get("HF_SPACE_URL", "")


def settle_recent():
    log.info("Settling recently completed events...")
    prime_cache()
    pending   = db.table("events").select(
        "event_id,event_name").eq("is_completed", False).execute().data
    completed = {e["name"]: e["url"] for e in get_all_events(True)}
    settled   = 0
    for ev in pending:
        match = next(
            (url for name, url in completed.items()
             if ev["event_name"].lower() in name.lower()), None)
        if not match: continue
        log.info(f"Settling: {ev['event_name']}")
        scrape_event(match, ev["event_id"])
        db.table("events").update(
            {"is_completed": True}
        ).eq("event_id", ev["event_id"]).execute()
        settled += 1
    log.info(f"Settled {settled} events")


def load_upcoming():
    log.info("Loading new upcoming events...")
    prime_cache()
    added = 0
    for ev in get_all_events(False):
        if db.table("events").select("event_id").eq(
                "event_name", ev["name"]).execute().data:
            continue
        eid = upsert_event(ev, False)
        scrape_event(ev["url"], eid)
        added += 1
    log.info(f"Added {added} new events")


def trigger_predictions():
    if not API_URL: return
    try:
        r = requests.post(
            f"{API_URL}/api/generate-predictions", timeout=120)
        log.info(f"Predictions triggered: HTTP {r.status_code}")
    except Exception as e:
        log.warning(f"Could not reach prediction API: {e}")


if __name__ == "__main__":
    settle_recent()
    load_upcoming()
    trigger_predictions()