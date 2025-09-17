import streamlit as st
from api_client import healthz

st.set_page_config(page_title="jargis", layout="wide")
st.title("jargis – 자기소개서 RAG PoC")

with st.sidebar:
    st.header("Status")
    if st.button("Check API"):
        try:
            res = healthz()
            st.success(f"API: {res}")
        except Exception as e:
            st.error(f"API error: {e}")

st.subheader("검색")
q = st.text_input("문항/키워드 입력")
col1, col2 = st.columns(2)
with col1:
    company = st.text_input("기업")
with col2:
    job = st.text_input("직무")

if st.button("검색하기"):
    st.info("🔧 다음 단계에서 /search API 연동 예정")
