"""Run or import the internal-search link collection workflow."""

from collections.abc import Iterable
import logging
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from configs.search_sources import (  # noqa: E402
    DELAY_SECONDS,
    ENABLED_SEARCH_SOURCES,
    MAX_PAGES_PER_KEYWORD,
    OVERWRITE_EXISTING_RESULTS,
    SEARCH_KEYWORDS,
    TIMEOUT_SECONDS,
    create_search_adapters,
)
from src.collection.search.result_writer import (  # noqa: E402
    load_completed_pages,
    process_results,
    write_search_csvs,
)
from src.collection.search.search_collector import SearchCollector  # noqa: E402


LOGGER = logging.getLogger(__name__)


def collect_search_links(
    source_names: list[str],
    keywords: Iterable[str],
    *,
    max_pages_per_keyword: int = 10,
    delay_seconds: float = 2.0,
    timeout_seconds: int = 30,
    output_dir: str | Path = PROJECT_ROOT / "data/links",
    overwrite: bool = False,
) -> tuple[int, int]:
    """Collect and save links using values supplied directly by Python code.

    Returns:
        A ``(raw_result_count, unique_url_count)`` tuple.
    """
    destination = Path(output_dir)
    raw_path = destination / "search_results_raw.csv"
    unique_path = destination / "unique_links.csv"
    adapters = create_search_adapters(source_names)
    completed_pages = set() if overwrite else load_completed_pages(raw_path)
    collector = SearchCollector(
        adapters=adapters,
        delay_seconds=delay_seconds,
        timeout_seconds=timeout_seconds,
        max_pages_per_keyword=max_pages_per_keyword,
    )
    results = collector.collect(keywords, completed_pages)
    processed_results = process_results(results, adapters)
    raw_count, unique_count = write_search_csvs(
        processed_results,
        raw_path,
        unique_path,
        preserve_existing=not overwrite,
    )
    LOGGER.info("Tổng số bản ghi thô: %d", raw_count)
    LOGGER.info("Tổng số URL duy nhất: %d", unique_count)
    LOGGER.info("Đã ghi %s", raw_path)
    LOGGER.info("Đã ghi %s", unique_path)
    return raw_count, unique_count


def main() -> int:
    """Run collection with values declared in ``configs.search_sources``."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    collect_search_links(
        source_names=ENABLED_SEARCH_SOURCES,
        keywords=SEARCH_KEYWORDS,
        max_pages_per_keyword=MAX_PAGES_PER_KEYWORD,
        delay_seconds=DELAY_SECONDS,
        timeout_seconds=TIMEOUT_SECONDS,
        overwrite=True,
    )
    # collect_search_links(
    #     source_names=["vnexpress"],
    #     keywords=["nông nghiệp số"],
    #     max_pages_per_keyword=1,
    #     delay_seconds=DELAY_SECONDS,
    #     timeout_seconds=TIMEOUT_SECONDS,
    #     overwrite=True,
    # )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
