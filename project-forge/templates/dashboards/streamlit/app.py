import os

import plotly.express as px
import streamlit as st

st.set_page_config(page_title="{{project_name}} Dashboard", layout="wide")
st.title("{{project_name}}")
st.caption("Built by {{author}} at {{created_at}}")

sample = [{"x": 1, "y": 2}, {"x": 2, "y": 3}, {"x": 3, "y": 5}]
fig = px.line(sample, x="x", y="y", title="Sample Trend")
st.plotly_chart(fig, use_container_width=True)

st.write("DB connector configured:", bool(os.getenv("DB_URL", "")))
