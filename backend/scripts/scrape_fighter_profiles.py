"""
Scrapes fighter profile stats (height, reach, stance, slpm, sapm etc.)
from ufcstats.com for all fighters missing stats.
Run once after backfill to populate career stats.
"""
import os, re, time, logging, datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("profiles")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
BASE = "http://www.ufcstats.com"

def make_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationDetection")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_page_load_timeout(60)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def get_page(driver, url, wait_class=None):
    for attempt in range(3):
        try:
            driver.get(url)
            time.sleep(0.6)
            if wait_class:
                try:
                    WebDriverWait(driver, 12).until(
                        EC.presence_of_element_located((By.CLASS_NAME, wait_class)))
                except: pass
            return BeautifulSoup(driver.page_source, "lxml"), driver
        except Exception as e:
            log.warning(f"Attempt {attempt+1} failed: {e}")
            time.sleep(3)
            try: driver.quit()
            except: pass
            driver = make_driver()
    return BeautifulSoup(driver.page_source, "lxml"), driver

def scrape_profile(soup) -> dict:
    stats = {}
    for item in soup.select("li.b-list__box-list-item"):
        text = item.get_text(" ", strip=True)
        if "Height:" in text:
            m = re.match(r".*?(\d+)'\s*(\d+)", text)
            if m:
                stats["height_cm"] = round(int(m.group(1))*30.48 + int(m.group(2))*2.54, 1)
        elif "Reach:" in text:
            try:
                stats["reach_cm"] = round(float(text.split(":")[-1].replace('"','').strip())*2.54, 1)
            except: pass
        elif "STANCE:" in text.upper():
            val = text.split(":")[-1].strip()
            if val and val != "--": stats["stance"] = val
        elif "DOB:" in text.upper():
            try:
                stats["birthday"] = datetime.datetime.strptime(
                    text.split(":")[-1].strip(), "%b %d, %Y").date().isoformat()
            except: pass

    smap = {
        "SLpM": "slpm", "SApM": "sapm",
        "Str. Acc.": "str_acc", "Str. Def": "str_def",
        "TD Avg.": "td_avg", "TD Acc.": "td_acc",
        "TD Def.": "td_def", "Sub. Avg.": "sub_avg",
    }
    for row in soup.select("li.b-list__box-list-item_type_block"):
        lbl_el = row.select_one(".b-list__box-list-item-title")
        val_el = row.select_one(".b-list__box-list-item-value")
        if not lbl_el or not val_el: continue
        lbl = lbl_el.get_text(strip=True)
        val = val_el.get_text(strip=True).replace("%","").strip()
        col = smap.get(lbl)
        if col and val and val != "--":
            try:
                v = float(val)/100.0 if "Acc" in lbl or "Def" in lbl else float(val)
                stats[col] = round(v, 4)
            except: pass
    return stats

def get_fighter_url(driver, first_name, last_name):
    """Search ufcstats fighter list for this fighter."""
    initial = last_name[0].lower() if last_name else first_name[0].lower()
    search_url = f"{BASE}/statistics/fighters?char={initial}&page=all"
    soup, driver = get_page(driver, search_url, wait_class="b-statistics__table-col")
    full_name = f"{first_name} {last_name}".strip().lower()
    for a in soup.select("a.b-link_style_black"):
        if a.get_text(strip=True).lower() == full_name:
            return a.get("href"), driver
    # fuzzy: try first name match
    for a in soup.select("a.b-link_style_black"):
        text = a.get_text(strip=True).lower()
        if first_name.lower() in text and last_name.lower() in text:
            return a.get("href"), driver
    return None, driver

def main():
    # Get fighters missing stats — prioritize those in upcoming bouts
    upcoming_ids = set()
    upcoming_bouts = db.table("bouts").select(
        "fighter_red_id,fighter_blue_id"
    ).in_("event_id",
        [e["event_id"] for e in db.table("events").select("event_id").eq(
            "is_completed", False).execute().data]
    ).execute().data
    for b in upcoming_bouts:
        upcoming_ids.add(b["fighter_red_id"])
        upcoming_ids.add(b["fighter_blue_id"])

    log.info(f"Upcoming bout fighters: {len(upcoming_ids)}")

    # Get all fighters missing slpm (main stat indicator)
    missing = db.table("fighters").select(
        "fighter_id,first_name,last_name"
    ).is_("slpm", "null").execute().data

    # Sort: upcoming fighters first
    missing.sort(key=lambda f: 0 if f["fighter_id"] in upcoming_ids else 1)
    log.info(f"Fighters missing stats: {len(missing)} (doing upcoming first)")

    driver = make_driver()
    updated = 0

    try:
        for i, f in enumerate(missing, 1):
            fname = f["first_name"]
            lname = f["last_name"]
            log.info(f"[{i}/{len(missing)}] {fname} {lname}")
            url, driver = get_fighter_url(driver, fname, lname)
            if not url:
                log.debug(f"  Not found on ufcstats")
                continue
            soup, driver = get_page(driver, url, wait_class="b-content__title-highlight")
            stats = scrape_profile(soup)
            if stats:
                db.table("fighters").update(stats).eq("fighter_id", f["fighter_id"]).execute()
                updated += 1
                log.info(f"  Updated: {stats}")
            else:
                log.debug(f"  No stats found")
    finally:
        try: driver.quit()
        except: pass

    log.info(f"Done! Updated {updated} fighters.")

if __name__ == "__main__":
    main()