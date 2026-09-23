"""Unit tests for the media appointment parser."""

import unittest
from src.media_talent_tracker.parser.regex_parser import (
    MediaNoticeParser,
    extract_rank_level,
    extract_beat,
)


class TestMediaNoticeParser(unittest.TestCase):
    def setUp(self):
        self.parser = MediaNoticeParser()

    def test_basic_article_parsing(self):
        text = """[인사] 조선일보
◇승진
▲정치부장 홍길동(洪吉童)
▲사회부 차장대우 김철수
◇전보
▲논설위원실 논설위원 이영희(李英姬)
"""
        entries = self.parser.parse_article(text, default_company="조선일보")
        self.assertEqual(len(entries), 3)

        e0 = entries[0]
        self.assertEqual(e0.company, "조선일보")
        self.assertEqual(e0.name, "홍길동")
        self.assertEqual(e0.hanja, "洪吉童")
        self.assertEqual(e0.title, "부장")
        self.assertEqual(e0.department, "정치부")
        self.assertEqual(e0.rank_level, 4)
        self.assertEqual(e0.beat, "정치")
        self.assertEqual(e0.action_type, "승진")

        e1 = entries[1]
        self.assertEqual(e1.name, "김철수")
        self.assertIsNone(e1.hanja)
        self.assertIn("차장대우", e1.title)
        self.assertEqual(e1.rank_level, 3)

        e2 = entries[2]
        self.assertEqual(e2.name, "이영희")
        self.assertEqual(e2.hanja, "李英姬")
        self.assertEqual(e2.rank_level, 6)  # 논설위원 is level 6
        self.assertEqual(e2.action_type, "전보")

    def test_previous_company_extraction(self):
        text = """[인사] 한국경제신문
◇영입
▲금융부 부장 김민준(전 중앙일보 차장)
"""
        entries = self.parser.parse_article(text, default_company="한국경제신문")
        self.assertEqual(len(entries), 1)
        e = entries[0]
        self.assertEqual(e.name, "김민준")
        self.assertEqual(e.company, "한국경제신문")
        self.assertEqual(e.previous_company, "중앙일보")
        self.assertEqual(e.action_type, "영입/이직")

    def test_rank_and_beat_extraction(self):
        self.assertEqual(extract_rank_level("수습기자"), 1)
        self.assertEqual(extract_rank_level("산업부 기자"), 2)
        self.assertEqual(extract_rank_level("차장"), 3)
        self.assertEqual(extract_rank_level("정치부장"), 4)
        self.assertEqual(extract_rank_level("부국장"), 5)
        self.assertEqual(extract_rank_level("논설위원"), 6)
        self.assertEqual(extract_rank_level("주필"), 7)

        self.assertEqual(extract_beat("정치부장"), "정치")
        self.assertEqual(extract_beat("금융증권부 차장"), "경제/산업")
        self.assertEqual(extract_beat("사회부 사건팀장"), "사회/법조")
        self.assertEqual(extract_beat("디지털뉴스센터장"), "디지털/영상")


if __name__ == "__main__":
    unittest.main()
