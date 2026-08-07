import streamlit as st

from services.dataset_store import STATUS_LABELS, create_dataset, dataset_dir, list_datasets
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
    header = st.columns([3, 2, 3, 1])
    header[0].markdown("**Tên**")
    header[1].markdown("**Trạng thái**")
    header[2].markdown("**Tạo lúc**")

    for meta in datasets:
        row = st.columns([3, 2, 3, 1])
        row[0].write(meta.name)
        row[1].write(STATUS_LABELS.get(meta.status, meta.status))
        row[2].write(meta.created_at[:19].replace("T", " "))
        if row[3].button("Chọn", key=f"select-{meta.id}"):
            st.session_state["dataset_id"] = meta.id
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
if selected_id:
    st.sidebar.success(f"Dataset đang chọn:\n\n**{selected_id}**")
    if st.sidebar.button("Sang bước 2: Ingest →", type="primary"):
        st.switch_page("pages/ingest_page.py")
else:
    st.sidebar.warning("Chưa chọn dataset nào.")
