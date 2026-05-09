"""통합 계층구조 화면 (UI_SAMPLE 기반).

- 좌측 패널: System / Package / Tag 단일 트리 (▶/▼ 토글, 카운트 표시)
- 중앙 패널: 선택된 Tag 상세 정보 (미선택 시 placeholder)
- 우측 패널: 선택된 Tag 의 관련 문서/도면 (미선택 시 placeholder)

세션 상태 키:
- ``selected_tag_no``      : 현재 선택된 Tag (트리 클릭으로 갱신)
- ``exp_systems``          : set[str] 펼쳐진 SystemID 집합
- ``exp_packages``         : set[str] 펼쳐진 PackageID 집합

Tag 우측 도면 카드의 ``📄 DrawingNo`` 버튼을 누르면 ``tag_detail.py`` 의 PDF
뷰어 단계(STEP_VIEWER)로 컨텍스트와 함께 이동한다.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components.auth import require_permission
from components.manufacture_popup import show_manufacture_popup
from components.tree_styles import inject_tree_css
from config import APP_TITLE, PAGE_HIERARCHY
from data.data_loader import (
  get_document_meta,
  get_tag_register_row,
  load_drawing,
  load_equipment,
)

require_permission(PAGE_HIERARCHY)

# ── session_state 키 ─────────────────────────────────────────────────────
KEY_SELECTED_TAG = "selected_tag_no"
KEY_EXP_SYSTEMS = "exp_systems"
KEY_EXP_PACKAGES = "exp_packages"
KEY_SEARCH = "tree_search_query"

# Tag_Register 에서 별도 표시되는 컬럼 (그리드 중복 제외)
_SPECIAL_COLS = {"Tag", "Description", "Manufacture Name"}
_INFO_GRID_COLS = 3


def _init_state() -> None:
  """세션 키 기본값 보장."""
  st.session_state.setdefault(KEY_SELECTED_TAG, None)
  st.session_state.setdefault(KEY_EXP_SYSTEMS, set())
  st.session_state.setdefault(KEY_EXP_PACKAGES, set())
  st.session_state.setdefault(KEY_SEARCH, "")


def _fmt(value) -> str:
  """그리드 셀 값 포맷. None/NaN/공백은 '-' 로 통일."""
  if value is None:
    return "-"
  try:
    if pd.isna(value):
      return "-"
  except (TypeError, ValueError):
    pass
  s = str(value).strip()
  return s if s else "-"


@st.cache_data(show_spinner=False)
def _summarize(df: pd.DataFrame) -> dict:
  """System/Package 단위 카운트와 Tag 원본을 묶어 반환한다."""
  systems = (
    df.groupby(["SystemID", "SystemName"], as_index=False)
    .agg(PackageCount=("PackageID", "nunique"), TagCount=("TagNo", "nunique"))
    .sort_values("SystemName")
  )
  packages = (
    df.groupby(["SystemID", "PackageID", "PackageName"], as_index=False)
    .agg(TagCount=("TagNo", "nunique"))
    .sort_values(["SystemID", "PackageName"])
  )
  return {"systems": systems, "packages": packages, "tags": df}


def _toggle_in_set(state_key: str, value) -> None:
  """session_state[state_key] 의 set 안에 value 토글."""
  bag: set = st.session_state[state_key]
  if value in bag:
    bag.remove(value)
  else:
    bag.add(value)


# ── 상단 다크 헤더 ───────────────────────────────────────────────────────
def _render_top_bar() -> None:
  """샘플 이미지의 다크 상단 바 (제목 + 검색 + 역할)."""
  user_role = st.session_state.get("user_role", "-")
  st.markdown(
    f"""
    <div class="eis-topbar">
      <div class="eis-topbar-title">{APP_TITLE}</div>
      <div class="eis-topbar-spacer"></div>
      <div class="eis-topbar-role">역할 <b>{user_role}</b></div>
    </div>
    """,
    unsafe_allow_html=True,
  )
  # 검색 입력은 별도 Streamlit 위젯으로 (실제 동작 위해)
  st.text_input(
    "검색",
    key=KEY_SEARCH,
    placeholder="Tag / System / Package / Document 검색",
    label_visibility="collapsed",
  )


# ── 좌측 트리 ────────────────────────────────────────────────────────────
def _filter_match(text: str, q: str) -> bool:
  """대소문자 무시 부분 일치."""
  if not q:
    return True
  return q.lower() in str(text).lower()


def _render_tree(summary: dict) -> None:
  """좌측 SYSTEM / PACKAGE / TAG 트리 렌더링.

  검색어가 있으면 Tag 까지 자동 펼침으로 매칭만 노출.
  """
  st.markdown(
    '<div class="tree-section-title">SYSTEM / PACKAGE / TAG</div>',
    unsafe_allow_html=True,
  )

  systems = summary["systems"]
  packages = summary["packages"]
  tags = summary["tags"]

  exp_sys: set = st.session_state[KEY_EXP_SYSTEMS]
  exp_pkg: set = st.session_state[KEY_EXP_PACKAGES]
  selected_tag = st.session_state.get(KEY_SELECTED_TAG)
  query = (st.session_state.get(KEY_SEARCH) or "").strip()

  # 검색어가 있으면 매칭된 System/Package 만 펼친 채로 표시
  matched_systems: set = set()
  matched_packages: set = set()
  matched_tags: set = set()
  if query:
    matched_tags = set(
      tags.loc[
        tags["TagNo"].astype(str).str.lower().str.contains(query.lower(), na=False)
        | tags["TagDescription"].astype(str).str.lower().str.contains(query.lower(), na=False)
      ]["TagNo"].astype(str)
    )
    matched_packages = set(
      packages.loc[
        packages["PackageName"].astype(str).str.lower().str.contains(query.lower(), na=False)
        | packages["PackageID"].astype(str).str.lower().str.contains(query.lower(), na=False)
      ]["PackageID"].astype(str)
    )
    matched_systems = set(
      systems.loc[
        systems["SystemName"].astype(str).str.lower().str.contains(query.lower(), na=False)
      ]["SystemID"].astype(str)
    )
    # Tag/Package 매칭의 상위 SystemID/PackageID 도 노출
    matched_packages |= set(
      tags.loc[tags["TagNo"].astype(str).isin(matched_tags)]["PackageID"].astype(str)
    )
    matched_systems |= set(
      packages.loc[packages["PackageID"].astype(str).isin(matched_packages)]["SystemID"].astype(str)
    )

  scroll = st.container(height=720, border=False)
  with scroll:
    for _, sys_row in systems.iterrows():
      sys_id = str(sys_row["SystemID"])
      sys_name = str(sys_row["SystemName"])
      sys_count = int(sys_row["TagCount"])

      if query and sys_id not in matched_systems:
        continue

      is_exp = (sys_id in exp_sys) or bool(query and sys_id in matched_systems)
      chevron = "▼" if is_exp else "▶"

      c_btn, c_cnt = st.columns([6, 1])
      with c_btn:
        if st.button(
          f"{chevron}  {sys_name}",
          key=f"tree_sys_{sys_id}",
          use_container_width=True,
        ):
          _toggle_in_set(KEY_EXP_SYSTEMS, sys_id)
          st.rerun()
      with c_cnt:
        st.markdown(
          f'<div class="tree-count">{sys_count}</div>',
          unsafe_allow_html=True,
        )

      if not is_exp:
        continue

      sub_pkgs = packages.loc[packages["SystemID"] == sys_id]
      for _, pkg_row in sub_pkgs.iterrows():
        pkg_id = str(pkg_row["PackageID"])
        pkg_name = str(pkg_row["PackageName"])
        pkg_count = int(pkg_row["TagCount"])

        if query and pkg_id not in matched_packages:
          continue

        is_pkg_exp = (pkg_id in exp_pkg) or bool(query and pkg_id in matched_packages)
        pkg_chevron = "▼" if is_pkg_exp else "▶"

        c_btn, c_cnt = st.columns([6, 1])
        with c_btn:
          if st.button(
            f"    {pkg_chevron}  {pkg_name}",
            key=f"tree_pkg_{pkg_id}",
            use_container_width=True,
          ):
            _toggle_in_set(KEY_EXP_PACKAGES, pkg_id)
            st.rerun()
        with c_cnt:
          st.markdown(
            f'<div class="tree-count">{pkg_count}</div>',
            unsafe_allow_html=True,
          )

        if not is_pkg_exp:
          continue

        sub_tags = tags.loc[tags["PackageID"] == pkg_id].sort_values("TagNo")
        for _, tag_row in sub_tags.iterrows():
          tag_no = str(tag_row["TagNo"])
          if query and matched_tags and tag_no not in matched_tags:
            continue
          is_sel = tag_no == selected_tag
          marker = "●" if is_sel else "·"
          if st.button(
            f"        {marker}  {tag_no}",
            key=f"tree_tag_{tag_no}",
            use_container_width=True,
            type="primary" if is_sel else "secondary",
          ):
            st.session_state[KEY_SELECTED_TAG] = tag_no
            st.rerun()


# ── 중앙 Tag 상세 ────────────────────────────────────────────────────────
def _render_center(equipment: pd.DataFrame) -> None:
  """선택된 Tag 의 상세 정보 카드 + Tag_Register 모든 컬럼 그리드."""
  selected_tag = st.session_state.get(KEY_SELECTED_TAG)
  if not selected_tag:
    st.markdown(
      '<div class="eis-placeholder">왼쪽 트리에서 Tag 를 선택하면 상세 정보가 여기에 표시됩니다.</div>',
      unsafe_allow_html=True,
    )
    return

  matched = equipment[equipment["TagNo"].astype(str).str.strip() == str(selected_tag).strip()]
  if matched.empty:
    st.error(f"Equipment 에서 TagNo='{selected_tag}' 를 찾을 수 없습니다.")
    return
  tag_row = matched.iloc[0]

  reg_row = get_tag_register_row(selected_tag)
  using_register = reg_row is not None

  description = (
    _fmt(reg_row.get("Description")) if using_register
    else _fmt(tag_row.get("TagDescription"))
  )

  st.markdown(f"### 🏷️ {selected_tag}")
  st.caption(description if description != "-" else "(설명 없음)")
  if not using_register:
    st.warning("Tag_Register.xlsx 미등록 — Equipment_master 기준으로 표시")
  st.markdown("---")

  # Manufacture Name (특수: 클릭 시 팝업)
  mfg_raw = (
    reg_row.get("Manufacture Name") if using_register
    else tag_row.get("ManufactureName")
  )
  mfg = "" if mfg_raw is None or (isinstance(mfg_raw, float) and pd.isna(mfg_raw)) else str(mfg_raw).strip()

  mc1, mc2 = st.columns([1, 3])
  with mc1:
    st.markdown("**Manufacture Name**")
  with mc2:
    if mfg:
      if st.button(f"🏭 {mfg}", key=f"mfg_btn_{selected_tag}", help="제조사 상세 보기"):
        show_manufacture_popup(mfg)
    else:
      st.markdown("-")

  st.markdown("---")

  # 정보 그리드
  if using_register:
    cols = [c for c in reg_row.index if c not in _SPECIAL_COLS]
    src = reg_row
  else:
    cols = [c for c in tag_row.index if c not in {"TagNo", "TagDescription", "ManufactureName"}]
    src = tag_row

  if not cols:
    st.info("표시할 추가 컬럼이 없습니다.")
    return

  for i in range(0, len(cols), _INFO_GRID_COLS):
    chunk = cols[i:i + _INFO_GRID_COLS]
    grid = st.columns(_INFO_GRID_COLS)
    for j, name in enumerate(chunk):
      with grid[j]:
        st.markdown(f"**{name}**")
        st.markdown(_fmt(src.get(name)))


# ── 우측 관련 도면 ───────────────────────────────────────────────────────
def _render_right(equipment: pd.DataFrame, drawing: pd.DataFrame) -> None:
  """선택된 Tag 의 관련 도면 카드 목록."""
  st.markdown(
    '<div class="panel-title">관련 문서 / 도면</div>',
    unsafe_allow_html=True,
  )

  selected_tag = st.session_state.get(KEY_SELECTED_TAG)
  if not selected_tag:
    st.markdown(
      '<div class="eis-placeholder">Tag 를 선택하면 표시됩니다.</div>',
      unsafe_allow_html=True,
    )
    return

  tag_no = str(selected_tag).strip()
  drawings = drawing[drawing["TagNo"].astype(str).str.strip() == tag_no].copy()

  # 폴백: Drawing_master 미등록 시 Equipment.ReferenceDrawing 사용
  if drawings.empty:
    eq_match = equipment[equipment["TagNo"].astype(str).str.strip() == tag_no]
    if not eq_match.empty:
      ref = str(eq_match.iloc[0].get("ReferenceDrawing") or "").strip().replace(".pdf", "")
      if ref:
        drawings = pd.DataFrame([{
          "DrawingNo": ref,
          "DrawingTitle": "(Equipment 참조 도면)",
          "TagNo": tag_no,
          "Revision": "-",
          "FilePath": f"drawings/{ref}.pdf",
        }])

  if drawings.empty:
    st.info("관련 도면 없음")
    return

  # Document_List 정본으로 Title/Revision 덮어쓰기
  drawings = drawings.reset_index(drop=True)
  for idx, row in drawings.iterrows():
    title, rev = get_document_meta(row.get("DrawingNo"))
    if title is not None:
      drawings.at[idx, "DrawingTitle"] = title
    if rev is not None:
      drawings.at[idx, "Revision"] = rev

  st.caption(f"총 {len(drawings)}건")
  for idx, row in drawings.iterrows():
    drw_no = str(row["DrawingNo"])
    drw_title = _fmt(row.get("DrawingTitle"))
    rev = _fmt(row.get("Revision"))
    with st.container(border=True):
      if st.button(
        f"📄 {drw_no}",
        key=f"open_drw_{tag_no}_{idx}",
        use_container_width=True,
        help="도면 PDF 열람",
      ):
        st.session_state["selected_tag_no"] = tag_no
        st.session_state["selected_drawing_no"] = drw_no
        st.session_state["tag_detail_step"] = "viewer"
        st.switch_page("pages/tag_detail.py")
      st.markdown(
        f'<div class="drw-meta-title">{drw_title}</div>',
        unsafe_allow_html=True,
      )
      st.markdown(
        f'<div class="drw-meta-rev">Rev. {rev}</div>',
        unsafe_allow_html=True,
      )


# ── 페이지 본체 ──────────────────────────────────────────────────────────
inject_tree_css()
_init_state()
_render_top_bar()

equipment = load_equipment()
drawing = load_drawing()
summary = _summarize(equipment)

# 3 패널 (좌 트리 / 중앙 상세 / 우 도면)
col_tree, col_center, col_right = st.columns([1.4, 3.0, 1.5], gap="medium")

with col_tree:
  _render_tree(summary)

with col_center:
  _render_center(equipment)

with col_right:
  _render_right(equipment, drawing)
