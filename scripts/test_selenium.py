from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time, sys

print("Starting...", flush=True)

options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationDetection")
options.add_argument("--window-size=1920,1080")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

try:
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    print("Driver started.", flush=True)

    driver.get("http://www.ufcstats.com/statistics/events/completed?page=all")
    print("Page loaded, waiting for content...", flush=True)

    # Wait up to 15 seconds for actual table rows to appear
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CLASS_NAME, "b-statistics__table-row"))
    )

    rows = driver.find_elements(By.CLASS_NAME, "b-statistics__table-row")
    print(f"Found {len(rows)} rows", flush=True)
    print("Page length:", len(driver.page_source), flush=True)

    # Print first event name as a sanity check
    links = driver.find_elements(By.CSS_SELECTOR, "tr.b-statistics__table-row a.b-link")
    if links:
        print("First event:", links[0].text, flush=True)

    driver.quit()
    print("Done.", flush=True)
except Exception as e:
    print("ERROR:", e, flush=True)
    sys.exit(1)
