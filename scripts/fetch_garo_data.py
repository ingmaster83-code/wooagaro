"""
wooagaro 가로수길 데이터 수집 스크립트
전국가로수길정보표준데이터(publicDataPk=15021145)를 data.go.kr 표준데이터셋
벌크 다운로드 API에서 JSON으로 내려받아 data/street_trees_seed.json으로 저장한다.

원본 데이터 특징:
- localdata.go.kr 파일다운로드 방식이 아니라 표준데이터셋제공시스템(data.go.kr 자체 그리드) 방식
  → www.data.go.kr/download/columList.json 으로 컬럼정보+totalCount를 먼저 얻고,
     www.data.go.kr/download/standard.json 으로 전체 레코드를 한 번에 받아옴(perPage=totalCount)
- 좌표는 시작/종료 위경도(도로 구간)로 이미 WGS84 제공 → 변환 불필요
- 시도/시군구 컬럼이 따로 없고 INSTT_NM(제공기관명, 예: "경상남도 함양군")에서 파싱해야 함
- 소개글(STTREE_STRET_INTRCN)이 사실상 전량 채워져 있어 콘텐츠 밀도가 높음

실행: python scripts/fetch_garo_data.py
"""
import io
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import json
import requests

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
OUT_PATH = DATA_DIR / "street_trees_seed.json"

PUBLIC_DATA_PK = "15021145"
SVC_TABLE_NM = "tn_pubr_public_sttree_stret_svc"
COLUMN_LIST_URL = f"https://www.data.go.kr/download/columList.json?pk={PUBLIC_DATA_PK}&ext=CSV"
STANDARD_URL = "https://www.data.go.kr/download/standard.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": f"https://www.data.go.kr/data/{PUBLIC_DATA_PK}/standard.do",
}


# INSTT_CODE/INSTT_NM(제공기관코드/명)은 서버가 응답에 항상 자동으로 붙여주는 필드라,
# colNmList에 명시적으로 다시 넣으면 API가 200/빈바디로 조용히 실패함 — 요청에서 제외할 것.
ALWAYS_INCLUDED_COLS = {"INSTT_CODE", "INSTT_NM"}


def fetch_columns_and_total():
    resp = requests.get(COLUMN_LIST_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    col_codes = [c["columCode"] for c in data["columList"] if c["columCode"] not in ALWAYS_INCLUDED_COLS]
    total_count = data.get("totalCount") or data["tableVO"].get("totalCount") or 0
    return col_codes, total_count


def fetch_all(col_codes, total_count):
    params = [("publicDataPk", PUBLIC_DATA_PK)]
    for code in col_codes:
        params.append(("colNmList", code))
    params += [
        ("totalCount", str(total_count)),
        ("svcTableNm", SVC_TABLE_NM),
        ("perPage", str(total_count)),
        ("page", "1"),
    ]
    resp = requests.get(STANDARD_URL, headers=HEADERS, params=params, timeout=120)
    resp.raise_for_status()
    return resp.json()


def main():
    col_codes, total_count = fetch_columns_and_total()
    print(f"컬럼 {len(col_codes)}개, totalCount={total_count}")
    if total_count < 1000:
        raise SystemExit(f"totalCount가 비정상적으로 작음({total_count}) — API 응답 확인 필요")

    records = fetch_all(col_codes, total_count)
    if not isinstance(records, list):
        raise SystemExit(f"예상과 다른 응답 형식: {type(records)}")

    print(f"다운로드 완료: {len(records):,}건")

    if OUT_PATH.exists():
        existing = json.loads(OUT_PATH.read_text(encoding="utf-8"))
        if isinstance(existing, list) and existing and len(records) < len(existing) * 0.5:
            raise SystemExit(
                f"수집 건수({len(records)}건)가 기존 데이터({len(existing)}건)의 절반 미만입니다. "
                "다운로드 오류로 판단하여 저장을 중단합니다."
            )

    DATA_DIR.mkdir(exist_ok=True)
    OUT_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"저장 완료: {OUT_PATH}")


if __name__ == "__main__":
    main()
