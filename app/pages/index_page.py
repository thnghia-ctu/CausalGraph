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
from services.upload_store import parse_url_list_files, save_uploaded_documents


st.title("Khai phá dữ liệu nhân quả")
st.caption(
    "Khai phá các yếu tố chi phối quyết định ứng dụng công cụ số trong sản xuất lúa gạo, "
    "từ văn bản tiếng Việt đến đồ thị nhân quả ở mức concept."
)

st.subheader("Dataset hiện có")

datasets = list_datasets()

if not datasets:
    st.info("Chưa có dataset nào. Tạo dataset mới ở bên dưới để bắt đầu.")
else:
    header = st.columns([3, 2, 3, 3])
    header[0].markdown("**Tên**")
    header[1].markdown("**Trạng thái**")
    header[2].markdown("**Tạo lúc**")
    header[3].markdown("")

    pending_delete = st.session_state.get("pending_delete_id")

    for meta in datasets:
        row = st.columns([3, 2, 3, 3])
        row[0].write(meta.name)
        row[1].write(STATUS_LABELS.get(meta.status, meta.status))
        row[2].write(meta.created_at[:19].replace("T", " "))

        actions = ["crawl", "delete"] if meta.status == STATUS_NEW else ["select", "crawl", "delete"]
        _, *action_cols = row[3].columns([1, *([1] * len(actions))])

        for action, col in zip(actions, action_cols):
            if action == "select":
                if col.button("Chọn", key=f"select-{meta.id}"):
                    st.session_state["dataset_id"] = meta.id
                    st.rerun()
            elif action == "crawl":
                crawl_label = "Crawl lại" if meta.status != STATUS_NEW else "Crawl"
                if col.button(crawl_label, key=f"crawl-{meta.id}"):
                    urls = load_source_urls(meta.id)
                    meta.status = STATUS_INGESTING
                    meta.error = ""
                    save_meta(meta)
                    service = get_pipeline_service()
                    try:
                        with st.spinner(f"Đang thu thập dữ liệu cho '{meta.name}'..."):
                            docs = service.crawl(urls, dataset_dir(meta.id))
                        meta.stage_counts["crawl"] = len(docs)
                        meta.status = STATUS_CRAWLED
                        save_meta(meta)
                        st.success(f"Đã thu thập {len(docs)} văn bản cho '{meta.name}'.")
                    except Exception as error:
                        meta.status = STATUS_FAILED
                        meta.error = str(error)
                        save_meta(meta)
                        st.error(f"Lỗi khi crawl '{meta.name}': {error}")
                    st.rerun()
            elif action == "delete":
                if col.button("🗑️", key=f"delete-{meta.id}", help="Xóa dataset"):
                    st.session_state["pending_delete_id"] = meta.id
                    st.rerun()

        if pending_delete == meta.id:
            st.warning(f"Xóa dataset '{meta.name}'? Hành động này không thể hoàn tác.")
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
st.subheader("Tạo dataset mới")

with st.form("create-dataset", clear_on_submit=True):
    name = st.text_input("Tên dataset")
    urls_text = st.text_area(
        "Danh sách URL nguồn (mỗi dòng một URL, có thể để trống nếu chỉ nhập file)",
        height=160,
        placeholder="https://vnexpress.net/...\nhttps://baonongnghiepmoitruong.vn/...",
    )
    uploaded_url_files = st.file_uploader(
        "Hoặc tải lên file danh sách URL (.txt, mỗi dòng một URL)",
        type=["txt"],
        accept_multiple_files=True,
        key="uploaded_url_files",
    )
    uploaded_files = st.file_uploader(
        "Hoặc tải lên file nội dung văn bản đã có sẵn (.txt), mỗi file là một tài liệu",
        type=["txt"],
        accept_multiple_files=True,
        key="uploaded_documents",
    )
    submitted = st.form_submit_button("Tạo dataset")

if submitted:
    urls = [line.strip() for line in urls_text.splitlines() if line.strip()]
    url_list_result = parse_url_list_files(uploaded_url_files) if uploaded_url_files else None
    if url_list_result:
        urls.extend(url_list_result.urls)
    urls = list(dict.fromkeys(urls))

    if not name.strip():
        st.error("Cần nhập tên dataset.")
    elif not urls and not uploaded_files:
        st.error("Cần ít nhất một URL (dán tay hoặc từ file) hoặc một file văn bản.")
    else:
        meta = create_dataset(name.strip(), urls)
        upload_result = (
            save_uploaded_documents(uploaded_files, dataset_dir(meta.id))
            if uploaded_files
            else None
        )
        st.session_state["dataset_id"] = meta.id
        saved_count = len(upload_result.documents) if upload_result else 0
        st.success(
            f"Đã tạo dataset '{meta.name}' ({len(urls)} URL, {saved_count} file). "
            "Mở trang Ingest ở sidebar để chạy pipeline."
        )
        skipped_files = (upload_result.skipped_files if upload_result else []) + (
            url_list_result.skipped_files if url_list_result else []
        )
        if skipped_files:
            st.warning(
                "Không đọc được encoding của các file sau, đã bỏ qua: "
                + ", ".join(skipped_files)
            )
        st.rerun()

selected_id = st.session_state.get("dataset_id")
if not selected_id:
    st.sidebar.warning("Chưa chọn dataset nào.")