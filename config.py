# config.py
"""
Konfigurasi untuk aplikasi Mesin Pencari Internal.
"""

# URL awal (seed URL) organisasi.
SEED_URL = "https://upi.edu"

# Batas jumlah halaman yang akan di-crawl untuk demo.
MAX_PAGES_TO_CRAWL = 100

# Batas jumlah hasil pencarian yang ditampilkan.
SEARCH_RESULT_LIMIT = 100

# Strategi crawling: "BFS" atau "DFS"
# BFS akan menjelajah level demi level (lebih melebar).
# DFS akan menjelajah sedalam mungkin pada satu cabang sebelum ke cabang lain.
# CRAWL_STRATEGY = "BFS"  # Ubah menjadi "DFS" jika ingin menggunakan Depth-First Search