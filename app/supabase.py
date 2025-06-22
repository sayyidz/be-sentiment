from supabase import create_client
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Ambil URL dan API Key
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Buat client supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
