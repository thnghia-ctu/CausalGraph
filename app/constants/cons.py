STATUS_INGESTING = "ingesting"
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"

STATUS_LABELS = {
    STATUS_INGESTING: "Đang xử lý",
    STATUS_SUCCESS: "Thành công",
    STATUS_FAILED: "Lỗi",
}

STEP_NONE = 0
STEP_CRAWL = 1
STEP_CHUNK = 2
STEP_FILTER = 3
STEP_CAUSAL_DETECTION = 4
STEP_SIMPLIFICATION = 5
STEP_SPO = 6
STEP_CONCEPT_STATE = 7
STEP_VISULIZE = 8

STEP_LABELS = {
    STEP_NONE: "",
    STEP_CRAWL: "Thu thập dữ liệu",
    STEP_CHUNK: "Phân đoạn dữ liệu",
    STEP_FILTER: "Lọc dữ liệu",
    STEP_CAUSAL_DETECTION: "Nhận diện câu nhân quả",
    STEP_SIMPLIFICATION: "Tách câu đơn",
    STEP_SPO: "Trích xuất subject-predicate-object",
    STEP_CONCEPT_STATE: "Phân rã concept/state",
    STEP_VISULIZE: "Xây dựng đồ thị",
}
