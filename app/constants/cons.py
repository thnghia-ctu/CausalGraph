STATUS_NEW = "new"
STATUS_INGESTING = "ingesting"
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"

STATUS_LABELS = {
    STATUS_NEW: "Mới tạo",
    STATUS_INGESTING: "Đang xử lý",
    STATUS_SUCCESS: "Sẵn sàng",
    STATUS_FAILED: "Lỗi",
}

STEP_NONE = 0
STEP_CRAWL = 1
STEP_CHUNK = 2

STEP_LABELS = {
    STEP_NONE: "",
    STEP_CRAWL: "Thu thập dữ liệu",
    STEP_CHUNK: "Phân đoạn dữ liệu",
}

STEP_PROGRESS = {
    STEP_NONE: 0,
    STEP_CRAWL: 50,
    STEP_CHUNK: 75,
}

URLS_FILENAME = "urls.txt"
