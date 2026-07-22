"""Keywords and enabled internal-search sources for link collection."""

from src.collection.search.adapters import (
    NongNghiepSearchAdapter,
    VnExpressSearchAdapter,
)
from src.collection.search.base_search_adapter import BaseSearchAdapter


ENABLED_SEARCH_SOURCES = ["vnexpress", "nongnghiep"]
MAX_PAGES_PER_KEYWORD = 10
DELAY_SECONDS = 2.0
TIMEOUT_SECONDS = 30
OVERWRITE_EXISTING_RESULTS = False

SEARCH_KEYWORDS = [
    "chuyển đổi số nông nghiệp",
    "nông nghiệp số",
    "số hóa nông nghiệp",
    "công nghệ số trong nông nghiệp",
    "nông nghiệp thông minh",
    "trí tuệ nhân tạo trong nông nghiệp",
    "IoT trong nông nghiệp",
    "truy xuất nguồn gốc nông sản",
    "chuyển đổi số nông dân",
    "chuyển đổi số hợp tác xã",
    "chuyển đổi số sản xuất lúa",
    "công nghệ số sản xuất lúa",
    "khó khăn chuyển đổi số nông nghiệp",
    "rào cản chuyển đổi số nông nghiệp",
    "chi phí chuyển đổi số nông nghiệp",
    "hạ tầng số nông nghiệp",
    "kỹ năng số nông dân",
    "chuyển đổi số nâng cao năng suất",
    "chuyển đổi số giảm chi phí",
    "chuyển đổi số mở rộng thị trường nông sản",
]

SEARCH_ADAPTER_TYPES: dict[str, type[BaseSearchAdapter]] = {
    "vnexpress": VnExpressSearchAdapter,
    "nongnghiep": NongNghiepSearchAdapter,
}


def create_search_adapters(source_names: list[str]) -> list[BaseSearchAdapter]:
    """Instantiate configured sources without a decorator-based registry."""
    return [SEARCH_ADAPTER_TYPES[name]() for name in source_names]
