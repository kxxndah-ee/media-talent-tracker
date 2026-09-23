"""High-precision Regex Parser for Korean Media Appointment Notices (인사 기사 파서)."""

import re
from dataclasses import dataclass
from typing import Any

# Rank Hierarchy Mapping (Evaluated in strict precedence order)
RANK_PATTERNS = [
    (7, re.compile(r"(대표이사|사장|부사장|전무|상무|이사|주필|논설주간|고문|감사)")),
    (5, re.compile(r"(부국장대우|부국장|부주필|총괄에디터|에디터)")),
    (6, re.compile(r"(국장|본부장|논설위원|실장|주간)")),
    (4, re.compile(r"(부장대우|부석간)")),
    (3, re.compile(r"(차장대우|부데스크|선임기자)")),
    (4, re.compile(r"(부장|센터장|데스크)")),
    (3, re.compile(r"(차장|팀장)")),
    (1, re.compile(r"(수습기자|수습|인턴)")),
    (2, re.compile(r"(기자|전문기자|특파원|PD|아나운서)")),
    (1, re.compile(r"(사원)")),
]

BEAT_PATTERNS = [
    ("정치", re.compile(r"(정치|국회|청와대|대통령실|외교|안보|통일)")),
    ("경제/산업", re.compile(r"(경제|금융|증권|산업|기업|유통|부동산|건설|바이오|IT|과학|테크|반도체|모빌리티)")),
    ("사회/법조", re.compile(r"(사회|법조|검찰|경찰|사건|노동|전국|지역|시민)")),
    ("문화/스포츠", re.compile(r"(문화|스포츠|연예|라이프|여행|학술|출판|주말)")),
    ("디지털/영상", re.compile(r"(디지털|뉴미디어|온라인|영상|사진|그래픽|오디오|유튜브)")),
    ("오피니언/논설", re.compile(r"(논설|오피니언|칼럼|기획위원)")),
]

BULLETS_REGEX = r"[▲◆◇■◎○▶▶\-·●□★☆]"


@dataclass
class ParsedPersonnelEntry:
    company: str
    action_type: str  # 승진, 전보, 보임, 영입, 퇴임, 위촉 등
    department: str
    title: str
    name: str
    hanja: str | None = None
    rank_level: int = 2
    beat: str = "일반"
    previous_company: str | None = None  # (전 OO일보 ...) 에서 추출된 전 직장
    raw_text: str = ""


def extract_rank_level(title: str) -> int:
    for rank, pattern in RANK_PATTERNS:
        if pattern.search(title):
            return rank
    return 2  # default: 기자급


def extract_beat(dept_and_title: str) -> str:
    for beat, pattern in BEAT_PATTERNS:
        if pattern.search(dept_and_title):
            return beat
    return "일반"


def clean_media_name(name: str) -> str:
    """Clean company name tokens like '[인사] 조선일보' -> '조선일보'."""
    s = re.sub(r"[\[\(【<]인사[\]\)】>]", "", name)
    s = re.sub(r"^[◆◇■◎○▲\s]+", "", s)
    s = re.sub(r"[\s]+.*(?:인사|발령)$", "", s)
    return s.strip()


def split_compound_dept_and_title(raw_token: str) -> tuple[str, str]:
    """Split compound Korean dept/title tokens like '정치부장' -> ('정치부', '부장')."""
    token = raw_token.strip()

    # Pattern: [OO부][장] e.g. 정치부장, 사회부장, 경제부장
    if token.endswith("부장") and len(token) > 2:
        prefix = token[:-2]
        dept = prefix if prefix.endswith("부") else f"{prefix}부"
        return (dept, "부장")

    # Pattern: [OO국][장] e.g. 편집국장, 보도국장, 디지털국장
    if token.endswith("국장") and len(token) > 2:
        prefix = token[:-2]
        dept = prefix if prefix.endswith("국") else f"{prefix}국"
        return (dept, "국장")

    # Pattern: [OO팀][장] e.g. 정치팀장, 사건팀장
    if token.endswith("팀장") and len(token) > 2:
        prefix = token[:-2]
        dept = prefix if prefix.endswith("팀") else f"{prefix}팀"
        return (dept, "팀장")

    # Pattern: [OO실][장] e.g. 논설위원실장, 전략기획실장
    if token.endswith("실장") and len(token) > 2:
        prefix = token[:-2]
        dept = prefix if prefix.endswith("실") else f"{prefix}실"
        return (dept, "실장")

    # Generic dept ending match
    dept_split = re.match(r"^(.+?(?:부|국|실|팀|본부|센터|소|처|단))([가-힣]+)$", token)
    if dept_split:
        return (dept_split.group(1), dept_split.group(2))

    return ("본사", token)


class MediaNoticeParser:
    """Parser for parsing Korean media personnel appointment articles."""

    def parse_article(
        self,
        article_text: str,
        default_company: str = "",
        published_date: str = "",
    ) -> list[ParsedPersonnelEntry]:
        results: list[ParsedPersonnelEntry] = []
        lines = [line.strip() for line in article_text.splitlines() if line.strip()]

        current_company = clean_media_name(default_company)
        current_action = "전보/발령"

        # Check title line for company name if default is empty
        if not current_company and lines:
            header_match = re.search(r"\[인사\]\s*([가-힣A-Za-z0-9]+(?:신문|일보|뉴스|방송|경제|미디어|통신|TV|일간|헤럴드))", lines[0])
            if header_match:
                current_company = header_match.group(1).strip()

        for line in lines:
            # 1. Check for company section header
            comp_match = re.match(r"^[◆◇■◎○]?\s*(?:\[인사\])?\s*([가-힣A-Za-z0-9]+(?:신문|일보|뉴스|방송|경제|미디어|통신|TV|헤럴드|타임스|저널))\s*$", line)
            if comp_match:
                current_company = clean_media_name(comp_match.group(1))
                continue

            # 2. Check for action category header (e.g. '◇승진', '◇ 전보', '<보임>', '◆ 승진')
            action_match = re.match(r"^[◇◆■◎<\[\s]*(승진|전보|보임|신임|영입|전입|파견|퇴임|선임|위촉|승격)\s*[>\]]?$", line)
            if action_match:
                current_action = action_match.group(1)
                continue

            # 3. Check for bullet entries
            bullet_chunks = re.split(rf"(?=[▲▶\-·●□★☆])", line)
            for chunk in bullet_chunks:
                chunk = chunk.strip()
                if not chunk:
                    continue

                entry = self._parse_entry_line(chunk, current_company, current_action)
                if entry:
                    results.append(entry)

        return results

    def _parse_entry_line(
        self,
        line: str,
        current_company: str,
        current_action: str,
    ) -> ParsedPersonnelEntry | None:
        clean_line = re.sub(rf"^{BULLETS_REGEX}\s*", "", line).strip()
        if not clean_line:
            return None

        # Ignore obvious non-entry lines
        if any(w in clean_line for w in ["대표번호", "문의", "배포일", "전화", "구독신청"]):
            return None

        # Check for previous company pattern e.g. '(전 OO일보 부장)', '(전 한국경제 차장)'
        prev_company = None
        prev_comp_match = re.search(r"\(전\s+([가-힣A-Za-z0-9]+(?:신문|일보|뉴스|방송|경제|미디어|통신|TV))(?:\s+[^)]+)?\)", clean_line)
        if prev_comp_match:
            prev_company = prev_comp_match.group(1)
            clean_line = clean_line.replace(prev_comp_match.group(0), "").strip()

        # Check for Hanja e.g. '홍길동(洪吉童)'
        hanja = None
        hanja_match = re.search(r"([가-힣]{2,4})\s*\(([一-龥]+)\)", clean_line)
        if hanja_match:
            name = hanja_match.group(1)
            hanja = hanja_match.group(2)
            clean_line = clean_line[:hanja_match.start()] + name + clean_line[hanja_match.end():]
            clean_line = clean_line.strip()
        else:
            name_match = re.search(r"([가-힣]{2,4})$", clean_line)
            if not name_match:
                return None
            name = name_match.group(1)

        pos_part = clean_line[:clean_line.rfind(name)].strip()
        if not pos_part:
            return None

        # Clean internal rank parentheses like '(차장대우)', '(승진)'
        internal_rank_addon = ""
        rank_parenthesis = re.search(r"\(([^)]+)\)", pos_part)
        if rank_parenthesis:
            inside = rank_parenthesis.group(1)
            if any(k in inside for k in ["대우", "승진", "전보", "보임", "전무", "상무", "국장", "부장", "차장"]):
                internal_rank_addon = inside
            pos_part = pos_part.replace(rank_parenthesis.group(0), "").strip()

        tokens = pos_part.split()
        if len(tokens) == 1:
            dept, title = split_compound_dept_and_title(tokens[0])
        elif len(tokens) >= 2:
            dept = " ".join(tokens[:-1])
            title = tokens[-1]
        else:
            dept = "본사"
            title = pos_part

        if internal_rank_addon and internal_rank_addon not in title:
            title = f"{title}({internal_rank_addon})"

        rank_level = extract_rank_level(f"{title} {internal_rank_addon}")
        beat = extract_beat(f"{dept} {title}")

        action = current_action
        if prev_company or "영입" in current_action or "전입" in current_action:
            action = "영입/이직"

        return ParsedPersonnelEntry(
            company=current_company or "미지정 언론사",
            action_type=action,
            department=dept,
            title=title,
            name=name,
            hanja=hanja,
            rank_level=rank_level,
            beat=beat,
            previous_company=prev_company,
            raw_text=line.strip(),
        )
