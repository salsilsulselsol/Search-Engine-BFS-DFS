# crawler.py
"""
Modul ini berisi kelas WebCrawler untuk melakukan crawling dan pencarian.
"""
import requests
import bs4 # Import bs4 to explicitly catch its exceptions
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin #
from collections import deque #
import re #
import os

class WebCrawler:
    def __init__(self, seed_url, base_domain, strategy="BFS"): #
        self.seed_url = seed_url #
        self.base_domain = base_domain #
        self.visited_urls = set()
        self.frontier = deque()
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
        # Jika tidak ada nama file yang jelas (misalnya URL adalah domain atau path tanpa file)
        # kembalikan bagian path terakhir atau netloc jika path kosong
        parsed_url = urlparse(url)
        if parsed_url.path and parsed_url.path != '/':
             # Ambil bagian terakhir dari path
            return parsed_url.path.strip('/').split('/')[-1]
        return parsed_url.netloc # Fallback ke domain jika path kosong atau hanya "/"

    def _fetch_and_extract_html_info(self, url):
        """
        Mengambil konten halaman web. Jika HTML, mengekstrak info.
        Mengembalikan tuple (title, content, new_links_from_page).
        Untuk non-HTML atau error, title bisa nama file/URL, content kosong atau pesan error, new_links kosong.
        """
        default_title = self._get_filename_from_url(url) # Judul default jika tidak ada yang lain

        try:
            response = requests.get(url, timeout=10, headers=self.headers, allow_redirects=True) # allow_redirects=True adalah default, tapi eksplisitkan
            
            # Periksa status code setelah potensi redirect
            # Untuk error seperti 401, 403, kita tetap ingin menyimpan linknya
            if response.status_code >= 400:
                print(f"HTTP error {response.status_code} for {url}. Storing link.")
                # Konten kosong karena tidak bisa diakses atau bukan konten yang bisa diproses
                return default_title, "", []

            content_type = response.headers.get('Content-Type', '').lower()

            if 'text/html' in content_type:
                try:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    title = soup.title.string.strip() if soup.title and soup.title.string else default_title
                    
                    content_tags = soup.find_all(['p', 'h1', 'h2', 'h3', 'li', 'span', 'article', 'main'])
                    texts = [tag.get_text(separator=' ', strip=True) for tag in content_tags]
                    content = ' '.join(texts)
                    content = re.sub(r'\s+', ' ', content).strip() #
                    if not content:
                        body_tag = soup.find('body')
                        if body_tag:
                            content = body_tag.get_text(separator=' ', strip=True)
                            content = re.sub(r'\s+', ' ', content).strip() #
                    
                    new_links = []
                    for a_tag in soup.find_all('a', href=True): #
                        href = a_tag['href']
                        if href.lower().startswith(('mailto:', 'tel:', 'javascript:')):
                            continue
                        absolute_url = urljoin(url, href) #
                        parsed_absolute_url = urlparse(absolute_url) #
                        absolute_url = parsed_absolute_url._replace(fragment="").geturl() #
                        if parsed_absolute_url.scheme not in ('http', 'https'):
                            continue
                        if self._is_same_organization(absolute_url): #
                            link_text = a_tag.get_text(strip=True) if a_tag.get_text(strip=True) else absolute_url #
                            new_links.append((absolute_url, link_text)) #
                    
                    return title, content, new_links

                except bs4.exceptions.ParserRejectedMarkup as e:
                    print(f"Markup parsing error (ParserRejectedMarkup) for HTML {url}: {e}")
                    return default_title, "", [] # Konten kosong jika parsing HTML gagal
                except Exception as e: # Termasuk error saat parsing BeautifulSoup
                    print(f"General error parsing or processing HTML for {url}: {e}")
                    return default_title, "", [] # Konten kosong
            else:
                # Jika bukan HTML (misalnya PDF, DOCX, dll.)
                print(f"Storing non-HTML content at {url} (Content-Type: {content_type}) as a link with empty content.")
                return default_title, "", [] # Konten dikosongkan

        except requests.exceptions.HTTPError as e: # Menangkap HTTPError secara spesifik (4xx, 5xx)
            print(f"HTTP error during request for {url}: {e}. Storing link.")
            # response mungkin tidak ada di sini jika error sebelum response diterima
            # jadi kita tidak bisa cek response.status_code lagi.
            return default_title, "", [] # Konten kosong
        except requests.exceptions.RequestException as e: # Menangkap error koneksi, timeout, dll.
            print(f"Request exception for {url}: {e}. Storing link.")
            return default_title, "", [] # Konten kosong
        except Exception as e: # Catchall untuk error tak terduga lainnya
            print(f"Unexpected error processing {url}: {e}. Storing link.")
            return default_title, "", [] # Konten kosong

    def crawl(self, max_pages): #
        print(f"Memulai crawling dari: {self.seed_url} menggunakan strategi: {self.strategy}") #
        self.frontier.append((self.seed_url, None, [(self.seed_url, "Seed URL")])) #
        self.visited_urls.add(self.seed_url) #
        crawled_count = 0 #

        while self.frontier and crawled_count < max_pages: #
            if self.strategy == "BFS":
                current_url, parent_url, current_path_info = self.frontier.popleft() #
            elif self.strategy == "DFS":
                current_url, parent_url, current_path_info = self.frontier.pop() #
            else:
                print(f"Strategi '{self.strategy}' tidak dikenali.")
                return

            print(f"Processing ({crawled_count+1}/{max_pages}) [{self.strategy}]: {current_url}")

            title, content, new_links_from_page = self._fetch_and_extract_html_info(current_url)
            
            self.crawled_data[current_url] = { #
                'title': title, #
                'content': content, # Sekarang akan "" untuk file atau error
                'parent_url': parent_url, #
                'path_info': current_path_info #
            }
            crawled_count += 1 #

            if new_links_from_page:
                if self.strategy == "DFS":
                    new_links_from_page.reverse()

                for link_url, link_text in new_links_from_page: #
                    if link_url not in self.visited_urls: #
                        self.visited_urls.add(link_url) #
                        new_path_info_for_link = current_path_info + [(link_url, link_text)] #
                        self.frontier.append((link_url, current_url, new_path_info_for_link)) #
            
        print(f"Crawling selesai. Total URL diproses: {crawled_count}") #

    def search(self, keyword, limit): #
        results = [] #
        keyword_lower = keyword.lower() #
        for url, data in self.crawled_data.items(): #
            title_text = data.get('title', '')
            content_text = data.get('content', '') # Akan "" untuk file non-HTML atau error
            
            match_in_title = keyword_lower in title_text.lower()
            # Hanya cari di konten jika kontennya ada (bukan string kosong yang disengaja)
            match_in_content = False
            if content_text: # Periksa apakah content_text tidak kosong
                 match_in_content = keyword_lower in content_text.lower()


            if match_in_title or match_in_content:
                # Jika kontennya kosong (misalnya file), snippet akan kosong
                snippet = content_text[:200] + '...' if len(content_text) > 200 else content_text #
                results.append({ #
                    'url': url, #
                    'title': title_text, #
                    'snippet': snippet, #
                    'path_info': data.get('path_info', []) #
                })
                if len(results) >= limit: #
                    break
        return results #

    def get_path_details(self, target_url): #
        if target_url in self.crawled_data: #
            return self.crawled_data[target_url].get('path_info', []) #
        return [] #