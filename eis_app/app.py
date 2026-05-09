"""Engineering Information System 메인 진입점.

로그인 gate 통과 → 사용자 역할에 맞는 페이지만 ``st.navigation`` 메뉴에 노출.
``streamlit run app.py`` 로 실행한다.

페이지 set_page_config 는 본 파일 한 곳에서만 호출 (Streamlit 정책).
"""
import sys
from pathlib import Path

import streamlit as st

# eis_app 루트를 sys.path 에 추가 (pages/ 등에서 config import 가능하도록)
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from components.auth import is_authenticated, render_login_page  # noqa: E402
from config import (  # noqa: E402
    APP_ICON,
    APP_TITLE,
    PAGE_COMMENT,
    PAGE_HIERARCHY,
    PAGE_HISTORY,
    PAGE_SEARCH,
    PAGE_TAG_DETAIL,
    ROLE_PERMISSIONS,
)

# ── 1. 페이지 설정 (전역 1회) ─────────────────────────────────────────────
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 2. 로그인 gate ────────────────────────────────────────────────────────
if not is_authenticated():
    render_login_page()
    st.stop()

# ── 3. 페이지 정의 ────────────────────────────────────────────────────────
ALL_PAGES: dict[str, st.Page] = {
    PAGE_HIERARCHY: st.Page(
        "pages/hierarchy_view.py", title="Hierarchy", icon="🗂️", default=True,
    ),
    PAGE_TAG_DETAIL: st.Page(
        "pages/tag_detail.py", title="Tag Detail", icon="🏷️",
    ),
    PAGE_SEARCH: st.Page(
        "pages/search_page.py", title="Search", icon="🔍",
    ),
    PAGE_COMMENT: st.Page(
        "pages/comment_page.py", title="Comment", icon="💬",
    ),
    PAGE_HISTORY: st.Page(
        "pages/history_page.py", title="History", icon="📜",
    ),
}

# ── 4. 권한별 메뉴 노출 ───────────────────────────────────────────────────
role = st.session_state.get("user_role")
allowed_keys = ROLE_PERMISSIONS.get(role, [])

browse_keys = [PAGE_HIERARCHY, PAGE_TAG_DETAIL, PAGE_SEARCH]
manage_keys = [PAGE_COMMENT, PAGE_HISTORY]

browse_pages = [ALL_PAGES[k] for k in browse_keys if k in allowed_keys]
manage_pages = [ALL_PAGES[k] for k in manage_keys if k in allowed_keys]

nav_dict: dict[str, list[st.Page]] = {}
if browse_pages:
    nav_dict["Browse"] = browse_pages
if manage_pages:
    nav_dict["Manage"] = manage_pages

if not nav_dict:
    # 권한이 하나도 없는 비정상 상태 (방어용)
    st.error("이 역할에는 노출 가능한 페이지가 없습니다. 관리자에게 문의하세요.")
    st.stop()

# default 페이지가 권한에 없는 경우 첫 허용 페이지를 default 로 승격
all_visible = [p for ps in nav_dict.values() for p in ps]
if not any(getattr(p, "_default", False) or p is ALL_PAGES[PAGE_HIERARCHY] for p in all_visible):
    pass  # st.Page 의 default 는 페이지 객체 생성 시점에만 지정 가능 → 그냥 방치 (Streamlit 이 첫 페이지를 자동 선택)

navigation = st.navigation(nav_dict)
navigation.run()
