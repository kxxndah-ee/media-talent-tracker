"""Unit tests for disambiguation and cross-company transfer tracking."""

import os
import tempfile
import unittest
from pathlib import Path

from src.media_talent_tracker.db.schema import init_db
from src.media_talent_tracker.db.repository import Repository
from src.media_talent_tracker.parser.regex_parser import ParsedPersonnelEntry
from src.media_talent_tracker.tracking.disambiguation import calculate_match_score
from src.media_talent_tracker.tracking.transfer_detector import TransferDetectorPipeline


class TestTrackingAndDisambiguation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_tracker.db"
        init_db(self.db_path)
        self.repo = Repository(self.db_path)
        self.pipeline = TransferDetectorPipeline(self.repo)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_intra_company_promotion(self):
        # 1. First appointment: reporter
        e1 = ParsedPersonnelEntry(
            company="조선일보",
            action_type="승진",
            department="사회부",
            title="차장",
            name="홍길동",
            hanja="洪吉童",
            rank_level=3,
            beat="사회/법조",
        )
        res1 = self.pipeline.ingest_entries([e1], published_date="2024-01-01")
        self.assertEqual(res1["created_persons"], 1)

        # 2. Second appointment: promotion to department head
        e2 = ParsedPersonnelEntry(
            company="조선일보",
            action_type="승진",
            department="사회부",
            title="부장",
            name="홍길동",
            hanja="洪吉童",
            rank_level=4,
            beat="사회/법조",
        )
        res2 = self.pipeline.ingest_entries([e2], published_date="2025-01-01")
        self.assertEqual(res2["updated_persons"], 1)
        self.assertEqual(res2["detected_transfers"], 0)

        # Verify career records
        persons = self.repo.search_persons(name="홍길동")
        self.assertEqual(len(persons), 1)
        p = persons[0]
        self.assertEqual(p["current_title"], "부장")
        careers = self.repo.get_person_career(p["id"])
        self.assertEqual(len(careers), 2)

    def test_inter_company_transfer_detection(self):
        # 1. Person active at Media A
        e1 = ParsedPersonnelEntry(
            company="중앙일보",
            action_type="승진",
            department="금융부",
            title="차장",
            name="김민준",
            hanja="金民俊",
            rank_level=3,
            beat="경제/산업",
        )
        self.pipeline.ingest_entries([e1], published_date="2024-06-01")

        # 2. Re-appears 8 months later at Media B as department head with explicit previous company mention
        e2 = ParsedPersonnelEntry(
            company="한국경제신문",
            action_type="영입/이직",
            department="금융부",
            title="부장",
            name="김민준",
            hanja=None,
            rank_level=4,
            beat="경제/산업",
            previous_company="중앙일보",
        )
        res2 = self.pipeline.ingest_entries([e2], published_date="2025-02-01")
        self.assertEqual(res2["detected_transfers"], 1)

        transfers = self.repo.get_all_transfers()
        self.assertEqual(len(transfers), 1)
        t = transfers[0]
        self.assertEqual(t["name"], "김민준")
        self.assertEqual(t["from_company"], "중앙일보")
        self.assertEqual(t["to_company"], "한국경제신문")
        self.assertGreaterEqual(t["confidence_score"], 80)

    def test_homonym_separation_by_hanja(self):
        # Two people with exact same Korean name but different Hanja
        e1 = ParsedPersonnelEntry(
            company="한겨레",
            action_type="전보",
            department="사회부",
            title="차장",
            name="이진우",
            hanja="李振宇",
            rank_level=3,
            beat="사회/법조",
        )
        self.pipeline.ingest_entries([e1], published_date="2024-05-01")

        e2 = ParsedPersonnelEntry(
            company="경향신문",
            action_type="승진",
            department="문화부",
            title="부장",
            name="이진우",
            hanja="李鎭雨",
            rank_level=4,
            beat="문화/스포츠",
        )
        res2 = self.pipeline.ingest_entries([e2], published_date="2024-11-01")

        # Different Hanja -> strictly not the same person
        self.assertEqual(res2["created_persons"], 1)
        self.assertEqual(res2["detected_transfers"], 0)

        persons = self.repo.search_persons(name="이진우")
        self.assertEqual(len(persons), 2)


if __name__ == "__main__":
    unittest.main()
