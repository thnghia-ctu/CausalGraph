from chonkie import SemanticChunker as ChonkieSemanticChunker
from underthesea import sent_tokenize

class SemanticChunker:
    _chunker = None
    @classmethod
    def get_chunker(cls):
        if cls._chunker is None:
            cls._chunker = ChonkieSemanticChunker(
                embedding_model="keepitreal/vietnamese-sbert",
                min_sentences_per_chunk=2,
                delim="\n",
            )
        return cls._chunker

    def chunk(self, text):
        sentences = sent_tokenize(text)
        return self.get_chunker().chunk("\n".join(sentences))