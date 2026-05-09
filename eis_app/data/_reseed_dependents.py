"""의존 마스터 파일을 Equipment_master.xlsx 기준으로 재생성한다.

새 ``Equipment_master.xlsx`` (Tag_Register 기반) 의 TagNo / ReferenceDrawing /
ManufactureName 을 진실의 원천(SoR) 으로 보고, 다음 4 개 파일을 정합 상태로
재시드한다.

대상
- Drawing_master.xlsx   : Tag 의 ReferenceDrawing 을 DrawingNo 로 사용. 같은 도면을
                          여러 Tag 가 공유 → (DrawingNo, TagNo) 행으로 표현
- Document_master.xlsx  : Tag 당 Data Sheet 1건 (DOC-NNNN 자동 채번)
- Comment_master.xlsx   : 샘플 10건만 신규 TagNo 풀에서 생성
- Manufacture_list.xlsx : Equipment 의 unique ManufactureName 으로 재구성

실행: ``python eis_app/data/_reseed_dependents.py``

주의
- 기존 4 개 파일을 덮어쓴다. 의도치 않은 데이터 손실을 막기 위해 실행 전
  자동으로 ``*.bak`` 백업을 생성한다.
"""
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from config import (  # noqa: E402
    COMMENT_XLSX,
    DOCUMENT_XLSX,
    DRAWING_XLSX,
    EQUIPMENT_XLSX,
    MANUFACTURE_XLSX,
    SHEET_COMMENT,
    SHEET_DOCUMENT,
    SHEET_DRAWING,
    SHEET_EQUIPMENT,
    SHEET_MANUFACTURE,
    STATUS_CLOSED,
    STATUS_OPEN,
    STATUS_REVIEW,
)

# ── 결정론적 fixture (Manufacture 정보 라운드로빈용) ───────────────────────
COUNTRIES = [
    ("Korea",       "Seoul, Korea"),
    ("Sweden",      "Lund, Sweden"),
    ("Germany",     "Erlangen, Germany"),
    ("USA",         "Houston, TX, USA"),
    ("Japan",       "Tokyo, Japan"),
    ("UK",          "London, UK"),
    ("France",      "Paris, France"),
    ("Italy",       "Milan, Italy"),
    ("Singapore",   "Singapore"),
    ("Norway",      "Oslo, Norway"),
]
PHONE_PREFIX = {
    "Korea": "+82-", "Sweden": "+46-", "Germany": "+49-", "USA": "+1-",
    "Japan": "+81-", "UK": "+44-", "France": "+33-", "Italy": "+39-",
    "Singapore": "+65-", "Norway": "+47-",
}
CONTACT_NAMES = [
    "Min-jun Kim", "Erik Lindberg", "Hans Mueller", "Robert Smith",
    "Hiroshi Tanaka", "James Wilson", "Pierre Dubois", "Marco Rossi",
    "Wei Lim", "Anders Olsen", "Soo-yeon Park", "Lukas Frei",
    "Jennifer Davis", "Michael Brown", "Sarah Johnson", "David Lee",
]
CERTS = [
    "ISO 9001, API Q1", "ISO 9001, ASME U", "ISO 9001, API 617",
    "ISO 9001, API 610", "FM, UL Listed", "ISO 9001, IEC 61508",
    "ISO 9001, API 670", "ISO 9001, IEC 61439",
]
REMARKS = [
    "Pump OEM", "Heat Exchanger OEM", "Compressor OEM", "Pressure Vessel OEM",
    "Instrumentation", "Diesel Engine OEM", "Fire Protection",
    "Electrical OEM", "DCS / Instrumentation", "Valve OEM",
]
REVISIONS = ["0", "1", "A", "B", "C", "2", "3"]


def _load_equipment() -> pd.DataFrame:
    if not EQUIPMENT_XLSX.exists():
        raise FileNotFoundError(
            f"{EQUIPMENT_XLSX.name} 가 없습니다. 먼저 _import_tag_register.py 를 실행하세요."
        )
    return pd.read_excel(EQUIPMENT_XLSX, sheet_name=SHEET_EQUIPMENT, dtype=object)


def _backup_if_exists(path: Path) -> None:
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))


# ── Manufacture 재생성 ───────────────────────────────────────────────────
def build_manufacture(eq: pd.DataFrame) -> pd.DataFrame:
    """Equipment 의 unique ManufactureName 으로 마스터 행을 결정론적으로 합성."""
    names = sorted({str(x).strip() for x in eq["ManufactureName"].dropna() if str(x).strip()})
    rows = []
    for i, name in enumerate(names):
        country, address = COUNTRIES[i % len(COUNTRIES)]
        contact = CONTACT_NAMES[i % len(CONTACT_NAMES)]
        # 결정론적 더미 전화 (이름 기반 해시 안 쓰고 인덱스만 사용)
        phone = f"{PHONE_PREFIX[country]}{1000 + i:04d}-{2000 + i:04d}"
        slug = name.lower().replace(" ", "").replace(",", "").replace("&", "and")
        email = f"contact@{slug[:20]}.com"
        cert = CERTS[i % len(CERTS)]
        remark = REMARKS[i % len(REMARKS)]
        rows.append({
            "ManufactureName": name,
            "Country": country,
            "ContactPerson": contact,
            "Phone": phone,
            "Email": email,
            "Address": address,
            "Certification": cert,
            "Remark": remark,
        })
    return pd.DataFrame(rows)


# ── Drawing 재생성 ───────────────────────────────────────────────────────
def build_drawing(eq: pd.DataFrame) -> pd.DataFrame:
    """Equipment 의 (TagNo, ReferenceDrawing) 매핑을 Drawing_master 로 표현.

    같은 도면번호를 여러 Tag 가 공유할 수 있어 (DrawingNo, TagNo) 조합당 1행을 만든다.
    DrawingTitle / Revision / FilePath 는 도면 단위로 일관되게 결정론적 값을 부여.
    """
    # 도면 단위 메타 (정렬된 DrawingNo 기준 결정론)
    unique_drawings = sorted({
        str(x).replace(".pdf", "").strip()
        for x in eq["ReferenceDrawing"].dropna() if str(x).strip()
    })
    drawing_meta = {
        no: {
            "title": f"Reference Drawing - {no}",
            "revision": REVISIONS[i % len(REVISIONS)],
            "file_path": f"drawings/{no}.pdf",
        }
        for i, no in enumerate(unique_drawings)
    }

    rows = []
    for _, r in eq.iterrows():
        drw = str(r.get("ReferenceDrawing") or "").replace(".pdf", "").strip()
        if not drw:
            continue
        meta = drawing_meta.get(drw, {
            "title": f"Reference Drawing - {drw}",
            "revision": "0",
            "file_path": f"drawings/{drw}.pdf",
        })
        rows.append({
            "DrawingNo": drw,
            "DrawingTitle": meta["title"],
            "TagNo": str(r["TagNo"]).strip(),
            "Revision": meta["revision"],
            "FilePath": meta["file_path"],
        })
    return pd.DataFrame(rows, columns=["DrawingNo", "DrawingTitle", "TagNo", "Revision", "FilePath"])


# ── Document 재생성 ──────────────────────────────────────────────────────
def build_document(eq: pd.DataFrame) -> pd.DataFrame:
    """각 Tag 당 Data Sheet 1건. DocNo 는 정렬된 TagNo 순서로 채번."""
    rows = []
    sorted_eq = eq.sort_values("TagNo").reset_index(drop=True)
    for i, r in sorted_eq.iterrows():
        tag = str(r["TagNo"]).strip()
        drw = str(r.get("ReferenceDrawing") or "").replace(".pdf", "").strip()
        rows.append({
            "DocNo": f"DOC-{i + 1:04d}",
            "DocTitle": f"Data Sheet - {tag}",
            "TagNo": tag,
            "Revision": REVISIONS[i % len(REVISIONS)],
            "FilePath": f"drawings/{drw}.pdf" if drw else "",
        })
    return pd.DataFrame(rows, columns=["DocNo", "DocTitle", "TagNo", "Revision", "FilePath"])


# ── Comment 재생성 ───────────────────────────────────────────────────────
def build_comment(eq: pd.DataFrame, doc: pd.DataFrame) -> pd.DataFrame:
    """샘플 10건. 정렬된 첫 10개 Tag 에 결정론적 코멘트를 부여."""
    sorted_eq = eq.sort_values("TagNo").reset_index(drop=True).head(10)
    statuses = [STATUS_OPEN, STATUS_REVIEW, STATUS_CLOSED, STATUS_OPEN, STATUS_OPEN,
                STATUS_REVIEW, STATUS_CLOSED, STATUS_OPEN, STATUS_REVIEW, STATUS_CLOSED]
    authors = ["Kim, J.", "Lee, S.", "Park, H.", "Choi, M.", "Jung, K.",
               "Kim, J.", "Yoon, T.", "Lee, S.", "Park, H.", "Choi, M."]
    bodies = [
        "Confirm material certificate prior to FAT.",
        "Vibration spec to be aligned with API 610.",
        "Heat duty re-checked, no further action.",
        "Surge margin to be reviewed by process team.",
        "Mist eliminator type to be specified.",
        "Pressure drop slightly above design — vendor to comment.",
        "Closed after vendor confirmation on shaft seal.",
        "Add custody transfer accuracy class to data sheet.",
        "Diesel engine emission certificate required.",
        "Closed — sizing accepted.",
    ]

    # TagNo → DocNo 매핑 (Document 마스터에서)
    doc_map = dict(zip(doc["TagNo"].astype(str), doc["DocNo"].astype(str)))

    rows = []
    for i, r in sorted_eq.iterrows():
        tag = str(r["TagNo"]).strip()
        drw = str(r.get("ReferenceDrawing") or "").replace(".pdf", "").strip()
        created = pd.Timestamp("2026-04-01") + pd.Timedelta(days=i)
        updated = created + pd.Timedelta(days=2)
        rows.append({
            "CommentID": f"CMT-{i + 1:04d}",
            "TagNo": tag,
            "Comment": bodies[i],
            "Author": authors[i],
            "Status": statuses[i],
            "LinkedDoc": doc_map.get(tag, ""),
            "LinkedDrawing": drw,
            "CreatedAt": created.strftime("%Y-%m-%d"),
            "UpdatedAt": updated.strftime("%Y-%m-%d"),
        })
    return pd.DataFrame(rows)


# ── 검증 ────────────────────────────────────────────────────────────────
def _validate(eq: pd.DataFrame, dwg: pd.DataFrame, doc: pd.DataFrame, cmt: pd.DataFrame) -> list[str]:
    """외래키 정합성을 검사해 이상 메시지 리스트를 반환 (빈 리스트면 정상)."""
    issues: list[str] = []
    eq_tags = set(eq["TagNo"].astype(str).str.strip())

    # Drawing.TagNo ⊂ Equipment.TagNo
    missing = set(dwg["TagNo"].astype(str)) - eq_tags
    if missing:
        issues.append(f"Drawing.TagNo 중 Equipment 에 없는 값 {len(missing)}개")

    # Document.TagNo ⊂ Equipment.TagNo
    missing = set(doc["TagNo"].astype(str)) - eq_tags
    if missing:
        issues.append(f"Document.TagNo 중 Equipment 에 없는 값 {len(missing)}개")

    # Comment.TagNo ⊂ Equipment.TagNo
    missing = set(cmt["TagNo"].astype(str)) - eq_tags
    if missing:
        issues.append(f"Comment.TagNo 중 Equipment 에 없는 값 {len(missing)}개")

    # Comment.LinkedDoc ⊂ Document.DocNo (빈 값은 허용)
    doc_nos = set(doc["DocNo"].astype(str))
    bad_links = [
        x for x in cmt["LinkedDoc"].astype(str)
        if x and x.strip() and x.strip() not in doc_nos
    ]
    if bad_links:
        issues.append(f"Comment.LinkedDoc 중 Document 에 없는 DocNo {len(bad_links)}개")

    return issues


# ── 메인 ────────────────────────────────────────────────────────────────
def main() -> None:
    eq = _load_equipment()
    print(f"[*] Equipment 기준 {len(eq)} Tag / {eq['ManufactureName'].nunique()} Mfg / "
          f"{eq['ReferenceDrawing'].nunique()} Drawing 으로 재시드")

    # 백업
    for path in (DRAWING_XLSX, DOCUMENT_XLSX, COMMENT_XLSX, MANUFACTURE_XLSX):
        _backup_if_exists(path)

    # 의존성 순서: Manufacture / Drawing / Document → Comment(Document.DocNo 참조)
    mfg_df = build_manufacture(eq)
    dwg_df = build_drawing(eq)
    doc_df = build_document(eq)
    cmt_df = build_comment(eq, doc_df)

    # 저장
    mfg_df.to_excel(MANUFACTURE_XLSX, sheet_name=SHEET_MANUFACTURE, index=False)
    dwg_df.to_excel(DRAWING_XLSX, sheet_name=SHEET_DRAWING, index=False)
    doc_df.to_excel(DOCUMENT_XLSX, sheet_name=SHEET_DOCUMENT, index=False)
    cmt_df.to_excel(COMMENT_XLSX, sheet_name=SHEET_COMMENT, index=False)

    print("[OK] 저장 완료")
    print(f"  - Manufacture_list.xlsx : {len(mfg_df):>4} rows")
    print(f"  - Drawing_master.xlsx   : {len(dwg_df):>4} rows  ({dwg_df['DrawingNo'].nunique()} unique drawings)")
    print(f"  - Document_master.xlsx  : {len(doc_df):>4} rows")
    print(f"  - Comment_master.xlsx   : {len(cmt_df):>4} rows")

    # 정합성 검증
    issues = _validate(eq, dwg_df, doc_df, cmt_df)
    if issues:
        print("\n[!] 정합성 경고:")
        for msg in issues:
            print(f"    - {msg}")
    else:
        print("\n[OK] 정합성 검증 통과 (모든 외래키 일치)")


if __name__ == "__main__":
    main()
