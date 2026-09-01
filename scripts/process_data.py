#!/usr/bin/env python3
"""
process_data.py - data/street_trees_seed.json을 Jekyll 페이지 생성용 JSON으로 가공

입력: data/street_trees_seed.json (원본 컬럼코드 그대로인 dict 리스트)
출력: _rawdata/garo.json (가로수길 목록), search_index.json (검색용, 루트)

사용법:
  python scripts/process_data.py
"""
import json, re, hashlib, sys
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
RAW = ROOT / "data" / "street_trees_seed.json"
OUT = ROOT / "_rawdata" / "garo.json"
SEARCH_INDEX_OUT = ROOT / "search_index.json"

SIDO_FULL_TO_SHORT = {
    "서울특별시": "서울", "부산광역시": "부산", "인천광역시": "인천",
    "대구광역시": "대구", "광주광역시": "광주", "대전광역시": "대전",
    "울산광역시": "울산", "세종특별자치시": "세종",
    "경기도": "경기",
    "강원특별자치도": "강원", "강원도": "강원",
    "충청북도": "충북", "충청남도": "충남",
    "전북특별자치도": "전북", "전라북도": "전북", "전라남도": "전남",
    "경상북도": "경북", "경상남도": "경남",
    "제주특별자치도": "제주", "제주도": "제주",
}


def guess_sido_sggu(instt_nm: str):
    """제공기관명(예: "경상남도 함양군", "전남광주통합특별시 화순군")에서 시도/시군구 파싱."""
    text = (instt_nm or "").strip()
    if not text:
        return "", ""
    if text.startswith("전남광주통합특별시"):
        rest = text[len("전남광주통합특별시"):].strip()
        sggu = rest.split()[0] if rest else ""
        short = "광주" if sggu.endswith("구") else "전남"
        return short, sggu
    tokens = text.split()
    sido_full = tokens[0]
    short = SIDO_FULL_TO_SHORT.get(sido_full, "")
    sggu = tokens[1] if len(tokens) > 1 else ""
    return short, sggu


def make_slug(name: str, road: str) -> str:
    slug = re.sub(r"[^\w가-힣\s-]", "", name).strip()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    h = hashlib.md5(f"{name}|{road}".encode("utf-8")).hexdigest()[:6]
    return f"{slug}-{h}" if slug else h


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    items = []
    seen_slugs = Counter()
    for d in raw:
        # 필드명 주의: Jekyll 내장 Page.name과 충돌하므로 "garoName" 사용
        garo_name = (d.get("STTREE_STRET_NM") or "").strip()
        instt_nm = (d.get("INSTT_NM") or "").strip()
        do_short, sigungu = guess_sido_sggu(instt_nm)
        if not garo_name or not do_short:
            continue

        road_nm = (d.get("ROAD_NM") or "").strip()
        slug = make_slug(garo_name, road_nm or instt_nm)
        seen_slugs[slug] += 1
        if seen_slugs[slug] > 1:
            slug = f"{slug}-{seen_slugs[slug]}"

        items.append({
            "garoName": garo_name,
            "doShort": do_short,
            "sigungu": sigungu,
            "intro": (d.get("STTREE_STRET_INTRCN") or "").strip(),
            "species": (d.get("STTREE_KND") or "").strip(),
            "treeCount": (d.get("STTREE_CO") or "").strip(),
            "length": (d.get("STTREE_STRET_LT") or "").strip(),
            "plantYear": (d.get("PLT_YEAR") or "").strip(),
            "roadNm": road_nm,
            "roadKnd": (d.get("ROAD_KND") or "").strip(),
            "roadSection": (d.get("ROAD_SCTN") or "").strip(),
            "tel": (d.get("PHONE_NUMBER") or "").strip(),
            "institution": (d.get("INSTITUTION_NM") or "").strip(),
            "lat": (d.get("START_LATITUDE") or "").strip(),
            "lng": (d.get("START_LONGITUDE") or "").strip(),
            "endLat": (d.get("END_LATITUDE") or "").strip(),
            "endLng": (d.get("END_LONGITUDE") or "").strip(),
            "slug": slug,
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"가로수길 {len(items)}개 저장 → {OUT}")

    do_counts = Counter(i["doShort"] for i in items)
    print("\n지역별 수:")
    for do, cnt in sorted(do_counts.items(), key=lambda x: -x[1]):
        print(f"  {do}: {cnt}개")

    coord_count = sum(1 for i in items if i["lat"] and i["lng"])
    intro_count = sum(1 for i in items if i["intro"])
    print(f"\n좌표 보유: {coord_count}개 / 소개글 보유: {intro_count}개")

    index = [
        {"n": i["garoName"], "slug": i["slug"], "doShort": i["doShort"], "sigungu": i["sigungu"]}
        for i in items
    ]
    SEARCH_INDEX_OUT.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size_mb = SEARCH_INDEX_OUT.stat().st_size / 1024 / 1024
    print(f"\n검색 인덱스 {len(index)}건 저장 → {SEARCH_INDEX_OUT} ({size_mb:.1f}MB)")


if __name__ == "__main__":
    main()
