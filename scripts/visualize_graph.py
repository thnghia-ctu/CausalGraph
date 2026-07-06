from src.graph.graph_builder import build_graph
from src.graph.graph_visualizer import visualize_graph
from src.data_models.relation import Relation
from src.data_models.trigger import Trigger
import pandas as pd
from configs.config import BASE_DIR

df = pd.read_csv(f"{BASE_DIR}/output/relations.csv", sep = ",", encoding="utf-8-sig")
relations=[]
for row in df.itertuples(index=False):
    source = row.source
    trigger = row.trigger
    target = row.target
    root = row.root
    sentence = row.sentence
    if pd.isna(source) or pd.isna(target) or pd.isna(trigger):
        continue
    relations.append(Relation(source, Trigger(0, 0, trigger), "", target))

G = build_graph(relations)
visualize_graph(G, f"{BASE_DIR}/output/graph.html")

# print(df.info())