import bootstrap

bootstrap.ensure_repo_root_on_path()

import streamlit as st

st.set_page_config(page_title="CausalGraph", page_icon="🕸️", layout="wide")

page = st.navigation(
    [
        st.Page("pages/index_page.py", title="Bộ dữ liệu", icon="🗂️", default=True),
        st.Page("pages/ingest_page.py", title="Xử lý dữ liệu", icon="⚙️"),
    ]
)
page.run()
