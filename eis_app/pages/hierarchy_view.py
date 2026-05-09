"""계층구조 탐색 페이지.

Equipment_master.xlsx 의 System → Package → Tag 계층을 3단 패널로 탐색한다.

- 좌측 패널: System 목록 (각 항목에 하위 Package 건수 표시)
- 중앙 패널: 선택된 System 의 Package 목록 (Tag 건수 표시)
- 우측 패널: 선택된 Package 의 Tag 목록 (클릭 시 tag_detail 로 이동)

선택 상태는 ``st.session_state`` 에 저장되어 페이지 재실행 시 유지된다.
"""
import pandas as pd
import streamlit as st

from components.auth import require_permission
from components.sidebar import render_sidebar
from config import PAGE_HIERARCHY
from data.data_loader import load_equipment

require_permission(PAGE_HIERARCHY)

# ── session_state 키 상수 ────────────────────────────────────────────────
KEY_SELECTED_SYSTEM = "selected_system_id"
KEY_SELECTED_PACKAGE = "selected_package_id"
KEY_SELECTED_TAG = "selected_tag_no"


@st.cache_data(show_spinner=False)
def _summarize(df: pd.DataFrame) -> dict:
    """System/Package/Tag 단위 집계 결과를 캐싱하여 반환한다.

    Returns:
        dict: 다음 키를 포함한다.
            - systems: SystemID/SystemName/PackageCount/TagCount 가 담긴 DataFrame
            - packages: SystemID/PackageID/PackageName/TagCount 가 담긴 DataFrame
            - tags: 원본 Tag 행 그대로
    """
    # System 단위 집계 (Package 개수, Tag 개수)
    systems = (
        df.groupby(["SystemID", "SystemName"], as_index=False)
        .agg(PackageCount=("PackageID", "nunique"), TagCount=("TagNo", "nunique"))
        .sort_values("SystemID")
    )

    # Package 단위 집계 (Tag 개수)
    packages = (
        df.groupby(["SystemID", "PackageID", "PackageName"], as_index=False)
        .agg(TagCount=("TagNo", "nunique"))
        .sort_values(["SystemID", "PackageID"])
    )

    return {"systems": systems, "packages": packages, "tags": df}


def _render_breadcrumb(
    systems: pd.DataFrame,
    packages: pd.DataFrame,
    selected_system: str | None,
    selected_package: str | None,
) -> None:
    """현재 탐색 위치를 breadcrumb 형태로 표시한다."""
    crumbs: list[str] = ["🏠 Hierarchy"]

    if selected_system:
        sys_row = systems.loc[systems["SystemID"] == selected_system]
        if not sys_row.empty:
            crumbs.append(f"🔧 {sys_row.iloc[0]['SystemName']}")

    if selected_package:
        pkg_row = packages.loc[packages["PackageID"] == selected_package]
        if not pkg_row.empty:
            crumbs.append(f"📦 {pkg_row.iloc[0]['PackageName']}")

    st.markdown(" › ".join(crumbs))


def _render_system_panel(systems: pd.DataFrame, selected_system: str | None) -> None:
    """좌측 System 목록 패널 렌더링."""
    st.markdown("#### 🔧 System")
    st.caption(f"총 {len(systems)}건")

    for _, row in systems.iterrows():
        system_id = row["SystemID"]
        is_selected = system_id == selected_system
        label = (
            f"{'✅ ' if is_selected else ''}**{row['SystemName']}**\n\n"
            f"`{system_id}` · Package {int(row['PackageCount'])}개 · Tag {int(row['TagCount'])}개"
        )
        if st.button(
            label,
            key=f"sys_btn_{system_id}",
            use_container_width=True,
            type="primary" if is_selected else "secondary",
        ):
            # 시스템이 변경되면 하위 선택을 초기화한다
            if st.session_state.get(KEY_SELECTED_SYSTEM) != system_id:
                st.session_state[KEY_SELECTED_SYSTEM] = system_id
                st.session_state[KEY_SELECTED_PACKAGE] = None
                st.rerun()


def _render_package_panel(
    packages: pd.DataFrame,
    selected_system: str | None,
    selected_package: str | None,
) -> None:
    """중앙 Package 목록 패널 렌더링."""
    st.markdown("#### 📦 Package")

    if not selected_system:
        st.info("← 좌측에서 System 을 선택하세요.")
        return

    sub = packages.loc[packages["SystemID"] == selected_system]
    st.caption(f"총 {len(sub)}건")

    if sub.empty:
        st.warning("선택된 System 에 등록된 Package 가 없습니다.")
        return

    for _, row in sub.iterrows():
        package_id = row["PackageID"]
        is_selected = package_id == selected_package
        label = (
            f"{'✅ ' if is_selected else ''}**{row['PackageName']}**\n\n"
            f"`{package_id}` · Tag {int(row['TagCount'])}개"
        )
        if st.button(
            label,
            key=f"pkg_btn_{package_id}",
            use_container_width=True,
            type="primary" if is_selected else "secondary",
        ):
            if st.session_state.get(KEY_SELECTED_PACKAGE) != package_id:
                st.session_state[KEY_SELECTED_PACKAGE] = package_id
                st.rerun()


def _render_tag_panel(tags: pd.DataFrame, selected_package: str | None) -> None:
    """우측 Tag 목록 패널 렌더링. Tag 클릭 시 tag_detail 로 이동한다."""
    st.markdown("#### 🏷️ Tag")

    if not selected_package:
        st.info("← 중앙에서 Package 를 선택하세요.")
        return

    sub = tags.loc[tags["PackageID"] == selected_package].sort_values("TagNo")
    st.caption(f"총 {len(sub)}건")

    if sub.empty:
        st.warning("선택된 Package 에 등록된 Tag 가 없습니다.")
        return

    for _, row in sub.iterrows():
        tag_no = row["TagNo"]
        description = row.get("TagDescription") or ""
        manufacturer = row.get("ManufactureName") or "-"
        label = (
            f"**{tag_no}**\n\n"
            f"{description}\n\n"
            f"🏭 {manufacturer}"
        )
        if st.button(
            label,
            key=f"tag_btn_{tag_no}",
            use_container_width=True,
        ):
            # 선택된 Tag 를 session_state 에 저장 후 상세 페이지로 이동
            st.session_state[KEY_SELECTED_TAG] = tag_no
            st.switch_page("pages/tag_detail.py")


def _init_session_keys() -> None:
    """페이지 진입 시 session_state 기본값을 설정한다."""
    for key in (KEY_SELECTED_SYSTEM, KEY_SELECTED_PACKAGE, KEY_SELECTED_TAG):
        st.session_state.setdefault(key, None)


# ── 페이지 본체 ──────────────────────────────────────────────────────────
render_sidebar()
_init_session_keys()

st.title("🗂️ Hierarchy View")
st.caption("System → Package → Tag 계층 탐색")

df = load_equipment()
summary = _summarize(df)

selected_system = st.session_state.get(KEY_SELECTED_SYSTEM)
selected_package = st.session_state.get(KEY_SELECTED_PACKAGE)

# Breadcrumb
_render_breadcrumb(summary["systems"], summary["packages"], selected_system, selected_package)
st.markdown("---")

# 3단 패널
col_system, col_package, col_tag = st.columns([1, 1, 1.2], gap="medium")

with col_system:
    _render_system_panel(summary["systems"], selected_system)

with col_package:
    _render_package_panel(summary["packages"], selected_system, selected_package)

with col_tag:
    _render_tag_panel(summary["tags"], selected_package)
