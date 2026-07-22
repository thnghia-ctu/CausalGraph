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
    
    def run(self, path: str | None, is_save = True)->str:

        if is_save and path is None:
            raise ValueError("path is required when is_save=True")

        raw = self.fetch()
        parsed = self.parse(raw)
        cleaned = self.postprocess(parsed)
        if is_save:
            self.save(cleaned, path)
        return cleaned
