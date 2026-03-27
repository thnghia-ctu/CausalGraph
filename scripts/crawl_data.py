from src.crawlers.web_crawler import WebCrawler
from src.crawlers.youtube_crawler import YouTubeCrawler

links_path = 'data/raw/links.txt'

with open(links_path, 'r') as f:
    links = f.read().splitlines()

w_i = 1
y_i = 1
for link in links:
    try:
        # validate link
        if not link:
            continue

        if "youtube" in link.lower():
            crawler = YouTubeCrawler(link)
            text = crawler.run(f"data/raw/youtube_{y_i}_text.txt")
            y_i += 1
            
        else:
            crawler = WebCrawler(link)
            text = crawler.run(f"data/raw/web_{w_i}_text.txt")
            w_i += 1

    except Exception as e:
        print(f"Error at link {link}: {e}")