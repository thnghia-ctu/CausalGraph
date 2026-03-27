class BaseCrawler:
    def __init__(self, url):
        self.url = url

    def fetch(self):
        raise NotImplementedError

    def parse(self):
        raise NotImplementedError

    def save(self, path):
        raise NotImplementedError
    def postprocess(self, text):
        raise NotImplementedError
    
    def run(self, path):
        raw = self.fetch()
        parsed = self.parse(raw)
        # cleaned = self.postprocess(parsed)
        self.save(parsed, path)
        return parsed