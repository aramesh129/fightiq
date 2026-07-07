import requests, os
from dotenv import load_dotenv
load_dotenv()
url = os.environ.get('HF_SPACE_URL', 'https://aramesh129-fightiq-api.hf.space') + '/api/generate-predictions'
print('Calling', url)
r = requests.post(url, timeout=120)
print('Status:', r.status_code)
print(r.text)