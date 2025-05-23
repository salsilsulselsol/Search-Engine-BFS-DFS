# app.py
# Ini adalah file utama untuk aplikasi Flask Anda.

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from collections import deque
import re # Untuk regex, bisa digunakan untuk membersihkan teks atau pencarian lebih spesifik

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# --- Konfigurasi Awal ---
# URL awal (seed URL) organisasi. Ganti dengan URL yang Anda inginkan.
SEED_URL = "https://upi.edu"
# Batas jumlah halaman yang akan di-crawl untuk demo.
# Untuk proyek akhir, Anda mungkin ingin meningkatkan ini atau menghapusnya setelah data di-cache.
MAX_PAGES_TO_CRAWL = 100
# Batas jumlah hasil pencarian yang ditampilkan.
SEARCH_RESULT_LIMIT = 10

# --- Kelas WebCrawler ---
class WebCrawler:
    def __init__(self, seed_url):
        self.seed_url = seed_url
        # Domain utama dari seed URL (misal: upi.edu)
        self.base_domain = urlparse(seed_url).netloc
        # Set untuk melacak URL yang sudah dikunjungi agar tidak mengulang
        self.visited_urls = set()
        # Deque (double-ended queue) untuk implementasi BFS
        self.queue = deque()
        # Dictionary untuk menyimpan data halaman yang di-crawl:
        # {url: {'title': '...', 'content': '...', 'parent_url': '...', 'path_info': [(url, title)]}}
        self.crawled_data = {}
        # Menambahkan header User-Agent untuk menghindari pemblokiran oleh server
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def _is_same_organization(self, url):
        """
        Memeriksa apakah URL termasuk dalam domain organisasi yang sama (termasuk subdomain).
        """
        parsed_url = urlparse(url)
        # Pastikan skema adalah http atau https
        if parsed_url.scheme not in ('http', 'https'):
            return False
        # Periksa apakah netloc (domain) berakhir dengan base_domain
        # Ini akan mencakup subdomain seperti 'pddikti.upi.edu'
        return parsed_url.netloc.endswith(self.base_domain)

    def _fetch_page(self, url):
        """
        Mengambil konten halaman web dari URL tertentu.
        Mengembalikan objek BeautifulSoup jika berhasil, None jika gagal.
        """
        try:
            # Mengatur timeout untuk request agar tidak terlalu lama menunggu
            # Menambahkan headers User-Agent
            response = requests.get(url, timeout=5, headers=self.headers)
            response.raise_for_status()  # Akan memunculkan HTTPError untuk status kode 4xx/5xx
            return BeautifulSoup(response.content, 'html.parser')
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def _extract_info(self, soup, current_url):
        """
        Mengekstrak judul dan konten teks utama dari objek BeautifulSoup.
        """
        title = soup.title.string if soup.title else "No Title"
        # Mencoba mengekstrak teks dari elemen-elemen konten utama
        # Anda bisa menyesuaikan selektor ini tergantung struktur website target
        content_tags = soup.find_all(['p', 'h1', 'h2', 'h3', 'li', 'span'])
        content = ' '.join([tag.get_text(separator=' ', strip=True) for tag in content_tags])
        # Membersihkan spasi berlebih
        content = re.sub(r'\s+', ' ', content).strip()
        return title, content

    def _extract_links(self, soup, base_url):
        """
        Mengekstrak semua tautan absolut dari objek BeautifulSoup yang berada dalam organisasi yang sama.
        Mengembalikan list tuple (url, link_text).
        """
        links = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            absolute_url = urljoin(base_url, href)
            # Normalisasi URL: hapus fragmen (misal #section)
            absolute_url = urlparse(absolute_url)._replace(fragment="").geturl()

            if self._is_same_organization(absolute_url):
                link_text = a_tag.get_text(strip=True) if a_tag.get_text(strip=True) else absolute_url
                links.append((absolute_url, link_text))
        return links

    def crawl(self, max_pages=MAX_PAGES_TO_CRAWL):
        """
        Melakukan crawling web menggunakan algoritma Breadth-First Search (BFS).
        """
        print(f"Memulai crawling dari: {self.seed_url}")
        self.queue.append((self.seed_url, None, [(self.seed_url, "Seed URL")])) # (url, parent_url, path_info)
        self.visited_urls.add(self.seed_url)
        crawled_count = 0

        while self.queue and crawled_count < max_pages:
            current_url, parent_url, current_path_info = self.queue.popleft()
            print(f"Crawling ({crawled_count+1}/{max_pages}): {current_url}")

            soup = self._fetch_page(current_url)
            if soup:
                title, content = self._extract_info(soup, current_url)
                # Simpan data halaman yang di-crawl
                self.crawled_data[current_url] = {
                    'title': title,
                    'content': content,
                    'parent_url': parent_url,
                    'path_info': current_path_info # Simpan rute lengkap ke halaman ini
                }
                crawled_count += 1

                # Ekstrak tautan baru
                new_links = self._extract_links(soup, current_url)
                for link_url, link_text in new_links:
                    if link_url not in self.visited_urls:
                        self.visited_urls.add(link_url)
                        # Buat path_info baru untuk link_url
                        new_path_info = current_path_info + [(link_url, link_text)]
                        self.queue.append((link_url, current_url, new_path_info))
            else:
                # Jika halaman tidak dapat diambil, tetap tandai sebagai dikunjungi
                # agar tidak mencoba lagi di masa mendatang
                self.visited_urls.add(current_url)

        print(f"Crawling selesai. Total halaman di-crawl: {crawled_count}")

    def search(self, keyword, limit=SEARCH_RESULT_LIMIT):
        """
        Mencari halaman yang mengandung kata kunci.
        Mengembalikan daftar hasil pencarian.
        """
        results = []
        keyword_lower = keyword.lower()
        for url, data in self.crawled_data.items():
            # Pencocokan sederhana: periksa kata kunci di judul atau konten
            if keyword_lower in data['title'].lower() or keyword_lower in data['content'].lower():
                snippet = data['content'][:200] + '...' if len(data['content']) > 200 else data['content']
                results.append({
                    'url': url,
                    'title': data['title'],
                    'snippet': snippet,
                    'path_info': data['path_info'] # Rute sudah disimpan saat crawling
                })
                if len(results) >= limit:
                    break
        return results

    def get_path_details(self, target_url):
        """
        Mengembalikan detail rute tautan untuk URL target.
        """
        if target_url in self.crawled_data:
            return self.crawled_data[target_url]['path_info']
        return []

# --- Inisialisasi Crawler dan Lakukan Crawling (sekali saat aplikasi dimulai) ---
# Dalam aplikasi nyata, data ini akan di-cache ke database atau file.
crawler = WebCrawler(SEED_URL)
# Lakukan crawling saat aplikasi dimulai. Ini bisa memakan waktu!
# Untuk pengembangan, Anda mungkin ingin menjalankan ini secara terpisah dan menyimpan hasilnya.
crawler.crawl(max_pages=MAX_PAGES_TO_CRAWL)

# --- Rute Flask ---
@app.route('/')
def index():
    """
    Rute utama untuk menampilkan formulir pencarian.
    """
    return render_template('index.html', SEED_URL=SEED_URL) # Pass SEED_URL to template

@app.route('/search', methods=['POST'])
def search_results():
    """
    Rute untuk menangani permintaan pencarian.
    """
    keyword = request.form.get('keyword', '').strip()
    if not keyword:
        return render_template('index.html', error="Kata kunci tidak boleh kosong.", SEED_URL=SEED_URL)

    results = crawler.search(keyword)
    return render_template('index.html', keyword=keyword, results=results, SEED_URL=SEED_URL)

@app.route('/get_link_path')
def get_link_path():
    """
    API untuk mendapatkan detail rute tautan untuk URL tertentu.
    Dipanggil oleh JavaScript di frontend.
    """
    target_url = request.args.get('url')
    if not target_url:
        return jsonify({'error': 'URL target tidak disediakan.'}), 400

    path_details = crawler.get_path_details(target_url)
    return jsonify({'path': path_details})

# --- Jalankan Aplikasi Flask ---
if __name__ == '__main__':
    # Pastikan direktori 'templates' dan 'static' ada di lokasi yang sama dengan app.py
    # Untuk menjalankan: python app.py
    # Kemudian buka browser dan kunjungi http://127.0.0.1:5000/
    app.run(debug=True) # debug=True akan me-reload server secara otomatis saat ada perubahan kode
