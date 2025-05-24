from collections import defaultdict
from flask import Flask, render_template, request, jsonify
from urllib.parse import urlparse
import os # Import os

import config
from crawler import WebCrawler

crawler_instance = None

def get_user_choice_for_cache():
    """Meminta pengguna apakah akan menggunakan cache atau crawl ulang."""
    if os.path.exists(config.CACHE_FILE_PATH):
        while True:
            print(f"\nCache ditemukan di: {config.CACHE_FILE_PATH}")
            print("Apakah Anda ingin menggunakan data dari cache?")
            print("1: Ya, gunakan cache (lanjutkan crawling jika belum selesai atau sesuai MAX_DEPTH)")
            print("2: Tidak, hapus cache dan mulai crawling baru")
            print("3: Tidak, mulai crawling baru tanpa menghapus cache saat ini (akan menimpa jika disimpan)")
            choice = input("Masukkan pilihan (1, 2, atau 3, default 1 jika ada cache): ").strip()

            if choice == '1' or (not choice and os.path.exists(config.CACHE_FILE_PATH)):
                return "use_cache"
            elif choice == '2':
                try:
                    os.remove(config.CACHE_FILE_PATH)
                    print(f"Cache {config.CACHE_FILE_PATH} telah dihapus.")
                except OSError as e:
                    print(f"Error menghapus cache: {e}")
                return "recrawl_delete_cache"
            elif choice == '3':
                return "recrawl_overwrite_cache"
            else:
                print("Pilihan tidak valid. Ulangi.")
    else:
        print("\nTidak ada cache ditemukan. Akan memulai crawling baru.")
        return "no_cache_new_crawl"


def get_crawl_strategy_from_input():
    """Meminta pengguna memilih strategi crawling."""
    while True:
        print("\nPilih strategi crawling:")
        print("1: BFS (Breadth-First Search)")
        print("2: DFS (Depth-First Search)")
        choice = input("Masukkan pilihan (1 atau 2, default BFS jika kosong): ").strip()

        if choice == '1':
            return "BFS"
        elif choice == '2':
            return "DFS"
        elif not choice:
            print("Tidak ada input. Gunakan BFS sebagai default.")
            return "BFS"
        else:
            print("Pilihan tidak valid. Ulangi.")

def create_app(selected_strategy, cache_choice):
    """Inisialisasi aplikasi Flask dan crawler."""
    global crawler_instance

    app = Flask(__name__)
    base_domain = urlparse(config.SEED_URL).netloc

    try:
        crawler_instance = WebCrawler(
            seed_url=config.SEED_URL,
            base_domain=base_domain,
            strategy=selected_strategy # Teruskan strategi ke konstruktor
        )
    except ValueError as e:
        print(f"Kesalahan inisialisasi crawler: {e}")
        exit()

    perform_crawl = False
    if cache_choice == "use_cache":
        if crawler_instance._load_cache():
            print("Data berhasil dimuat dari cache.")
            # Cek apakah crawling perlu dilanjutkan (misalnya jika cache belum mencapai MAX_DEPTH)
            # Atau jika kita ingin selalu melanjutkan untuk menemukan update (logic lebih kompleks)
            # Untuk saat ini, kita anggap jika cache ada dan MAX_DEPTH config sama, mungkin tidak perlu crawl lagi.
            # Namun, untuk memastikan semua halaman hingga MAX_DEPTH tercapai, kita bisa set perform_crawl = True
            # atau tambahkan logic di crawler untuk melanjutkan dari state cache.
            # Untuk implementasi ini, kita akan tetap memanggil crawl, dan crawler akan handle
            # apa yang sudah ada di cache.
            
            # Cek apakah kedalaman maksimum dari cache kurang dari MAX_DEPTH
            max_depth_in_cache = crawler_instance.get_max_depth_from_data()
            if max_depth_in_cache < config.MAX_DEPTH:
                print(f"Cache mencapai kedalaman {max_depth_in_cache}, melanjutkan crawl hingga kedalaman {config.MAX_DEPTH}.")
                perform_crawl = True
            else:
                 # Periksa apakah semua halaman pada max_depth_in_cache memiliki konten
                 # Jika tidak, mungkin proses crawling sebelumnya terputus
                pages_at_max_depth = [
                    url for url, data in crawler_instance.crawled_data.items() 
                    if data.get('depth') == max_depth_in_cache and data.get('content') is None
                ]
                if pages_at_max_depth:
                    print(f"Beberapa halaman pada kedalaman {max_depth_in_cache} dari cache belum memiliki konten. Melanjutkan crawl.")
                    perform_crawl = True
                else:
                    print(f"Cache sudah mencakup hingga kedalaman {config.MAX_DEPTH} dan data tampak lengkap. Tidak ada crawling tambahan yang dijalankan kecuali ada link baru yang ditemukan dari halaman yang sudah di-cache hingga MAX_DEPTH-1.")
                    # Kita tetap panggil crawl agar frontier diisi dari halaman cache terakhir jika mereka belum dieksplor
                    perform_crawl = True # Tetap panggil crawl, biarkan crawler yang menentukan
        else:
            print("Gagal memuat cache atau cache tidak ada. Memulai crawling baru.")
            crawler_instance._reset_stats_for_new_crawl() # Reset jika gagal load
            perform_crawl = True
    elif cache_choice in ["recrawl_delete_cache", "recrawl_overwrite_cache", "no_cache_new_crawl"]:
        print("Memulai crawling baru.")
        crawler_instance._reset_stats_for_new_crawl() # Reset sebelum crawl baru
        perform_crawl = True

    if perform_crawl:
        print(f"\nMulai crawling (atau melanjutkan) menggunakan strategi: {selected_strategy} hingga kedalaman maksimal: {config.MAX_DEPTH}")
        if selected_strategy == "BFS":
            crawler_instance.crawl_bfs()
        else: # DFS
            crawler_instance.crawl_dfs()
        print("Proses crawling/pemeriksaan cache selesai.")
    else:
        print("Menggunakan data yang sudah ada dari cache. Tidak ada crawling baru yang dijalankan.")
        # Pastikan statistik total di-print jika hanya menggunakan cache
        print("\n--- Statistik dari Cache yang Digunakan ---")
        print(f"Seed URL: {config.SEED_URL}")
        print(f"MAX_DEPTH Dikonfigurasi: {config.MAX_DEPTH}")
        print(f"Total Halaman Tersimpan dari Cache: {len(crawler_instance.crawled_data)}")
        max_depth_cache_only = crawler_instance.get_max_depth_from_data()
        print(f"Kedalaman Maksimum dari Cache: {max_depth_cache_only}")
        
        current_pages_per_depth = defaultdict(int)
        for data_item in crawler_instance.crawled_data.values():
            current_pages_per_depth[data_item['depth']] +=1
        print("Distribusi Halaman per Kedalaman (dari cache):")
        for depth, count in sorted(current_pages_per_depth.items()):
            print(f"  Kedalaman {depth}: {count} halaman")
        if crawler_instance.stats.get("cache_file_used"):
             print(f"Cache file: {crawler_instance.stats.get('cache_file_used')}")
        print("-------------------------------------\n")


    # --- Rute Flask ---
    @app.route('/')
    def index():
        return render_template('index.html', SEED_URL=config.SEED_URL)

    @app.route('/search', methods=['POST'])
    def search_results():
        global crawler_instance
        keyword = request.form.get('keyword', '').strip()
        if not keyword:
            return render_template('index.html', error="Kata kunci tidak boleh kosong.", SEED_URL=config.SEED_URL)

        results = crawler_instance.search(keyword, limit=config.SEARCH_RESULT_LIMIT)
        return render_template('index.html', keyword=keyword, results=results, SEED_URL=config.SEED_URL)

    @app.route('/get_link_path')
    def get_link_path():
        global crawler_instance
        target_url = request.args.get('url')
        if not target_url:
            return jsonify({'error': 'URL target tidak disediakan.'}), 400

        path_details = crawler_instance.get_path_details(target_url)
        return jsonify({'path': path_details})

    return app

# --- Main ---
if __name__ == '__main__':
    cache_decision = get_user_choice_for_cache()
    chosen_strategy = get_crawl_strategy_from_input()
    
    flask_app = create_app(chosen_strategy, cache_decision)
    print(f"\nServer Flask berjalan di http://127.0.0.1:5000/ (Seed: {config.SEED_URL}, Max Depth: {config.MAX_DEPTH})")
    flask_app.run(debug=False)