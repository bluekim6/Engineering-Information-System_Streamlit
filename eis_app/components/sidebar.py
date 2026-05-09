"""공통 사이드바 컴포넌트.

로그인된 사용자명/역할을 표시하고 로그아웃 버튼을 제공한다.
``app.py`` 의 gate 가 인증을 보장하므로, 사이드바는 인증 후 페이지에서만 호출된다.
"""
import streamlit as st

from components.auth import is_authenticated, logout
from config import APP_ICON, APP_TITLE

DEFAULT_PROJECT_NAME = "Offshore FPSO Project"


def _ensure_session_defaults() -> None:
    """프로젝트 정보 등 기본값을 session_state 에 채운다."""
    st.session_state.setdefault("project_name", DEFAULT_PROJECT_NAME)


def render_sidebar() -> None:
    """공통 사이드바 렌더링."""
    _ensure_session_defaults()

    with st.sidebar:
        st.markdown(f"## {APP_ICON} {APP_TITLE}")
        st.markdown("---")

        if is_authenticated():
            st.markdown("### 👤 사용자")
            st.markdown(f"**{st.session_state.get('user_name', '-')}**")
            st.markdown(f"역할: `{st.session_state.get('user_role', '-')}`")
            if st.button("🚪 로그아웃", use_container_width=True, key="sidebar_logout"):
                logout()
            st.markdown("---")

        st.markdown("### 📁 프로젝트")
        st.markdown(f"**{st.session_state.get('project_name', DEFAULT_PROJECT_NAME)}**")

        st.markdown("---")
        st.caption("Engineering Information System v1.0")
