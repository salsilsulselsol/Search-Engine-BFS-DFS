# config.py
import os

SEED_URL = "https://upi.edu"

MAX_DEPTH = 2

SEARCH_RESULT_LIMIT = 30

CACHE_DIR = "cache_data"
parsed_seed_url = SEED_URL.replace("https://", "").replace("http://", "").replace("/", "_")
CACHE_FILENAME = f"crawled_data_{parsed_seed_url}_depth{MAX_DEPTH}.pkl"
CACHE_FILE_PATH = os.path.join(CACHE_DIR, CACHE_FILENAME)