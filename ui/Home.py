# ui/Home.py
import streamlit as st
from api_client import healthz, upload, search, draft

st.set_page_config(page_title="jargis – RAG PoC", layout="wide")
st.title("jargis – 자기소개서 RAG PoC")

# 세션 상태
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "last_query" not in st.session_state:
    st.session_state.last_query = ""

with st.sidebar:
    st.header("Status")
    if st.button("Check API"):
        try:
            res = healthz()
            st.success(f"API: {res['status']}")
        except Exception as e:
            st.error(f"API error: {e}")

tabs = st.tabs(["🔼 업로드", "🔎 검색/추천", "📝 초안 생성"])

# ----------------------
# 업로드 탭
# ----------------------
with tabs[0]:
    st.subheader("문항 업로드")
    company = st.text_input("회사명 (선택)", value="")
    job = st.text_input("직무명 (선택)", value="")
    colA, colB = st.columns(2)
    with colA:
        title = st.text_input("문항/답변 제목 (선택)", value="")
    with colB:
        year = st.number_input(
            "연도 (선택)", min_value=1990, max_value=2100, value=2025, step=1
        )

    content = st.text_area(
        "문항/답변 원문 (필수)",
        height=240,
        placeholder="자기소개서 문항/답변 텍스트를 붙여넣으세요.",
    )
    if st.button("업로드 & 임베딩 저장"):
        if not content.strip():
            st.warning("내용을 입력하세요.")
        else:
            with st.spinner("업로드 중... (임베딩 생성 포함)"):
                try:
                    res = upload(
                        content,
                        company or None,
                        job or None,
                        title or None,
                        int(year) if year else None,
                    )
                    st.success(
                        f"업로드 완료! question_id={res['question_id']}, chunks={res['chunks']}, model={res['model']}"
                    )
                except Exception as e:
                    st.error(f"업로드 실패: {e}")

# ----------------------
# 검색 탭
# ----------------------
with tabs[1]:
    st.subheader("유사 문항/소재 검색")
    q = st.text_input("검색어 (예: 협업 갈등 해결 사례)")
    col1, col2, col3 = st.columns(3)
    with col1:
        f_company = st.text_input("회사(필터)", value="")
    with col2:
        f_job = st.text_input("직무(필터)", value="")
    with col3:
        top_k = st.number_input("Top-K", min_value=1, max_value=50, value=5, step=1)

    col4, col5 = st.columns(2)
    with col4:
        year_min = st.number_input(
            "최소 연도", min_value=1990, max_value=2100, value=2020, step=1
        )
    with col5:
        year_max = st.number_input(
            "최대 연도", min_value=1990, max_value=2100, value=2030, step=1
        )

    if st.button("검색"):
        if not q.strip():
            st.warning("검색어를 입력하세요.")
        else:
            with st.spinner("검색 중..."):
                try:
                    res = search(
                        q,
                        top_k=int(top_k),
                        company=f_company or None,
                        job=f_job or None,
                        year_min=int(year_min) if year_min else None,
                        year_max=int(year_max) if year_max else None,
                    )
                    st.session_state.search_results = res.get("hits", [])
                    st.session_state.last_query = q
                    st.success(
                        f"총 {len(st.session_state.search_results)}건 (model: {res.get('model')})"
                    )
                except Exception as e:
                    st.error(f"검색 실패: {e}")

    st.divider()
    st.caption("검색 결과")
    if not st.session_state.search_results:
        st.info("검색 결과가 여기에 표시됩니다.")
    else:
        for i, h in enumerate(st.session_state.search_results, start=1):
            with st.container(border=True):
                st.markdown(f"**#{i}. {h.get('title') or '(제목 없음)'}**")
                meta = f"{h.get('company') or '-'} / {h.get('job') or '-'} / {h.get('year') or '-'}"
                st.caption(
                    f"{meta} | distance={h['distance']:.4f}, similarity={h['similarity']:.4f}"
                )
                st.code(h["snippet"])

                cols = st.columns([1, 1, 6])
                with cols[0]:
                    st.button(
                        "초안 생성",
                        key=f"draft_btn_{i}",
                        on_click=lambda qid=h["question_id"]: st.session_state.update(
                            {"_draft_target": qid}
                        ),
                    )
                with cols[1]:
                    st.write(f"QID: {h['question_id']}")

# ----------------------
# 초안 생성 탭
# ----------------------
with tabs[2]:
    st.subheader("초안 생성")
    target_qid = st.session_state.get("_draft_target")
    if target_qid:
        st.info(f"선택된 question_id = {target_qid}")
    else:
        st.caption("검색 탭에서 결과의 [초안 생성] 버튼을 눌러주세요.")

    top_k_for_draft = st.number_input(
        "참조할 청크 수 (top_k)", min_value=1, max_value=10, value=1, step=1
    )
    if st.button("초안 만들기", disabled=not bool(target_qid)):
        with st.spinner("초안 생성 중..."):
            try:
                res = draft(target_qid, top_k=int(top_k_for_draft))
                st.text_area("자동 생성된 초안", value=res["draft"], height=220)
                st.success(f"model: {res['model']}")
            except Exception as e:
                st.error(f"초안 생성 실패: {e}")
