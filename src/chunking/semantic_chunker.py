from chonkie import SemanticChunker as ChonkieSemanticChunker

class SemanticChunker:
    _chunker = None
    @classmethod
    def get_chunker(cls):
        if cls._chunker is None:
            cls._chunker = ChonkieSemanticChunker(embedding_model="keepitreal/vietnamese-sbert")
        return cls._chunker

    def chunk(self, text):
        return self.get_chunker().chunk(text)