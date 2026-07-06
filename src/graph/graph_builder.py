import networkx as nx
def build_graph(relations):    
    G = nx.DiGraph()
    for r in relations:
        G.add_edge(
            r.source,
            r.target,
            relation=r.trigger.text,
            score=r.confidence
        )
    return G