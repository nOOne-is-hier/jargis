# ui/Home.py
import os
import tempfile
import streamlit as st
from api_client import healthz, upload, search, draft, preview_md, commit_md

# -----------------------------
# Page setup (단 한 번만 설정)
# -----------------------------
st.set_page_config(page_title="jargis – RAG PoC", layout="wide")
st.title("jargis – 자기소개서 RAG PoC")

# -----------------------------
# Session state 초기화
# -----------------------------
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "last_query" not in st.session_state:
    st.session_state.last_query = ""
if "preview" not in st.session_state:
    st.session_state.preview = None
if "raw_text" not in st.session_state:
    st.session_state.raw_text = None
if "file_name" not in st.session_state:
    st.session_state.file_name = None
if "_draft_target" not in st.session_state:
    st.session_state._draft_target = None

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.header("Status")
    if st.button("Check API"):
        try:
            res = healthz()
            st.success(f"API: {res['status']}")
        except Exception as e:
            st.error(f"API error: {e}")

    st.markdown("---")
    st.header("Hints (optional)")
    hint_company = st.text_input("회사(Hint)", value="")
    hint_job = st.text_input("직무(Hint)", value="")
    hint_year = st.number_input(
        "연도(Hint)", min_value=2000, max_value=2100, value=2025, step=1
    )
    st.caption("힌트는 프리뷰 분류가 애매할 때 도움이 됩니다.")

# -----------------------------
# Tabs
# -----------------------------
tabs = st.tabs(["🔼 업로드", "🔎 검색/추천"])
# 필요 시 초안 탭 활성화:
# tabs = st.tabs(["🔼 업로드", "🔎 검색/추천", "📝 초안 생성"])

# =========================================================
# Tab 0: 업로드 (파일 업로드 → 프리뷰/커밋, 그리고 문항 텍스트 업로드)
# =========================================================
with tabs[0]:
    # -----------------------------
    # A. 파일 업로드 (Preview → Commit)
    # -----------------------------
    st.subheader("📄 1) 파일 업로드 (Preview → Commit)")

    uploaded = st.file_uploader("Markdown 파일을 업로드하세요 (.md)", type=["md"])
    colA, colB = st.columns([1, 1])

    def run_preview(temp_path: str):
        res = preview_md(
            temp_path,
            hint_company=hint_company or None,
            hint_job=hint_job or None,
            hint_year=hint_year or None,
        )
        st.session_state.preview = res
        # commit 시 필요하므로 업로드 원문 저장
        st.session_state.raw_text = open(temp_path, "r", encoding="utf-8").read()
        st.session_state.file_name = os.path.basename(temp_path)

    with colA:
        if st.button("🔍 프리뷰 실행", disabled=(uploaded is None)):
            if uploaded is None:
                st.warning("먼저 파일을 업로드하세요.")
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as tmp:
                    tmp.write(uploaded.getvalue())
                    tmp.flush()
                    run_preview(tmp.name)
                st.success("프리뷰 완료!")

    with colB:
        if st.button("프리뷰 초기화"):
            st.session_state.preview = None
            st.session_state.raw_text = None
            st.session_state.file_name = None

    # Preview & Edit
    if st.session_state.preview:
        prev = st.session_state.preview
        st.markdown("---")
        st.subheader("2) 프리뷰 결과 확인 / 수정")

        # Document info
        dc = prev["document"]
        st.markdown(
            f"**파일명**: `{dc['filename']}`  |  **문서 중복**: `{dc['duplicate']}`"
        )
        st.caption(f"content_hash: `{dc['content_hash']}`")

        # Meta edit
        meta = prev["meta"]
        st.markdown("**메타 수정**")
        meta_company = st.text_input("회사", value=meta.get("company") or "")
        meta_job = st.text_input("직무", value=meta.get("job") or "")
        meta_year = st.number_input(
            "연도", min_value=0, max_value=9999, value=meta.get("year") or 0, step=1
        )

        st.markdown("**문항 리스트**")
        edited_questions = []
        for idx, q in enumerate(prev.get("questions", []), start=1):
            with st.expander(f"{idx}. {q['title']}  |  duplicate: {q['duplicate']}"):
                include = st.checkbox(
                    "저장 대상 포함", value=True, key=f"include_{idx}"
                )
                title = st.text_input(
                    "제목", value=q.get("title", ""), key=f"title_{idx}"
                )
                question = st.text_area(
                    "질문",
                    value=q.get("question", ""),
                    height=120,
                    key=f"question_{idx}",
                )
                answer = st.text_area(
                    "답변", value=q.get("answer", ""), height=160, key=f"answer_{idx}"
                )
                st.caption(
                    f"hash_prefix: `{q.get('hash_prefix')}`  | exists_question_id: `{q.get('exists_question_id')}`"
                )
                edited_questions.append(
                    {
                        "title": title,
                        "question": question,
                        "answer": answer,
                        "hash_prefix": q.get("hash_prefix"),
                        "include": include,
                    }
                )

        st.divider()
        if st.button("✅ 저장(Commit) 실행"):
            if not st.session_state.raw_text:
                st.error("원본 raw_text가 없습니다. 프리뷰를 다시 실행해주세요.")
            else:
                payload = {
                    "document": {
                        "filename": st.session_state.file_name or dc["filename"],
                        "content_hash": dc["content_hash"],
                        "raw_text": st.session_state.raw_text,  # 최초 저장이면 필요
                    },
                    "meta": {
                        "company": meta_company or "Unknown Company",
                        "job": meta_job or "Unknown Job",
                        "year": int(meta_year) if meta_year else None,
                    },
                    "questions": edited_questions,
                }
                try:
                    with st.spinner("저장 중..."):
                        res = commit_md(payload)
                    st.success("저장 완료!")
                    st.json(res)
                except Exception as e:
                    st.error(f"커밋 실패: {e}")

    # -----------------------------
    # B. (선택) 문항/답변 텍스트 직접 업로드 & 임베딩
    # -----------------------------
    st.markdown("---")
    st.subheader("📝 3) 문항/답변 텍스트 업로드 (선택)")

    company = st.text_input("회사명 (선택)", value="", key="text_company")
    job = st.text_input("직무명 (선택)", value="", key="text_job")
    colTA, colTB = st.columns(2)
    with colTA:
        title = st.text_input("문항/답변 제목 (선택)", value="", key="text_title")
    with colTB:
        year = st.number_input(
            "연도 (선택)",
            min_value=1990,
            max_value=2100,
            value=2025,
            step=1,
            key="text_year",
        )

    content = st.text_area(
        "문항/답변 원문 (필수)",
        height=240,
        placeholder="자기소개서 문항/답변 텍스트를 붙여넣으세요.",
        key="text_content",
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

# =========================================================
# Tab 1: 검색
# =========================================================
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
                    st.write(f"QID: {h['question_id']}")
                # 초안 기능이 필요할 때 주석 해제
                # with cols[1]:
                #     st.button(
                #         "초안 생성",
                #         key=f"draft_btn_{i}",
                #         on_click=lambda qid=h["question_id"]: st.session_state.update({"_draft_target": qid}),
                #     )

# =========================================================
# (선택) Tab 2: 초안 생성 – 필요 시 활성화
# =========================================================
# with tabs[2]:
#     st.subheader("초안 생성")
#     target_qid = st.session_state.get("_draft_target")
#     if target_qid:
#         st.info(f"선택된 question_id = {target_qid}")
#     else:
#         st.caption("검색 탭에서 결과의 [초안 생성] 버튼을 눌러주세요.")
#
#     top_k_for_draft = st.number_input("참조할 청크 수 (top_k)", min_value=1, max_value=10, value=1, step=1)
#     if st.button("초안 만들기", disabled=not bool(target_qid)):
#         with st.spinner("초안 생성 중..."):
#             try:
#                 res = draft(target_qid, top_k=int(top_k_for_draft))
#                 st.text_area("자동 생성된 초안", value=res["draft"], height=220)
#                 st.success(f"model: {res['model']}")
#             except Exception as e:
#                 st.error(f"초안 생성 실패: {e}")
