# config.py
"""
Konfigurasi untuk aplikasi Mesin Pencari Internal.
"""
import os

# URL awal (seed URL) organisasi.
SEED_URL = "https://upi.edu"

# Batas kedalaman crawling (0 berarti hanya seed URL, 1 berarti seed URL dan link langsungnya, dst.)
# Untuk kasus ini, kita set MAX_DEPTH = 3 agar crawling berhenti setelah mencapai halaman di kedalaman 3.
# Artinya, halaman pada kedalaman 0, 1, 2, dan 3 akan di-crawl.
# Link yang ditemukan pada halaman di kedalaman 3 tidak akan diikuti lagi (yang akan menjadi kedalaman 4).
MAX_DEPTH = 2

# Batas jumlah hasil pencarian yang ditampilkan.
SEARCH_RESULT_LIMIT = 30

# Direktori dan nama file untuk cache
CACHE_DIR = "cache_data"
# Membuat nama file cache yang lebih dinamis berdasarkan SEED_URL dan MAX_DEPTH
parsed_seed_url = SEED_URL.replace("https://", "").replace("http://", "").replace("/", "_")
CACHE_FILENAME = f"crawled_data_{parsed_seed_url}_depth{MAX_DEPTH}.pkl"
CACHE_FILE_PATH = os.path.join(CACHE_DIR, CACHE_FILENAME)