from flask import Flask, render_template, request, jsonify
from urllib.parse import urlparse

import config
from crawler import WebCrawler

crawler_instance = None

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

def create_app(selected_strategy):
    """Inisialisasi aplikasi Flask dan crawler."""
    global crawler_instance

    app = Flask(__name__)
    base_domain = urlparse(config.SEED_URL).netloc

    try:
        crawler_instance = WebCrawler(
            seed_url=config.SEED_URL,
            base_domain=base_domain,
        )
    except ValueError as e:
        print(f"Kesalahan inisialisasi crawler: {e}")
        exit()

    print(f"\nMulai crawling menggunakan strategi: {selected_strategy}")
    if selected_strategy == "BFS":
        crawler_instance.crawl_bfs(max_pages=config.MAX_PAGES_TO_CRAWL)
    else:
        crawler_instance.crawl_dfs(max_pages=config.MAX_PAGES_TO_CRAWL)
    print("Crawling selesai.")

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
    chosen_strategy = get_crawl_strategy_from_input()
    flask_app = create_app(chosen_strategy)
    print("\nServer Flask berjalan di http://127.0.0.1:5000/")
    flask_app.run(debug=True)
