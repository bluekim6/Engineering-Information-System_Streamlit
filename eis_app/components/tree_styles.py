"""Hierarchy 화면 전용 CSS 주입 컴포넌트.

UI_SAMPLE.jpg 의 다음 요소를 재현하기 위한 커스텀 스타일을 한 곳에 모아두고,
``hierarchy_view.py`` 에서 ``inject_tree_css()`` 한 번만 호출한다.

- 상단 다크 헤더 바 (제목 + 역할)
- 좌측 트리: chevron, 들여쓰기, 카운트, 좌측 정렬, 컴팩트한 행 높이
- 중앙/우측 패널 placeholder 와 헤더 라벨
- 우측 도면 카드 메타(제목/리비전) 폰트
"""
import streamlit as st


_CSS = """
<style>
  /* 본문 상단 패딩 축소 */
  .block-container {
    padding-top: 1.0rem !important;
    padding-bottom: 1.0rem !important;
    max-width: 100% !important;
  }

  /* ── 상단 다크 헤더 ──────────────────────────────────────────────── */
  .eis-topbar {
    background: #1a2233;
    color: #fff;
    padding: 12px 18px;
    margin: -1rem -1rem 0.5rem -1rem;
    display: flex;
    align-items: center;
    border-bottom: 1px solid #2a3447;
  }
  .eis-topbar-title {
    font-weight: 700;
    font-size: 17px;
    color: #c8d0e0;
    letter-spacing: 0.2px;
  }
  .eis-topbar-spacer { flex: 1; }
  .eis-topbar-role {
    font-size: 13px;
    color: #aab7d4;
  }
  .eis-topbar-role b {
    color: #fff;
    margin-left: 6px;
  }

  /* ── 트리 섹션 헤더 라벨 ────────────────────────────────────────── */
  .tree-section-title {
    font-size: 11px;
    color: #6c7a8e;
    letter-spacing: 1.2px;
    padding: 4px 6px 8px 6px;
    border-bottom: 1px solid #e6e8ec;
    margin-bottom: 6px;
    font-weight: 600;
  }
  .panel-title {
    font-size: 14px;
    font-weight: 600;
    color: #1a2233;
    padding: 4px 6px 8px 6px;
    border-bottom: 1px solid #e6e8ec;
    margin-bottom: 8px;
  }

  /* ── 좌측 트리 버튼 (좌측 정렬, 컴팩트) ─────────────────────────── */
  /* 첫 번째 컬럼 영역의 버튼만 트리 스타일 적용 */
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child
    div.stButton > button {
    text-align: left !important;
    background: transparent !important;
    border: none !important;
    color: #1a2233 !important;
    padding: 3px 6px !important;
    font-weight: 400 !important;
    box-shadow: none !important;
    min-height: 28px !important;
    height: 28px !important;
    line-height: 22px !important;
    justify-content: flex-start !important;
    white-space: pre !important;
  }
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child
    div.stButton > button:hover {
    background: #f1f4f9 !important;
    color: #1a2233 !important;
  }
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child
    div.stButton > button[kind="primary"] {
    background: #e8eef9 !important;
    color: #1a2233 !important;
    font-weight: 600 !important;
  }
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child
    div.stButton > button p {
    text-align: left !important;
    font-size: 13px !important;
    color: inherit !important;
    margin: 0 !important;
  }

  /* 트리 카운트 (오른쪽 정렬, 회색 작은 글씨) */
  .tree-count {
    text-align: right;
    color: #6c7a8e;
    font-size: 12px;
    padding-top: 6px;
    padding-right: 4px;
  }

  /* ── placeholder ──────────────────────────────────────────────── */
  .eis-placeholder {
    color: #95a0b3;
    text-align: center;
    padding: 80px 20px;
    font-size: 14px;
  }

  /* ── 우측 도면 카드 메타 ─────────────────────────────────────── */
  .drw-meta-title {
    font-size: 12px;
    color: #4a5568;
    margin-top: 4px;
    line-height: 1.4;
  }
  .drw-meta-rev {
    font-size: 11px;
    color: #8b95a8;
    margin-top: 2px;
  }
</style>
"""


def inject_tree_css() -> None:
  """Hierarchy 화면 CSS 한 번 주입."""
  st.markdown(_CSS, unsafe_allow_html=True)
