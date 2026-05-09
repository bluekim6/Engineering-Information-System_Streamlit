"""PDF 도면 열람 컴포넌트.

``streamlit-pdf-viewer`` 패키지의 ``pdf_viewer`` 를 래핑해 도면 PDF 를 인라인 표시한다.
파일이 존재하지 않으면 명시적인 에러 메시지를 보이고, 다운로드 버튼은 항상 함께 제공한다.
"""
from pathlib import Path

import streamlit as st
from streamlit_pdf_viewer import pdf_viewer


def render_pdf(file_path: str | Path, height: int = 800, key: str | None = None) -> None:
    """주어진 경로의 PDF 를 인라인 뷰어로 표시한다.

    Parameters
    ----------
    file_path: PDF 파일 경로 (절대/상대 모두 허용).
    height: 뷰어 높이 (px).
    key: 동일 페이지에서 여러 PDF 뷰어를 사용할 때 충돌 방지용 키.
    """
    path = Path(file_path)

    if not path.exists():
        st.error(f"도면 파일을 찾을 수 없습니다 (경로: {path})")
        return

    # 다운로드 버튼 (뷰어가 렌더되지 않더라도 사용자가 파일을 받을 수 있도록)
    with open(path, "rb") as fh:
        pdf_bytes = fh.read()

    col_dl, col_info = st.columns([1, 4])
    with col_dl:
        st.download_button(
            label="📥 PDF 다운로드",
            data=pdf_bytes,
            file_name=path.name,
            mime="application/pdf",
            key=f"dl_{key or path.stem}",
            use_container_width=True,
        )
    with col_info:
        st.caption(f"파일: `{path.name}` ({len(pdf_bytes) / 1024:.1f} KB)")

    # 인라인 뷰어
    pdf_viewer(
        input=pdf_bytes,
        height=height,
        key=f"viewer_{key or path.stem}",
    )
