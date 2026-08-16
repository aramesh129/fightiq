import requests
import os
from dotenv import load_dotenv

load_dotenv()
base = os.environ.get('HF_SPACE_URL', 'https://aramesh129-fightiq-api.hf.space')

r = requests.get(f'{base}/health')
print('Health:', r.json())

r2 = requests.get(f'{base}/api/upcoming')
print('Upcoming bouts:', len(r2.json()))
