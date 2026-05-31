from src.chunking.semantic_chunker import SemanticChunker
chunker = SemanticChunker()

from src.utils.helpers import load_txt, save_txt
chunks = []
for i in range(1, 19):
    text = load_txt(f"data/raw/web/{i}_text.txt")
    chunks.extend([chunk.text for chunk in chunker.chunk(text)])

save_txt("chunked_text.txt", chunks)