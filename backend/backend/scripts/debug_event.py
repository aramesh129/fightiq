import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

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

driver = make_driver()
driver.get('http://www.ufcstats.com/statistics/events/completed?page=all')
time.sleep(3)
WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, 'b-statistics__table-row')))
soup = BeautifulSoup(driver.page_source, 'lxml')
event_url = None
for row in soup.select('tr.b-statistics__table-row'):
    a = row.select_one('a.b-link')
    if a and a.get('href'):
        event_url = a['href']
        print(f'Event: {a.get_text(strip=True)}')
        break

driver.get(event_url)
time.sleep(3)
WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, 'b-fight-details__table-row')))
soup2 = BeautifulSoup(driver.page_source, 'lxml')
data_rows = soup2.select('tr.b-fight-details__table-row[data-link]')
print(f'Data rows found: {len(data_rows)}')

if data_rows:
    print('\n=== FIRST BOUT ROW RAW HTML ===')
    print(str(data_rows[0])[:2000])
    print('\n=== COL 0 FULL HTML (W/L column) ===')
    cols = data_rows[0].select('td.b-fight-details__table-col')
    if cols:
        print(str(cols[0]))
    print('\n=== ALL COLS TEXT ===')
    for j, col in enumerate(cols):
        print(f'  Col {j}: {repr(col.get_text(chr(32), strip=True)[:150])}')

driver.quit()
print('Done.')
