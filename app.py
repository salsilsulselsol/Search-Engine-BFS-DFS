# app.py
"""
File utama untuk aplikasi Flask Mesin Pencari Internal.
"""
# Hapus import argparse jika tidak digunakan lagi
# import argparse
from flask import Flask, render_template, request, jsonify
from urllib.parse import urlparse

# Impor dari modul lokal
import config
from crawler import WebCrawler

# Variabel global untuk menyimpan instance crawler agar bisa diakses oleh rute Flask
crawler_instance = None

def get_crawl_strategy_from_input():
    """Meminta pengguna untuk memilih strategi crawling."""
    while True:
        print("\nPilih strategi crawling:")
        print("1: BFS (Breadth-First Search)")
        print("2: DFS (Depth-First Search)")
        choice = input("Masukkan pilihan (1 atau 2, default BFS jika input kosong): ").strip()

        if choice == '1':
            return "BFS"
        elif choice == '2':
            return "DFS"
        elif not choice: # Jika pengguna hanya menekan Enter (input kosong)
            print("Tidak ada input, menggunakan strategi default: BFS.")
            return "BFS"
        else:
            print("Pilihan tidak valid. Silakan coba lagi.")

def create_app(selected_strategy):
    """
    Membuat dan mengkonfigurasi instance aplikasi Flask.
    Juga menginisialisasi dan menjalankan crawler.
    """
    global crawler_instance

    app = Flask(__name__)

    # --- Inisialisasi Crawler ---
    base_domain = urlparse(config.SEED_URL).netloc
    try:
        crawler_instance = WebCrawler(
            seed_url=config.SEED_URL,
            base_domain=base_domain,
            strategy=selected_strategy
        )
    except ValueError as e:
        print(f"Kesalahan inisialisasi crawler: {e}")
        exit()

    # --- Lakukan Crawling ---
    print(f"\nMemulai proses crawling (Strategi: {selected_strategy})...")
    crawler_instance.crawl(max_pages=config.MAX_PAGES_TO_CRAWL)
    print("Proses crawling selesai.")

    # --- Rute Flask ---
    @app.route('/')
    def index():
        return render_template('index.html', SEED_URL=config.SEED_URL) #

    @app.route('/search', methods=['POST'])
    def search_results():
        global crawler_instance
        keyword = request.form.get('keyword', '').strip()
        if not keyword:
            return render_template('index.html', error="Kata kunci tidak boleh kosong.", SEED_URL=config.SEED_URL) #

        if crawler_instance is None:
            return render_template('index.html', error="Crawler belum diinisialisasi.", SEED_URL=config.SEED_URL)

        results = crawler_instance.search(keyword, limit=config.SEARCH_RESULT_LIMIT) #
        return render_template('index.html', keyword=keyword, results=results, SEED_URL=config.SEED_URL) #

    @app.route('/get_link_path')
    def get_link_path():
        global crawler_instance
        target_url = request.args.get('url')
        if not target_url:
            return jsonify({'error': 'URL target tidak disediakan.'}), 400 #

        if crawler_instance is None:
            return jsonify({'error': 'Crawler belum diinisialisasi.'}), 500

        path_details = crawler_instance.get_path_details(target_url) #
        return jsonify({'path': path_details}) #

    return app

# --- Jalankan Aplikasi Flask ---
if __name__ == '__main__':
    # Minta input strategi dari pengguna
    chosen_strategy = get_crawl_strategy_from_input()

    # Buat aplikasi Flask dengan strategi yang dipilih
    flask_app = create_app(chosen_strategy)
    
    # Jalankan server Flask
    # Tidak perlu khawatir tentang reloader Flask dan argparse di sini
    # karena kita tidak menggunakan argparse.
    print(f"\nServer Flask berjalan di http://127.0.0.1:5000/")
    print("Tekan CTRL+C untuk menghentikan server.")
    flask_app.run(debug=True) # Anda bisa membiarkan debug=True jika diinginkan