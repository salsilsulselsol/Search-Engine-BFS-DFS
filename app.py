# app.py
"""
File utama untuk aplikasi Flask Mesin Pencari Internal.
"""
from flask import Flask, render_template, request, jsonify
from urllib.parse import urlparse

# Impor dari modul lokal
import config
from crawler import WebCrawler

app = Flask(__name__) #

# --- Inisialisasi Crawler ---
# Domain dasar diekstrak dari SEED_URL untuk diteruskan ke crawler
base_domain = urlparse(config.SEED_URL).netloc #
crawler_instance = WebCrawler(config.SEED_URL, base_domain) #

# --- Lakukan Crawling (sekali saat aplikasi dimulai atau sesuai kebutuhan) ---
# Dalam aplikasi nyata, data ini akan di-cache ke database atau file,
# dan proses crawling mungkin dijalankan secara terpisah atau terjadwal.
# Untuk demo ini, kita jalankan saat startup.
print("Memulai proses crawling saat aplikasi dimulai...") #
crawler_instance.crawl(max_pages=config.MAX_PAGES_TO_CRAWL) #
print("Proses crawling selesai.") #

# --- Rute Flask ---
@app.route('/') #
def index():
    """
    Rute utama untuk menampilkan formulir pencarian.
    """
    return render_template('index.html', SEED_URL=config.SEED_URL) #

@app.route('/search', methods=['POST']) #
def search_results():
    """
    Rute untuk menangani permintaan pencarian.
    """
    keyword = request.form.get('keyword', '').strip() #
    if not keyword: #
        return render_template('index.html', error="Kata kunci tidak boleh kosong.", SEED_URL=config.SEED_URL) #

    results = crawler_instance.search(keyword, limit=config.SEARCH_RESULT_LIMIT) #
    return render_template('index.html', keyword=keyword, results=results, SEED_URL=config.SEED_URL) #

@app.route('/get_link_path') #
def get_link_path():
    """
    API untuk mendapatkan detail rute tautan untuk URL tertentu.
    Dipanggil oleh JavaScript di frontend.
    """
    target_url = request.args.get('url') #
    if not target_url: #
        return jsonify({'error': 'URL target tidak disediakan.'}), 400 #

    path_details = crawler_instance.get_path_details(target_url) #
    return jsonify({'path': path_details}) #

# --- Jalankan Aplikasi Flask ---
if __name__ == '__main__': #
    # Pastikan direktori 'templates' dan 'static' ada di lokasi yang sama dengan app.py
    # Untuk menjalankan: python app.py
    # Kemudian buka browser dan kunjungi http://127.0.0.1:5000/
    app.run(debug=True) #