# Search-Engine-BFS-DFS

Mesin Pencari domain upi.edu sederhana yang dibuat dengan Flask dan Python. Proyek ini mendemonstrasikan penggunaan algoritma Breadth-First Search (BFS) atau Depth-First Search (DFS) untuk melakukan crawling halaman web dalam satu domain organisasi dan menyediakan fungsionalitas pencarian berdasarkan kata kunci pada konten yang telah di-crawl. Tujuan lainnya adalah untuk menganalisis algoritma yang digunakan pada proses crawling dan searching.

## Fitur Utama

* **Web Crawling**: Mampu menjelajahi halaman-halaman web mulai dari satu URL awal (seed URL) dalam domain yang ditentukan.
* **Pilihan Strategi Crawling**: Pengguna dapat memilih antara BFS atau DFS saat memulai aplikasi.
* **Ekstraksi Konten**: Mengekstrak judul dan konten teks dari halaman HTML. Untuk halaman error atau non-HTML, hanya URL dan judul (dari anchor text atau nama file) yang disimpan.
* **Pencarian Konten**: Memungkinkan pengguna untuk mencari kata kunci dalam judul dan konten halaman yang telah di-crawl.
* **Tampilan Rute Link**: Menampilkan bagaimana sebuah halaman hasil pencarian ditemukan (jalur dari seed URL).
* **Antarmuka Web**: Antarmuka pengguna berbasis web yang sederhana menggunakan Flask dan Tailwind CSS.
* **Upaya Anti-Blokir**: Menggunakan `requests.Session` untuk manajemen cookie, header HTTP yang lebih realistis (`User-Agent`, `Referer`), dan penundaan antar permintaan untuk mengurangi kemungkinan diblokir.

## Struktur Proyek

* `app.py`: File utama aplikasi Flask, menangani routing dan logika presentasi.
* `crawler.py`: Berisi kelas `WebCrawler` yang mengimplementasikan logika crawling dan pencarian.
* `config.py`: File konfigurasi untuk `SEED_URL`, `MAX_PAGES_TO_CRAWL`, dll.
* `templates/index.html`: Template HTML utama untuk antarmuka pengguna.
* `static/style.css`: File CSS tambahan (jika diperlukan).
* `requirements.txt`: Daftar dependensi Python.

## Cara Kerja Algoritma

### 1. Crawling (Penjelajahan Web)

Proses crawling dimulai dari satu URL yang disebut **Seed URL**. Tujuannya adalah untuk mengunjungi halaman-halaman web secara sistematis, mengambil kontennya, dan menemukan link ke halaman lain dalam domain yang sama.

* **Inisialisasi**:
    * Sebuah antrian (untuk BFS) atau stack (untuk DFS) diinisialisasi dengan Seed URL, beserta informasi jalur awal (parent URL adalah `None`, path berisi Seed URL itu sendiri, dan kedalaman 0).
    * Sebuah `set` (`` `visited_urls` ``) digunakan untuk melacak URL yang sudah dikunjungi agar tidak terjadi duplikasi proses atau loop tak terbatas.
    * Data hasil crawl disimpan dalam dictionary `` `crawled_data` ``.

* **Loop Utama Crawling**:
    1.  **Ambil URL**: Sebuah URL (`` `current_url` ``) diambil dari antrian (BFS: `popleft()`) atau stack (DFS: `pop()`).
    2.  **Delay**: Diterapkan penundaan acak untuk menghindari pembebanan server secara berlebihan dan mengurangi risiko diblokir.
    3.  **Fetch & Extract (`` `_fetch_and_extract_html_info` ``)**:
        * Permintaan HTTP GET dibuat ke `` `current_url` `` menggunakan `requests.Session` (untuk manajemen cookie dan header persisten). Header `Referer` diatur berdasarkan URL induk (`` `parent_url` ``).
        * **Penanganan Error**: Jika status respons adalah error (misalnya, 403, 404), judul diambil dari anchor text yang mengarah ke URL tersebut (jika ada) atau nama file dari URL. Konten dikosongkan.
        * **Non-HTML**: Jika tipe konten bukan HTML, judul diambil dari nama file URL, dan konten dikosongkan.
        * **HTML Sukses**:
            * Judul: Diambil dari tag `<title>`, fallback ke anchor text, lalu ke nama file.
            * Konten: Konten teks diekstrak dari elemen HTML prioritas seperti `<main>`, `<article>`, `div#content`, atau `div.content`. Jika kosong, fallback ke tag `<p>`, `<h1>-<h6>`, `<li>`. Sebagai upaya terakhir, seluruh teks dari `<body>` diambil. Teks dibersihkan dari spasi berlebih.
            * Ekstraksi Link: Semua tag `<a>` dengan `href` dianalisis. Link yang valid (HTTP/HTTPS, dalam domain yang sama, bukan `mailto:`, `tel:`, `javascript:`, atau `#`) diubah menjadi URL absolut. Teks link (anchor text) juga diekstrak.
    4.  **Simpan Data**: Informasi yang diekstrak (judul, konten, URL induk, path, kedalaman) disimpan di `` `crawled_data` `` dengan `` `current_url` `` sebagai key.
    5.  **Tambahkan Link Baru**: Untuk setiap link baru yang ditemukan dan belum ada di `` `visited_urls` ``:
        * URL ditambahkan ke `` `visited_urls` ``.
        * Path baru (dari Seed URL ke link ini) dibuat.
        * Tuple berisi (URL baru, URL saat ini sebagai parent, path baru, kedalaman saat ini + 1) ditambahkan ke antrian (BFS) atau stack (DFS).
    6.  Loop berlanjut hingga antrian/stack kosong atau `` `MAX_PAGES_TO_CRAWL` `` tercapai.

* **Strategi**:
    * **BFS (Breadth-First Search)**: Menjelajahi halaman level demi level. Menggunakan antrian (FIFO - First In, First Out). Cenderung menemukan halaman yang lebih dekat dengan Seed URL terlebih dahulu.
    * **DFS (Depth-First Search)**: Menjelajahi sedalam mungkin pada satu cabang sebelum kembali. Menggunakan stack (LIFO - Last In, First Out). Cenderung menemukan halaman yang lebih jauh lebih cepat jika berada di cabang yang "benar".

### 2. Search (Pencarian)

Setelah proses crawling selesai, data yang terkumpul di `` `crawled_data` `` digunakan untuk pencarian.

1.  **Input**: Pengguna memasukkan satu atau lebih kata kunci.
2.  **Preprocessing**: Kata kunci diubah menjadi huruf kecil dan dipecah menjadi beberapa term jika terdiri dari banyak kata.
3.  **Iterasi Data**: Crawler mengiterasi setiap entri (URL dan datanya) dalam `` `crawled_data` ``.
4.  **Pencocokan**:
    * **Judul**: Semua term pencarian harus ada dalam judul halaman (setelah diubah ke huruf kecil).
    * **Konten**: Jika konten halaman ada, semua term pencarian juga harus ada dalam konten tersebut (setelah diubah ke huruf kecil).
5.  **Hasil**: Jika ada kecocokan di judul atau konten:
    * Sebuah **snippet** dibuat. Jika konten cocok, snippet diambil dari sekitar term pencarian yang ditemukan. Jika hanya judul yang cocok atau konten tidak ada/tidak cocok, snippet akan mengindikasikan hal tersebut.
    * URL, judul, snippet, dan informasi path (`` `path_info` ``) ditambahkan ke daftar hasil.
6.  Proses dihentikan jika jumlah hasil mencapai `` `SEARCH_RESULT_LIMIT` ``.

## Analisis Algoritma

### Kompleksitas Waktu

* **Crawling (BFS/DFS)**:
    * Misalkan `V` adalah jumlah halaman (vertex) yang dikunjungi dan `E` adalah jumlah total link (edge) pada halaman-halaman tersebut.
    * Setiap halaman dikunjungi sekali (karena `` `visited_urls` ``). Untuk setiap halaman, semua linknya diekstrak.
    * Operasi dominan adalah permintaan HTTP (`requests.get`) dan parsing HTML (`BeautifulSoup`). Waktu parsing bisa bergantung pada ukuran halaman.
    * Secara teoritis, kompleksitas dasar untuk BFS dan DFS pada graf adalah O(V + E). Namun, dalam konteks web crawling, faktor waktu I/O (network latency, server response time) dan parsing HTML menjadi sangat signifikan dan seringkali mendominasi.
    * Jika `P_max` adalah batas halaman yang di-crawl (sesuai dengan `` `MAX_PAGES_TO_CRAWL` ``), maka crawler akan berhenti setelah `P_max` halaman, sehingga `V` akan kurang dari atau sama dengan `P_max`.
    * Delay `time.sleep()` yang ditambahkan akan secara langsung meningkatkan waktu total eksekusi.

* **Search**:
    * Misalkan `N` adalah jumlah halaman yang berhasil di-crawl dan disimpan dalam `` `crawled_data` `` (`N` kurang dari atau sama dengan `P_max`).
    * Misalkan `L_t` adalah panjang rata-rata judul dan `L_c` adalah panjang rata-rata konten.
    * Misalkan `K` adalah jumlah term dalam kata kunci pencarian.
    * Untuk setiap halaman, kita melakukan pencocokan `K` term pada judul dan konten. Operasi `term in text` bisa memakan waktu proporsional dengan panjang teks.
    * Kompleksitas kasarnya adalah sekitar O(N * K * (L_t + L_c)).
    * Ini adalah pencarian linear sederhana. Untuk dataset yang sangat besar, ini tidak efisien. Mesin pencari skala besar menggunakan struktur data terindeks (seperti inverted index) untuk pencarian yang jauh lebih cepat (mendekati O(K) atau O(log N) tergantung implementasi).

### Kompleksitas Ruang

* **Crawling**:
    * `` `visited_urls` ``: Menyimpan hingga `V` URL. Perkiraan: O(V * panjang rata-rata URL).
    * `frontier` (antrian/stack): Dalam kasus terburuk (misalnya, graf seperti bintang untuk BFS), bisa menyimpan hingga O(V) URL.
    * `` `crawled_data` ``: Menyimpan data untuk setiap halaman yang dikunjungi. Ini adalah komponen terbesar. Perkiraan: O(V * (panjang rata-rata judul + panjang rata-rata konten + panjang rata-rata info path)). Info path bisa cukup panjang untuk halaman yang dalam.

* **Search**:
    * Membutuhkan ruang untuk menyimpan hasil pencarian, hingga `` `SEARCH_RESULT_LIMIT` ``. Perkiraan: O(`` `SEARCH_RESULT_LIMIT` `` * ukuran rata-rata item hasil).
    * Ruang yang digunakan oleh `` `crawled_data` `` tetap menjadi faktor dominan.

### Kelebihan Proyek

* **Sederhana dan Mudah Dipahami**: Implementasi algoritma BFS dan DFS cukup straightforward.
* **Pilihan Strategi**: Memberikan fleksibilitas dalam cara penjelajahan.
* **Fokus pada Satu Domain**: Cocok untuk kebutuhan mesin pencari internal.
* **Dasar yang Baik**: Bisa menjadi titik awal untuk pengembangan fitur yang lebih canggih.
* **Penanganan Error Dasar**: Mencoba menangani error HTTP dan parsing.
* **Upaya Etika Crawling**: Menyertakan delay dan penggunaan session.

### Keterbatasan dan Potensi Peningkatan

* **Skalabilitas Pencarian**: Pencarian linear tidak akan efisien untuk jumlah halaman yang besar. Implementasi inverted index akan sangat meningkatkan performa pencarian.
* **Relevansi Peringkat Hasil**: Saat ini tidak ada mekanisme pemeringkatan hasil pencarian berdasarkan relevansi (misalnya, TF-IDF, PageRank sederhana, atau faktor lain). Hasil ditampilkan berdasarkan urutan ditemukannya kecocokan.
* **Ketahanan Terhadap Blokir**: Meskipun ada upaya, crawler masih bisa diblokir oleh sistem anti-bot yang canggih. Teknik yang lebih advanced (rotasi IP, rendering JavaScript penuh) mungkin diperlukan.
* **Parsing Konten**: Ekstraksi konten bisa lebih disempurnakan untuk menghilangkan boilerplate (menu, footer, iklan) secara lebih akurat.
* **Tidak Ada Persistence**: Data `` `crawled_data` `` hilang setiap kali aplikasi di-restart. Perlu mekanisme penyimpanan (misalnya, database atau file) jika data ingin persisten.
* **Manajemen `robots.txt`**: Saat ini belum ada implementasi untuk mematuhi `robots.txt` secara otomatis.
* **Deduplikasi Konten**: Tidak ada mekanisme untuk mendeteksi dan menangani halaman dengan konten yang sangat mirip atau duplikat.
* **Crawling Dinamis**: Tidak bisa menangani konten yang dimuat secara dinamis oleh JavaScript tanpa menggunakan browser headless.
* **Batasan Jumlah Halaman**: `` `MAX_PAGES_TO_CRAWL` `` membatasi cakupan crawling, yang mungkin diperlukan untuk demo tetapi tidak ideal untuk cakupan penuh.