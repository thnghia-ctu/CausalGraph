from pyvis.network import Network

def visualize_graph(graph, path):
    net = Network(notebook=True, directed=True)
    for node in graph.nodes():
        net.add_node(node, label=node, title=node)
    for source, target, data in graph.edges(data=True):
        relation = data.get('relation', '')
        score = data.get('score', 0)
        net.add_edge(source, target, title=f"{relation} ({score:.2f})")
    net.show(path)
    return None

import os

# from causalgraph import Graph

# def convert_and_visualize_with_causalgraph(networkx_graph, db_name="causal_model.sqlite3"):
#     # 1. Khởi tạo một đồ thị causalgraph mới (lưu vào file SQLite)
#     if os.path.exists(db_name):
#         os.remove(db_name)  # Xóa DB cũ nếu có để khởi tạo mới
        
#     cg_graph = Graph(sql_db_filename=db_name)
    
#     # 2. Thêm các CausalNodes từ NetworkX Graph vào causalgraph
#     for node in networkx_graph.nodes():
#         # Chuyển đổi tên nút thành chuỗi (string) vì causalgraph yêu cầu định dạng này
#         cg_graph.add.causal_node(str(node))
        
#     # 3. Thêm các CausalEdges kèm theo thông tin bổ sung (Metadata)
#     for source, target, data in networkx_graph.edges(data=True):
#         relation = data.get('relation', 'causal_relation')
#         score = data.get('score', 0.0)
        
#         # Định nghĩa tên định danh duy nhất cho cạnh (Edge Name)
#         edge_id = f"edge_{source}_to_{target}"
        
#         # causalgraph cho phép tạo mối quan hệ nhân quả giữa Cause và Effect
#         cg_graph.add.causal_edge(
#             str(source), 
#             str(target), 
#             f"{relation} ({score:.2f})"
#         )
        
#         # LƯU Ý: Khác với pyvis lưu title text, trong causalgraph nếu bạn muốn gán 
#         # sâu thuộc tính 'relation' hay 'score' vào bản thể luận (Ontology), bạn sẽ 
#         # ánh xạ thuộc tính đó sau. Hiện tại ta có thể vẽ nhanh cấu trúc này.

#     # 4. Hiển thị đồ thị bằng tính năng tích hợp của causalgraph 
#     # (Hàm này gọi NetworkX backend để vẽ đồ thị tĩnh)
#     print("Đang hiển thị đồ thị nhân quả:")
#     cg_graph.draw.nx()
    
#     return cg_graph