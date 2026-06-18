from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()
db = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])

# Check upcoming events
events = db.table('events').select('event_id,event_name').eq('is_completed', False).execute()
print(f'Upcoming events: {len(events.data)}')
for e in events.data:
    print(f'  {e["event_name"]} - {e["event_id"]}')
    bouts = db.table('bouts').select('bout_id,winner_id').eq('event_id', e['event_id']).execute()
    print(f'    Bouts: {len(bouts.data)}')

preds = db.table('predictions').select('bout_id').execute()
print(f'Total existing predictions: {len(preds.data)}')
