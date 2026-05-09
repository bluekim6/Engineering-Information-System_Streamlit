"""제조사 상세정보 팝업 컴포넌트.

Tag 의 ``ManufactureName`` 클릭 시 ``Manufacture_list.xlsx`` 의 상세정보를
``st.dialog`` 모달로 표시한다. 매칭되는 행이 없으면 안내 메시지만 출력한다.
"""
import streamlit as st

from data.data_loader import load_manufacture

# 다이얼로그에 출력할 컬럼 (label, key)
_FIELDS: list[tuple[str, str]] = [
    ("국가 (Country)", "Country"),
    ("담당자 (Contact Person)", "ContactPerson"),
    ("전화 (Phone)", "Phone"),
    ("이메일 (Email)", "Email"),
    ("주소 (Address)", "Address"),
    ("인증 (Certification)", "Certification"),
    ("비고 (Remark)", "Remark"),
]


@st.dialog("제조사 상세정보")
def _manufacture_dialog(manufacture_name: str) -> None:
    """다이얼로그 본체. ``@st.dialog`` 데코레이터로 모달 표시."""
    st.markdown(f"### 🏭 {manufacture_name}")
    st.markdown("---")

    df = load_manufacture()
    # ManufactureName 정확 매칭 (대소문자/공백 정규화)
    target = (manufacture_name or "").strip().lower()
    matched = df[df["ManufactureName"].astype(str).str.strip().str.lower() == target]

    if matched.empty:
        st.warning("등록된 정보 없음")
        st.caption(
            f"`Manufacture_list.xlsx` 에서 '{manufacture_name}' 에 해당하는 제조사 정보를 찾을 수 없습니다."
        )
        return

    row = matched.iloc[0]
    for label, key in _FIELDS:
        value = row.get(key)
        display = "-" if value is None or str(value).strip() == "" or str(value) == "nan" else str(value)
        st.markdown(f"**{label}**  \n{display}")


def show_manufacture_popup(manufacture_name: str) -> None:
    """주어진 제조사명의 상세정보 다이얼로그를 띄운다.

    Parameters
    ----------
    manufacture_name: ``Manufacture_list.xlsx`` 의 ``ManufactureName`` 값.
    """
    _manufacture_dialog(manufacture_name)
