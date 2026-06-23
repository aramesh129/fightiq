import os, time, logging
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
log = logging.getLogger('fix_winners')
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
db = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])
BASE = 'http://www.ufcstats.com'

def make_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationDetection')
    options.add_argument('--window-size=1920,1080')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_page_load_timeout(60)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def get_page(driver, url, wait_class=None):
    for attempt in range(3):
        try:
            driver.get(url)
            time.sleep(0.8)
            if wait_class:
                try:
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CLASS_NAME, wait_class)))
                except: pass
            return BeautifulSoup(driver.page_source, 'lxml'), driver
        except Exception as e:
            log.warning(f'Attempt {attempt+1} failed: {e}')
            time.sleep(3)
            try: driver.quit()
            except: pass
            driver = make_driver()
    return BeautifulSoup(driver.page_source, 'lxml'), driver

def build_name_cache():
    fighters = db.table('fighters').select('fighter_id,first_name,last_name').execute().data
    cache = {}
    for f in fighters:
        name = f"{f['first_name']} {f['last_name']}".strip().lower()
        cache[name] = f['fighter_id']
    log.info(f'Name cache: {len(cache)} fighters')
    return cache

def process_event(driver, event_url, event_id, name_cache):
    soup, driver = get_page(driver, event_url, wait_class='b-fight-details__table-row')
    rows = soup.select('tr.b-fight-details__table-row[data-link]')
    updated = 0
    for row in rows:
        cols = row.select('td.b-fight-details__table-col')
        if len(cols) < 8: continue

        # Col 0: check for b-flag_style_green = winner is first fighter listed
        col0 = cols[0]
        has_win_flag = bool(col0.select_one('a.b-flag_style_green'))

        # Col 1: two fighter names first listed is always the winner on ufcstats
        fighter_links = cols[1].select('a.b-link')
        if len(fighter_links) < 2: continue
        name_first  = fighter_links[0].get_text(strip=True).lower()
        name_second = fighter_links[1].get_text(strip=True).lower()

        id_first  = name_cache.get(name_first)
        id_second = name_cache.get(name_second)
        if not id_first or not id_second:
            log.debug(f'  Fighters not found: {name_first} vs {name_second}')
            continue

        # Winner = first listed fighter (ufcstats always puts winner first)
        # Only set winner if green flag present (excludes draws/NCs)
        winner_id = id_first if has_win_flag else None

        win_method = cols[7].get_text(strip=True) if len(cols) > 7 else None
        win_round = None
        if len(cols) > 8:
            try: win_round = int(cols[8].get_text(strip=True))
            except: pass
        if not win_method or win_method in ['', '---', 'Method']:
            win_method = None

        # Find the bout try both red/blue assignments since scraper was arbitrary
        bout = None
        for r, b in [(id_first, id_second), (id_second, id_first)]:
            res = db.table('bouts').select('bout_id').eq('event_id', event_id).eq(
                'fighter_red_id', r).eq('fighter_blue_id', b).execute()
            if res.data:
                bout = res.data[0]
                break

        if not bout:
            log.debug(f'  Bout not found: {name_first} vs {name_second}')
            continue

        db.table('bouts').update({
            'winner_id':  winner_id,
            'win_method': win_method,
            'win_round':  win_round,
        }).eq('bout_id', bout['bout_id']).execute()
        updated += 1

    log.debug(f'  Updated {updated} bouts')
    return driver

def main():
    log.info('Starting winner fix...')
    name_cache = build_name_cache()

    # Get all event URLs in one scrape
    driver = make_driver()
    log.info('Browser started. Fetching event URLs...')
    soup, driver = get_page(driver, f'{BASE}/statistics/events/completed?page=all',
                             wait_class='b-statistics__table-row')
    event_url_map = {}
    for row in soup.select('tr.b-statistics__table-row'):
        a = row.select_one('a.b-link')
        if a and a.get('href'):
            event_url_map[a.get_text(strip=True).lower()] = a['href']
    log.info(f'Got {len(event_url_map)} event URLs')

    db_events = db.table('events').select('event_id,event_name').eq(
        'is_completed', True).execute().data
    total = len(db_events)

    try:
        for i, event in enumerate(db_events, 1):
            missing = db.table('bouts').select('bout_id', count='exact').eq(
                'event_id', event['event_id']).is_('winner_id', 'null').execute()
            if missing.count == 0:
                log.info(f'[{i}/{total}] SKIP: {event["event_name"]}')
                continue

            url = event_url_map.get(event['event_name'].lower())
            if not url:
                log.warning(f'[{i}/{total}] No URL: {event["event_name"]}')
                continue

            log.info(f'[{i}/{total}] {event["event_name"]} ({missing.count} bouts)')
            driver = process_event(driver, url, event['event_id'], name_cache)
    finally:
        try: driver.quit()
        except: pass

    red = db.table('bouts').select('bout_id', count='exact').not_.is_('winner_id','null').filter('winner_id','eq','fighter_red_id').execute()
    result = db.table('bouts').select('bout_id', count='exact').not_.is_('winner_id','null').execute()
    log.info(f'Done! {result.count} bouts now have winners set.')

    # Quick sanity check
    import subprocess
    log.info('Run this SQL to verify: SELECT COUNT(*) FILTER (WHERE winner_id = fighter_red_id) AS red_wins, COUNT(*) FILTER (WHERE winner_id = fighter_blue_id) AS blue_wins FROM bouts;')

if __name__ == '__main__':
    main()
