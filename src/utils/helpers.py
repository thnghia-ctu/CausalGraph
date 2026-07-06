from sentence_transformers import SentenceTransformer
import yaml

def load_txt(path: str) -> str:
    """Đọc file và trả về một chuỗi văn bản duy nhất."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            # .read() trả về toàn bộ nội dung dưới dạng string
            return f.read().strip()
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file tại {path}")
        return ""
    
def save_txt(path, data):
    """
    Lưu dữ liệu vào file. 
    Hỗ trợ cả chuỗi (str) và danh sách các đoạn văn (list).
    """
    try:
        # 1. Tự động tạo thư mục cha nếu chưa có (ví dụ: tạo folder 'output')
        # os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            # 2. Kiểm tra nếu data là list thì nối lại bằng dấu xuống dòng
            if isinstance(data, list):
                # Nối các chunk lại, mỗi chunk cách nhau 2 dấu dòng để dễ đọc
                text_to_save = "##\n".join(data)
            else:
                text_to_save = str(data)
            
            f.write(text_to_save)
            
        print(f"--- Đã lưu thành công tại: {path} ---")
        
    except Exception as e:
        print(f"Lỗi khi lưu file: {e}")

def load_embedding_model(model_name="keepitreal/vietnamese-sbert"):
    return SentenceTransformer(model_name)

def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

import pandas as pd

def load_xlsx(file_path, sheet_name="Sheet1", column_name=None):
    
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    if column_name is None:
        return df

    if column_name not in df.columns:
        raise ValueError(
            f"Column '{column_name}' not found. "
            f"Available columns: {list(df.columns)}"
        )

    return (
        df[column_name]
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()
    )