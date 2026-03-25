from src.utils.lexicon_manager import LexiconManager
from src.utils.lexicon_embedding import LexiconEmbedding


def filter_chunks(chunks):

    lex = LexiconManager("configs/lexicon.json")
    terms = lex.get_terms()

    lex_embed = LexiconEmbedding(terms)

    filtered = []
    out_filtered = []

    for chunk in chunks:
        if lex_embed.is_relevant(chunk, 0.55):
            filtered.append(chunk)
        else:
            out_filtered.append(chunk)
    return filtered, out_filtered