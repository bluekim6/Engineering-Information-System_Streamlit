"""통합 검색 페이지.

TagNo / Description / PackageName / DocNo / DrawingNo 의 다중 조건을 AND 로
조합 검색한다. 결과 행의 TagNo 를 클릭하면 Tag Detail 페이지로 이동한다.

검색 동작
- TagNo / Description / DocNo / DrawingNo : 부분 일치 (대소문자 무시)
- PackageName : 드롭다운 선택 (전체 / 특정 Package)
- DocNo  : ``Document_master.xlsx`` 의 ``DocNo`` 부분 일치 → 매칭 TagNo 만 결과 포함
- DrawingNo : ``Drawing_master.xlsx`` 의 ``DrawingNo`` 부분 일치 + Equipment 의
              ``ReferenceDrawing`` 부분 일치 둘 다 인정
"""
import pandas as pd
import streamlit as st

from components.auth import require_permission
from components.sidebar import render_sidebar
from config import PAGE_SEARCH
from data.data_loader import load_document, load_drawing, load_equipment

require_permission(PAGE_SEARCH)

# session_state 키
KEY_SELECTED_TAG = "selected_tag_no"
KEY_TAG_DETAIL_STEP = "tag_detail_step"

# ── 헬퍼 ────────────────────────────────────────────────────────────────
def _ilike(series: pd.Series, query: str) -> pd.Series:
    """대소문자 무시 부분 일치 마스크. 빈 query 면 전체 True."""
    if not query:
        return pd.Series(True, index=series.index)
    return series.astype(str).str.contains(query, case=False, na=False, regex=False)


@st.cache_data(show_spinner=False)
def _package_options(equipment: pd.DataFrame) -> list[str]:
    """PackageName 선택 옵션을 정렬된 unique 리스트로 반환."""
    names = sorted({str(x).strip() for x in equipment["PackageName"].dropna() if str(x).strip()})
    return ["(전체)"] + names


def _filter_by_doc(equipment: pd.DataFrame, document: pd.DataFrame, query: str) -> pd.DataFrame:
    """DocNo 부분 일치 → 매칭된 Document 행의 TagNo 만 남긴다."""
    if not query:
        return equipment
    matched = document[_ilike(document["DocNo"], query)]
    valid_tags = set(matched["TagNo"].astype(str).str.strip())
    return equipment[equipment["TagNo"].astype(str).str.strip().isin(valid_tags)]


def _filter_by_drawing(equipment: pd.DataFrame, drawing: pd.DataFrame, query: str) -> pd.DataFrame:
    """DrawingNo 부분 일치: Drawing_master 매칭 TagNo + Equipment.ReferenceDrawing 매칭 둘 다 포함."""
    if not query:
        return equipment

    # 1) Drawing_master 측 매칭
    dm_matched = drawing[_ilike(drawing["DrawingNo"], query)]
    valid_tags = set(dm_matched["TagNo"].astype(str).str.strip())

    # 2) Equipment.ReferenceDrawing 측 매칭 (확장자 제거 후 비교)
    ref_clean = (
        equipment["ReferenceDrawing"]
        .astype(str)
        .str.replace(".pdf", "", regex=False)
        .str.strip()
    )
    ref_mask = _ilike(ref_clean, query)

    tag_mask = equipment["TagNo"].astype(str).str.strip().isin(valid_tags)
    return equipment[tag_mask | ref_mask]


def _execute_search(
    equipment: pd.DataFrame,
    document: pd.DataFrame,
    drawing: pd.DataFrame,
    *,
    tag_q: str,
    desc_q: str,
    package_pick: str,
    doc_q: str,
    drw_q: str,
) -> pd.DataFrame:
    """모든 조건을 AND 로 적용해 결과 DataFrame 반환."""
    df = equipment.copy()

    if tag_q:
        df = df[_ilike(df["TagNo"], tag_q)]
    if desc_q:
        df = df[_ilike(df["TagDescription"], desc_q)]
    if package_pick and package_pick != "(전체)":
        df = df[df["PackageName"].astype(str).str.strip() == package_pick]
    df = _filter_by_doc(df, document, doc_q)
    df = _filter_by_drawing(df, drawing, drw_q)

    return df.reset_index(drop=True)


def _go_to_tag_detail(tag_no: str) -> None:
    """선택된 TagNo 를 session_state 에 저장 후 Tag Detail 페이지로 이동."""
    st.session_state[KEY_SELECTED_TAG] = tag_no
    st.session_state[KEY_TAG_DETAIL_STEP] = "info"
    st.switch_page("pages/tag_detail.py")


# ── 페이지 본체 ──────────────────────────────────────────────────────────
render_sidebar()

st.title("🔍 Search")
st.caption("Tag / 문서 / 도면 통합 검색 (AND 조건 복합 검색)")

equipment = load_equipment()
document = load_document()
drawing = load_drawing()

# 검색 입력 폼
with st.form("search_form"):
    row1 = st.columns(3)
    tag_q = row1[0].text_input("TagNo (부분 일치)", value="")
    desc_q = row1[1].text_input("Equipment Name / Description (부분 일치)", value="")
    package_pick = row1[2].selectbox("PackageName", _package_options(equipment), index=0)

    row2 = st.columns([1, 1, 1])
    doc_q = row2[0].text_input("DocNo (Document_master 부분 일치)", value="")
    drw_q = row2[1].text_input("DrawingNo (Drawing_master 부분 일치)", value="")
    row2[2].markdown("&nbsp;", unsafe_allow_html=True)

    btn_cols = st.columns([1, 1, 5])
    submitted = btn_cols[0].form_submit_button("🔍 검색", type="primary", use_container_width=True)
    reset = btn_cols[1].form_submit_button("초기화", use_container_width=True)

if reset:
    st.rerun()

# 검색 수행 (검색 폼 제출 시점에만)
if submitted or any([tag_q, desc_q, doc_q, drw_q]) or package_pick != "(전체)":
    result = _execute_search(
        equipment, document, drawing,
        tag_q=tag_q, desc_q=desc_q, package_pick=package_pick,
        doc_q=doc_q, drw_q=drw_q,
    )

    st.markdown("---")
    st.markdown(f"### 📋 검색 결과 — 총 **{len(result):,}건**")

    if result.empty:
        st.info("검색 결과가 없습니다. 조건을 조정해 보세요.")
    else:
        # 표시용 컬럼만 추출
        view = result[["TagNo", "TagDescription", "PackageName", "SystemName"]].rename(
            columns={"TagDescription": "Description"}
        )

        # 헤더 + 행별 클릭 가능한 TagNo 버튼
        header = st.columns([1.2, 3, 1.5, 2])
        header[0].markdown("**TagNo**")
        header[1].markdown("**Description**")
        header[2].markdown("**PackageName**")
        header[3].markdown("**SystemName**")

        # 큰 결과셋 보호: 화면에 한꺼번에 그릴 행 수 제한
        MAX_ROWS = 200
        for idx, row in view.head(MAX_ROWS).iterrows():
            cols = st.columns([1.2, 3, 1.5, 2])
            if cols[0].button(f"`{row['TagNo']}`", key=f"go_tag_{idx}", use_container_width=True):
                _go_to_tag_detail(row["TagNo"])
            cols[1].markdown(str(row["Description"] or "-"))
            cols[2].markdown(str(row["PackageName"] or "-"))
            cols[3].markdown(str(row["SystemName"] or "-"))

        if len(view) > MAX_ROWS:
            st.caption(
                f"⚠️ 결과 {len(view):,}건 중 상위 {MAX_ROWS}건만 표시했습니다. 검색 조건을 더 좁혀 주세요."
            )
else:
    st.info("👆 위 검색 조건을 입력하고 [🔍 검색] 버튼을 누르세요.")
