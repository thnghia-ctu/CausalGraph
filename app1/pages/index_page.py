import streamlit as st

from services.dataset_store import (
    STATUS_CRAWLED,
    STATUS_FAILED,
    STATUS_INGESTING,
    STATUS_LABELS,
    STATUS_NEW,
    create_dataset,
    dataset_dir,
    delete_dataset,
    list_datasets,
    load_source_urls,
    save_meta,
)
from services.pipeline_service import get_pipeline_service
from services.upload_store import parse_url_list_files


title_col, status_col = st.columns([4, 1])
with title_col:
    st.title("Khai phá dữ liệu nhân quả")
    st.caption(
        "Khai phá các yếu tố chi phối quyết định ứng dụng công cụ số trong sản xuất lúa gạo, "
        "từ văn bản tiếng Việt đến đồ thị nhân quả ở mức concept."
    )
status_placeholder = status_col.empty()

st.subheader("Tập dữ liệu hiện có")

datasets = list_datasets()

if not datasets:
    st.info("Chưa có tập dữ liệu nào. Tạo tập dữ liệu mới ở bên dưới để bắt đầu.")
else:
    header = st.columns([3, 2, 3, 3])
    header[0].markdown("**Tên**")
    header[1].markdown("**Trạng thái**")
    header[2].markdown("**Tạo lúc**")
    header[3].markdown("")

    pending_delete = st.session_state.get("pending_delete_id")

    for meta in datasets:
        row = st.columns([2, 2, 2, 4])
        row[0].write(meta.name)
        row[1].write(STATUS_LABELS.get(meta.status, meta.status))
        row[2].write(meta.created_at[:19].replace("T", " "))

        actions = ["", "crawl", "delete"] if meta.status == STATUS_NEW else ["select", "crawl", "delete"]
        _, *action_cols = row[3].columns([1, *([1] * len(actions))])

        for action, col in zip(actions, action_cols):
            if action == "select":
                if col.button("Chọn", key=f"select-{meta.id}"):
                    st.session_state["dataset_id"] = meta.id
                    st.rerun()
            elif action == "crawl":
                if col.button("Thu thập dữ liệu", key=f"crawl-{meta.id}"):
                    urls = load_source_urls(meta.id)
                    meta.status = STATUS_INGESTING
                    meta.error = ""
                    save_meta(meta)
                    service = get_pipeline_service()

                    try:
                        with status_placeholder.status(f"Đang thu thập dữ liệu cho '{meta.name}'...") as status:
                            def on_progress(stage_key: str, count: int) -> None:
                                meta.stage_counts[stage_key] = count
                                save_meta(meta)
                                if stage_key == "crawl":
                                    status.update(label=f"Đang phân đoạn dữ liệu cho '{meta.name}'...")

                            chunks = service.crawl_and_chunk(urls, dataset_dir(meta.id), on_progress=on_progress)
                            status.update(
                                label=f"Đã thu thập và phân đoạn xong cho '{meta.name}'.",
                                state="complete",
                            )
                        meta.status = STATUS_CRAWLED
                        save_meta(meta)
                        st.success(f"Đã thu thập và phân đoạn xong cho '{meta.name}' ({len(chunks)} chunk).")
                    except Exception as error:
                        meta.status = STATUS_FAILED
                        meta.error = str(error)
                        save_meta(meta)
                        st.error(f"Lỗi khi tải dữ liệu '{meta.name}': {error}")
                    st.rerun()
            elif action == "delete":
                if col.button("🗑️", key=f"delete-{meta.id}", help="Xóa tập dữ liệu"):
                    st.session_state["pending_delete_id"] = meta.id
                    st.rerun()

        if pending_delete == meta.id:
            st.warning(f"Xóa tập dữ liệu '{meta.name}'? Hành động này không thể hoàn tác.")
            confirm_cols = st.columns([1, 1, 5])
            if confirm_cols[0].button("Xác nhận xóa", key=f"confirm-delete-{meta.id}"):
                delete_dataset(meta.id)
                if st.session_state.get("dataset_id") == meta.id:
                    del st.session_state["dataset_id"]
                del st.session_state["pending_delete_id"]
                st.rerun()
            if confirm_cols[1].button("Hủy", key=f"cancel-delete-{meta.id}"):
                del st.session_state["pending_delete_id"]
                st.rerun()

st.divider()
st.subheader("Tạo tập dữ liệu mới")

with st.form("create-dataset", clear_on_submit=True):
    name = st.text_input("Tên tập dữ liệu")
    uploaded_url_files = st.file_uploader(
        "Hoặc tải lên file danh sách URL (.txt, mỗi dòng một URL)",
        type=["txt"],
        accept_multiple_files=True,
        key="uploaded_url_files",
    )
    submitted = st.form_submit_button("Tạo tập dữ liệu")

if submitted:
    url_list_result = parse_url_list_files(uploaded_url_files) if uploaded_url_files else None
    urls = list(dict.fromkeys(url_list_result.urls)) if url_list_result else []

    if not name.strip():
        st.error("Cần nhập tên tập dữ liệu.")
    elif not urls:
        st.error("Cần tải lên file danh sách URL.")
    else:
        meta = create_dataset(name.strip(), urls)
        st.session_state["dataset_id"] = meta.id
        st.success(
            f"Đã tạo tập dữ liệu '{meta.name}' ({len(urls)} URL). "
            "Mở trang Ingest ở sidebar để chạy pipeline."
        )
        skipped_files = url_list_result.skipped_files if url_list_result else []
        if skipped_files:
            st.warning(
                "Không đọc được encoding của các file sau, đã bỏ qua: "
                + ", ".join(skipped_files)
            )
        st.rerun()

selected_id = st.session_state.get("dataset_id")
if not selected_id:
    st.sidebar.warning("Chưa chọn tập dữ liệu nào.")