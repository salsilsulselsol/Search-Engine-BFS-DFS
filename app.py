# app.py
from collections import defaultdict
from flask import Flask, render_template, request, jsonify
from urllib.parse import urlparse
import os

import config
from crawler import WebCrawler

crawler_instance = None  # Inisialisasi crawler_instance global sebagai None

def get_user_choice_for_cache():
    # Kode ini tetap sama seperti yang Anda sediakan
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
    # Kode ini tetap sama seperti yang Anda sediakan
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

def create_app(perform_initial_crawl_flag):
    global crawler_instance # Menyatakan penggunaan instance global

    app = Flask(__name__)

    if crawler_instance is None:
        print("ERROR: crawler_instance tidak diinisialisasi sebelum create_app. Membuat instance default.")
        base_domain = urlparse(config.SEED_URL).netloc
        crawler_instance = WebCrawler(
            seed_url=config.SEED_URL,
            base_domain=base_domain,
            strategy="BFS"
        )

    if perform_initial_crawl_flag:
        print(f"\nMulai crawling (atau melanjutkan) menggunakan strategi: {crawler_instance.strategy} hingga kedalaman maksimal: {config.MAX_DEPTH}")
        if crawler_instance.strategy == "BFS":
            crawler_instance.crawl_bfs()
        else: 
            crawler_instance.crawl_dfs()
        print("Proses crawling/pemeriksaan cache selesai.")
    else:
        if crawler_instance.stats.get("loaded_from_cache"):
            print("Menggunakan data yang sudah ada dari cache. Tidak ada crawling baru yang dijalankan.")
            print("\n--- Statistik dari Cache yang Digunakan ---")
            print(f"Seed URL: {crawler_instance.seed_url}")
            print(f"Strategi dari Cache (atau saat ini): {crawler_instance.strategy}")
            print(f"MAX_DEPTH Dikonfigurasi: {config.MAX_DEPTH}")
            print(f"Total Halaman Tersimpan dari Cache: {len(crawler_instance.crawled_data)}")
            max_depth_cache_only = crawler_instance.get_max_depth_from_data()
            print(f"Kedalaman Maksimum dari Cache: {max_depth_cache_only}")
            
            current_pages_per_depth = defaultdict(int)
            if crawler_instance.crawled_data:
                for data_item in crawler_instance.crawled_data.values():
                    current_pages_per_depth[data_item.get('depth',0)] +=1
            print("Distribusi Halaman per Kedalaman (dari cache):")
            for depth, count in sorted(current_pages_per_depth.items()):
                print(f"  Kedalaman {depth}: {count} halaman")
            if crawler_instance.stats.get("cache_file_used"):
                 print(f"Cache file: {crawler_instance.stats.get('cache_file_used')}")
            print("-------------------------------------\n")
        else:
            print("Tidak ada data cache yang dimuat dan tidak ada crawling yang dijalankan. Pencarian mungkin tidak menghasilkan apa-apa.")

    @app.route('/')
    def index():
        current_seed_url = config.SEED_URL
        if crawler_instance and hasattr(crawler_instance, 'seed_url'):
            current_seed_url = crawler_instance.seed_url
        return render_template('index.html', SEED_URL=current_seed_url)

    @app.route('/search', methods=['POST'])
    def search_results():
        global crawler_instance 
        keyword = request.form.get('keyword', '').strip()
        
        current_seed_url = config.SEED_URL
        if crawler_instance and hasattr(crawler_instance, 'seed_url'):
            current_seed_url = crawler_instance.seed_url

        if not keyword:
            return render_template('index.html', error="Kata kunci tidak boleh kosong.", SEED_URL=current_seed_url)

        if crawler_instance is None or not crawler_instance.crawled_data:
             return render_template('index.html', keyword=keyword, results=[], error="Data belum di-crawl atau tidak ada data di cache. Silakan jalankan crawling terlebih dahulu.", SEED_URL=current_seed_url)

        results = crawler_instance.search(keyword, limit=config.SEARCH_RESULT_LIMIT)
        return render_template('index.html', keyword=keyword, results=results, SEED_URL=current_seed_url)

    @app.route('/get_link_path')
    def get_link_path():
        global crawler_instance
        target_url = request.args.get('url')
        if not target_url:
            return jsonify({'error': 'URL target tidak disediakan.'}), 400
        if crawler_instance is None:
            return jsonify({'error': 'Crawler tidak diinisialisasi.'}), 500

        path_details = crawler_instance.get_path_details(target_url)
        return jsonify({'path': path_details})

    return app

if __name__ == '__main__':
    cache_decision = get_user_choice_for_cache()
    chosen_strategy_for_crawl = None 
    perform_crawl_on_startup = False

    base_domain_for_init = urlparse(config.SEED_URL).netloc

    if cache_decision == "use_cache":
        # Inisialisasi instance crawler - strategi default "BFS" untuk memuat cache,
        # akan diperbarui jika strategi ada di cache atau jika pengguna memilih untuk melanjutkan crawling.
        crawler_instance = WebCrawler(seed_url=config.SEED_URL, base_domain=base_domain_for_init, strategy="BFS") 
        
        if crawler_instance._load_cache(): 
            print(f"Data berhasil dimuat dari cache. Strategi dari cache (atau default): {crawler_instance.strategy}")

            max_depth_in_cache = crawler_instance.get_max_depth_from_data()
            pages_at_max_depth_incomplete = False
            if max_depth_in_cache >= config.MAX_DEPTH:
                pages_at_max_depth_val = [
                    url for url, data in crawler_instance.crawled_data.items()
                    if data.get('depth') == max_depth_in_cache and data.get('content') is None and data.get('is_html')
                ]
                if pages_at_max_depth_val:
                    pages_at_max_depth_incomplete = True

            if max_depth_in_cache < config.MAX_DEPTH or pages_at_max_depth_incomplete:
                print(f"Cache saat ini pada kedalaman {max_depth_in_cache} atau ada data tidak lengkap. Crawling akan dilanjutkan hingga kedalaman {config.MAX_DEPTH}.")
                chosen_strategy_for_crawl = get_crawl_strategy_from_input()
                crawler_instance.strategy = chosen_strategy_for_crawl 
                perform_crawl_on_startup = True
                
                if pages_at_max_depth_incomplete:
                    print("Mengidentifikasi halaman HTML yang dikunjungi sebelumnya tanpa konten untuk di-fetch ulang.")
                    urls_to_refetch = [
                        url for url, data in crawler_instance.crawled_data.items()
                        if data.get('depth') == max_depth_in_cache and data.get('content') is None and data.get('is_html')
                    ]
                    for url_to_refetch in urls_to_refetch:
                        if url_to_refetch in crawler_instance.visited_urls:
                            print(f"Menandai {url_to_refetch} untuk di-fetch ulang dengan menghapusnya dari visited_urls sementara.")
                            crawler_instance.visited_urls.remove(url_to_refetch)
            else:
                print(f"Cache sudah mencakup hingga kedalaman {config.MAX_DEPTH} dan data tampak lengkap.")
                perform_crawl_on_startup = False
        else:
            print("Gagal memuat cache atau cache tidak ada / rusak. Memulai crawling baru.")
            chosen_strategy_for_crawl = get_crawl_strategy_from_input()
            # crawler_instance sudah dibuat dengan strategi "BFS", perbarui strategi dan reset data
            crawler_instance.strategy = chosen_strategy_for_crawl
            crawler_instance._reset_stats_for_new_crawl() 
            perform_crawl_on_startup = True
    
    elif cache_decision in ["recrawl_delete_cache", "recrawl_overwrite_cache", "no_cache_new_crawl"]:
        print("Memulai crawling baru.")
        chosen_strategy_for_crawl = get_crawl_strategy_from_input()
        crawler_instance = WebCrawler(seed_url=config.SEED_URL, base_domain=base_domain_for_init, strategy=chosen_strategy_for_crawl)
        perform_crawl_on_startup = True
    
    if crawler_instance is None:
        print("Peringatan: crawler_instance tidak terinisialisasi dengan benar. Menggunakan default.")
        temp_strategy = chosen_strategy_for_crawl if chosen_strategy_for_crawl else "BFS"
        crawler_instance = WebCrawler(seed_url=config.SEED_URL, base_domain=base_domain_for_init, strategy=temp_strategy)
        if not perform_crawl_on_startup : # Jika belum diset untuk crawl, dan kita jatuh ke fallback ini, maka harus crawl.
             perform_crawl_on_startup = True


    flask_app = create_app(perform_crawl_on_startup)
    
    active_strategy = crawler_instance.strategy if crawler_instance else "N/A"
    print(f"\nServer Flask berjalan di http://127.0.0.1:5000/ (Seed: {config.SEED_URL}, Max Depth: {config.MAX_DEPTH}, Strategy Active: {active_strategy})")
    flask_app.run(debug=False)