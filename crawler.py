# crawler.py
"""
Modul ini berisi kelas WebCrawler untuk melakukan crawling dan pencarian.
"""
import requests
import bs4 # Import bs4 to explicitly catch its exceptions
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from collections import deque, defaultdict # defaultdict untuk distribusi kedalaman
import time
import re
import os
import config # Import config untuk mengakses MAX_DEPTH

class WebCrawler:
    def __init__(self, seed_url, base_domain, strategy="BFS"):
        self.seed_url = seed_url
        self.base_domain = base_domain
        self.visited_urls = set()
        # self.frontier akan diinisialisasi di metode crawl_bfs/dfs
        self.crawled_data = {}
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        self.strategy = strategy.upper()
        if self.strategy not in ["BFS", "DFS"]:
            raise ValueError("Strategi crawling tidak didukung. Pilih 'BFS' atau 'DFS'.")

        # Statistik untuk analisis
        self.stats = {
            "total_links_extracted": 0,
            "total_unique_domain_links_added_to_frontier": 0,
            "http_errors": 0,
            "request_errors": 0,
            "non_html_pages": 0,
            "pages_per_depth": defaultdict(int)
        }

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

    def _reset_stats(self):
        self.stats = {
            "total_links_extracted": 0,
            "total_unique_domain_links_added_to_frontier": 0,
            "http_errors": 0,
            "request_errors": 0,
            "non_html_pages": 0,
            "pages_per_depth": defaultdict(int)
        }
        self.visited_urls = set()
        self.crawled_data = {}


    def crawl_bfs(self):
        self._reset_stats()
        print(f"Memulai crawling (BFS) dari: {self.seed_url} dengan MAX_DEPTH={config.MAX_DEPTH}")
        queue = deque() # Frontier spesifik untuk metode ini
        queue.append((self.seed_url, None, [(self.seed_url, "Seed URL")], 0)) # url, parent_url, path_info, depth
        self.visited_urls.add(self.seed_url)
        self.stats["total_unique_domain_links_added_to_frontier"] +=1

        crawled_count = 0
        max_depth_reached = 0
        start_time = time.time()

        while queue:
            current_url, parent_url, current_path_info, current_depth = queue.popleft()
            
            if current_depth > config.MAX_DEPTH:
                continue

            link_text_for_current_url = current_path_info[-1][1] if current_path_info else self._get_filename_from_url(current_url)
            
            print(f"Crawling ke-{crawled_count+1} [BFS]: {current_url} (kedalaman={current_depth}, dari_teks='{link_text_for_current_url[:50]}...')")

            title, content, new_links, is_html = self._fetch_and_extract_html_info(current_url, link_text_for_current_url)
            
            self.crawled_data[current_url] = {
                'title': title,
                'content': content,
                'parent_url': parent_url,
                'path_info': current_path_info,
                'depth': current_depth,
                'is_html': is_html
            }
            crawled_count += 1
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

        duration = time.time() - start_time
        print("\n--- Statistik Crawling BFS Selesai ---")
        print(f"Strategi Crawling Digunakan: BFS")
        print(f"Seed URL: {self.seed_url}")
        print(f"MAX_DEPTH Dikonfigurasi: {config.MAX_DEPTH}")
        print(f"Total Halaman Berhasil Di-crawl: {crawled_count}")
        print(f"Kedalaman Maksimum Tercapai: {max_depth_reached}")
        print(f"Total Durasi Crawling: {duration:.2f} detik")
        print(f"Total Tautan Diekstrak (sebelum filter unik/domain): {self.stats['total_links_extracted']}")
        print(f"Total Tautan Unik (dalam domain) Ditambahkan ke Frontier: {self.stats['total_unique_domain_links_added_to_frontier']}")
        print(f"Jumlah Error HTTP (mis. 404, 403): {self.stats['http_errors']}")
        print(f"Jumlah Error Request Lainnya (mis. timeout): {self.stats['request_errors']}")
        print(f"Jumlah Halaman Non-HTML Ditemukan: {self.stats['non_html_pages']}")
        print("Distribusi Halaman per Kedalaman:")
        for depth, count in sorted(self.stats['pages_per_depth'].items()):
            print(f"  Kedalaman {depth}: {count} halaman")
        print("-------------------------------------\n")


    def crawl_dfs(self):
        self._reset_stats()
        print(f"Memulai crawling (DFS) dari: {self.seed_url} dengan MAX_DEPTH={config.MAX_DEPTH}")
        stack = [] # Frontier spesifik untuk metode ini
        stack.append((self.seed_url, None, [(self.seed_url, "Seed URL")], 0)) 
        self.visited_urls.add(self.seed_url)
        self.stats["total_unique_domain_links_added_to_frontier"] +=1
        
        crawled_count = 0
        max_depth_reached = 0
        start_time = time.time()

        while stack:
            current_url, parent_url, current_path_info, current_depth = stack.pop()

            if current_depth > config.MAX_DEPTH:
                continue
            
            # Untuk DFS, URL bisa sudah dikunjungi tapi belum di-fetch jika ditemukan via path lain yg lebih dalam duluan
            # Namun, karena kita add ke visited_urls saat push ke stack, jika di-pop dan ada di crawled_data berarti sudah diproses.
            # Kita perlu memastikan URL hanya diproses sekali.
            if current_url in self.crawled_data: # Jika sudah diproses, lewati
                continue

            link_text_for_current_url = current_path_info[-1][1] if current_path_info else self._get_filename_from_url(current_url)

            print(f"Crawling ke-{crawled_count+1} [DFS]: {current_url} (kedalaman={current_depth}, dari_teks='{link_text_for_current_url[:50]}...')")

            title, content, new_links, is_html = self._fetch_and_extract_html_info(current_url, link_text_for_current_url)
            
            self.crawled_data[current_url] = {
                'title': title,
                'content': content,
                'parent_url': parent_url,
                'path_info': current_path_info,
                'depth': current_depth,
                'is_html': is_html
            }
            crawled_count += 1
            self.stats["pages_per_depth"][current_depth] += 1
            max_depth_reached = max(max_depth_reached, current_depth)

            if current_depth < config.MAX_DEPTH:
                if new_links:
                    for link_url, link_text in reversed(new_links): # Reverse untuk DFS
                        if link_url not in self.visited_urls:
                            self.visited_urls.add(link_url)
                            self.stats["total_unique_domain_links_added_to_frontier"] +=1
                            new_path = current_path_info + [(link_url, link_text)]
                            stack.append((link_url, current_url, new_path, current_depth + 1))
        
        duration = time.time() - start_time
        print("\n--- Statistik Crawling DFS Selesai ---")
        print(f"Strategi Crawling Digunakan: DFS")
        print(f"Seed URL: {self.seed_url}")
        print(f"MAX_DEPTH Dikonfigurasi: {config.MAX_DEPTH}")
        print(f"Total Halaman Berhasil Di-crawl: {crawled_count}")
        print(f"Kedalaman Maksimum Tercapai: {max_depth_reached}")
        print(f"Total Durasi Crawling: {duration:.2f} detik")
        print(f"Total Tautan Diekstrak (sebelum filter unik/domain): {self.stats['total_links_extracted']}")
        print(f"Total Tautan Unik (dalam domain) Ditambahkan ke Frontier: {self.stats['total_unique_domain_links_added_to_frontier']}")
        print(f"Jumlah Error HTTP (mis. 404, 403): {self.stats['http_errors']}")
        print(f"Jumlah Error Request Lainnya (mis. timeout): {self.stats['request_errors']}")
        print(f"Jumlah Halaman Non-HTML Ditemukan: {self.stats['non_html_pages']}")
        print("Distribusi Halaman per Kedalaman:")
        for depth, count in sorted(self.stats['pages_per_depth'].items()):
            print(f"  Kedalaman {depth}: {count} halaman")
        print("------------------------------------\n")

    def search(self, keyword, limit): #
        results = [] #
        keyword_lower = keyword.lower() #
        search_terms = keyword_lower.split()

        for url, data in self.crawled_data.items(): #
            title_text = data.get('title', '')
            content_text = data.get('content', '') #
            
            title_text_lower = title_text.lower()
            
            match_in_title = all(term in title_text_lower for term in search_terms)

            match_in_content = False
            if content_text: #
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
                
                results.append({ #
                    'url': url, #
                    'title': title_text, #
                    'snippet': snippet.strip(), #
                    'path_info': data.get('path_info', []) #
                })
                if len(results) >= limit: #
                    break
        return results #

    def get_path_details(self, target_url): #
        if target_url in self.crawled_data: #
            return self.crawled_data[target_url].get('path_info', []) #
        return [] #