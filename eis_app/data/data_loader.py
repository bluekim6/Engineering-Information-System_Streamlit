"""엑셀 마스터 파일 입출력 전담 모듈.

각 엑셀 파일을 읽는 함수는 ``st.cache_data`` 로 메모이제이션하여
페이지 전환 시 반복 디스크 I/O 를 방지한다. 저장 함수는 디스크 기록 후
대응되는 read 함수의 캐시를 무효화한다.
"""
from pathlib import Path

import pandas as pd
import streamlit as st

from config import (
    COL_DOC_LIST_NAME,
    COL_DOC_LIST_NUMBER,
    COL_DOC_LIST_REVISION,
    COMMENT_XLSX,
    DOCUMENT_LIST_XLSX,
    DOCUMENT_XLSX,
    DRAWING_XLSX,
    EQUIPMENT_XLSX,
    HISTORY_XLSX,
    MANUFACTURE_XLSX,
    SHEET_COMMENT,
    SHEET_DOCUMENT,
    SHEET_DOCUMENT_LIST,
    SHEET_DRAWING,
    SHEET_EQUIPMENT,
    SHEET_HISTORY,
    SHEET_MANUFACTURE,
    SHEET_TAG_REGISTER_DATA,
    TAG_REGISTER_XLSX,
)

# Tag_Register 의 Tag 키 컬럼명 (Equipment_master 의 TagNo 와 매칭)
TAG_REGISTER_KEY_COL = "Tag"


# History 로그 컬럼 (파일이 없을 때도 일관되게 만들기 위함)
HISTORY_COLUMNS = [
    "LogID", "TagNo", "Field", "OldValue", "NewValue", "ChangedBy", "ChangedAt",
]


class ExcelSaveError(RuntimeError):
    """엑셀 저장 실패를 호출자에게 명시적으로 전달."""


def _read(path: Path, sheet: str) -> pd.DataFrame:
    """공통 엑셀 read 헬퍼."""
    return pd.read_excel(path, sheet_name=sheet, dtype=object)


def _write(df: pd.DataFrame, path: Path, sheet: str) -> None:
    """공통 엑셀 write 헬퍼. 실패 시 ``ExcelSaveError`` 로 변환해 raise."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(path, sheet_name=sheet, index=False)
    except (PermissionError, OSError) as e:
        raise ExcelSaveError(
            f"엑셀 저장 실패: {path.name} ({e}). "
            f"파일이 다른 프로그램에서 열려 있거나 쓰기 권한이 없는지 확인하세요."
        ) from e
    except Exception as e:  # noqa: BLE001
        raise ExcelSaveError(f"엑셀 저장 실패: {path.name} — {e}") from e


# ── Equipment ────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_equipment() -> pd.DataFrame:
    """Equipment_master.xlsx 로드 (System/Package/Tag 마스터)."""
    return _read(EQUIPMENT_XLSX, SHEET_EQUIPMENT)


def save_equipment(df: pd.DataFrame) -> None:
    """Equipment_master.xlsx 저장 후 캐시 무효화."""
    _write(df, EQUIPMENT_XLSX, SHEET_EQUIPMENT)
    load_equipment.clear()


# ── Document ─────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_document() -> pd.DataFrame:
    """Document_master.xlsx 로드 (문서 목록)."""
    return _read(DOCUMENT_XLSX, SHEET_DOCUMENT)


def save_document(df: pd.DataFrame) -> None:
    """Document_master.xlsx 저장 후 캐시 무효화."""
    _write(df, DOCUMENT_XLSX, SHEET_DOCUMENT)
    load_document.clear()


# ── Document_List (도면 Title/Revision 정본) ─────────────────────────────
@st.cache_data(show_spinner=False)
def load_document_list() -> pd.DataFrame:
    """Document_List.xlsx 로드. 파일이 없으면 빈 DataFrame 반환."""
    if not DOCUMENT_LIST_XLSX.exists():
        return pd.DataFrame(
            columns=[COL_DOC_LIST_NUMBER, COL_DOC_LIST_NAME, COL_DOC_LIST_REVISION]
        )
    return _read(DOCUMENT_LIST_XLSX, SHEET_DOCUMENT_LIST)


# ── Tag_Register (Tag 원천 데이터 — 모든 Attribute 컬럼 보유) ────────────
@st.cache_data(show_spinner=False)
def load_tag_register() -> pd.DataFrame:
    """Tag_Register.xlsx 로드. 파일이 없으면 빈 DataFrame 반환.

    Equipment_master 는 일부 컬럼만 가지지만, Tag_Register 는 42개 컬럼 전체를
    보유하므로 Tag Detail 과 같이 풍부한 표시가 필요한 화면에서 직접 참조한다.
    """
    if not TAG_REGISTER_XLSX.exists():
        return pd.DataFrame(columns=[TAG_REGISTER_KEY_COL])
    return _read(TAG_REGISTER_XLSX, SHEET_TAG_REGISTER_DATA)


def get_tag_register_row(tag_no: str) -> pd.Series | None:
    """TagNo 로 Tag_Register 단일 행을 조회. 없으면 None."""
    if not tag_no:
        return None
    df = load_tag_register()
    if df.empty or TAG_REGISTER_KEY_COL not in df.columns:
        return None
    matched = df[df[TAG_REGISTER_KEY_COL].astype(str).str.strip() == str(tag_no).strip()]
    return None if matched.empty else matched.iloc[0]


def get_document_meta(drawing_no: str) -> tuple[str | None, str | None]:
    """DrawingNo 로 Document_List 에서 (DocumentName, Revision) 조회.

    매칭 실패 시 ``(None, None)``. 호출자는 None 을 기존 값 폴백으로 처리한다.
    """
    if not drawing_no:
        return (None, None)
    df = load_document_list()
    if df.empty:
        return (None, None)
    key = str(drawing_no).strip()
    matched = df[df[COL_DOC_LIST_NUMBER].astype(str).str.strip() == key]
    if matched.empty:
        return (None, None)
    row = matched.iloc[0]
    name = row.get(COL_DOC_LIST_NAME)
    rev = row.get(COL_DOC_LIST_REVISION)
    name_s = None if pd.isna(name) else str(name)
    rev_s = None if pd.isna(rev) else str(rev)
    return (name_s, rev_s)


# ── Drawing ──────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_drawing() -> pd.DataFrame:
    """Drawing_master.xlsx 로드 (도면 목록)."""
    return _read(DRAWING_XLSX, SHEET_DRAWING)


def save_drawing(df: pd.DataFrame) -> None:
    """Drawing_master.xlsx 저장 후 캐시 무효화."""
    _write(df, DRAWING_XLSX, SHEET_DRAWING)
    load_drawing.clear()


# ── Comment ──────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_comment() -> pd.DataFrame:
    """Comment_master.xlsx 로드 (코멘트 관리)."""
    return _read(COMMENT_XLSX, SHEET_COMMENT)


def save_comment(df: pd.DataFrame) -> None:
    """Comment_master.xlsx 저장 후 캐시 무효화."""
    _write(df, COMMENT_XLSX, SHEET_COMMENT)
    load_comment.clear()


# ── Manufacture ──────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_manufacture() -> pd.DataFrame:
    """Manufacture_list.xlsx 로드 (제조사 상세정보)."""
    return _read(MANUFACTURE_XLSX, SHEET_MANUFACTURE)


def save_manufacture(df: pd.DataFrame) -> None:
    """Manufacture_list.xlsx 저장 후 캐시 무효화."""
    _write(df, MANUFACTURE_XLSX, SHEET_MANUFACTURE)
    load_manufacture.clear()


# ── History (변경 이력) ──────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_history() -> pd.DataFrame:
    """History_log.xlsx 로드. 파일이 없으면 빈 DataFrame 반환."""
    if not HISTORY_XLSX.exists():
        return pd.DataFrame(columns=HISTORY_COLUMNS)
    df = _read(HISTORY_XLSX, SHEET_HISTORY)
    # 누락된 컬럼이 있으면 보강 (스키마 변경 대비)
    for col in HISTORY_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[HISTORY_COLUMNS]


def save_history(df: pd.DataFrame) -> None:
    """History_log.xlsx 저장 후 캐시 무효화."""
    _write(df, HISTORY_XLSX, SHEET_HISTORY)
    load_history.clear()


def _next_log_id(df: pd.DataFrame) -> str:
    """``LOG-NNNNNN`` 형식의 다음 시퀀스 ID 반환."""
    import re
    pat = re.compile(r"LOG-(\d+)")
    max_n = 0
    for cid in df.get("LogID", pd.Series([], dtype=object)).dropna():
        m = pat.match(str(cid))
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"LOG-{max_n + 1:06d}"


def log_change(tag_no: str, field: str, old_val, new_val, user: str) -> str:
    """변경 이력을 History_log.xlsx 에 기록.

    Parameters
    ----------
    tag_no : 변경 대상 TagNo
    field  : 변경 필드명 (예: 'TagDescription', 'AttributeA')
    old_val, new_val : 변경 전/후 값 (None 또는 임의 타입 가능)
    user   : 변경자 (사용자명)

    Returns
    -------
    str : 발급된 LogID
    """
    df = load_history()
    log_id = _next_log_id(df)
    new_row = {
        "LogID": log_id,
        "TagNo": str(tag_no),
        "Field": str(field),
        "OldValue": "" if old_val is None else str(old_val),
        "NewValue": "" if new_val is None else str(new_val),
        "ChangedBy": str(user or "unknown"),
        "ChangedAt": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    updated = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_history(updated)
    return log_id
