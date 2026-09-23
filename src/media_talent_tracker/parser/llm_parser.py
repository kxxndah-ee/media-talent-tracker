"""LLM-assisted parser for complex or narrative media appointment announcements."""

import json
import os
import re
from typing import Any
from .regex_parser import ParsedPersonnelEntry, extract_rank_level, extract_beat


class LLMNoticeParser:
    """Optional LLM parser using Gemini API (via google-genai SDK)."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Failed to initialize google-genai client: {e}")
                self.client = None

    def is_available(self) -> bool:
        return self.client is not None

    def parse_complex_article(
        self,
        article_text: str,
        default_company: str = "",
    ) -> list[ParsedPersonnelEntry]:
        if not self.is_available():
            return []

        prompt = f"""
당신은 한국 언론사 인사이동 기사 전문 분석기입니다.
다음 기사 본문에서 인사이동 내역을 JSON 배열 형태로 추출해주세요.

[입력 기사]
{article_text}

[추출 JSON 스키마]
[
  {{
    "company": "언론사명 (예: 조선일보, 한국경제)",
    "action_type": "구분 (승진, 전보, 보임, 영입, 퇴임 등)",
    "department": "부서 또는 국 (예: 편집국 사회부, 논설위원실)",
    "title": "직급 및 직책 (예: 부장, 논설위원, 차장)",
    "name": "성명 (한글)",
    "hanja": "한자 성명 (있는 경우만, 예: 洪吉童, 없으면 null)",
    "previous_company": "기사에서 언급된 직전 언론사 (예: '(전 동아일보 부장)'인 경우 '동아일보', 없으면 null)"
  }}
]
결과는 오직 유효한 JSON 배열만 반환하세요. 마크다운 코드 블록(```json) 없이 순수 JSON만 출력하세요.
"""
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            raw = response.text.strip()
            # Clean possible markdown fence
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            items = json.loads(raw)
            results: list[ParsedPersonnelEntry] = []
            for it in items:
                comp = it.get("company") or default_company or "미지정 언론사"
                title = it.get("title", "기자")
                dept = it.get("department", "본사")
                rank = extract_rank_level(title)
                beat = extract_beat(f"{dept} {title}")
                action = it.get("action_type", "전보")
                prev_comp = it.get("previous_company")
                if prev_comp or "영입" in action or "전입" in action:
                    action = "영입/이직"

                results.append(
                    ParsedPersonnelEntry(
                        company=comp,
                        action_type=action,
                        department=dept,
                        title=title,
                        name=it.get("name", ""),
                        hanja=it.get("hanja"),
                        rank_level=rank,
                        beat=beat,
                        previous_company=prev_comp,
                        raw_text=f"{dept} {title} {it.get('name')}",
                    )
                )
            return results
        except Exception as e:
            print(f"LLM parsing failed: {e}")
            return []
