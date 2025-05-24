# config.py
"""
Konfigurasi untuk aplikasi Mesin Pencari Internal.
"""

# URL awal (seed URL) organisasi.
SEED_URL = "https://upi.edu"

# Batas kedalaman crawling (0 berarti hanya seed URL, 1 berarti seed URL dan link langsungnya, dst.)
# Untuk kasus ini, kita set MAX_DEPTH = 3 agar crawling berhenti setelah mencapai halaman di kedalaman 3.
# Artinya, halaman pada kedalaman 0, 1, 2, dan 3 akan di-crawl.
# Link yang ditemukan pada halaman di kedalaman 3 tidak akan diikuti lagi (yang akan menjadi kedalaman 4).
MAX_DEPTH = 3

# Batas jumlah hasil pencarian yang ditampilkan.
SEARCH_RESULT_LIMIT = 100