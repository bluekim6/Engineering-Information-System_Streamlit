"""Comment 관리 페이지.

Tag 별 코멘트 입력 / 조회 / 상태(Open/Review/Closed) 변경을 한 화면에서 처리한다.

- 신규 입력 폼: TagNo / Comment / LinkedDoc / LinkedDrawing / Author 입력 후
                 ``Comment_master.xlsx`` 에 행 추가 (CommentID 자동 채번).
- 목록 조회   : 상태 탭(전체/Open/Review/Closed) 으로 필터링한 코멘트 리스트.
                각 코멘트는 ``st.expander`` 로 펼쳐 상세를 보고, 상태 변경 버튼으로
                즉시 ``Status`` / ``UpdatedAt`` 갱신 후 저장한다.
"""
import re

import pandas as pd
import streamlit as st

from components.auth import require_permission
from components.sidebar import render_sidebar
from config import (
    COMMENT_STATUSES,
    PAGE_COMMENT,
    STATUS_CLOSED,
    STATUS_OPEN,
    STATUS_REVIEW,
)
from data.data_loader import (
    ExcelSaveError,
    load_comment,
    load_document,
    load_drawing,
    load_equipment,
    save_comment,
)

require_permission(PAGE_COMMENT)


# ── 헬퍼 ────────────────────────────────────────────────────────────────
def _today_str() -> str:
    """오늘 날짜를 ``YYYY-MM-DD`` 문자열로 반환."""
    return pd.Timestamp.today().strftime("%Y-%m-%d")


def _next_comment_id(df: pd.DataFrame) -> str:
    """기존 ``CMT-NNNN`` 시퀀스 다음 ID 를 반환."""
    pattern = re.compile(r"CMT-(\d+)")
    max_n = 0
    for cid in df.get("CommentID", pd.Series([], dtype=object)).dropna():
        m = pattern.match(str(cid))
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"CMT-{max_n + 1:04d}"


def _summarize(text: str, n: int = 50) -> str:
    """긴 코멘트 본문을 N자로 요약."""
    text = str(text or "").strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def _save_new_comment(
    *,
    tag_no: str,
    comment: str,
    author: str,
    linked_doc: str | None,
    linked_drawing: str | None,
) -> str:
    """신규 Comment 행을 추가 저장하고 발급된 CommentID 를 반환."""
    df = load_comment()
    new_id = _next_comment_id(df)
    today = _today_str()

    new_row = {
        "CommentID": new_id,
        "TagNo": tag_no,
        "Comment": comment,
        "Author": author,
        "Status": STATUS_OPEN,  # 신규는 Open 으로 시작
        "LinkedDoc": linked_doc or "",
        "LinkedDrawing": linked_drawing or "",
        "CreatedAt": today,
        "UpdatedAt": today,
    }
    updated = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    try:
        save_comment(updated)
    except ExcelSaveError as e:
        st.error(str(e))
        raise
    return new_id


def _update_status(comment_id: str, new_status: str) -> None:
    """지정 CommentID 의 Status / UpdatedAt 을 갱신 저장."""
    df = load_comment().copy()
    mask = df["CommentID"].astype(str) == str(comment_id)
    if not mask.any():
        st.error(f"CommentID '{comment_id}' 를 찾을 수 없습니다.")
        return
    df.loc[mask, "Status"] = new_status
    df.loc[mask, "UpdatedAt"] = _today_str()
    try:
        save_comment(df)
    except ExcelSaveError as e:
        st.error(str(e))


def _status_badge(status: str) -> str:
    """상태값에 색 이모지 prefix 부착."""
    icon = {STATUS_OPEN: "🟢", STATUS_REVIEW: "🟡", STATUS_CLOSED: "⚪"}.get(status, "⚫")
    return f"{icon} {status}"


def _render_new_comment_form(equipment: pd.DataFrame, document: pd.DataFrame, drawing: pd.DataFrame) -> None:
    """신규 코멘트 입력 폼."""
    st.markdown("### ✏️ 신규 Comment")

    tag_options = sorted(equipment["TagNo"].astype(str).str.strip().unique().tolist())
    doc_options = ["(없음)"] + sorted(document["DocNo"].astype(str).str.strip().unique().tolist())
    drw_options = ["(없음)"] + sorted(drawing["DrawingNo"].astype(str).str.strip().unique().tolist())

    with st.form("new_comment_form", clear_on_submit=True):
        c1, c2 = st.columns([1, 1])
        tag_no = c1.selectbox("TagNo*", tag_options, index=0 if tag_options else None)
        author = c2.text_input("작성자*", placeholder="예: Kim, J.")

        comment_body = st.text_area(
            "Comment 내용*",
            placeholder="예: 자료 제출 전에 자재 인증서 확인 필요.",
            height=120,
        )

        c3, c4 = st.columns([1, 1])
        linked_doc = c3.selectbox("연결 문서번호 (선택)", doc_options, index=0)
        linked_drawing = c4.selectbox("연결 도면번호 (선택)", drw_options, index=0)

        submitted = st.form_submit_button("💾 저장", type="primary", use_container_width=True)

    if submitted:
        if not tag_no or not author.strip() or not comment_body.strip():
            st.error("TagNo / 작성자 / Comment 내용은 필수 입력입니다.")
            return
        new_id = _save_new_comment(
            tag_no=tag_no,
            comment=comment_body.strip(),
            author=author.strip(),
            linked_doc=None if linked_doc == "(없음)" else linked_doc,
            linked_drawing=None if linked_drawing == "(없음)" else linked_drawing,
        )
        st.success(f"저장 완료 — {new_id}")
        st.rerun()


def _render_comment_list(comments: pd.DataFrame) -> None:
    """상태 탭 + 코멘트 리스트 + expander 상세."""
    st.markdown("### 📋 Comment 목록")

    # 상태별 카운트
    counts = comments["Status"].value_counts()
    total = len(comments)
    tab_labels = [
        f"전체 ({total})",
        f"🟢 Open ({counts.get(STATUS_OPEN, 0)})",
        f"🟡 Review ({counts.get(STATUS_REVIEW, 0)})",
        f"⚪ Closed ({counts.get(STATUS_CLOSED, 0)})",
    ]
    tab_filters = [None, STATUS_OPEN, STATUS_REVIEW, STATUS_CLOSED]
    tabs = st.tabs(tab_labels)

    # 같은 코멘트가 '전체' 와 해당 상태 탭에 중복 렌더되므로 탭 인덱스를 위젯 key 에 포함시켜 충돌을 막는다.
    for tab_idx, (tab, status_filter) in enumerate(zip(tabs, tab_filters)):
        with tab:
            view = comments if status_filter is None else comments[comments["Status"] == status_filter]
            if view.empty:
                st.info("해당 상태의 코멘트가 없습니다.")
                continue

            # 최신순 정렬 (UpdatedAt → CreatedAt 내림차순)
            view = view.sort_values(by=["UpdatedAt", "CreatedAt"], ascending=False, na_position="last")

            for _, row in view.iterrows():
                cid = str(row["CommentID"])
                header = (
                    f"{_status_badge(str(row['Status']))} · "
                    f"`{cid}` · TagNo: **{row['TagNo']}** · "
                    f"{_summarize(row['Comment'])} · "
                    f"_{row['Author']}_ · {row.get('CreatedAt', '-')}"
                )
                with st.expander(header):
                    _render_comment_detail(row, key_suffix=f"tab{tab_idx}")


def _render_comment_detail(row: pd.Series, key_suffix: str = "") -> None:
    """expander 내부의 상세 + 상태 변경 버튼.

    key_suffix : 같은 코멘트가 여러 탭에 중복 렌더될 때 위젯 key 충돌을 막기 위한
                 호출처 식별자(예: 'tab0').
    """
    cid = str(row["CommentID"])

    detail_l, detail_r = st.columns([2, 1])
    with detail_l:
        st.markdown("**전체 내용**")
        st.markdown(f"> {row['Comment']}")
    with detail_r:
        st.markdown(f"**작성자**: {row.get('Author', '-')}")
        st.markdown(f"**상태**: {_status_badge(str(row['Status']))}")
        st.markdown(f"**연결 문서**: `{row.get('LinkedDoc') or '-'}`")
        st.markdown(f"**연결 도면**: `{row.get('LinkedDrawing') or '-'}`")
        st.markdown(f"**작성일**: {row.get('CreatedAt', '-')}")
        st.markdown(f"**수정일**: {row.get('UpdatedAt', '-')}")

    st.markdown("**상태 변경**")
    btn_cols = st.columns(len(COMMENT_STATUSES))
    current = str(row["Status"])
    for i, st_value in enumerate(COMMENT_STATUSES):
        is_current = st_value == current
        if btn_cols[i].button(
            _status_badge(st_value),
            key=f"set_status_{cid}_{st_value}_{key_suffix}",
            type="primary" if is_current else "secondary",
            disabled=is_current,
            use_container_width=True,
        ):
            _update_status(cid, st_value)
            st.success(f"{cid} 상태를 '{st_value}' 로 변경했습니다.")
            st.rerun()


# ── 페이지 본체 ──────────────────────────────────────────────────────────
render_sidebar()

st.title("💬 Comment Management")
st.caption("Tag 코멘트 입력 / 상태 관리 / 연결 문서·도면")

equipment = load_equipment()
document = load_document()
drawing = load_drawing()
comments = load_comment()

# 신규 입력 ↑ / 목록 ↓
_render_new_comment_form(equipment, document, drawing)
st.markdown("---")
_render_comment_list(comments)
