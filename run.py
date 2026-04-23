from src.crawlers.web_crawler import WebCrawler
from src.crawlers.youtube_crawler import YouTubeCrawler
from src.preprocessing.semantic_chunker import SemanticChunker
from src.preprocessing.filter_chunks import filter_chunks
from src.utils.helpers import load_txt, save_txt

# url = "https://www.youtube.com/watch?v=WYbE6B0qXqQ"

# crawler = YouTubeCrawler(url)
chunker = SemanticChunker()

# html = crawler.fetch()
text = load_txt("data/raw/web/1_text.txt")

chunks = chunker.chunk(text)
filtered_chunks, out_filter = filter_chunks(chunks)

save_txt("filtered1_text.txt", filtered_chunks)
save_txt("unfiltered1_text.txt", out_filter)


# crawler.run("raw_text.txt")
# crawler.save("\n".join(chunks), "chunked_text.txt")
# crawler.save("\n".join(filtered_chunks), "filtered_text.txt")
# crawler.save("\n".join(out_filter), "unfiltered_text.txt")