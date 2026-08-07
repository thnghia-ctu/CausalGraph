import math
from pathlib import Path

from pyvis.network import Network

DIRECTION_COLORS = {
    "positive": "#2ecc71",
    "negative": "#f1c40f",
    "conflict": "#e74c3c",
    "neutral": "#3498db",
}

MIN_NODE_SIZE = 15
MAX_NODE_SIZE = 45

EXTENSION_PATH = Path(__file__).parent / "graph_extension.html"
EXTENSION_MARKER = "<!-- graph-extension -->"


def visualize_graph(graph, path):
    net = _build_network(graph)
    net.show(path, notebook=True)
    _enhance_html(path)
    return None


def _build_network(graph):
    net = Network(notebook=True, directed=True, cdn_resources="in_line")
    sizes = _node_sizes(graph)

    for node, data in graph.nodes(data=True):
        _add_node(net, node, data, sizes[node])

    for source, target, data in graph.edges(data=True):
        _add_edge(net, source, target, data)

    return net


def _node_sizes(graph):
    weights = {}
    for node in graph.nodes:
        incident_edges = list(graph.in_edges(node, data=True)) + list(graph.out_edges(node, data=True))
        weights[node] = sum(len(data.get("relations", [])) for _, _, data in incident_edges)

    max_weight = max(weights.values(), default=0)
    if max_weight == 0:
        return {node: MIN_NODE_SIZE for node in graph.nodes}

    return {
        node: MIN_NODE_SIZE + (MAX_NODE_SIZE - MIN_NODE_SIZE) * math.sqrt(weight / max_weight)
        for node, weight in weights.items()
    }


def _add_node(net, node, data, size):
    direction_state = data.get("direction_state", "neutral")
    color = DIRECTION_COLORS.get(direction_state, DIRECTION_COLORS["neutral"])
    net.add_node(node, label=node, title=node, color=color, direction_state=direction_state, size=size)


def _add_edge(net, source, target, data):
    relations = data.get("relations", [])
    net.add_edge(
        source, target,
        title=str(len(relations)),
        relations=relations,
    )


def _enhance_html(path):
    output_path = Path(path)
    html = output_path.read_text(encoding="utf-8")

    if EXTENSION_MARKER in html:
        return

    if "</body>" not in html:
        raise ValueError("Không tìm thấy thẻ </body> trong HTML do pyvis tạo")

    extension = EXTENSION_PATH.read_text(encoding="utf-8")
    html = html.replace("</body>", f"{EXTENSION_MARKER}\n{extension}\n</body>")
    output_path.write_text(html, encoding="utf-8")
