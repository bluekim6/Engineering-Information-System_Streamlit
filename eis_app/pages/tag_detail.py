"""Tag 상세 + 도면 연동 페이지 (PRD 시나리오 D).

세 단계의 화면 흐름을 ``st.session_state['tag_detail_step']`` 으로 라우팅한다.

- ``info``     : Step 1 — Tag 정보 카드 + [관련 도면 보기] + 제조사 팝업
- ``drawings`` : Step 2 — 해당 Tag 와 연결된 도면 목록
- ``viewer``   : Step 3 — 선택된 도면의 PDF 뷰어 + 같은 도면을 공유하는 다른 Tag 목록
                          (Tag 클릭 시 Step 1 로 복귀)

데이터 소스
- Equipment_master.xlsx : Tag 본 정보
- Drawing_master.xlsx   : Tag↔Drawing 매핑
- Manufacture_list.xlsx : 제조사 상세 (팝업)

Drawing_master 에 해당 TagNo 가 등록되지 않은 경우, Equipment 의 ``ReferenceDrawing``
값을 폴백으로 사용해 단일 도면 행을 합성한다 (실제 PDF 파일은 ``drawings/{No}.pdf``).
"""
from pathlib import Path

import pandas as pd
import streamlit as st

from components.auth import require_permission
from components.manufacture_popup import show_manufacture_popup
from components.pdf_viewer import render_pdf
from components.sidebar import render_sidebar
from config import DRAWINGS_DIR, PAGE_TAG_DETAIL, ROLES_CAN_EDIT_TAG
from data.data_loader import (
    ExcelSaveError,
    get_document_meta,
    get_tag_register_row,
    load_drawing,
    load_equipment,
    log_change,
    save_equipment,
)

# Tag_Register 컬럼 중 별도 위치에서 렌더되어 그리드에서 제외되는 항목
_SPECIAL_RENDERED_COLS = {"Tag", "Description", "Manufacture Name"}
# 정보 그리드 열 수 (3열 = 42개 컬럼 기준 14행)
_INFO_GRID_COLS = 3

require_permission(PAGE_TAG_DETAIL)

# ── session_state 키 상수 ────────────────────────────────────────────────
KEY_SELECTED_TAG = "selected_tag_no"
KEY_STEP = "tag_detail_step"
KEY_SELECTED_DRAWING = "selected_drawing_no"

STEP_INFO = "info"
STEP_DRAWINGS = "drawings"
STEP_VIEWER = "viewer"


# ── 데이터 헬퍼 ──────────────────────────────────────────────────────────
def _get_tag_row(equipment: pd.DataFrame, tag_no: str) -> pd.Series | None:
    """선택된 TagNo 의 Equipment 행을 반환. 없으면 None."""
    matched = equipment[equipment["TagNo"].astype(str).str.strip() == str(tag_no).strip()]
    return None if matched.empty else matched.iloc[0]


def _apply_document_list_meta(df: pd.DataFrame) -> pd.DataFrame:
    """Document_List.xlsx 의 Document Name/Revision 으로 DrawingTitle/Revision 을 덮어쓴다.

    - DrawingNo == Document Number 매칭
    - 매칭 실패 시 기존 값 유지
    - Document_List 가 정본이므로 일치할 때는 항상 우선
    """
    if df.empty:
        return df
    out = df.copy()
    for idx, row in out.iterrows():
        title, rev = get_document_meta(row.get("DrawingNo"))
        if title is not None:
            out.at[idx, "DrawingTitle"] = title
        if rev is not None:
            out.at[idx, "Revision"] = rev
    return out


def _get_drawings_for_tag(drawing: pd.DataFrame, tag_row: pd.Series) -> pd.DataFrame:
    """TagNo 로 Drawing_master 를 조회. 없으면 ReferenceDrawing 으로 폴백 행 합성.

    DrawingTitle/Revision 은 Document_List.xlsx 를 정본으로 덮어쓴다.
    """
    tag_no = str(tag_row["TagNo"]).strip()
    matched = drawing[drawing["TagNo"].astype(str).str.strip() == tag_no].copy()
    if not matched.empty:
        return _apply_document_list_meta(matched.reset_index(drop=True))

    # 폴백: Equipment.ReferenceDrawing 컬럼에서 도면번호 추정
    ref = str(tag_row.get("ReferenceDrawing") or "").strip()
    if not ref:
        return pd.DataFrame(columns=drawing.columns)

    drawing_no = ref.replace(".pdf", "")
    fallback = pd.DataFrame([{
        "DrawingNo": drawing_no,
        "DrawingTitle": "(Drawing master 미등록 — Equipment 참조 도면)",
        "TagNo": tag_no,
        "Revision": "-",
        "FilePath": f"drawings/{drawing_no}.pdf",
    }])
    return _apply_document_list_meta(fallback)


def _get_tags_sharing_drawing(drawing: pd.DataFrame, equipment: pd.DataFrame, drawing_no: str) -> pd.DataFrame:
    """동일 DrawingNo 를 공유하는 모든 Tag 목록을 반환.

    Drawing_master 우선, 없으면 Equipment.ReferenceDrawing 으로도 검색하여
    폴백 매칭을 보강한다.
    """
    no = str(drawing_no).strip()
    rows: list[dict] = []

    # 1) Drawing_master 매핑
    dm = drawing[drawing["DrawingNo"].astype(str).str.strip() == no]
    for _, r in dm.iterrows():
        rows.append({"TagNo": str(r["TagNo"]).strip(), "Source": "Drawing master"})

    # 2) Equipment.ReferenceDrawing 폴백 매핑
    em = equipment[
        equipment["ReferenceDrawing"].astype(str).str.replace(".pdf", "", regex=False).str.strip() == no
    ]
    for _, r in em.iterrows():
        tag_no = str(r["TagNo"]).strip()
        if not any(x["TagNo"] == tag_no for x in rows):
            rows.append({"TagNo": tag_no, "Source": "Equipment ref."})

    if not rows:
        return pd.DataFrame(columns=["TagNo", "TagDescription", "Source"])

    result = pd.DataFrame(rows)
    # TagDescription 보강
    desc_map = dict(zip(equipment["TagNo"].astype(str).str.strip(), equipment["TagDescription"]))
    result["TagDescription"] = result["TagNo"].map(desc_map).fillna("-")
    return result[["TagNo", "TagDescription", "Source"]].reset_index(drop=True)


def _resolve_pdf_path(drawing_row: pd.Series) -> Path:
    """Drawing 행에서 실제 PDF 파일 경로를 결정한다."""
    file_path = str(drawing_row.get("FilePath") or "").strip()
    if file_path:
        p = Path(file_path)
        if not p.is_absolute():
            # FilePath 가 'drawings/xxx.pdf' 같은 상대 경로면 프로젝트 루트 기준
            p = DRAWINGS_DIR.parent / file_path
        if p.exists():
            return p
    # 폴백: drawings/{DrawingNo}.pdf
    return DRAWINGS_DIR / f"{str(drawing_row['DrawingNo']).strip()}.pdf"


# ── 단계별 렌더 함수 ─────────────────────────────────────────────────────
def _format_cell_value(value) -> str:
    """그리드 셀에 표시할 값 포맷. NaN/빈문자열은 '-' 로 통일."""
    if value is None:
        return "-"
    try:
        if pd.isna(value):
            return "-"
    except (TypeError, ValueError):
        pass
    s = str(value).strip()
    return s if s else "-"


def _render_info_grid(reg_row: pd.Series) -> None:
    """Tag_Register 모든 컬럼을 N열 그리드로 표시 (특수 처리 컬럼은 제외)."""
    cols = [c for c in reg_row.index if c not in _SPECIAL_RENDERED_COLS]
    if not cols:
        st.info("표시할 추가 컬럼이 없습니다.")
        return

    # N개씩 묶어 한 행씩 렌더
    for i in range(0, len(cols), _INFO_GRID_COLS):
        chunk = cols[i : i + _INFO_GRID_COLS]
        widgets = st.columns(_INFO_GRID_COLS)
        for j, name in enumerate(chunk):
            with widgets[j]:
                st.markdown(f"**{name}**")
                st.markdown(_format_cell_value(reg_row.get(name)))


def _render_step_info(equipment: pd.DataFrame, tag_row: pd.Series) -> None:
    """Step 1 — Tag 정보 카드 (Tag_Register 전체 컬럼) + 관련 도면 보기 버튼."""
    tag_no = str(tag_row["TagNo"]).strip()

    # Tag_Register 에서 풀 컬럼 행 조회 (없으면 Equipment 행으로 폴백)
    reg_row = get_tag_register_row(tag_no)
    using_register = reg_row is not None

    # 헤더 (Description 은 Tag_Register 우선, 없으면 Equipment.TagDescription)
    description = (
        _format_cell_value(reg_row.get("Description")) if using_register
        else _format_cell_value(tag_row.get("TagDescription"))
    )
    st.markdown(f"### 🏷️ {tag_no}")
    st.caption(description if description != "-" else "(설명 없음)")
    if not using_register:
        st.warning(
            "Tag_Register.xlsx 에서 해당 Tag 를 찾지 못해 Equipment_master 기준으로 표시합니다."
        )
    st.markdown("---")

    # Manufacture Name — 팝업 버튼 (특수 위젯이라 그리드 밖에서 별도 렌더)
    mfg_col_l, mfg_col_r = st.columns([1, 3])
    with mfg_col_l:
        st.markdown("**Manufacture Name**")
    with mfg_col_r:
        mfg_raw = (
            reg_row.get("Manufacture Name") if using_register
            else tag_row.get("ManufactureName")
        )
        mfg = "" if mfg_raw is None or (isinstance(mfg_raw, float) and pd.isna(mfg_raw)) else str(mfg_raw).strip()
        if mfg:
            if st.button(f"🏭 {mfg}", key="mfg_popup_btn", help="클릭하여 제조사 상세정보 보기"):
                show_manufacture_popup(mfg)
        else:
            st.markdown("-")

    st.markdown("---")

    # 정보 그리드 (Tag_Register 전체 컬럼 — 특수 처리된 항목 제외)
    if using_register:
        _render_info_grid(reg_row)
    else:
        # Equipment_master 폴백 — 보유 컬럼만 그리드로 표시
        eq_cols_to_show = [
            c for c in tag_row.index
            if c not in {"TagNo", "TagDescription", "ManufactureName"}
        ]
        for i in range(0, len(eq_cols_to_show), _INFO_GRID_COLS):
            chunk = eq_cols_to_show[i : i + _INFO_GRID_COLS]
            widgets = st.columns(_INFO_GRID_COLS)
            for j, name in enumerate(chunk):
                with widgets[j]:
                    st.markdown(f"**{name}**")
                    st.markdown(_format_cell_value(tag_row.get(name)))

    st.markdown("---")

    if st.button("📐 관련 도면 보기 →", type="primary", use_container_width=True):
        st.session_state[KEY_STEP] = STEP_DRAWINGS
        st.rerun()

    # Tag 정보 편집 (설계엔지니어 / 문서관리자만 — 변경 시 History 자동 기록)
    # 편집은 Equipment_master 기준 컬럼(TagDescription/ManufactureName/AttributeA/B)만 대상.
    user_role = st.session_state.get("user_role")
    if user_role in ROLES_CAN_EDIT_TAG:
        with st.expander("✏️ Tag 정보 편집 (변경 시 History 자동 기록)"):
            _render_edit_form(tag_row)
    else:
        st.caption(f"_편집 권한 없음 — 현재 역할: {user_role}_")


def _render_edit_form(tag_row: pd.Series) -> None:
    """Tag 일부 필드 편집 폼. 변경 시 Equipment_master 갱신 + History 기록."""
    editable_fields = ["TagDescription", "ManufactureName", "AttributeA", "AttributeB"]
    user_name = st.session_state.get("user_name", "unknown")

    with st.form(f"edit_tag_{tag_row['TagNo']}"):
        new_values: dict[str, str] = {}
        for field in editable_fields:
            current = "" if pd.isna(tag_row.get(field)) else str(tag_row.get(field))
            new_values[field] = st.text_input(field, value=current, key=f"edit_{field}")

        submitted = st.form_submit_button("💾 변경 저장", type="primary", use_container_width=True)

    if not submitted:
        return

    # 변경 감지
    diffs: list[tuple[str, str, str]] = []
    for field in editable_fields:
        old_val = "" if pd.isna(tag_row.get(field)) else str(tag_row.get(field))
        new_val = new_values[field].strip()
        if old_val != new_val:
            diffs.append((field, old_val, new_val))

    if not diffs:
        st.info("변경된 항목이 없습니다.")
        return

    # Equipment 마스터 갱신
    eq = load_equipment().copy()
    mask = eq["TagNo"].astype(str).str.strip() == str(tag_row["TagNo"]).strip()
    if not mask.any():
        st.error(f"Equipment 마스터에서 TagNo='{tag_row['TagNo']}' 를 찾을 수 없습니다.")
        return

    for field, _, new_val in diffs:
        eq.loc[mask, field] = new_val

    try:
        save_equipment(eq)
    except ExcelSaveError as e:
        st.error(str(e))
        return

    # History 기록 (필드별 1행)
    for field, old_val, new_val in diffs:
        try:
            log_change(
                tag_no=str(tag_row["TagNo"]),
                field=field,
                old_val=old_val,
                new_val=new_val,
                user=user_name,
            )
        except ExcelSaveError as e:
            st.error(f"History 기록 실패: {e}")
            return

    st.success(f"{len(diffs)}개 필드 변경 저장 + History 기록 완료")
    st.rerun()


def _render_step_drawings(equipment: pd.DataFrame, drawing: pd.DataFrame, tag_row: pd.Series) -> None:
    """Step 2 — Tag 에 연결된 도면 목록."""
    st.markdown(f"### 📐 도면 목록 — {tag_row['TagNo']}")
    st.caption(f"{tag_row.get('TagDescription') or ''}")

    if st.button("← Tag 정보로 돌아가기", key="back_to_info"):
        st.session_state[KEY_STEP] = STEP_INFO
        st.rerun()

    st.markdown("---")

    drawings = _get_drawings_for_tag(drawing, tag_row)
    if drawings.empty:
        st.warning("이 Tag 에 연결된 도면이 없습니다.")
        return

    st.caption(f"총 {len(drawings)}건")

    # 헤더
    header = st.columns([2, 4, 1, 1])
    header[0].markdown("**DrawingNo**")
    header[1].markdown("**DrawingTitle**")
    header[2].markdown("**Revision**")
    header[3].markdown("**열람**")

    for idx, row in drawings.iterrows():
        cols = st.columns([2, 4, 1, 1])
        # DrawingNo 자체도 클릭 가능 (요구사항: '도면 No 클릭 시 Step 3 으로 전환')
        if cols[0].button(f"`{row['DrawingNo']}`", key=f"drw_no_{idx}", use_container_width=True):
            st.session_state[KEY_SELECTED_DRAWING] = row["DrawingNo"]
            st.session_state[KEY_STEP] = STEP_VIEWER
            st.rerun()
        cols[1].markdown(str(row.get("DrawingTitle") or "-"))
        cols[2].markdown(str(row.get("Revision") or "-"))
        if cols[3].button("📄 열람", key=f"drw_open_{idx}", use_container_width=True):
            st.session_state[KEY_SELECTED_DRAWING] = row["DrawingNo"]
            st.session_state[KEY_STEP] = STEP_VIEWER
            st.rerun()


def _render_step_viewer(equipment: pd.DataFrame, drawing: pd.DataFrame, tag_row: pd.Series) -> None:
    """Step 3 — PDF 뷰어 + 같은 도면을 공유하는 Tag 목록."""
    drawing_no = st.session_state.get(KEY_SELECTED_DRAWING)
    if not drawing_no:
        st.warning("선택된 도면이 없습니다. Step 2 로 돌아가 도면을 선택하세요.")
        if st.button("← 도면 목록으로"):
            st.session_state[KEY_STEP] = STEP_DRAWINGS
            st.rerun()
        return

    # 현재 Tag 컨텍스트의 도면 행에서 메타정보 가져오기 (없으면 Drawing_master 전역에서)
    drawings_for_tag = _get_drawings_for_tag(drawing, tag_row)
    matched = drawings_for_tag[drawings_for_tag["DrawingNo"].astype(str) == str(drawing_no)]
    if matched.empty:
        # Drawing_master 전체에서 검색 (폴백) — Document_List 메타로 덮어쓰기 적용
        matched = _apply_document_list_meta(
            drawing[drawing["DrawingNo"].astype(str) == str(drawing_no)].reset_index(drop=True)
        )
    drawing_row = (
        matched.iloc[0]
        if not matched.empty
        else pd.Series({"DrawingNo": drawing_no, "DrawingTitle": "-", "Revision": "-", "FilePath": ""})
    )

    # 상단 네비
    nav_l, nav_r = st.columns([1, 5])
    with nav_l:
        if st.button("← 도면 목록", key="back_to_drawings"):
            st.session_state[KEY_STEP] = STEP_DRAWINGS
            st.rerun()

    # 도면 메타
    st.markdown(f"### 📄 {drawing_row['DrawingNo']}")
    meta_cols = st.columns([3, 1])
    meta_cols[0].markdown(f"**제목**: {drawing_row.get('DrawingTitle') or '-'}")
    meta_cols[1].markdown(f"**Revision**: `{drawing_row.get('Revision') or '-'}`")
    st.markdown("---")

    # 본문: 좌측 PDF 뷰어 + 우측 연관 Tag 목록
    body_l, body_r = st.columns([3, 1.2])

    with body_l:
        pdf_path = _resolve_pdf_path(drawing_row)
        render_pdf(pdf_path, height=820, key=f"pdf_{drawing_row['DrawingNo']}")

    with body_r:
        st.markdown("#### 🔗 같은 도면의 다른 Tag")
        related = _get_tags_sharing_drawing(drawing, equipment, drawing_row["DrawingNo"])
        if related.empty:
            st.info("이 도면을 참조하는 다른 Tag 가 없습니다.")
        else:
            current = str(tag_row["TagNo"]).strip()
            st.caption(f"총 {len(related)}건 (현재 Tag 포함)")
            for idx, row in related.iterrows():
                tag_no = row["TagNo"]
                is_current = tag_no == current
                label = (
                    f"{'⭐ ' if is_current else ''}**{tag_no}**\n\n"
                    f"{row['TagDescription']}\n\n"
                    f"_{row['Source']}_"
                )
                if st.button(
                    label,
                    key=f"share_tag_{idx}",
                    use_container_width=True,
                    type="primary" if is_current else "secondary",
                    disabled=is_current,
                ):
                    # 다른 Tag 클릭 시 Step 1 로 복귀
                    st.session_state[KEY_SELECTED_TAG] = tag_no
                    st.session_state[KEY_STEP] = STEP_INFO
                    st.session_state[KEY_SELECTED_DRAWING] = None
                    st.rerun()


def _init_state() -> None:
    """페이지 진입 시 session_state 기본값 보장."""
    st.session_state.setdefault(KEY_SELECTED_TAG, None)
    st.session_state.setdefault(KEY_STEP, STEP_INFO)
    st.session_state.setdefault(KEY_SELECTED_DRAWING, None)


# ── 페이지 본체 ──────────────────────────────────────────────────────────
render_sidebar()
_init_state()

st.title("🏷️ Tag Detail")

selected_tag = st.session_state.get(KEY_SELECTED_TAG)
if not selected_tag:
    st.warning("선택된 Tag 가 없습니다. Hierarchy 페이지에서 Tag 를 먼저 선택하세요.")
    st.stop()

equipment = load_equipment()
drawing = load_drawing()
tag_row = _get_tag_row(equipment, selected_tag)
if tag_row is None:
    st.error(f"Equipment 마스터에서 TagNo='{selected_tag}' 를 찾을 수 없습니다.")
    st.stop()

# 단계 라우팅
step = st.session_state.get(KEY_STEP, STEP_INFO)
if step == STEP_INFO:
    _render_step_info(equipment, tag_row)
elif step == STEP_DRAWINGS:
    _render_step_drawings(equipment, drawing, tag_row)
elif step == STEP_VIEWER:
    _render_step_viewer(equipment, drawing, tag_row)
else:
    st.error(f"알 수 없는 단계: {step}")
    st.session_state[KEY_STEP] = STEP_INFO
    st.rerun()
