"""사용자 인증 / 권한 제어 컴포넌트.

- 로그인 화면 렌더 (사용자명 + 역할 선택)
- 인증 상태 / 권한 검사 헬퍼
- 페이지 가드 (``require_permission``)
- 로그아웃

세션 키
- ``authenticated`` : bool
- ``user_name``     : str
- ``user_role``     : str (config.ROLES 중 하나)
"""
import streamlit as st

from config import APP_ICON, APP_TITLE, ROLE_PERMISSIONS, ROLES


def is_authenticated() -> bool:
    """로그인 상태 여부."""
    return bool(st.session_state.get("authenticated"))


def has_permission(page_key: str) -> bool:
    """현재 로그인 사용자가 ``page_key`` 페이지에 접근 가능한지."""
    role = st.session_state.get("user_role")
    if not role:
        return False
    return page_key in ROLE_PERMISSIONS.get(role, [])


def require_permission(page_key: str) -> None:
    """페이지 진입 가드. 로그인/권한 미충족 시 메시지 표시 후 ``st.stop()``."""
    if not is_authenticated():
        st.error("🔒 로그인이 필요합니다.")
        st.caption("좌측 상단 메뉴에서 첫 페이지로 이동해 로그인해 주세요.")
        st.stop()
    if not has_permission(page_key):
        st.error("🚫 접근 권한이 없습니다")
        role = st.session_state.get("user_role", "-")
        st.caption(
            f"현재 역할: **{role}** · 요청 페이지: `{page_key}` — "
            "이 페이지를 사용하려면 다른 역할로 로그인해 주세요."
        )
        st.stop()


def logout() -> None:
    """세션 인증 정보 초기화 후 첫 페이지로 재실행."""
    for key in ("authenticated", "user_name", "user_role"):
        st.session_state.pop(key, None)
    # 화면별 임시 상태도 안전하게 정리
    for key in ("selected_tag_no", "tag_detail_step", "selected_drawing_no",
                "selected_system_id", "selected_package_id"):
        st.session_state.pop(key, None)
    st.rerun()


def render_login_page() -> None:
    """로그인 화면. ``app.py`` 의 gate 에서 호출된다."""
    # 가운데 정렬 컬럼
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown(f"# {APP_ICON} {APP_TITLE}")
        st.caption("Engineering Information System — 로그인")
        st.markdown("---")

        with st.form("login_form"):
            user_name = st.text_input("사용자명", placeholder="예: 홍길동")
            user_role = st.selectbox("역할 선택", ROLES, index=0)
            submitted = st.form_submit_button(
                "🔓 로그인", type="primary", use_container_width=True
            )

        if submitted:
            if not user_name.strip():
                st.error("사용자명을 입력하세요.")
                return
            st.session_state["authenticated"] = True
            st.session_state["user_name"] = user_name.strip()
            st.session_state["user_role"] = user_role
            st.success(f"환영합니다, {user_name.strip()} 님 ({user_role})")
            st.rerun()

        st.markdown("---")
        st.caption(
            "역할별 메뉴 노출:\n"
            "- **설계엔지니어 / 문서관리자**: 전체 메뉴\n"
            "- **운영자**: Hierarchy / Tag Detail / Search / Comment\n"
            "- **발주처**: Hierarchy / Tag Detail / Search (읽기 위주)"
        )
