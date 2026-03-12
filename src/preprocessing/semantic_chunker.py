import underthesea


class SemanticChunker:

    def __init__(self, n_sent=2):
        self.n_sent = n_sent

    def chunk(self, text):
        sentences = underthesea.sent_tokenize(text)

        chunks = []
        for i in range(0, len(sentences), self.n_sent):
            chunk = " ".join(sentences[i:i+self.n_sent])
            chunks.append(chunk)

        return chunks