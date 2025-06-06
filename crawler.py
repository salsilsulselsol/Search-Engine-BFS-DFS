# crawler.py
import requests
import bs4 #
from bs4 import BeautifulSoup #
from urllib.parse import urlparse, urljoin #
from collections import deque, defaultdict #
import time #
import re #
import os #
import pickle #
import config #

class WebCrawler:
    def __init__(self, seed_url, base_domain, strategy="BFS"): #
        self.seed_url = seed_url #
        self.base_domain = base_domain #
        self.visited_urls = set() #
        self.crawled_data = {} #
        self.headers = { #
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        self.strategy = strategy.upper() #
        if self.strategy not in ["BFS", "DFS"]: #
            raise ValueError("Strategi crawling tidak didukung. Pilih 'BFS' atau 'DFS'.")

        self.stats = { #
            "total_links_extracted": 0,
            "total_unique_domain_links_added_to_frontier": 0,
            "http_errors": 0,
            "request_errors": 0,
            "non_html_pages": 0,
            "pages_per_depth": defaultdict(int),
            "loaded_from_cache": False,
            "cache_file_used": None
        }
        if not os.path.exists(config.CACHE_DIR): #
            os.makedirs(config.CACHE_DIR) #

    def _save_cache(self): #
        try:
            # Tambahkan strategi ke data yang disimpan
            data_to_save = {
                'crawled_data': self.crawled_data, #
                'visited_urls': self.visited_urls, #
                'stats': self.stats, #
                'strategy': self.strategy # Simpan strategi #
            }
            with open(config.CACHE_FILE_PATH, 'wb') as f: #
                pickle.dump(data_to_save, f) #
            print(f"Data crawling berhasil disimpan ke cache: {config.CACHE_FILE_PATH}") #
        except Exception as e:
            print(f"Error saat menyimpan cache: {e}")

    def _load_cache(self): #
        if os.path.exists(config.CACHE_FILE_PATH): #
            try:
                with open(config.CACHE_FILE_PATH, 'rb') as f: #
                    cache_content = pickle.load(f) #
                    self.crawled_data = cache_content.get('crawled_data', {}) #
                    self.visited_urls = cache_content.get('visited_urls', set()) #
                    loaded_stats = cache_content.get('stats', {}) #
                    self.stats.update(loaded_stats) #
                    
                    # Muat strategi jika tersedia, jika tidak, pertahankan yang dari __init__
                    self.strategy = cache_content.get('strategy', self.strategy) # Muat strategi #
                    
                    self.stats["total_links_extracted"] = 0 #
                    self.stats["http_errors"] = 0 #
                    self.stats["request_errors"] = 0 #
                    self.stats["non_html_pages"] = 0 #
                    
                    self.stats["loaded_from_cache"] = True #
                    self.stats["cache_file_used"] = config.CACHE_FILE_PATH #
                print(f"Data crawling berhasil dimuat dari cache: {config.CACHE_FILE_PATH}") #
                print(f"Jumlah halaman dimuat dari cache (crawled_data): {len(self.crawled_data)}") #
                print(f"Jumlah URL dimuat dari cache (visited_urls): {len(self.visited_urls)}") #
                return True
            except Exception as e:
                print(f"Error saat memuat cache: {e}. Akan memulai crawling baru.")
                self._reset_stats_for_new_crawl() #
                return False
        return False

    # ... Sisa kode crawler.py tetap sama ...
    def _is_same_organization(self, url): #
        parsed_url = urlparse(url) #
        if parsed_url.scheme not in ('http', 'https'): #
            return False
        return parsed_url.netloc.endswith(self.base_domain) #

    def _get_filename_from_url(self, url): #
        try:
            path = urlparse(url).path #
            filename = os.path.basename(path) #
            if filename:
                return filename
        except Exception: pass
        parsed_url = urlparse(url) #
        if parsed_url.path and parsed_url.path != '/': #
            return parsed_url.path.strip('/').split('/')[-1] #
        return parsed_url.netloc #

    def _fetch_and_extract_html_info(self, url, link_text_from_parent=None): #
        fallback_title = link_text_from_parent if link_text_from_parent and link_text_from_parent != url else self._get_filename_from_url(url) #
        try:
            response = requests.get(url, timeout=10, headers=self.headers, allow_redirects=True) #
            actual_url = response.url #
            if response.status_code >= 400: #
                self.stats["http_errors"] += 1 #
                return fallback_title, "", [], False
            content_type = response.headers.get('Content-Type', '').lower() #
            if 'text/html' in content_type: #
                try:
                    soup = BeautifulSoup(response.content, 'html.parser') #
                    html_title_tag = soup.title.string.strip() if soup.title and soup.title.string else None #
                    title = html_title_tag or fallback_title #
                    content = "" #
                    main_content_area = soup.find('main') or soup.find('article') or soup.find('div', id='content') or soup.find('div', class_='content') #
                    if main_content_area: #
                        texts_tags = main_content_area.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'th', 'pre', 'span']) #
                        content = ' '.join([tag.get_text(separator=' ', strip=True) for tag in texts_tags]) #
                    if not content.strip(): #
                        content_tags_fallback = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']) #
                        texts_fallback = [tag.get_text(separator=' ', strip=True) for tag in content_tags_fallback] #
                        content = ' '.join(texts_fallback) #
                    content = re.sub(r'\s+', ' ', content).strip() #
                    if not content.strip(): #
                        body_tag = soup.find('body') #
                        if body_tag: content = re.sub(r'\s+', ' ', body_tag.get_text(separator=' ', strip=True)).strip() #
                    new_links = [] #
                    for a_tag in soup.find_all('a', href=True): #
                        self.stats["total_links_extracted"] += 1 #
                        href = a_tag['href'] #
                        if href.lower().startswith(('mailto:', 'tel:', 'javascript:', '#')): continue #
                        absolute_url = urljoin(actual_url, href) #
                        parsed_absolute_url = urlparse(absolute_url) #
                        absolute_url = parsed_absolute_url._replace(fragment="").geturl() #
                        if parsed_absolute_url.scheme not in ('http', 'https') or not self._is_same_organization(absolute_url): continue #
                        link_text = a_tag.get_text(strip=True) or a_tag.get('title', '').strip() or a_tag.get('aria-label', '').strip() or absolute_url #
                        new_links.append((absolute_url, link_text)) #
                    return title, content, new_links, True #
                except bs4.exceptions.ParserRejectedMarkup: return fallback_title, "", [], True #
                except Exception: return fallback_title, "", [], True
            else:
                self.stats["non_html_pages"] += 1 #
                return self._get_filename_from_url(url), "", [], False #
        except requests.exceptions.HTTPError: self.stats["http_errors"] += 1; return fallback_title, "", [], False #
        except requests.exceptions.RequestException: self.stats["request_errors"] += 1; return fallback_title, "", [], False #
        except Exception: return fallback_title, "", [], False

    def _reset_stats_for_new_crawl(self): #
        self.stats = { #
            "total_links_extracted": 0,
            "total_unique_domain_links_added_to_frontier": 0,
            "http_errors": 0,
            "request_errors": 0,
            "non_html_pages": 0,
            "pages_per_depth": defaultdict(int),
            "loaded_from_cache": False,
            "cache_file_used": None
        }
        self.visited_urls = set() #
        self.crawled_data = {} #


    def crawl_bfs(self): #
        print(f"Memulai crawling (BFS) dari: {self.seed_url} dengan MAX_DEPTH={config.MAX_DEPTH}") #
        queue = deque() #
        
        frontier_visited_check = set() #

        if self.seed_url not in self.visited_urls: #
            queue.append((self.seed_url, None, [(self.seed_url, "Seed URL")], 0)) #
            frontier_visited_check.add(self.seed_url) #
            self.stats["total_unique_domain_links_added_to_frontier"] += 1 #
        elif self.seed_url in self.crawled_data and self.crawled_data[self.seed_url].get('content') is not None: #
             queue.append((self.seed_url, None, [(self.seed_url, "Seed URL")], 0)) #
             frontier_visited_check.add(self.seed_url) #


        crawled_count_session = 0 #
        max_depth_reached = 0 #
        start_time = time.time() #

        while queue: #
            current_url, parent_url, current_path_info, current_depth = queue.popleft() #
            
            if current_depth > config.MAX_DEPTH: #
                continue

            new_links = [] #
            should_fetch_content = True #

            if current_url in self.visited_urls: #
                print(f"BFS: Menggunakan data dari cache/proses sebelumnya untuk {current_url} (kedalaman={current_depth}). Memproses ulang link...") #
                cached_data = self.crawled_data.get(current_url, {}) #
                title = cached_data.get('title', self._get_filename_from_url(current_url)) #
                content = cached_data.get('content', "") #
                is_html = cached_data.get('is_html', False) #
                max_depth_reached = max(max_depth_reached, current_depth) #
                should_fetch_content = False #

                if is_html and content: #
                    try:
                        soup = BeautifulSoup(content, 'html.parser') #
                        for a_tag in soup.find_all('a', href=True): #
                            self.stats["total_links_extracted"] += 1 #
                            href = a_tag['href'] #
                            if href.lower().startswith(('mailto:', 'tel:', 'javascript:', '#')): continue #
                            absolute_url = urljoin(current_url, href) #
                            parsed_absolute_url = urlparse(absolute_url) #
                            absolute_url = parsed_absolute_url._replace(fragment="").geturl() #
                            if parsed_absolute_url.scheme not in ('http', 'https') or not self._is_same_organization(absolute_url): continue #
                            link_text = a_tag.get_text(strip=True) or a_tag.get('title', '') or a_tag.get('aria-label', '') or absolute_url #
                            new_links.append((absolute_url, link_text)) #
                    except Exception: pass
            
            if should_fetch_content: #
                if current_url in self.visited_urls: #
                    print(f"BFS WARNING: current_url {current_url} in visited_urls tapi should_fetch_content True") #
                    continue

                link_text_for_current_url = current_path_info[-1][1] if current_path_info else self._get_filename_from_url(current_url) #
                print(f"Crawling ke-{len(self.visited_urls) + 1} (sesi: {crawled_count_session + 1}) [BFS]: {current_url} (kedalaman={current_depth}, dari_teks='{link_text_for_current_url[:50]}...')") #
                title, content, new_links_from_fetch, is_html = self._fetch_and_extract_html_info(current_url, link_text_for_current_url) #
                new_links.extend(new_links_from_fetch) #

                self.crawled_data[current_url] = { #
                    'title': title, 'content': content, 'parent_url': parent_url,
                    'path_info': current_path_info, 'depth': current_depth, 'is_html': is_html
                }
                self.visited_urls.add(current_url) #
                crawled_count_session += 1 #
                self.stats["pages_per_depth"][current_depth] += 1 #
                max_depth_reached = max(max_depth_reached, current_depth) #

            if current_depth < config.MAX_DEPTH: #
                for link_url, link_text in new_links: #
                    if link_url not in frontier_visited_check: #
                        if link_url not in self.visited_urls: #
                             queue.append((link_url, current_url, current_path_info + [(link_url, link_text)], current_depth + 1)) #
                             frontier_visited_check.add(link_url) #
                             self.stats["total_unique_domain_links_added_to_frontier"] += 1 #
                        
        duration = time.time() - start_time #
        if crawled_count_session > 0 or (self.stats.get("loaded_from_cache") and not queue) : #
             self._save_cache() #
        print("\n--- Statistik Crawling BFS Selesai ---") #
        if self.stats.get("loaded_from_cache"): #
            print(f"Sebagian data dimuat dari cache: {self.stats.get('cache_file_used')}") #
            print(f"Halaman baru di-crawl pada sesi ini: {crawled_count_session}") #
        print(f"Strategi Crawling Digunakan: BFS") #
        print(f"Seed URL: {self.seed_url}") #
        print(f"MAX_DEPTH Dikonfigurasi: {config.MAX_DEPTH}") #
        print(f"Total Halaman Tersimpan (crawled_data): {len(self.crawled_data)}") #
        
        final_max_depth = 0 #
        final_pages_per_depth = defaultdict(int) #
        if self.crawled_data: #
            for data_item in self.crawled_data.values(): #
                d = data_item.get('depth',0) #
                final_pages_per_depth[d] +=1 #
                if d > final_max_depth: final_max_depth = d #
        else: final_max_depth = max_depth_reached #

        print(f"Kedalaman Maksimum Tercapai (total): {final_max_depth}") #
        print(f"Total Durasi Crawling (sesi ini): {duration:.2f} detik") #
        print(f"Total Tautan Diekstrak (sesi ini): {self.stats['total_links_extracted']}") #
        print(f"Total Tautan Unik (dalam domain) Ditambahkan ke Frontier (sesi ini): {self.stats['total_unique_domain_links_added_to_frontier']}") #
        print(f"Jumlah Error HTTP (sesi ini): {self.stats['http_errors']}") #
        print(f"Jumlah Error Request Lainnya (sesi ini): {self.stats['request_errors']}") #
        print(f"Jumlah Halaman Non-HTML Ditemukan (sesi ini): {self.stats['non_html_pages']}") #
        print("Distribusi Halaman per Kedalaman (total dari crawled_data):") #
        for depth_stat, count_stat in sorted(final_pages_per_depth.items()): #
            print(f"  Kedalaman {depth_stat}: {count_stat} halaman") #
        print("-------------------------------------\n") #


    def crawl_dfs(self): #
        print(f"Memulai crawling (DFS) dari: {self.seed_url} dengan MAX_DEPTH={config.MAX_DEPTH}") #
        stack = [] #
        
        frontier_dfs_check = set() #

        if self.seed_url not in self.visited_urls: #
            stack.append((self.seed_url, None, [(self.seed_url, "Seed URL")], 0)) #
            frontier_dfs_check.add(self.seed_url) #
            self.stats["total_unique_domain_links_added_to_frontier"] += 1 #
        elif self.seed_url in self.crawled_data and self.crawled_data[self.seed_url].get('content') is not None: #
            print(f"DFS: Seed URL {self.seed_url} ada di cache dengan konten, menjadwalkan untuk proses link.") #
            stack.append((self.seed_url, None, [(self.seed_url, "Seed URL")], 0)) #
            frontier_dfs_check.add(self.seed_url) #
        elif self.seed_url in self.crawled_data and self.crawled_data[self.seed_url].get('content') is None: #
            stack.append((self.seed_url, None, [(self.seed_url, "Seed URL")], 0)) #
            frontier_dfs_check.add(self.seed_url) #
            if self.seed_url not in frontier_dfs_check: #
                self.stats["total_unique_domain_links_added_to_frontier"] += 1 #


        crawled_count_session = 0 #
        max_depth_reached = 0 #
        start_time = time.time() #

        while stack: #
            current_url, parent_url, current_path_info, current_depth = stack.pop() #

            if current_depth > config.MAX_DEPTH: #
                continue

            if current_url in self.visited_urls: #
                if current_url in self.crawled_data and self.crawled_data[current_url].get('content') is not None: #
                    print(f"DFS: Menggunakan data dari cache/proses sebelumnya untuk {current_url} (kedalaman={current_depth}). Memproses ulang link...") #
                    cached_data = self.crawled_data[current_url] #
                    content_from_cache = cached_data.get('content') #
                    is_html_from_cache = cached_data.get('is_html') #
                    new_links = [] #

                    if is_html_from_cache and content_from_cache: #
                        try:
                            soup = BeautifulSoup(content_from_cache, 'html.parser') #
                            for a_tag in soup.find_all('a', href=True): #
                                self.stats["total_links_extracted"] += 1 #
                                href = a_tag['href'] #
                                if href.lower().startswith(('mailto:', 'tel:', 'javascript:', '#')): continue #
                                absolute_url = urljoin(current_url, href) #
                                parsed_absolute_url = urlparse(absolute_url) #
                                absolute_url = parsed_absolute_url._replace(fragment="").geturl() #
                                if parsed_absolute_url.scheme not in ('http', 'https') or not self._is_same_organization(absolute_url): continue #
                                link_text = a_tag.get_text(strip=True) or a_tag.get('title', '') or a_tag.get('aria-label', '') or absolute_url #
                                new_links.append((absolute_url, link_text)) #
                        except Exception: pass
                    
                    if current_depth < config.MAX_DEPTH and new_links: #
                        for link_url_cached, link_text_cached in reversed(new_links): #
                            if link_url_cached not in self.visited_urls : #
                                if link_url_cached not in frontier_dfs_check: #
                                    stack.append((link_url_cached, current_url, current_path_info + [(link_url_cached, link_text_cached)], current_depth + 1)) #
                                    frontier_dfs_check.add(link_url_cached) #
                                    self.stats["total_unique_domain_links_added_to_frontier"] += 1 #
                            elif link_url_cached in self.crawled_data and self.crawled_data[link_url_cached].get('content') is None: #
                                if link_url_cached not in frontier_dfs_check: #
                                    stack.append((link_url_cached, current_url, current_path_info + [(link_url_cached, link_text_cached)], current_depth + 1)) #
                                    frontier_dfs_check.add(link_url_cached) #

                    continue #
                else:
                    continue #


            link_text_for_current_url = current_path_info[-1][1] if current_path_info else self._get_filename_from_url(current_url) #
            print(f"Crawling ke-{len(self.visited_urls) + 1} (sesi: {crawled_count_session + 1}) [DFS]: {current_url} (kedalaman={current_depth}, dari_teks='{link_text_for_current_url[:50]}...')") #

            title, content, new_links_from_fetch, is_html = self._fetch_and_extract_html_info(current_url, link_text_for_current_url) #
            
            self.crawled_data[current_url] = { #
                'title': title, 'content': content, 'parent_url': parent_url,
                'path_info': current_path_info, 'depth': current_depth, 'is_html': is_html
            }
            self.visited_urls.add(current_url) #
            crawled_count_session += 1 #
            self.stats["pages_per_depth"][current_depth] += 1 #
            max_depth_reached = max(max_depth_reached, current_depth) #

            if current_depth < config.MAX_DEPTH: #
                if new_links_from_fetch: #
                    for link_url, link_text in reversed(new_links_from_fetch): #
                        if link_url not in self.visited_urls: #
                            if link_url not in frontier_dfs_check: #
                                stack.append((link_url, current_url, current_path_info + [(link_url, link_text)], current_depth + 1)) #
                                frontier_dfs_check.add(link_url) #
                                self.stats["total_unique_domain_links_added_to_frontier"] += 1 #
                        elif link_url in self.crawled_data and self.crawled_data[link_url].get('content') is None: #
                             if link_url not in frontier_dfs_check: #
                                stack.append((link_url, current_url, current_path_info + [(link_url, link_text)], current_depth + 1)) #
                                frontier_dfs_check.add(link_url) #

        duration = time.time() - start_time #
        if crawled_count_session > 0 or (self.stats.get("loaded_from_cache") and not stack): #
            self._save_cache() #
            
        print("\n--- Statistik Crawling DFS Selesai ---") #
        if self.stats.get("loaded_from_cache"): #
            print(f"Sebagian data dimuat dari cache: {self.stats.get('cache_file_used')}") #
            print(f"Halaman baru di-crawl pada sesi ini: {crawled_count_session}") #
        print(f"Strategi Crawling Digunakan: DFS") #
        print(f"Seed URL: {self.seed_url}") #
        print(f"MAX_DEPTH Dikonfigurasi: {config.MAX_DEPTH}") #
        print(f"Total Halaman Tersimpan (crawled_data): {len(self.crawled_data)}") #
        
        final_max_depth = 0 #
        final_pages_per_depth = defaultdict(int) #
        if self.crawled_data: #
            for data_item in self.crawled_data.values(): #
                d = data_item.get('depth',0) #
                final_pages_per_depth[d] +=1 #
                if d > final_max_depth: final_max_depth = d #
        else: final_max_depth = max_depth_reached #

        print(f"Kedalaman Maksimum Tercapai (total): {final_max_depth}") #
        print(f"Total Durasi Crawling (sesi ini): {duration:.2f} detik") #
        print(f"Total Tautan Diekstrak (sesi ini): {self.stats['total_links_extracted']}") #
        print(f"Total Tautan Unik (dalam domain) Ditambahkan ke Frontier (sesi ini): {self.stats['total_unique_domain_links_added_to_frontier']}") #
        print(f"Jumlah Error HTTP (sesi ini): {self.stats['http_errors']}") #
        print(f"Jumlah Error Request Lainnya (sesi ini): {self.stats['request_errors']}") #
        print(f"Jumlah Halaman Non-HTML Ditemukan (sesi ini): {self.stats['non_html_pages']}") #
        print("Distribusi Halaman per Kedalaman (total dari crawled_data):") #
        for depth_stat, count_stat in sorted(final_pages_per_depth.items()): #
            print(f"  Kedalaman {depth_stat}: {count_stat} halaman") #
        print("------------------------------------\n") #


    def get_max_depth_from_data(self): #
        if not self.crawled_data: return 0 #
        max_d = 0 #
        for data_item in self.crawled_data.values(): #
            if data_item.get('depth', 0) > max_d: max_d = data_item['depth'] #
        return max_d

    def search(self, keyword, limit): #
        results = [] #
        keyword_lower = keyword.lower() #
        search_terms = keyword_lower.split() #
        for url, data in self.crawled_data.items(): #
            title_text = data.get('title', '') #
            content_text = data.get('content', '') #
            if title_text is None: title_text = "" #
            if content_text is None: content_text = "" #
            title_text_lower = title_text.lower() #
            match_in_title = all(term in title_text_lower for term in search_terms) #
            match_in_content = False #
            if content_text: #
                 content_text_lower = content_text.lower() #
                 match_in_content = all(term in content_text_lower for term in search_terms) #
            if match_in_title or match_in_content: #
                snippet = "" #
                if content_text and match_in_content: #
                    first_term_in_content_index = -1 #
                    current_search_term_for_snippet = "" #
                    for term_idx, term in enumerate(search_terms): #
                        try:
                            idx = content_text_lower.index(term) #
                            if first_term_in_content_index == -1 or idx < first_term_in_content_index: #
                                first_term_in_content_index = idx #
                                current_search_term_for_snippet = term #
                        except ValueError:
                            if term_idx == len(search_terms) -1 and first_term_in_content_index == -1: #
                                snippet = content_text[:200] + ('...' if len(content_text) > 200 else '') #
                                break
                            continue #
                    else:
                        if first_term_in_content_index != -1: #
                            start_index = first_term_in_content_index #
                            snippet_start = max(0, start_index - 70) #
                            snippet_end = min(len(content_text), start_index + len(current_search_term_for_snippet) + 130) #
                            prefix = "..." if snippet_start > 0 else ""; suffix = "..." if snippet_end < len(content_text) else "" #
                            snippet = prefix + content_text[snippet_start:snippet_end] + suffix #
                        elif content_text: snippet = content_text[:200] + ('...' if len(content_text) > 200 else '') #
                elif match_in_title: #
                    if not content_text: snippet = f"Judul '{title_text}' cocok. Konten tidak tersedia atau tidak relevan." #
                    else: snippet = f"Judul '{title_text}' cocok. Pratinjau konten: " + (content_text[:150] + ('...' if len(content_text) > 150 else '')) #
                elif not content_text and not match_in_title: snippet = "Informasi tidak cukup untuk menampilkan snippet." #
                results.append({'url': url, 'title': title_text, 'snippet': snippet.strip(), 'path_info': data.get('path_info', []) }) #
                if len(results) >= limit: break #
        return results #

    def get_path_details(self, target_url): #
        if target_url in self.crawled_data: return self.crawled_data[target_url].get('path_info', []) #
        return [] #