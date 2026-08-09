import bootstrap

bootstrap.ensure_repo_root_on_path()

import streamlit as st

from services.dataset_store import load_meta

st.set_page_config(page_title="CausalGraph", page_icon="🕸️", layout="wide")

dataset_id = st.session_state.get("dataset_id")
selected_meta = load_meta(dataset_id) if dataset_id else None

index_page = st.Page("pages/index_page.py", title="Bộ dữ liệu", icon="🗂️", default=True)
ingest_page = st.Page("pages/ingest_page.py", title="Xử lý dữ liệu", icon="⚙️")
explore_page = st.Page("pages/explore_page.py", title="Khám phá đồ thị", icon="🕸️")

page = st.navigation([index_page, ingest_page, explore_page], position="hidden")

st.sidebar.page_link(index_page)
if selected_meta is not None:
    st.sidebar.divider()
    st.sidebar.subheader(f":blue[{selected_meta.name}]")
    st.sidebar.page_link(ingest_page)
    st.sidebar.page_link(explore_page)

page.run()
