"""Tag_Register.xlsx → Equipment_master.xlsx 변환 스크립트.

루트 디렉토리의 ``Tag_Register.xlsx`` **Sheet1 만** 을 읽어
``eis_app/data/Equipment_master.xlsx`` 의 표준 스키마
(SystemID/SystemName/PackageID/PackageName/TagNo/...) 로 변환해 저장한다.

매핑 규칙 (Sheet1 단독 기준):
  - SystemID   : Sheet1 의 System 이름을 정렬한 순서로 ``SYS-001 ~ SYS-NNN`` 자동 부여
  - PackageID  : ``PKG-{package_code}`` (D 컬럼 'Package' 코드 그대로 사용 →
                 unique PackageID 수 = unique Package 코드 수)
  - PackageName: ``Package {package_code}`` (Tag_Register 에 패키지명이 별도로 없음)
  - TagNo / TagDescription / ManufactureName / ReferenceDrawing : 그대로 매핑
  - AttributeA / AttributeB : Tag_Register 의 ``Attribute A`` / ``Attribute B`` 매핑

실행: ``python eis_app/data/_import_tag_register.py``
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from config import (  # noqa: E402
    EQUIPMENT_XLSX,
    SHEET_EQUIPMENT,
    SHEET_TAG_REGISTER_DATA,
    TAG_REGISTER_XLSX,
)

# 결과물 컬럼 (data_loader / hierarchy_view 가 기대하는 표준 스키마)
EQUIPMENT_COLS = [
    "SystemID", "SystemName", "PackageID", "PackageName",
    "TagNo", "TagDescription", "ManufactureName",
    "AttributeA", "AttributeB", "ReferenceDrawing",
]


def _build_system_id_map(system_names: pd.Series) -> dict[str, str]:
    """SystemName → ``SYS-{idx:03d}`` 매핑을 정렬 순서로 부여한다."""
    uniques = sorted({str(s).strip() for s in system_names.dropna() if str(s).strip()})
    return {name: f"SYS-{i:03d}" for i, name in enumerate(uniques, start=1)}


def build_equipment_from_tag_register(path: Path = TAG_REGISTER_XLSX) -> pd.DataFrame:
    """Tag_Register.xlsx Sheet1 을 읽어 Equipment 표준 스키마 DataFrame 으로 변환."""
    if not path.exists():
        raise FileNotFoundError(f"Tag_Register 파일을 찾을 수 없습니다: {path}")

    raw = pd.read_excel(path, sheet_name=SHEET_TAG_REGISTER_DATA, dtype=object)
    sys_id_map = _build_system_id_map(raw["System"])

    rows: list[dict] = []
    for _, r in raw.iterrows():
        tag = r.get("Tag")
        if pd.isna(tag) or str(tag).strip() == "":
            continue

        system_name = "" if pd.isna(r.get("System")) else str(r["System"]).strip()
        package_code = "" if pd.isna(r.get("Package")) else str(r["Package"]).strip()

        system_id = sys_id_map.get(system_name, "SYS-UNKNOWN")
        # PackageID 는 Package 코드 그대로 사용 (시스템 무관 — unique 수 = Package 코드 종수)
        package_id = f"PKG-{package_code}" if package_code else "PKG-NONE"
        package_name = f"Package {package_code}" if package_code else "Unassigned"

        rows.append({
            "SystemID": system_id,
            "SystemName": system_name,
            "PackageID": package_id,
            "PackageName": package_name,
            "TagNo": str(tag).strip(),
            "TagDescription": "" if pd.isna(r.get("Description")) else str(r["Description"]),
            "ManufactureName": "" if pd.isna(r.get("Manufacture Name")) else str(r["Manufacture Name"]),
            "AttributeA": "" if pd.isna(r.get("Attribute A")) else str(r["Attribute A"]),
            "AttributeB": "" if pd.isna(r.get("Attribute B")) else str(r["Attribute B"]),
            "ReferenceDrawing": "" if pd.isna(r.get("Reference Drawing")) else str(r["Reference Drawing"]),
        })

    return pd.DataFrame(rows, columns=EQUIPMENT_COLS)


def main() -> None:
    df = build_equipment_from_tag_register()
    EQUIPMENT_XLSX.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(EQUIPMENT_XLSX, sheet_name=SHEET_EQUIPMENT, index=False)

    # 요약 출력
    print("[OK] Equipment_master.xlsx update done")
    print(f"     - Total Tag      : {len(df):>5}")
    print(f"     - Unique System  : {df['SystemID'].nunique():>5}")
    print(f"     - Unique Package : {df['PackageID'].nunique():>5}")
    print(f"     - Path           : {EQUIPMENT_XLSX}")


if __name__ == "__main__":
    main()
