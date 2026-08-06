from src.pipeline import Pipeline



pipeline = Pipeline()
with open("input/ip.txt", encoding="utf-8") as file:
    urls = [line.strip() for line in file if line.strip()]

docs = pipeline.crawl_data(
    urls=urls
)

chunks = pipeline.chunk_data(docs)
sens = pipeline.detect_causal_sentences(chunks)
simplified_sens = pipeline.simplify_sentences(sens)
spo_records = pipeline.extract_spo(simplified_sens)
concept_states = pipeline.extract_concept_states(spo_records)
graph = pipeline.build_concept_graph(concept_states)

print(f"docs={len(docs)} chunks={len(chunks)} causal_sentences={len(sens)} simplified={len(simplified_sens)}")
print(f"spo_records={len(spo_records)} concept_states={len(concept_states)}")
print(f"graph nodes={graph.number_of_nodes()} edges={graph.number_of_edges()}")
