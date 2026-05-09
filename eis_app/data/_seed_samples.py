"""샘플 데이터 시드 스크립트.

5 개의 마스터 엑셀 파일에 10건씩 참조 무결성을 갖춘 샘플 데이터를 작성한다.
초기 셋업 시 1회만 실행하면 되며, 이미 파일이 존재해도 덮어쓴다.

실행: ``python eis_app/data/_seed_samples.py``
"""
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


# ── 공통 마스터 키 ────────────────────────────────────────────────────────
TAGS = [
    ("SYS-100", "Sea Water Cooling System",     "PKG-110", "SW Cooling Pump Package",   "P-1101A", "Primary Sea Water Pump A",        "Hyundai Heavy Industries", "ABCD-AA-0007.pdf"),
    ("SYS-100", "Sea Water Cooling System",     "PKG-110", "SW Cooling Pump Package",   "P-1101B", "Primary Sea Water Pump B",        "Hyundai Heavy Industries", "ABCD-AA-0111.pdf"),
    ("SYS-100", "Sea Water Cooling System",     "PKG-120", "SW Heat Exchanger Package", "E-1201",  "SW Plate Heat Exchanger",         "Alfa Laval",               "ABCD-AA-6111.pdf"),
    ("SYS-200", "Fuel Gas Supply System",       "PKG-210", "Fuel Gas Compressor Pkg",   "K-2101",  "Fuel Gas Centrifugal Compressor", "Siemens Energy",           "ABCD-AL-0007.pdf"),
    ("SYS-200", "Fuel Gas Supply System",       "PKG-210", "Fuel Gas Compressor Pkg",   "V-2102",  "Fuel Gas Suction Drum",           "Doosan Enerbility",        "ABCD-AL-0008.pdf"),
    ("SYS-200", "Fuel Gas Supply System",       "PKG-220", "Fuel Gas Heater Pkg",       "E-2201",  "Fuel Gas Heater",                 "Alfa Laval",               "ABCD-AL-0012.pdf"),
    ("SYS-300", "Crude Oil Export System",      "PKG-310", "Export Pump Package",       "P-3101",  "Crude Oil Export Pump",           "Sulzer",                   "ABCD-AL-0034.pdf"),
    ("SYS-300", "Crude Oil Export System",      "PKG-320", "Metering Skid",             "M-3201",  "Custody Transfer Meter Skid",     "Emerson Process",          "ABCD-DD-0012.pdf"),
    ("SYS-400", "Firewater System",             "PKG-410", "Fire Pump Package",         "P-4101",  "Diesel Driven Fire Water Pump",   "Caterpillar",              "ABCD-DE-0012.pdf"),
    ("SYS-400", "Firewater System",             "PKG-420", "Deluge Valve Skid",         "V-4201",  "Deluge Valve Skid",               "Tyco Fire Products",       "ABCD-QT-0011.pdf"),
]

EQUIPMENT_COLS = [
    "SystemID", "SystemName", "PackageID", "PackageName",
    "TagNo", "TagDescription", "ManufactureName",
    "AttributeA", "AttributeB", "ReferenceDrawing",
]

ATTRIBUTE_A = [
    "Centrifugal, Single Stage", "Centrifugal, Single Stage", "Plate, Titanium",
    "Centrifugal, 6-Stage", "Vertical, 2-Phase Separator", "Plate, SS316",
    "Multistage Centrifugal", "Coriolis Mass Flow", "Diesel Engine Driven",
    "Pneumatic Actuated",
]
ATTRIBUTE_B = [
    "Capacity 1200 m3/h", "Capacity 1200 m3/h", "Duty 8.5 MW",
    "Capacity 250 MMSCFD", "ID 2400 mm × T/T 7000 mm", "Duty 4.2 MW",
    "Capacity 12000 m3/h", "Range 0–5000 m3/h", "Capacity 600 m3/h @ 12 bar",
    "DN 200, ANSI 300#",
]


# ── Equipment_master ─────────────────────────────────────────────────────
def build_equipment() -> pd.DataFrame:
    rows = []
    for (sys_id, sys_name, pkg_id, pkg_name, tag, desc, mfg, drw), attr_a, attr_b in zip(
        TAGS, ATTRIBUTE_A, ATTRIBUTE_B
    ):
        rows.append({
            "SystemID": sys_id,
            "SystemName": sys_name,
            "PackageID": pkg_id,
            "PackageName": pkg_name,
            "TagNo": tag,
            "TagDescription": desc,
            "ManufactureName": mfg,
            "AttributeA": attr_a,
            "AttributeB": attr_b,
            "ReferenceDrawing": drw,
        })
    return pd.DataFrame(rows, columns=EQUIPMENT_COLS)


# ── Document_master ──────────────────────────────────────────────────────
def build_document() -> pd.DataFrame:
    titles = [
        "Data Sheet",
        "Data Sheet",
        "Technical Specification",
        "Performance Curve",
        "P&ID Reference",
        "Vendor Drawing List",
        "Inspection & Test Plan",
        "Material Take Off",
        "Operation Manual",
        "Maintenance Manual",
    ]
    rows = []
    for i, ((_, _, _, _, tag, _, _, drw), title) in enumerate(zip(TAGS, titles), start=1):
        rows.append({
            "DocNo": f"DOC-{i:04d}",
            "DocTitle": f"{title} - {tag}",
            "TagNo": tag,
            "Revision": ["A", "B", "0", "1", "A", "0", "B", "1", "C", "0"][i - 1],
            "FilePath": f"drawings/{drw}",  # 샘플은 도면 PDF 를 재사용
        })
    return pd.DataFrame(rows)


# ── Drawing_master ───────────────────────────────────────────────────────
def build_drawing() -> pd.DataFrame:
    rows = []
    for i, (_, _, _, _, tag, desc, _, drw) in enumerate(TAGS, start=1):
        rows.append({
            "DrawingNo": drw.replace(".pdf", ""),
            "DrawingTitle": f"GA Drawing - {desc}",
            "TagNo": tag,
            "Revision": ["0", "1", "A", "B", "0", "1", "A", "B", "0", "1"][i - 1],
            "FilePath": f"drawings/{drw}",
        })
    return pd.DataFrame(rows)


# ── Comment_master ───────────────────────────────────────────────────────
def build_comment() -> pd.DataFrame:
    statuses = [STATUS_OPEN, STATUS_REVIEW, STATUS_CLOSED, STATUS_OPEN, STATUS_OPEN,
                STATUS_REVIEW, STATUS_CLOSED, STATUS_OPEN, STATUS_REVIEW, STATUS_CLOSED]
    authors = ["Kim, J.", "Lee, S.", "Park, H.", "Choi, M.", "Jung, K.",
               "Kim, J.", "Yoon, T.", "Lee, S.", "Park, H.", "Choi, M."]
    comments = [
        "Confirm material certificate prior to FAT.",
        "Vibration spec to be aligned with API 610.",
        "Heat duty re-checked, no further action.",
        "Surge margin to be reviewed by process team.",
        "Mist eliminator type to be specified.",
        "Pressure drop slightly above design — vendor to comment.",
        "Closed after vendor confirmation on shaft seal.",
        "Add custody transfer accuracy class to data sheet.",
        "Diesel engine emission certificate required.",
        "Closed — deluge valve sizing accepted.",
    ]
    rows = []
    for i, ((_, _, _, _, tag, _, _, drw), st_, auth, cmt) in enumerate(
        zip(TAGS, statuses, authors, comments), start=1
    ):
        created = pd.Timestamp("2026-03-01") + pd.Timedelta(days=i)
        updated = created + pd.Timedelta(days=2)
        rows.append({
            "CommentID": f"CMT-{i:04d}",
            "TagNo": tag,
            "Comment": cmt,
            "Author": auth,
            "Status": st_,
            "LinkedDoc": f"DOC-{i:04d}",
            "LinkedDrawing": drw.replace(".pdf", ""),
            "CreatedAt": created.strftime("%Y-%m-%d"),
            "UpdatedAt": updated.strftime("%Y-%m-%d"),
        })
    return pd.DataFrame(rows)


# ── Manufacture_list ─────────────────────────────────────────────────────
def build_manufacture() -> pd.DataFrame:
    data = [
        ("Hyundai Heavy Industries", "Korea",      "Min-jun Kim",   "+82-52-202-2114", "contact@hhi.co.kr",        "Ulsan, Korea",        "ISO 9001, API Q1",  "Pump OEM"),
        ("Alfa Laval",               "Sweden",     "Erik Lindberg", "+46-46-36-65-00", "info@alfalaval.com",       "Lund, Sweden",        "ISO 9001, ASME U",  "Heat Exchanger OEM"),
        ("Siemens Energy",           "Germany",    "Hans Mueller",  "+49-9131-180",    "contact@siemens-energy.com","Erlangen, Germany",  "ISO 9001, API 617", "Compressor OEM"),
        ("Doosan Enerbility",        "Korea",      "Soo-yeon Park", "+82-55-278-6114", "info@doosanenerbility.com","Changwon, Korea",     "ISO 9001, ASME U",  "Pressure Vessel OEM"),
        ("Sulzer",                   "Switzerland","Lukas Frei",    "+41-52-262-1122", "contact@sulzer.com",       "Winterthur, Switzerland","ISO 9001, API 610","Pump OEM"),
        ("Emerson Process",          "USA",        "Robert Smith",  "+1-512-832-3774", "info@emerson.com",         "Austin, TX, USA",     "ISO 9001, API 670", "Instrumentation"),
        ("Caterpillar",              "USA",        "Jennifer Davis","+1-309-675-1000", "contact@cat.com",          "Peoria, IL, USA",     "ISO 9001, API 7B",  "Diesel Engine OEM"),
        ("Tyco Fire Products",       "USA",        "Michael Brown", "+1-414-570-5000", "info@tyco-fire.com",       "Lansdale, PA, USA",   "FM, UL Listed",     "Fire Protection"),
        ("Schneider Electric",       "France",     "Pierre Dubois", "+33-1-41-29-7000","contact@schneider.com",    "Rueil-Malmaison, France","ISO 9001, IEC 61439","Electrical OEM"),
        ("Yokogawa",                 "Japan",      "Hiroshi Tanaka","+81-422-52-5535", "info@yokogawa.com",        "Tokyo, Japan",        "ISO 9001, IEC 61508","DCS / Instrumentation"),
    ]
    cols = ["ManufactureName", "Country", "ContactPerson", "Phone", "Email",
            "Address", "Certification", "Remark"]
    return pd.DataFrame(data, columns=cols)


# ── 메인 ─────────────────────────────────────────────────────────────────
def main() -> None:
    targets = [
        (build_equipment(),   EQUIPMENT_XLSX,   SHEET_EQUIPMENT),
        (build_document(),    DOCUMENT_XLSX,    SHEET_DOCUMENT),
        (build_drawing(),     DRAWING_XLSX,     SHEET_DRAWING),
        (build_comment(),     COMMENT_XLSX,     SHEET_COMMENT),
        (build_manufacture(), MANUFACTURE_XLSX, SHEET_MANUFACTURE),
    ]
    for df, path, sheet in targets:
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(path, sheet_name=sheet, index=False)
        print(f"  [OK] {path.name:<28} {df.shape[0]:>3} rows x {df.shape[1]} cols")


if __name__ == "__main__":
    main()
