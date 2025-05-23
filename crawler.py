# crawler.py
"""
Modul ini berisi kelas WebCrawler untuk melakukan crawling dan pencarian.
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from collections import deque
import re #

class WebCrawler:
    def __init__(self, seed_url, base_domain): #
        self.seed_url = seed_url #
        self.base_domain = base_domain # Domain utama dari seed URL, diekstrak dari seed_url
        self.visited_urls = set() #
        self.queue = deque() #
        self.crawled_data = {} #
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        } #

    def _is_same_organization(self, url): #
        """
        Memeriksa apakah URL termasuk dalam domain organisasi yang sama (termasuk subdomain).
        """
        parsed_url = urlparse(url) #
        if parsed_url.scheme not in ('http', 'https'): #
            return False
        return parsed_url.netloc.endswith(self.base_domain) #

    def _fetch_page(self, url): #
        """
        Mengambil konten halaman web dari URL tertentu.
        Mengembalikan objek BeautifulSoup jika berhasil, None jika gagal.
        """
        try:
            response = requests.get(url, timeout=5, headers=self.headers) #
            response.raise_for_status() #
            return BeautifulSoup(response.content, 'html.parser') #
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}") #
            return None

    def _extract_info(self, soup, current_url): #
        """
        Mengekstrak judul dan konten teks utama dari objek BeautifulSoup.
        """
        title = soup.title.string if soup.title else "No Title" #
        content_tags = soup.find_all(['p', 'h1', 'h2', 'h3', 'li', 'span']) #
        content = ' '.join([tag.get_text(separator=' ', strip=True) for tag in content_tags]) #
        content = re.sub(r'\s+', ' ', content).strip() #
        return title, content

    def _extract_links(self, soup, base_url): #
        """
        Mengekstrak semua tautan absolut dari objek BeautifulSoup yang berada dalam organisasi yang sama.
        Mengembalikan list tuple (url, link_text).
        """
        links = [] #
        for a_tag in soup.find_all('a', href=True): #
            href = a_tag['href'] #
            absolute_url = urljoin(base_url, href) #
            absolute_url = urlparse(absolute_url)._replace(fragment="").geturl() #

            if self._is_same_organization(absolute_url): #
                link_text = a_tag.get_text(strip=True) if a_tag.get_text(strip=True) else absolute_url #
                links.append((absolute_url, link_text)) #
        return links

    def crawl(self, max_pages): #
        """
        Melakukan crawling web menggunakan algoritma Breadth-First Search (BFS).
        """
        print(f"Memulai crawling dari: {self.seed_url}") #
        self.queue.append((self.seed_url, None, [(self.seed_url, "Seed URL")])) #
        self.visited_urls.add(self.seed_url) #
        crawled_count = 0 #

        while self.queue and crawled_count < max_pages: #
            current_url, parent_url, current_path_info = self.queue.popleft() #
            print(f"Crawling ({crawled_count+1}/{max_pages}): {current_url}") #

            soup = self._fetch_page(current_url) #
            if soup:
                title, content = self._extract_info(soup, current_url) #
                self.crawled_data[current_url] = { #
                    'title': title, #
                    'content': content, #
                    'parent_url': parent_url, #
                    'path_info': current_path_info #
                }
                crawled_count += 1 #

                new_links = self._extract_links(soup, current_url) #
                for link_url, link_text in new_links: #
                    if link_url not in self.visited_urls: #
                        self.visited_urls.add(link_url) #
                        new_path_info = current_path_info + [(link_url, link_text)] #
                        self.queue.append((link_url, current_url, new_path_info)) #
            else:
                self.visited_urls.add(current_url) #

        print(f"Crawling selesai. Total halaman di-crawl: {crawled_count}") #

    def search(self, keyword, limit): #
        """
        Mencari halaman yang mengandung kata kunci.
        Mengembalikan daftar hasil pencarian.
        """
        results = [] #
        keyword_lower = keyword.lower() #
        for url, data in self.crawled_data.items(): #
            if keyword_lower in data['title'].lower() or keyword_lower in data['content'].lower(): #
                snippet = data['content'][:200] + '...' if len(data['content']) > 200 else data['content'] #
                results.append({ #
                    'url': url, #
                    'title': data['title'], #
                    'snippet': snippet, #
                    'path_info': data['path_info'] #
                })
                if len(results) >= limit: #
                    break
        return results

    def get_path_details(self, target_url): #
        """
        Mengembalikan detail rute tautan untuk URL target.
        """
        if target_url in self.crawled_data: #
            return self.crawled_data[target_url]['path_info'] #
        return []