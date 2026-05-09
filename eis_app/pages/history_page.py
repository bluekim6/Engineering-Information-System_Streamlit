"""변경이력 (History) 조회 페이지.

``History_log.xlsx`` 의 변경 로그를 TagNo / 날짜 범위 / 변경 항목으로 필터링해
조회한다. 편집 화면에서 ``data_loader.log_change()`` 가 호출될 때 자동으로 누적되며,
본 페이지는 읽기 전용이다.
"""
from datetime import date

import pandas as pd
import streamlit as st

from components.auth import require_permission
from components.sidebar import render_sidebar
from config import PAGE_HISTORY
from data.data_loader import load_history

# ── 가드 ────────────────────────────────────────────────────────────────
require_permission(PAGE_HISTORY)
render_sidebar()

st.title("📜 변경 이력 (History)")
st.caption("Equipment Tag 변경 로그 조회")

df = load_history()

if df.empty:
    st.info(
        "기록된 변경 이력이 없습니다. "
        "Tag Detail 페이지의 [✏️ Tag 정보 편집] 에서 값을 변경하면 자동으로 기록됩니다."
    )
    st.stop()

# 날짜 파싱 (필터 기준)
df = df.copy()
df["_at"] = pd.to_datetime(df["ChangedAt"], errors="coerce")

# ── 필터 ────────────────────────────────────────────────────────────────
with st.expander("🔎 필터", expanded=True):
    f1, f2, f3 = st.columns([1.5, 1, 1])
    tag_filter = f1.text_input("TagNo (부분 일치)", value="")

    min_dt = df["_at"].min()
    max_dt = df["_at"].max()
    default_start = min_dt.date() if pd.notna(min_dt) else date.today()
    default_end = max_dt.date() if pd.notna(max_dt) else date.today()

    start_d = f2.date_input("시작일", value=default_start)
    end_d = f3.date_input("종료일", value=default_end)

    field_filter = st.multiselect(
        "변경 항목 (Field)",
        sorted(df["Field"].dropna().astype(str).unique().tolist()),
        default=[],
    )

# ── 필터 적용 ────────────────────────────────────────────────────────────
view = df.copy()
if tag_filter:
    view = view[view["TagNo"].astype(str).str.contains(tag_filter, case=False, na=False)]
if start_d and end_d:
    view = view[(view["_at"].dt.date >= start_d) & (view["_at"].dt.date <= end_d)]
if field_filter:
    view = view[view["Field"].isin(field_filter)]

view = view.sort_values("_at", ascending=False, na_position="last").drop(columns=["_at"])

st.markdown("---")
st.markdown(f"### 📋 결과 — 총 **{len(view):,}건**")

if view.empty:
    st.warning("조건에 맞는 변경 이력이 없습니다.")
    st.stop()

display = view.rename(columns={
    "Field": "변경항목",
    "OldValue": "변경전",
    "NewValue": "변경후",
    "ChangedBy": "변경자",
    "ChangedAt": "변경일시",
})[["TagNo", "변경항목", "변경전", "변경후", "변경자", "변경일시"]]

st.dataframe(display, use_container_width=True, hide_index=True)
