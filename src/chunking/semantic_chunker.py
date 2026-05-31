from chonkie import SemanticChunker as ChonkieSemanticChunker

class SemanticChunker:
    def __init__(self):
        self.chunker = ChonkieSemanticChunker()

    def chunk(self, text):
        return self.chunker.chunk(text)