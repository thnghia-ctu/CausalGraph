class BaseCrawler:
    def __init__(self, url):
        self.url = url

    def fetch(self):
        raise NotImplementedError

    def parse(self):
        raise NotImplementedError

    def save(self, path):
        raise NotImplementedError