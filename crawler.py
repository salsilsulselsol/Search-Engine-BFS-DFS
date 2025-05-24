# crawler.py
"""
Modul ini berisi kelas WebCrawler untuk melakukan crawling dan pencarian.
"""
import requests
import bs4
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from collections import deque, defaultdict
import time
import re
import os
import pickle
import config

class WebCrawler:
    def __init__(self, seed_url, base_domain, strategy="BFS"):
        self.seed_url = seed_url
        self.base_domain = base_domain
        self.visited_urls = set()
        self.crawled_data = {}
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        self.strategy = strategy.upper()
        if self.strategy not in ["BFS", "DFS"]:
            raise ValueError("Strategi crawling tidak didukung. Pilih 'BFS' atau 'DFS'.")

        self.stats = {
            "total_links_extracted": 0,
            "total_unique_domain_links_added_to_frontier": 0,
            "http_errors": 0,
            "request_errors": 0,
            "non_html_pages": 0,
            "pages_per_depth": defaultdict(int),
            "loaded_from_cache": False,
            "cache_file_used": None
        }
        # Membuat direktori cache jika belum ada
        if not os.path.exists(config.CACHE_DIR):
            os.makedirs(config.CACHE_DIR)

    def _save_cache(self):
        """Menyimpan crawled_data dan visited_urls ke file cache."""
        try:
            with open(config.CACHE_FILE_PATH, 'wb') as f:
                pickle.dump({
                    'crawled_data': self.crawled_data,
                    'visited_urls': self.visited_urls,
                    'stats': self.stats # Simpan juga statistik
                }, f)
            print(f"Data crawling berhasil disimpan ke cache: {config.CACHE_FILE_PATH}")
        except Exception as e:
            print(f"Error saat menyimpan cache: {e}")

    def _load_cache(self):
        """Memuat crawled_data dan visited_urls dari file cache jika ada."""
        if os.path.exists(config.CACHE_FILE_PATH):
            try:
                with open(config.CACHE_FILE_PATH, 'rb') as f:
                    cache_content = pickle.load(f)
                    self.crawled_data = cache_content.get('crawled_data', {})
                    self.visited_urls = cache_content.get('visited_urls', set())
                    # Memuat statistik, tapi reset beberapa yang relevan dengan sesi ini
                    loaded_stats = cache_content.get('stats', {})
                    self.stats.update(loaded_stats) # Update dengan statistik dari cache
                    
                    # Reset statistik yang spesifik untuk sesi crawling baru jika cache tidak lengkap
                    # atau jika kita memutuskan untuk meng-update cache
                    self.stats["total_links_extracted"] = 0
                    self.stats["total_unique_domain_links_added_to_frontier"] = 0
                    self.stats["http_errors"] = 0
                    self.stats["request_errors"] = 0
                    self.stats["non_html_pages"] = 0
                    # pages_per_depth bisa dipertahankan atau direset tergantung kebutuhan
                    # Untuk kesederhanaan, kita pertahankan jika ada

                    self.stats["loaded_from_cache"] = True
                    self.stats["cache_file_used"] = config.CACHE_FILE_PATH
                print(f"Data crawling berhasil dimuat dari cache: {config.CACHE_FILE_PATH}")
                print(f"Jumlah halaman dimuat dari cache: {len(self.crawled_data)}")
                return True
            except Exception as e:
                print(f"Error saat memuat cache: {e}. Akan memulai crawling baru.")
                self._reset_stats_for_new_crawl() # Pastikan reset jika load gagal
                return False
        return False

    def _is_same_organization(self, url):
        parsed_url = urlparse(url)
        if parsed_url.scheme not in ('http', 'https'):
            return False
        return parsed_url.netloc.endswith(self.base_domain)

    def _get_filename_from_url(self, url):
        try:
            path = urlparse(url).path
            filename = os.path.basename(path)
            if filename:
                return filename
        except Exception:
            pass
        parsed_url = urlparse(url)
        if parsed_url.path and parsed_url.path != '/':
            return parsed_url.path.strip('/').split('/')[-1]
        return parsed_url.netloc

    def _fetch_and_extract_html_info(self, url, link_text_from_parent=None):
        fallback_title = link_text_from_parent if link_text_from_parent and link_text_from_parent != url else self._get_filename_from_url(url)
        # time.sleep(0.5) # Dihilangkan sesuai permintaan

        try:
            response = requests.get(url, timeout=10, headers=self.headers, allow_redirects=True)
            actual_url = response.url

            if response.status_code >= 400:
                print(f"Error HTTP {response.status_code} untuk {url} (URL final: {actual_url}). Menyimpan link dengan anchor text sebagai judul jika tersedia.")
                self.stats["http_errors"] += 1
                return fallback_title, "", [], False # Menambahkan status is_html

            content_type = response.headers.get('Content-Type', '').lower()

            if 'text/html' in content_type:
                try:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    html_title_tag = soup.title.string.strip() if soup.title and soup.title.string else None
                    title = html_title_tag or fallback_title
                    
                    content = ""
                    main_content_area = soup.find('main') or \
                                        soup.find('article') or \
                                        soup.find('div', id='content') or \
                                        soup.find('div', class_='content')

                    if main_content_area:
                        texts_tags = main_content_area.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'th', 'pre', 'span'])
                        content = ' '.join([tag.get_text(separator=' ', strip=True) for tag in texts_tags])
                    
                    if not content.strip():
                        content_tags_fallback = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li'])
                        texts_fallback = [tag.get_text(separator=' ', strip=True) for tag in content_tags_fallback]
                        content = ' '.join(texts_fallback)

                    content = re.sub(r'\s+', ' ', content).strip()
                    
                    if not content.strip():
                        body_tag = soup.find('body')
                        if body_tag:
                            content = body_tag.get_text(separator=' ', strip=True)
                            content = re.sub(r'\s+', ' ', content).strip()
                    
                    new_links = []
                    for a_tag in soup.find_all('a', href=True):
                        self.stats["total_links_extracted"] += 1 # Menghitung semua link yang diekstrak
                        href = a_tag['href']
                        if href.lower().startswith(('mailto:', 'tel:', 'javascript:', '#')):
                            continue
                        
                        absolute_url = urljoin(actual_url, href)
                        parsed_absolute_url = urlparse(absolute_url)
                        absolute_url = parsed_absolute_url._replace(fragment="").geturl()
                        
                        if parsed_absolute_url.scheme not in ('http', 'https'):
                            continue
                        if self._is_same_organization(absolute_url):
                            link_text = a_tag.get_text(strip=True)
                            if not link_text:
                                link_text = a_tag.get('title', '').strip() or \
                                            a_tag.get('aria-label', '').strip() or \
                                            absolute_url
                            new_links.append((absolute_url, link_text))
                    
                    return title, content, new_links, True # is_html = True

                except bs4.exceptions.ParserRejectedMarkup as e:
                    print(f"Error parsing markup (ParserRejectedMarkup) untuk HTML {url}: {e}")
                    return fallback_title, "", [], True # Dianggap HTML karena tipe konten, meski gagal parse
                except Exception as e:
                    print(f"Error umum parsing atau proses HTML untuk {url}: {e}")
                    return fallback_title, "", [], True # Dianggap HTML
            else:
                print(f"Menyimpan konten non-HTML di {url} (Content-Type: {content_type}) sebagai link.")
                self.stats["non_html_pages"] += 1
                non_html_title = self._get_filename_from_url(url)
                return non_html_title, "", [], False # is_html = False

        except requests.exceptions.HTTPError as e:
            print(f"Error HTTP saat request untuk {url}: {e}. Menyimpan link dengan anchor text sebagai judul jika tersedia.")
            self.stats["http_errors"] += 1 # Dihitung sebagai HTTP error juga
            return fallback_title, "", [], False
        except requests.exceptions.RequestException as e:
            print(f"Request exception untuk {url}: {e}. Menyimpan link dengan anchor text sebagai judul jika tersedia.")
            self.stats["request_errors"] += 1
            return fallback_title, "", [], False
        except Exception as e:
            print(f"Error tak terduga saat memproses {url}: {e}. Menyimpan link.")
            # Bisa jadi error lain, tidak secara spesifik request error
            return fallback_title, "", [], False

    def _reset_stats_for_new_crawl(self):
        self.stats = {
            "total_links_extracted": 0,
            "total_unique_domain_links_added_to_frontier": 0,
            "http_errors": 0,
            "request_errors": 0,
            "non_html_pages": 0,
            "pages_per_depth": defaultdict(int),
            "loaded_from_cache": False, # Pastikan ini direset
            "cache_file_used": None
        }
        self.visited_urls = set()
        self.crawled_data = {}


    def crawl_bfs(self):
        # self._reset_stats_for_new_crawl() # Pindah ke app.py untuk keputusan load cache
        print(f"Memulai crawling (BFS) dari: {self.seed_url} dengan MAX_DEPTH={config.MAX_DEPTH}")
        queue = deque() 
        
        # Hanya tambahkan seed ke frontier jika belum dikunjungi (penting jika cache dimuat sebagian)
        if self.seed_url not in self.visited_urls:
            queue.append((self.seed_url, None, [(self.seed_url, "Seed URL")], 0)) 
            self.visited_urls.add(self.seed_url)
            self.stats["total_unique_domain_links_added_to_frontier"] +=1
        elif self.seed_url not in self.crawled_data:
            # Jika sudah dikunjungi (misal dari cache visited_urls) tapi tidak ada datanya (misal cache korup/sebagian)
            # Tetap perlu di crawl
             queue.append((self.seed_url, None, [(self.seed_url, "Seed URL")], 0))
             # visited_urls sudah ada, jadi tidak perlu di-add lagi atau dihitung ke frontier


        crawled_count_session = 0 # Untuk menghitung halaman yang di-crawl di sesi ini saja
        max_depth_reached = 0
        start_time = time.time()

        while queue:
            current_url, parent_url, current_path_info, current_depth = queue.popleft()
            
            if current_depth > config.MAX_DEPTH:
                continue

            # Cek jika URL sudah ada di crawled_data (mungkin dari cache atau crawling sebelumnya di sesi ini)
            if current_url in self.crawled_data and self.crawled_data[current_url].get('content') is not None:
                # Jika sudah ada data lengkap, update kedalaman jika path baru lebih dangkal (opsional, tapi bisa jadi baik)
                if current_depth < self.crawled_data[current_url].get('depth', float('inf')):
                    self.crawled_data[current_url]['depth'] = current_depth
                    self.crawled_data[current_url]['path_info'] = current_path_info
                # Update statistik kedalaman jika belum tercatat atau jika kedalaman baru lebih baik
                self.stats["pages_per_depth"][self.crawled_data[current_url]['depth']] +=1 # Asumsi depth di data cache sudah benar
                max_depth_reached = max(max_depth_reached, self.crawled_data[current_url]['depth'])
                # Lanjutkan untuk mengekstrak link dari halaman ini jika belum pernah dieksplorasi dari kedalaman ini
                # (Untuk kasus ini, kita asumsikan jika sudah di crawled_data, link juga sudah dieksplorasi dari sana)
                # Namun, untuk menyederhanakan, kita akan re-ekstrak link jika belum pernah
                # Ini perlu keputusan desain: apakah kita re-fetch atau percaya cache sepenuhnya untuk link
                # Untuk saat ini, jika ada di cache, kita percaya link-nya juga sudah diproses.
                # Tapi jika kita mau update, kita bisa fetch ulang.
                # Untuk cache sederhana, kita skip fetch jika sudah ada di crawled_data.
                
                # Jika kita mau memastikan link dari halaman cache juga ditambahkan ke frontier jika kedalaman memungkinkan:
                if current_depth < config.MAX_DEPTH and self.crawled_data[current_url].get('is_html'):
                    # Perlu cara untuk mendapatkan new_links dari data yang di-cache atau fetch ulang
                    # Untuk saat ini, kita tidak akan re-fetch jika data sudah ada.
                    # Ini berarti jika cache dimuat, kita tidak akan menemukan link baru dari halaman yang di-cache
                    # kecuali kita merancang cache untuk menyimpan link mentah juga.
                    # Alternatifnya, jika ada di crawled_data, fetch ulang hanya untuk link jika ingin update.
                    # Untuk implementasi awal cache, kita anggap jika sudah di crawled_data, tidak perlu fetch ulang.
                    # Jika ingin crawling lebih dinamis (misal, update cache), maka perlu logic fetch ulang.
                    pass # Lewati fetch jika sudah di crawled_data
                else:
                    continue


            link_text_for_current_url = current_path_info[-1][1] if current_path_info else self._get_filename_from_url(current_url)
            
            print(f"Crawling ke-{len(self.crawled_data) + 1} (sesi: {crawled_count_session + 1}) [BFS]: {current_url} (kedalaman={current_depth}, dari_teks='{link_text_for_current_url[:50]}...')")

            title, content, new_links, is_html = self._fetch_and_extract_html_info(current_url, link_text_for_current_url)
            
            self.crawled_data[current_url] = {
                'title': title,
                'content': content,
                'parent_url': parent_url,
                'path_info': current_path_info,
                'depth': current_depth,
                'is_html': is_html
                # Jika ingin menyimpan link mentah untuk re-populasi frontier dari cache:
                # 'extracted_links': [(url, text) for url, text in new_links] # Contoh
            }
            crawled_count_session += 1
            self.stats["pages_per_depth"][current_depth] += 1
            max_depth_reached = max(max_depth_reached, current_depth)

            if current_depth < config.MAX_DEPTH:
                if new_links:
                    for link_url, link_text in new_links:
                        if link_url not in self.visited_urls:
                            self.visited_urls.add(link_url)
                            self.stats["total_unique_domain_links_added_to_frontier"] +=1
                            new_path = current_path_info + [(link_url, link_text)]
                            queue.append((link_url, current_url, new_path, current_depth + 1))
                        elif link_url not in self.crawled_data and (current_depth + 1) <= config.MAX_DEPTH :
                            # Jika sudah dikunjungi tapi belum ada datanya (misal dari visited_urls di cache)
                            # dan belum mencapai max_depth, tambahkan ke queue untuk diproses
                            new_path = current_path_info + [(link_url, link_text)]
                            queue.append((link_url, current_url, new_path, current_depth + 1))


        duration = time.time() - start_time
        if crawled_count_session > 0 : # Hanya simpan cache jika ada halaman baru yang di-crawl
             self._save_cache()

        print("\n--- Statistik Crawling BFS Selesai ---")
        if self.stats.get("loaded_from_cache"):
            print(f"Sebagian data dimuat dari cache: {self.stats.get('cache_file_used')}")
            print(f"Halaman di-crawl pada sesi ini: {crawled_count_session}")
        print(f"Strategi Crawling Digunakan: BFS")
        print(f"Seed URL: {self.seed_url}")
        print(f"MAX_DEPTH Dikonfigurasi: {config.MAX_DEPTH}")
        print(f"Total Halaman Tersimpan (termasuk dari cache jika ada): {len(self.crawled_data)}")
        print(f"Kedalaman Maksimum Tercapai (sesi ini atau dari cache): {max_depth_reached if max_depth_reached > 0 else self.get_max_depth_from_data()}")
        print(f"Total Durasi Crawling (sesi ini): {duration:.2f} detik")
        print(f"Total Tautan Diekstrak (sesi ini, sebelum filter unik/domain): {self.stats['total_links_extracted']}")
        print(f"Total Tautan Unik (dalam domain) Ditambahkan ke Frontier (sesi ini): {self.stats['total_unique_domain_links_added_to_frontier']}")
        print(f"Jumlah Error HTTP (sesi ini): {self.stats['http_errors']}")
        print(f"Jumlah Error Request Lainnya (sesi ini): {self.stats['request_errors']}")
        print(f"Jumlah Halaman Non-HTML Ditemukan (sesi ini): {self.stats['non_html_pages']}")
        print("Distribusi Halaman per Kedalaman (total):")
        # Hitung ulang pages_per_depth dari self.crawled_data untuk akurasi total
        current_pages_per_depth = defaultdict(int)
        for data_item in self.crawled_data.values():
            current_pages_per_depth[data_item['depth']] +=1
        for depth, count in sorted(current_pages_per_depth.items()):
            print(f"  Kedalaman {depth}: {count} halaman")
        print("-------------------------------------\n")


    def crawl_dfs(self):
        # self._reset_stats_for_new_crawl() # Pindah ke app.py
        print(f"Memulai crawling (DFS) dari: {self.seed_url} dengan MAX_DEPTH={config.MAX_DEPTH}")
        stack = [] 
        
        if self.seed_url not in self.visited_urls:
            stack.append((self.seed_url, None, [(self.seed_url, "Seed URL")], 0)) 
            self.visited_urls.add(self.seed_url)
            self.stats["total_unique_domain_links_added_to_frontier"] +=1
        elif self.seed_url not in self.crawled_data:
             stack.append((self.seed_url, None, [(self.seed_url, "Seed URL")], 0))
        
        crawled_count_session = 0
        max_depth_reached = 0
        start_time = time.time()

        while stack:
            current_url, parent_url, current_path_info, current_depth = stack.pop()

            if current_depth > config.MAX_DEPTH:
                continue
            
            if current_url in self.crawled_data and self.crawled_data[current_url].get('content') is not None:
                if current_depth < self.crawled_data[current_url].get('depth', float('inf')):
                    self.crawled_data[current_url]['depth'] = current_depth
                    self.crawled_data[current_url]['path_info'] = current_path_info
                self.stats["pages_per_depth"][self.crawled_data[current_url]['depth']] +=1
                max_depth_reached = max(max_depth_reached, self.crawled_data[current_url]['depth'])
                # Serupa dengan BFS, kita skip fetch jika sudah ada di crawled_data untuk cache sederhana
                continue


            link_text_for_current_url = current_path_info[-1][1] if current_path_info else self._get_filename_from_url(current_url)

            print(f"Crawling ke-{len(self.crawled_data) + 1} (sesi: {crawled_count_session + 1}) [DFS]: {current_url} (kedalaman={current_depth}, dari_teks='{link_text_for_current_url[:50]}...')")

            title, content, new_links, is_html = self._fetch_and_extract_html_info(current_url, link_text_for_current_url)
            
            self.crawled_data[current_url] = {
                'title': title,
                'content': content,
                'parent_url': parent_url,
                'path_info': current_path_info,
                'depth': current_depth,
                'is_html': is_html
            }
            crawled_count_session += 1
            self.stats["pages_per_depth"][current_depth] += 1
            max_depth_reached = max(max_depth_reached, current_depth)

            if current_depth < config.MAX_DEPTH:
                if new_links:
                    # Untuk DFS, kita tambahkan link ke stack. Urutan reversed() membantu menjaga sifat "depth-first".
                    for link_url, link_text in reversed(new_links): 
                        if link_url not in self.visited_urls:
                            self.visited_urls.add(link_url)
                            self.stats["total_unique_domain_links_added_to_frontier"] +=1
                            new_path = current_path_info + [(link_url, link_text)]
                            stack.append((link_url, current_url, new_path, current_depth + 1))
                        elif link_url not in self.crawled_data and (current_depth + 1) <= config.MAX_DEPTH :
                            new_path = current_path_info + [(link_url, link_text)]
                            stack.append((link_url, current_url, new_path, current_depth + 1))
        
        duration = time.time() - start_time
        if crawled_count_session > 0:
            self._save_cache()
            
        print("\n--- Statistik Crawling DFS Selesai ---")
        if self.stats.get("loaded_from_cache"):
            print(f"Sebagian data dimuat dari cache: {self.stats.get('cache_file_used')}")
            print(f"Halaman di-crawl pada sesi ini: {crawled_count_session}")
        print(f"Strategi Crawling Digunakan: DFS")
        print(f"Seed URL: {self.seed_url}")
        print(f"MAX_DEPTH Dikonfigurasi: {config.MAX_DEPTH}")
        print(f"Total Halaman Tersimpan (termasuk dari cache jika ada): {len(self.crawled_data)}")
        print(f"Kedalaman Maksimum Tercapai (sesi ini atau dari cache): {max_depth_reached if max_depth_reached > 0 else self.get_max_depth_from_data()}")
        print(f"Total Durasi Crawling (sesi ini): {duration:.2f} detik")
        print(f"Total Tautan Diekstrak (sesi ini, sebelum filter unik/domain): {self.stats['total_links_extracted']}")
        print(f"Total Tautan Unik (dalam domain) Ditambahkan ke Frontier (sesi ini): {self.stats['total_unique_domain_links_added_to_frontier']}")
        print(f"Jumlah Error HTTP (sesi ini): {self.stats['http_errors']}")
        print(f"Jumlah Error Request Lainnya (sesi ini): {self.stats['request_errors']}")
        print(f"Jumlah Halaman Non-HTML Ditemukan (sesi ini): {self.stats['non_html_pages']}")
        print("Distribusi Halaman per Kedalaman (total):")
        current_pages_per_depth = defaultdict(int)
        for data_item in self.crawled_data.values():
            current_pages_per_depth[data_item['depth']] +=1
        for depth, count in sorted(current_pages_per_depth.items()):
            print(f"  Kedalaman {depth}: {count} halaman")
        print("------------------------------------\n")

    def get_max_depth_from_data(self):
        """Mendapatkan kedalaman maksimum dari data yang sudah di-crawl (cache)."""
        if not self.crawled_data:
            return 0
        max_d = 0
        for data_item in self.crawled_data.values():
            if data_item.get('depth', 0) > max_d:
                max_d = data_item['depth']
        return max_d

    def search(self, keyword, limit): 
        results = [] 
        keyword_lower = keyword.lower() 
        search_terms = keyword_lower.split()

        for url, data in self.crawled_data.items(): 
            title_text = data.get('title', '')
            content_text = data.get('content', '') 
            
            title_text_lower = title_text.lower()
            
            match_in_title = all(term in title_text_lower for term in search_terms)

            match_in_content = False
            if content_text: 
                 content_text_lower = content_text.lower()
                 match_in_content = all(term in content_text_lower for term in search_terms)

            if match_in_title or match_in_content:
                snippet = ""
                if content_text and match_in_content:
                    first_term_in_content_index = -1
                    current_search_term_for_snippet = ""
                    for term in search_terms:
                        try:
                            idx = content_text_lower.index(term)
                            if first_term_in_content_index == -1 or idx < first_term_in_content_index:
                                first_term_in_content_index = idx
                                current_search_term_for_snippet = term 
                        except ValueError:
                            continue
                    
                    if first_term_in_content_index != -1:
                        start_index = first_term_in_content_index
                        snippet_start = max(0, start_index - 70) 
                        snippet_end = min(len(content_text), start_index + len(current_search_term_for_snippet) + 130) 
                        
                        prefix = "..." if snippet_start > 0 else ""
                        suffix = "..." if snippet_end < len(content_text) else ""
                        snippet = prefix + content_text[snippet_start:snippet_end] + suffix
                    else: 
                         snippet = content_text[:200] + ('...' if len(content_text) > 200 else '')
                
                elif match_in_title: 
                    if not content_text: 
                        snippet = ""
                    else: 
                        snippet = f"Judul '{title_text}' cocok. Pratinjau konten: " + (content_text[:150] + ('...' if len(content_text) > 150 else ''))
                
                results.append({ 
                    'url': url, 
                    'title': title_text, 
                    'snippet': snippet.strip(), 
                    'path_info': data.get('path_info', []) 
                })
                if len(results) >= limit: 
                    break
        return results 

    def get_path_details(self, target_url): 
        if target_url in self.crawled_data: 
            return self.crawled_data[target_url].get('path_info', []) 
        return []