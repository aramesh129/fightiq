import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

res = db.table("bouts").select(
    "win_method, win_round,"
    "winner:fighters!bouts_winner_id_fkey(first_name, last_name),"
    "red:fighters!bouts_fighter_red_id_fkey(first_name, last_name),"
    "blue:fighters!bouts_fighter_blue_id_fkey(first_name, last_name)"
).not_.is_("winner_id", "null").limit(5).execute()

print(f"{'WINNER':<25} {'RED FIGHTER':<25} {'BLUE FIGHTER':<25} {'METHOD'}")
print("-" * 95)
for b in res.data:
    w = f"{b['winner']['first_name']} {b['winner']['last_name']}"
    r = f"{b['red']['first_name']} {b['red']['last_name']}"
    bl = f"{b['blue']['first_name']} {b['blue']['last_name']}"
    m = b.get('win_method') or ''
    print(f"{w:<25} {r:<25} {bl:<25} {m}")
