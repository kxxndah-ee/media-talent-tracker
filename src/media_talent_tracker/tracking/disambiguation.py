"""Homonym disambiguation and identity matching engine for media personnel."""

from datetime import datetime
from typing import Any
from ..parser.regex_parser import ParsedPersonnelEntry


def calculate_match_score(
    entry: ParsedPersonnelEntry,
    person: dict[str, Any],
    change_date: str,
) -> tuple[int, str]:
    """Calculate match score (0-100+) between a parsed appointment entry and an existing person profile.

    Returns:
        (score, explanation)
    """
    reasons = []
    score = 0

    # 1. Name Check (Must be identical Hangul name)
    if entry.name != person["name"]:
        return (-1000, "성명 불일치")

    # 2. Hanja Check (Most decisive signal)
    entry_hanja = entry.hanja
    person_hanja = person.get("hanja")

    if entry_hanja and person_hanja:
        if entry_hanja == person_hanja:
            score += 55
            reasons.append(f"한자 일치({entry_hanja})")
        else:
            # Different Hanja -> Definite homonym
            return (-1000, f"한자 불일치(신규:{entry_hanja} vs 기존:{person_hanja})")
    elif entry_hanja or person_hanja:
        # One has Hanja and one does not
        score += 5

    # 3. Company & Hierarchy Context
    same_company = entry.company == person.get("current_company")
    rank_delta = entry.rank_level - (person.get("current_rank_level") or 2)

    # Calculate date difference if possible
    last_date_str = person.get("last_updated_date")
    gap_days = None
    if last_date_str and change_date:
        try:
            d_new = datetime.strptime(change_date[:10], "%Y-%m-%d")
            d_old = datetime.strptime(last_date_str[:10], "%Y-%m-%d")
            gap_days = (d_new - d_old).days
        except Exception:
            gap_days = None

    if same_company:
        score += 35
        reasons.append(f"동일 언론사({entry.company})")

        # Contemporaneous conflict check
        if gap_days is not None and gap_days == 0 and abs(rank_delta) >= 2:
            return (-500, "동일 일자 상이 직급 동시 발령(사내 동명이인)")

        # Normal internal promotion / transfer ladder
        if 0 <= rank_delta <= 2:
            score += 25
            reasons.append("정상 직급 승진/보임")
        elif rank_delta == -1:
            score += 15
            reasons.append("수평 전보")
        elif rank_delta < -2:
            score -= 40
            reasons.append("급격한 직급 강등(동명이인 의심)")
    else:
        # Different company: Potential Transfer or Cross-Company Homonym
        reasons.append(f"타 언론사({person.get('current_company')} -> {entry.company})")

        # Explicit previous company match (e.g. '전 XX일보 부장')
        if entry.previous_company and entry.previous_company == person.get("current_company"):
            score += 60
            reasons.append(f"기사 내 직전 소속사({entry.previous_company}) 직접 명시")

        # Rank compatibility for cross-company move
        # (People usually move laterally or for promotion, e.g. 차장 -> 부장, 부장 -> 부국장)
        if 0 <= rank_delta <= 2:
            score += 30
            reasons.append("이직 직급 연속성 부합")
        elif rank_delta == -1:
            score += 15
            reasons.append("이직 수평 이동 부합")
        elif rank_delta < -1:
            score -= 50
            reasons.append("이직 직급 불일치(기존 고직급 -> 신규 저직급)")
        elif rank_delta > 3:
            score -= 30
            reasons.append("비현실적 직급 비약")

        # Time window check (1 month ~ 18 months gap is typical for inter-company moves)
        if gap_days is not None:
            if 0 <= gap_days <= 540:  # within 18 months
                score += 25
                reasons.append(f"이직 타임라인 윈도우 부합({gap_days}일)")
            elif gap_days < 0 and abs(gap_days) < 30:
                # Slight overlap in appointment notice publishing
                score += 5
            elif gap_days < -30:
                score -= 30
                reasons.append("시간 역전(신규 발령일이 이전 발령일보다 현저히 앞섬)")
            elif gap_days > 540:
                score -= 10
                reasons.append("긴 공백기(1.5년 초과)")

    # 4. Beat (Domain Specialty) Consistency
    person_beat = person.get("primary_beat") or "일반"
    if entry.beat != "일반" and person_beat != "일반":
        if entry.beat == person_beat:
            score += 20
            reasons.append(f"전문 분야 일치({entry.beat})")
        else:
            # Different beats (e.g. 정치 vs 문화)
            score -= 10
            reasons.append(f"전문 분야 상이({person_beat} vs {entry.beat})")

    explanation = ", ".join(reasons)
    return (score, explanation)
