import os
from supabase import create_client
from dotenv import load_dotenv
load_dotenv()
db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
upcoming = db.table("events").select("event_id").eq("is_completed", False).execute().data
eids = [e["event_id"] for e in upcoming]
for eid in eids:
    bouts = db.table("bouts").select("bout_id").eq("event_id", eid).execute().data
    for b in bouts:
        db.table("predictions").delete().eq("bout_id", b["bout_id"]).execute()
        print(f"Deleted prediction for {b['bout_id']}")
print("Done")