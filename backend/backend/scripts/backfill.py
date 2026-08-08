"""
FightIQ Selenium Backfill - Crash-resistant version
Auto-restarts Chrome if it times out or crashes.
Safe to interrupt and re-run at any point.
"""
import os, uuid, time, logging, datetime
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
log = logging.getLogger("backfill")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
db   = create_client(os.environ["SUPABASE_URL"],
                     os.environ["SUPABASE_SERVICE_KEY"])
BASE = "http://www.ufcstats.com"
_cache: dict[str, str] = {}


def make_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationDetection")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--page-load-timeout=60")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.set_page_load_timeout(60)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def get_page(driver, url: str, wait_class: str = None,
             timeout: int = 15) -> BeautifulSoup:
    driver.get(url)
    time.sleep(0.5)
    if wait_class:
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, wait_class))
            )
        except: pass
    return BeautifulSoup(driver.page_source, "lxml")


def get_page_with_retry(driver, url: str, wait_class: str = None,
                         retries: int = 3) -> tuple:
    """
    Returns (soup, driver) driver may be a new instance if Chrome crashed.
    """
    for attempt in range(retries):
        try:
            soup = get_page(driver, url, wait_class=wait_class)
            return soup, driver
        except Exception as e:
            log.warning(f"Page load failed (attempt {attempt+1}): {e}")
            try:  driver.quit()
            except: pass
            time.sleep(3)
            log.info("Restarting Chrome...")
            driver = make_driver()
    # Final attempt after restart
    soup = get_page(driver, url, wait_class=wait_class)
    return soup, driver


def clean_int(v: str) -> int:
    try:    return int(v.strip().replace("---","0").replace("--","0"))
    except: return 0


def clean_ratio(v: str):
    try:
        a, b = v.strip().split(" of ")
        return int(a), int(b)
    except:
        return None, None


def prime_cache():
    global _cache
    for f in db.table("fighters").select(
            "fighter_id,first_name,last_name").execute().data:
        key = f"{f['first_name']} {f['last_name']}".strip().lower()
        _cache[key] = f["fighter_id"]
    log.info(f"Cache primed: {len(_cache)} fighters")


def get_or_create_fighter(name: str) -> str:
    key = name.strip().lower()
    if key in _cache:
        return _cache[key]
    parts   = name.strip().split(" ", 1)
    first   = parts[0]
    last    = parts[1] if len(parts) > 1 else ""

    # Try to find existing fighter first
    existing = db.table("fighters").select("fighter_id").eq(
        "first_name", first).eq("last_name", last).execute()
    if existing.data:
        fid = existing.data[0]["fighter_id"]
        _cache[key] = fid
        return fid

    # Create new fighter
    payload = {
        "fighter_id": str(uuid.uuid4()),
        "first_name": first,
        "last_name":  last,
    }
    res = db.table("fighters").insert(payload).execute()
    fid = res.data[0]["fighter_id"]
    _cache[key] = fid
    return fid


def scrape_fight_stats(driver, url: str,
                        bout_id: str, red_id: str, blue_id: str) -> webdriver.Chrome:
    try:
        soup, driver = get_page_with_retry(
            driver, url, wait_class="b-fight-details__table")
        tables = soup.select("table.b-fight-details__table")
        if not tables: return driver
        rows = tables[0].select("tr.b-fight-details__table-row")[1:]
        for i, row in enumerate(rows[:2]):
            fid  = red_id if i == 0 else blue_id
            cols = [td.get_text(strip=True) for td in row.select("td")]
            if len(cols) < 9: continue
            sl, sa   = clean_ratio(cols[2])
            tl, ta   = clean_ratio(cols[4]) if len(cols)>4 else (None,None)
            tdl, tda = clean_ratio(cols[5]) if len(cols)>5 else (None,None)
            ctrl = cols[9] if len(cols)>9 else "0:00"
            try:
                p = ctrl.split(":")
                ctrl_secs = int(p[0])*60 + int(p[1])
            except:
                ctrl_secs = 0
            s = {
                "stat_id":             str(uuid.uuid4()),
                "bout_id":             bout_id,
                "fighter_id":          fid,
                "kd":                  clean_int(cols[1]),
                "sig_str_landed":      sl  or 0,
                "sig_str_attempted":   sa  or 0,
                "total_str_landed":    tl  or 0,
                "total_str_attempted": ta  or 0,
                "td_landed":           tdl or 0,
                "td_attempted":        tda or 0,
                "sub_attempts":  clean_int(cols[7]) if len(cols)>7 else 0,
                "reversals":     clean_int(cols[8]) if len(cols)>8 else 0,
                "ctrl_time_secs": ctrl_secs,
            }
            if len(tables) > 1:
                trows = tables[1].select(
                    "tr.b-fight-details__table-row")[1:]
                if len(trows) > i:
                    tc = [td.get_text(strip=True)
                          for td in trows[i].select("td")]
                    if len(tc) >= 6:
                        hl,ha = clean_ratio(tc[3])
                        bl,ba = clean_ratio(tc[4])
                        ll,la = clean_ratio(tc[5])
                        s.update({
                            "head_landed":    hl or 0,
                            "head_attempted": ha or 0,
                            "body_landed":    bl or 0,
                            "body_attempted": ba or 0,
                            "leg_landed":     ll or 0,
                            "leg_attempted":  la or 0,
                        })
            db.table("fight_stats").upsert(
                s, on_conflict="bout_id,fighter_id").execute()
    except Exception as e:
        log.debug(f"Fight stats failed ({url}): {e}")
    return driver


def scrape_event(driver, event_url: str, event_id: str) -> webdriver.Chrome:
    soup, driver = get_page_with_retry(
        driver, event_url, wait_class="b-fight-details__table-row")
    rows = soup.select("tr.b-fight-details__table-row[data-link]")
    log.info(f"  {len(rows)} bouts")
    for order, row in enumerate(reversed(rows), start=1):
        cols  = row.select("td.b-fight-details__table-col")
        links = cols[1].select("a.b-link") if len(cols) > 1 else []
        if len(links) < 2: continue

        red_name  = links[0].get_text(strip=True)
        blue_name = links[1].get_text(strip=True)
        red_id    = get_or_create_fighter(red_name)
        blue_id   = get_or_create_fighter(blue_name)

        winner_idx = None
        for j, p in enumerate(cols[1].select("p")):
            if "status_style_green" in str(p):
                winner_idx = j; break
        winner_id = (red_id  if winner_idx == 0 else
                     blue_id if winner_idx == 1 else None)

        wc  = cols[6].get_text(strip=True) if len(cols)>6 else "Unknown"
        mth = cols[7].get_text(strip=True) if len(cols)>7 else None
        rnd = clean_int(cols[8].get_text()) if len(cols)>8 else None
        tme = cols[9].get_text(strip=True) if len(cols)>9 else None

        res = db.table("bouts").upsert({
            "bout_id":         str(uuid.uuid4()),
            "event_id":        event_id,
            "fighter_red_id":  red_id,
            "fighter_blue_id": blue_id,
            "weight_class":    wc.replace("Title Bout","").strip(),
            "bout_order":      order,
            "is_main_card":    order <= 5,
            "is_title_fight":  "title" in wc.lower(),
            "winner_id":       winner_id,
            "win_method":      mth,
            "win_round":       rnd,
            "win_time":        tme,
        }, on_conflict="event_id,fighter_red_id,fighter_blue_id").execute()

        actual_id  = res.data[0]["bout_id"]
        fight_link = row.get("data-link","")
        if fight_link:
            driver = scrape_fight_stats(
                driver, fight_link, actual_id, red_id, blue_id)

    return driver


def get_all_events(driver, completed: bool) -> list:
    path = "completed?page=all" if completed else "upcoming"
    soup, driver = get_page_with_retry(
        driver, f"{BASE}/statistics/events/{path}",
        wait_class="b-statistics__table-row")
    out = []
    for row in soup.select("tr.b-statistics__table-row"):
        a = row.select_one("a.b-link")
        if not a: continue
        d  = row.select_one("span.b-statistics__date")
        ls = row.select("td.b-statistics__table-col")
        out.append({
            "name":     a.get_text(strip=True),
            "url":      a["href"],
            "date":     d.get_text(strip=True) if d else None,
            "location": ls[1].get_text(strip=True) if len(ls)>1 else None,
        })
    return out, driver


def upsert_event(ev: dict, completed: bool) -> str:
    try:
        edate = datetime.datetime.strptime(
            ev["date"].strip(), "%B %d, %Y").isoformat()
    except:
        edate = datetime.datetime.utcnow().isoformat()
    res = db.table("events").upsert({
        "event_id":     str(uuid.uuid4()),
        "event_name":   ev["name"],
        "event_date":   edate,
        "location":     ev.get("location"),
        "is_completed": completed,
    }, on_conflict="event_name").execute()
    return res.data[0]["event_id"]


def main():
    log.info("Starting FightIQ backfill (crash-resistant)...")
    prime_cache()
    driver = make_driver()
    log.info("Browser started.")

    try:
        # Completed events
        log.info("Fetching completed events list...")
        completed, driver = get_all_events(driver, True)
        log.info(f"Found {len(completed)} completed events")

        for i, ev in enumerate(completed, 1):
            existing = db.table("events").select(
                "is_completed").eq("event_name", ev["name"]).execute()
            if existing.data and existing.data[0]["is_completed"]:
                log.info(f"[{i}/{len(completed)}] SKIP: {ev['name']}")
                continue
            log.info(f"[{i}/{len(completed)}] {ev['name']}")
            eid    = upsert_event(ev, True)
            driver = scrape_event(driver, ev["url"], eid)

        # Upcoming events
        log.info("Fetching upcoming events...")
        upcoming, driver = get_all_events(driver, False)
        for ev in upcoming:
            if db.table("events").select("event_id").eq(
                    "event_name", ev["name"]).execute().data:
                continue
            log.info(f"Loading upcoming: {ev['name']}")
            eid    = upsert_event(ev, False)
            driver = scrape_event(driver, ev["url"], eid)

    finally:
        try: driver.quit()
        except: pass
        log.info("Browser closed.")

    f = db.table("fighters").select("fighter_id", count="exact").execute().count
    e = db.table("events").select("event_id",     count="exact").execute().count
    b = db.table("bouts").select("bout_id",       count="exact").execute().count
    log.info(f"Done! Fighters={f} Events={e} Bouts={b}")


if __name__ == "__main__":
    main()
