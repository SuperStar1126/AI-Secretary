import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class UrlFetcher:

    # auxillary class for fetching urls in sitemaps or scraping sub-domains

    def __init__(self):
        pass
    
    def _linked_urls(self, url: str, base: str):
        # find all linked sub domains
        html = requests.get(url).text
        soup = BeautifulSoup(html, 'html.parser')
        for link in soup.find_all('a'):
            path = link.get('href')
            if path and not path.startswith("#"):
                path = urljoin(url, path)
                if path.startswith(base) and path != url:
                    yield path

    def __call__(self, url: str):
        if url.endswith(".xml") or url.endswith(".xml/"):
            # scrape <loc> tags for URLs in a XML sitemap
            txt = requests.get(url).text
            soup = BeautifulSoup(txt, "xml")

            url_tags = soup.find_all("loc")
            urls = [tag.contents[0] for tag in url_tags]
            urls = list(set(urls)) # de-duplicate URLs
            return urls # might need to stream/chunk response as it can get too big
        else:
            # scrape paths <a> tags to scrape sub domains
            visited = []
            to_visit = [url]
            base = url
            # implement a queue for urls and find and queue links for each one
            while to_visit:
                visiting = to_visit[0]
                for link in self._linked_urls(url, base):
                    if link not in visited and link not in to_visit:
                        to_visit.append(link)            
                visited.append(visiting)
                to_visit.pop(0)
            return visited
            

if __name__ == "__main__":
    fetcher = UrlFetcher()
    res = fetcher("https://www.aia.com.hk/en/sitemap1.xml")