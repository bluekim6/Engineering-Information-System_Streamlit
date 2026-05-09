"""전역 설정 모듈.

엑셀 파일 경로, 시트명, Comment 상태 enum 등 시스템 전역 상수를 정의한다.
모든 모듈은 이 파일을 import 하여 경로/이름을 일관되게 참조한다.
"""
from pathlib import Path

# 기본 경로
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DRAWINGS_DIR = BASE_DIR / "drawings"
PROJECT_ROOT = BASE_DIR.parent  # 저장소 루트 (Tag_Register.xlsx 위치)

# 엑셀 파일 경로 상수
EQUIPMENT_XLSX = DATA_DIR / "Equipment_master.xlsx"
DOCUMENT_XLSX = DATA_DIR / "Document_master.xlsx"
DRAWING_XLSX = DATA_DIR / "Drawing_master.xlsx"
COMMENT_XLSX = DATA_DIR / "Comment_master.xlsx"
MANUFACTURE_XLSX = DATA_DIR / "Manufacture_list.xlsx"
HISTORY_XLSX = DATA_DIR / "History_log.xlsx"

# 외부 입력 (System/Package/Tag 원천 데이터 — 루트 디렉토리 위치)
TAG_REGISTER_XLSX = PROJECT_ROOT / "Tag_Register.xlsx"
# 외부 입력 (도면/문서 메타 — Title/Revision 의 단일 정본)
DOCUMENT_LIST_XLSX = PROJECT_ROOT / "Document_List.xlsx"

# 시트명 상수
SHEET_EQUIPMENT = "Equipment"
SHEET_DOCUMENT = "Document"
SHEET_DRAWING = "Drawing"
SHEET_COMMENT = "Comment"
SHEET_MANUFACTURE = "Manufacture"
SHEET_HISTORY = "History"

# Tag_Register 시트명
SHEET_TAG_REGISTER_DATA = "Sheet1"      # 메인 Tag 데이터 (System/Package 정보 포함)
# Document_List 시트명
SHEET_DOCUMENT_LIST = "Sheet1"

# Document_List 컬럼명 (DrawingTitle/Revision 의 정본 컬럼)
COL_DOC_LIST_NUMBER = "Document Number"
COL_DOC_LIST_NAME = "Document Name"
COL_DOC_LIST_REVISION = "Revision"

# Comment 상태 enum
STATUS_OPEN = "Open"
STATUS_REVIEW = "Review"
STATUS_CLOSED = "Closed"
COMMENT_STATUSES = (STATUS_OPEN, STATUS_REVIEW, STATUS_CLOSED)

# 앱 메타
APP_TITLE = "Engineering Information System"
APP_ICON = "🛢️"

# ── 역할 / 권한 ───────────────────────────────────────────────────────────
ROLE_DESIGN_ENGINEER = "설계엔지니어"
ROLE_DOC_MANAGER = "문서관리자"
ROLE_CLIENT = "발주처"
ROLE_OPERATOR = "운영자"
ROLES = (ROLE_DESIGN_ENGINEER, ROLE_DOC_MANAGER, ROLE_CLIENT, ROLE_OPERATOR)

# 페이지 키 (권한 체크용)
PAGE_HIERARCHY = "hierarchy"
PAGE_TAG_DETAIL = "tag_detail"
PAGE_SEARCH = "search"
PAGE_COMMENT = "comment"
PAGE_HISTORY = "history"

ROLE_PERMISSIONS: dict[str, list[str]] = {
    ROLE_DESIGN_ENGINEER: [PAGE_HIERARCHY, PAGE_TAG_DETAIL, PAGE_SEARCH, PAGE_COMMENT, PAGE_HISTORY],
    ROLE_DOC_MANAGER:     [PAGE_HIERARCHY, PAGE_TAG_DETAIL, PAGE_SEARCH, PAGE_COMMENT, PAGE_HISTORY],
    ROLE_CLIENT:          [PAGE_HIERARCHY, PAGE_TAG_DETAIL, PAGE_SEARCH],
    ROLE_OPERATOR:        [PAGE_HIERARCHY, PAGE_TAG_DETAIL, PAGE_SEARCH, PAGE_COMMENT],
}

# Equipment Tag 편집 가능한 역할 (history 로깅 대상)
ROLES_CAN_EDIT_TAG = (ROLE_DESIGN_ENGINEER, ROLE_DOC_MANAGER)
