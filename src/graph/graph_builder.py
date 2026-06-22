import networkx as nx
def build_graph():
    relations = [
        {
            "source": "Chi phí đầu tư",
            "target": "Ứng dụng công cụ số",
            "relation": "cản trở",
            "score": 0.85
        },
        {
            "source": "Trình độ học vấn",
            "target": "Ứng dụng công cụ số",
            "relation": "thúc đẩy",
            "score": 0.92
        },
        {
            "source": "Tập huấn kỹ thuật",
            "target": "Ứng dụng công cụ số",
            "relation": "thúc đẩy",
            "score": 0.88
        },
        {
            "source": "Ứng dụng công cụ số",
            "target": "Năng suất lúa",
            "relation": "tăng",
            "score": 0.90
        },
        {
            "source": "Ứng dụng công cụ số",
            "target": "Hiệu quả sản xuất",
            "relation": "tăng",
            "score": 0.87
        }
    ]
    G = nx.DiGraph()
    for r in relations:
        G.add_edge(
            r["source"],
            r["target"],
            relation=r["relation"],
            score=r["score"]
        )
    return G