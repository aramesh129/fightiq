import requests
import os
from dotenv import load_dotenv

load_dotenv()

url = os.environ[https://aramesh129-fightiq-api.hf.space] + "/api/generate-predictions"
print(f"Calling {url}...")

r = requests.post(url, timeout=120)
print(f"Status: {r.status_code}")
print(r.text)