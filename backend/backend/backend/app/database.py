import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])