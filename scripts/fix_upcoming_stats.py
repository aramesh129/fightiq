import os, re, time, logging, requests
from bs4 import BeautifulSoup
from supabase import create_client
from dotenv import load_dotenv
load_dotenv()

log = logging.getLogger("fix_stats")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def cm(val):
    if not val: return None
    m = re.search(r'(\d+)\'?\s*(\d*)"?', val)
    if m:
        ft = int(m.group(1)); inc = int(m.group(2) or 0)
        return round((ft * 12 + inc) * 2.54, 1)
    return None

def reach_cm(val):
    if not val: return None
    m = re.search(r'([\d.]+)"', val)
    return round(float(m.group(1)) * 2.54, 1) if m else None

def pct(val):
    if not val: return None
    m = re.search(r'([\d.]+)%', val)
    return round(float(m.group(1)) / 100, 4) if m else None

def flt(val):
    if not val: return None
    try: return float(re.search(r'[\d.]+', val).group())
    except: return None

def scrape_fighter(ufc_id):
    url = f"http://www.ufcstats.com/fighter-details/{ufc_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")
        items = soup.select("li.b-list__box-list-item")
        data = {}
        for item in items:
            text = item.get_text(" ", strip=True)
            if "Height:" in text: data["height_cm"] = cm(text.replace("Height:", "").strip())
            elif "Reach:" in text: data["reach_cm"] = reach_cm(text.replace("Reach:", "").strip())
            elif "Stance:" in text: data["stance"] = text.replace("Stance:", "").strip() or None
            elif "DOB:" in text:
                dob = text.replace("DOB:", "").strip()
                try:
                    from datetime import datetime
                    data["birthday"] = datetime.strptime(dob, "%b %d, %Y").strftime("%Y-%m-%d")
                except: pass
        stats = soup.select("li.b-list__box-list-item_type_block")
        for s in stats:
            text = s.get_text(" ", strip=True)
            if "SLpM:" in text: data["slpm"] = flt(text.replace("SLpM:", ""))
            elif "Str. Acc.:" in text: data["str_acc"] = pct(text.replace("Str. Acc.:", ""))
            elif "SApM:" in text: data["sapm"] = flt(text.replace("SApM:", ""))
            elif "Str. Def:" in text: data["str_def"] = pct(text.replace("Str. Def:", ""))
            elif "TD Avg.:" in text: data["td_avg"] = flt(text.replace("TD Avg.:", ""))
            elif "TD Acc.:" in text: data["td_acc"] = pct(text.replace("TD Acc.:", ""))
            elif "TD Def.:" in text: data["td_def"] = pct(text.replace("TD Def.:", ""))
            elif "Sub. Avg.:" in text: data["sub_avg"] = flt(text.replace("Sub. Avg.:", ""))
        return data
    except Exception as e:
        log.warning(f"Failed {ufc_id}: {e}")
        return {}

def main():
    # Get all fighters in upcoming bouts
    upcoming = db.table("bouts").select(
        "fighter_red_id,fighter_blue_id"
    ).is_("winner_id", "null").execute().data

    fighter_ids = set()
    for b in upcoming:
        fighter_ids.add(b["fighter_red_id"])
        fighter_ids.add(b["fighter_blue_id"])

    log.info(f"Found {len(fighter_ids)} fighters in upcoming bouts")

    for fid in fighter_ids:
        f = db.table("fighters").select("first_name,last_name,ufc_id,slpm").eq(
            "fighter_id", fid).single().execute().data
        if not f: continue
        name = f"{f['first_name']} {f['last_name']}"
        ufc_id = f.get("ufc_id")
        if not ufc_id:
            log.info(f"SKIP (no ufc_id): {name}")
            continue
        log.info(f"Scraping: {name} ({ufc_id})")
        stats = scrape_fighter(ufc_id)
        if stats:
            db.table("fighters").update(stats).eq("fighter_id", fid).execute()
            log.info(f"  Updated: {stats}")
        time.sleep(0.5)

    log.info("Done — regenerating predictions...")
    import requests as req
    r = req.post("https://aramesh129-fightiq-api.hf.space/api/generate-predictions", timeout=120)
    log.info(f"Predictions: {r.text}")

if __name__ == "__main__":
    main()