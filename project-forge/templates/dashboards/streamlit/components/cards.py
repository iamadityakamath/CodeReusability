import streamlit as st


def metric_card(title: str, value: str) -> None:
    st.metric(label=title, value=value)
