from src.chunking.semantic_chunker import SemanticChunker
from src.filtering.semantic_filter import filter_chunks
from src.utils.helpers import load_txt, save_txt

chunker = SemanticChunker()

##

chunks = []
for i in range(3, 4):
    text = load_txt(f"data/raw/web/{i}_text.txt")
    chunks.extend([chunk.text for chunk in chunker.chunk(text)])

filtered_chunks, out_filtered_chunks = filter_chunks(chunks)
save_txt("filtered_chunks.txt", filtered_chunks)
save_txt("out_filtered_chunks.txt", out_filtered_chunks)