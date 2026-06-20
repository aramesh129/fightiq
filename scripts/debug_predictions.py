"""
Debug why generate-predictions returns 0.
Runs the same logic as the API endpoint but locally with full logging.
"""
import os, datetime, logging
import numpy as np
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("debug")
db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

# Step 1: what does upcoming_card return?
log.info("Fetching upcoming_card...")
upcoming = db.table("upcoming_card").select("*").execute().data
log.info(f"upcoming_card rows: {len(upcoming)}")

if not upcoming:
    log.error("upcoming_card is empty - that's the problem")
else:
    for bout in upcoming[:3]:
        log.info(f"  Bout: {bout.get('red_fighter')} vs {bout.get('blue_fighter')}")
        log.info(f"    red_fighter_id: {bout.get('red_fighter_id')}")
        log.info(f"    blue_fighter_id: {bout.get('blue_fighter_id')}")
        log.info(f"    bout_id: {bout.get('bout_id')}")

        # Step 2: fetch fighter stats
        red = db.table("fighters").select("*").eq(
            "fighter_id", bout["red_fighter_id"]).single().execute().data
        blue = db.table("fighters").select("*").eq(
            "fighter_id", bout["blue_fighter_id"]).single().execute().data

        log.info(f"    red slpm={red.get('slpm')} sapm={red.get('sapm')} wins={red.get('wins')}")
        log.info(f"    blue slpm={blue.get('slpm')} sapm={blue.get('sapm')} wins={blue.get('wins')}")

        # Step 3: try engineering features
        def s(v): return float(v) if v is not None else 0.0
        def wp(f):
            w = f.get("wins", 0) or 0
            l = f.get("losses", 0) or 0
            return w / (w + l) if (w + l) > 0 else 0.5

        try:
            features = [
                s(red.get("slpm"))    - s(blue.get("slpm")),
                s(red.get("str_acc")) - s(blue.get("str_acc")),
                s(red.get("sapm"))    - s(blue.get("sapm")),
                s(red.get("str_def")) - s(blue.get("str_def")),
                s(red.get("td_avg"))  - s(blue.get("td_avg")),
                s(red.get("td_acc"))  - s(blue.get("td_acc")),
                s(red.get("td_def"))  - s(blue.get("td_def")),
                s(red.get("sub_avg")) - s(blue.get("sub_avg")),
                wp(red), wp(blue), wp(red) - wp(blue),
            ]
            log.info(f"    Features OK: {features[:5]}")
        except Exception as e:
            log.error(f"    Feature engineering FAILED: {e}")