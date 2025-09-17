import streamlit as st
from api_client import healthz, search

st.set_page_config(page_title="jargis", layout="wide")
st.title("jargis – 자기소개서 RAG PoC")

with st.sidebar:
    st.header("Status")
    if st.button("Check API", key="btn_api"):
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

year_min = st.number_input(
    "최소 연도", min_value=2000, max_value=2100, value=2020, step=1
)
year_max = st.number_input(
    "최대 연도", min_value=2000, max_value=2100, value=2030, step=1
)

if st.button("검색하기", key="btn_search"):
    if not q.strip():
        st.warning("검색어를 입력하세요.")
    else:
        with st.spinner("검색 중..."):
            try:
                res = search(
                    q,
                    top_k=5,
                    company=company or None,
                    job=job or None,
                    year_min=int(year_min) if year_min else None,
                    year_max=int(year_max) if year_max else None,
                )
                hits = res.get("hits", [])
                st.success(f"결과 {len(hits)}건 (model: {res.get('model')})")
                for h in hits:
                    st.markdown(
                        f"**[{h['title'] or '(제목 없음)'}]**  "
                        f"({h.get('company') or '-'} / {h.get('job') or '-'} / {h.get('year') or '-'})"
                    )
                    st.code(h["snippet"])
                    st.caption(
                        f"distance={h['distance']:.4f}  similarity={h['similarity']:.4f}"
                    )
                    st.divider()
            except Exception as e:
                st.error(f"검색 실패: {e}")
