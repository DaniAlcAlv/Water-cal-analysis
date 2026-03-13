import streamlit as st

def set_page_config(page_title:str) -> None:
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1.5rem;
                padding-bottom: 0.5rem;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.set_page_config(
        page_title=page_title,
        layout="wide",
        initial_sidebar_state="expanded",
    )