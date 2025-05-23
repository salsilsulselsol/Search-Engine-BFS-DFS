# crawler.py
"""
Modul ini berisi kelas WebCrawler untuk melakukan crawling dan pencarian.
"""
import requests
import bs4 # Import bs4 to explicitly catch its exceptions
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from collections import deque
import time
import re
import os

class WebCrawler:
    def __init__(self, seed_url, base_domain, strategy="BFS"): #
        self.seed_url = seed_url #
        self.base_domain = base_domain #
        self.visited_urls = set()
        self.frontier = deque() #
        self.crawled_data = {}
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        self.strategy = strategy.upper()
        if self.strategy not in ["BFS", "DFS"]:
            raise ValueError("Strategi crawling tidak didukung. Pilih 'BFS' atau 'DFS'.")

    def _is_same_organization(self, url): #
        parsed_url = urlparse(url) #
        if parsed_url.scheme not in ('http', 'https'):
            return False
        return parsed_url.netloc.endswith(self.base_domain) #

    def _get_filename_from_url(self, url):
        """Mencoba mendapatkan nama file dari URL."""
        try:
            path = urlparse(url).path
            filename = os.path.basename(path)
            if filename:
                return filename
        except Exception:
            pass
        parsed_url = urlparse(url)
        if parsed_url.path and parsed_url.path != '/':
             # Ambil bagian terakhir dari path
            return parsed_url.path.strip('/').split('/')[-1]
        return parsed_url.netloc # Fallback ke domain jika path kosong atau hanya "/"

    def _fetch_and_extract_html_info(self, url, link_text_from_parent=None):
        """
        Mengambil konten halaman web. Jika HTML, mengekstrak info.
        Mengembalikan tuple (title, content, new_links_from_page).
        Untuk non-HTML atau error, title bisa nama file/URL atau anchor text, content kosong, new_links kosong.
        """
        fallback_title = link_text_from_parent if link_text_from_parent and link_text_from_parent != url else self._get_filename_from_url(url)

        try:
            response = requests.get(url, timeout=10, headers=self.headers, allow_redirects=True) #
            actual_url = response.url # URL setelah redirect, jika ada

            if response.status_code >= 400:
                print(f"HTTP error {response.status_code} for {url} (final URL: {actual_url}). Storing link with anchor text as title if available.")
                title_for_error = link_text_from_parent if link_text_from_parent and link_text_from_parent != url else self._get_filename_from_url(url)
                return title_for_error, "", [] # KONTEN KOSONG untuk error

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
                        texts_tags = main_content_area.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'th', 'pre', 'span']) # span bisa jadi penting di konten
                        content = ' '.join([tag.get_text(separator=' ', strip=True) for tag in texts_tags])
                    
                    if not content.strip():
                        content_tags_fallback = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li'])
                        texts_fallback = [tag.get_text(separator=' ', strip=True) for tag in content_tags_fallback]
                        content = ' '.join(texts_fallback)

                    content = re.sub(r'\s+', ' ', content).strip() #
                    
                    if not content.strip():
                        body_tag = soup.find('body')
                        if body_tag:
                            content = body_tag.get_text(separator=' ', strip=True)
                            content = re.sub(r'\s+', ' ', content).strip() #
                    
                    new_links = []
                    for a_tag in soup.find_all('a', href=True): #
                        href = a_tag['href']
                        if href.lower().startswith(('mailto:', 'tel:', 'javascript:', '#')):
                            continue
                        
                        absolute_url = urljoin(actual_url, href) #
                        parsed_absolute_url = urlparse(absolute_url) #
                        absolute_url = parsed_absolute_url._replace(fragment="").geturl() #
                        
                        if parsed_absolute_url.scheme not in ('http', 'https'):
                            continue
                        if self._is_same_organization(absolute_url): #
                            link_text = a_tag.get_text(strip=True)
                            if not link_text:
                                link_text = a_tag.get('title', '').strip() or \
                                            a_tag.get('aria-label', '').strip() or \
                                            absolute_url
                            new_links.append((absolute_url, link_text)) #
                    
                    return title, content, new_links

                except bs4.exceptions.ParserRejectedMarkup as e:
                    print(f"Markup parsing error (ParserRejectedMarkup) for HTML {url}: {e}")
                    return fallback_title, "", [] # KONTEN KOSONG
                except Exception as e: #
                    print(f"General error parsing or processing HTML for {url}: {e}")
                    return fallback_title, "", [] # KONTEN KOSONG
            else:
                # Jika bukan HTML (misalnya PDF, DOCX, dll.)
                print(f"Storing non-HTML content at {url} (Content-Type: {content_type}) as a link.")
                non_html_title = self._get_filename_from_url(url)
                return non_html_title, "", [] # KONTEN KOSONG

        except requests.exceptions.HTTPError as e: #
            print(f"HTTP error during request for {url}: {e}. Storing link with anchor text as title if available.")
            title_for_http_error = link_text_from_parent if link_text_from_parent and link_text_from_parent != url else self._get_filename_from_url(url)
            return title_for_http_error, "", [] # KONTEN KOSONG
        except requests.exceptions.RequestException as e: #
            print(f"Request exception for {url}: {e}. Storing link with anchor text as title if available.")
            title_for_req_error = link_text_from_parent if link_text_from_parent and link_text_from_parent != url else self._get_filename_from_url(url)
            return title_for_req_error, "", [] # KONTEN KOSONG
        except Exception as e: #
            print(f"Unexpected error processing {url}: {e}. Storing link.")
            title_for_unexp_error = link_text_from_parent if link_text_from_parent and link_text_from_parent != url else self._get_filename_from_url(url)
            return title_for_unexp_error, "", [] # KONTEN KOSONG

    def crawl_bfs(self, max_pages):
        print(f"Memulai crawling (BFS) dari: {self.seed_url}")
        self.queue = deque()
        self.queue.append((self.seed_url, None, [(self.seed_url, "Seed URL")], 0))
        self.visited_urls.add(self.seed_url)
        crawled_count = 0
        max_depth = 0
        start_time = time.time()

        while self.queue and crawled_count < max_pages:
            current_url, parent_url, current_path_info, current_depth = self.queue.popleft()
            link_text_for_current_url = current_path_info[-1][1] if current_path_info else self._get_filename_from_url(current_url)
            
            print(f"Crawling ({crawled_count+1}/{max_pages}) [BFS]: {current_url} (depth={current_depth}, from_text='{link_text_for_current_url[:50]}...')")

            title, content, new_links = self._fetch_and_extract_html_info(current_url, link_text_for_current_url)
            
            self.crawled_data[current_url] = {
                'title': title,
                'content': content, # Akan "" jika error atau non-HTML
                'parent_url': parent_url,
                'path_info': current_path_info,
                'depth': current_depth
            }
            crawled_count += 1
            max_depth = max(max_depth, current_depth)

            if new_links:
                for link_url, link_text in new_links:
                    if link_url not in self.visited_urls:
                        self.visited_urls.add(link_url)
                        new_path = current_path_info + [(link_url, link_text)]
                        self.queue.append((link_url, current_url, new_path, current_depth + 1))

        duration = time.time() - start_time
        print(f"Crawling BFS selesai. Total halaman: {crawled_count}, Max kedalaman: {max_depth}, Durasi: {duration:.2f} detik")


    def crawl_dfs(self, max_pages):
        print(f"Memulai crawling (DFS) dari: {self.seed_url}")
        self.stack = []
        self.stack.append((self.seed_url, None, [(self.seed_url, "Seed URL")], 0))
        self.visited_urls.add(self.seed_url)
        crawled_count = 0
        max_depth = 0
        start_time = time.time()

        while self.stack and crawled_count < max_pages:
            current_url, parent_url, current_path_info, current_depth = self.stack.pop()
            link_text_for_current_url = current_path_info[-1][1] if current_path_info else self._get_filename_from_url(current_url)

            print(f"Crawling ({crawled_count+1}/{max_pages}) [DFS]: {current_url} (depth={current_depth}, from_text='{link_text_for_current_url[:50]}...')")

            title, content, new_links = self._fetch_and_extract_html_info(current_url, link_text_for_current_url)
            
            self.crawled_data[current_url] = {
                'title': title,
                'content': content, # Akan "" jika error atau non-HTML
                'parent_url': parent_url,
                'path_info': current_path_info,
                'depth': current_depth
            }
            crawled_count += 1
            max_depth = max(max_depth, current_depth)

            if new_links:
                for link_url, link_text in reversed(new_links):
                    if link_url not in self.visited_urls:
                        self.visited_urls.add(link_url)
                        new_path = current_path_info + [(link_url, link_text)]
                        self.stack.append((link_url, current_url, new_path, current_depth + 1))
        
        duration = time.time() - start_time
        print(f"Crawling DFS selesai. Total halaman: {crawled_count}, Max kedalaman: {max_depth}, Durasi: {duration:.2f} detik")


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
                # Prioritaskan snippet dari konten jika konten cocok dan ada
                if content_text and match_in_content:
                    first_term_in_content_index = -1
                    # Cari term pertama dari keyword yang muncul di konten untuk memulai snippet
                    current_search_term_for_snippet = ""
                    for term in search_terms:
                        try:
                            # Cari posisi term yang case-insensitive
                            idx = content_text_lower.index(term)
                            if first_term_in_content_index == -1 or idx < first_term_in_content_index:
                                first_term_in_content_index = idx
                                current_search_term_for_snippet = term # Simpan term yang ditemukan
                        except ValueError:
                            continue
                    
                    if first_term_in_content_index != -1:
                        start_index = first_term_in_content_index
                        snippet_start = max(0, start_index - 70) # Perluas konteks sebelum
                        # Untuk snippet_end, kita ambil dari posisi term pertama + panjang term tersebut + buffer
                        snippet_end = min(len(content_text), start_index + len(current_search_term_for_snippet) + 130) # Perluas konteks sesudah
                        
                        prefix = "..." if snippet_start > 0 else ""
                        suffix = "..." if snippet_end < len(content_text) else ""
                        snippet = prefix + content_text[snippet_start:snippet_end] + suffix
                    else: # Fallback jika tidak ada term yang ditemukan (seharusnya tidak terjadi jika match_in_content true)
                         snippet = content_text[:200] + ('...' if len(content_text) > 200 else '')
                
                # Jika tidak ada snippet dari konten (misalnya konten tidak cocok atau tidak ada konten),
                # dan judul cocok, buat snippet dari judul atau pesan default.
                elif match_in_title: # Ini berarti konten tidak cocok atau tidak ada
                    if not content_text: # Tidak ada konten sama sekali (misalnya halaman error atau file)
                        snippet = ""
                    else: # Ada konten, tapi tidak cocok dengan keyword, namun judul cocok
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