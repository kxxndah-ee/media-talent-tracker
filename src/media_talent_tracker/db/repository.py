"""Database repository for querying and managing media talent data."""

import sqlite3
from contextlib import contextmanager
from typing import Any, Generator
from .schema import get_db_connection


class Repository:
    def __init__(self, db_path=None):
        self.db_path = db_path

    @contextmanager
    def _get_conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = get_db_connection(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    # ----------------- Articles -----------------
    def add_article(
        self,
        title: str,
        media_company: str,
        published_date: str,
        content: str,
        url: str | None = None,
    ) -> int:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO articles (title, media_company, published_date, content, url)
                VALUES (?, ?, ?, ?, ?)
                """,
                (title, media_company, published_date, content, url),
            )
            conn.commit()
            return cursor.lastrowid

    def get_articles(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM articles ORDER BY published_date DESC, id DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    # ----------------- Persons -----------------
    def search_persons(
        self,
        name: str = "",
        company: str = "",
        department: str = "",
        title: str = "",
        keyword: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            query = """
                SELECT p.*,
                       COUNT(DISTINCT c.id) as career_count,
                       COUNT(DISTINCT t.id) as transfer_count
                FROM persons p
                LEFT JOIN career_records c ON p.id = c.person_id
                LEFT JOIN transfers t ON p.id = t.person_id
                WHERE 1=1
            """
            params: list[Any] = []

            if name:
                query += " AND (p.name LIKE ? OR p.hanja LIKE ?)"
                params.extend([f"%{name}%", f"%{name}%"])

            if company:
                query += " AND p.current_company LIKE ?"
                params.append(f"%{company}%")

            if department:
                query += " AND p.current_department LIKE ?"
                params.append(f"%{department}%")

            if title:
                query += " AND p.current_title LIKE ?"
                params.append(f"%{title}%")

            if keyword:
                query += """
                    AND (p.name LIKE ? OR p.current_company LIKE ? OR
                         p.current_department LIKE ? OR p.current_title LIKE ? OR
                         p.primary_beat LIKE ?)
                """
                kw = f"%{keyword}%"
                params.extend([kw, kw, kw, kw, kw])

            query += """
                GROUP BY p.id
                ORDER BY p.last_updated_date DESC, p.id DESC
                LIMIT ?
            """
            params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_person(self, person_id: int) -> dict[str, Any] | None:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM persons WHERE id = ?", (person_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_person_career(self, person_id: int) -> list[dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT c.*, a.title as article_title, a.url as article_url
                FROM career_records c
                LEFT JOIN articles a ON c.article_id = a.id
                WHERE c.person_id = ?
                ORDER BY c.change_date DESC, c.id DESC
                """,
                (person_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def add_person(
        self,
        name: str,
        hanja: str | None = None,
        company: str | None = None,
        department: str | None = None,
        title: str | None = None,
        rank_level: int = 2,
        beat: str | None = None,
        date: str | None = None,
        notes: str | None = None,
    ) -> int:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO persons (
                    name, hanja, current_company, current_department,
                    current_title, current_rank_level, primary_beat,
                    last_updated_date, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (name, hanja, company, department, title, rank_level, beat, date, notes),
            )
            conn.commit()
            return cursor.lastrowid

    def update_person_current(
        self,
        person_id: int,
        company: str,
        department: str,
        title: str,
        rank_level: int,
        date: str,
        hanja: str | None = None,
        beat: str | None = None,
    ) -> None:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            query = """
                UPDATE persons
                SET current_company = ?,
                    current_department = ?,
                    current_title = ?,
                    current_rank_level = ?,
                    last_updated_date = ?
            """
            params: list[Any] = [company, department, title, rank_level, date]

            if hanja:
                query += ", hanja = COALESCE(hanja, ?)"
                params.append(hanja)
            if beat:
                query += ", primary_beat = COALESCE(primary_beat, ?)"
                params.append(beat)

            query += " WHERE id = ?"
            params.append(person_id)

            cursor.execute(query, params)
            conn.commit()

    # ----------------- Career Records -----------------
    def add_career_record(
        self,
        person_id: int,
        change_date: str,
        company: str,
        department: str,
        title: str,
        rank_level: int,
        action_type: str,
        article_id: int | None = None,
        raw_text: str | None = None,
    ) -> int:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO career_records (
                    person_id, article_id, change_date, company,
                    department, title, rank_level, action_type, raw_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    person_id,
                    article_id,
                    change_date,
                    company,
                    department,
                    title,
                    rank_level,
                    action_type,
                    raw_text,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    # ----------------- Transfers -----------------
    def add_transfer(
        self,
        person_id: int,
        from_company: str,
        to_company: str,
        transfer_date: str,
        from_title: str | None = None,
        to_title: str | None = None,
        gap_days: int | None = None,
        confidence_score: int = 80,
        detection_reason: str | None = None,
    ) -> int:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id FROM transfers
                WHERE person_id = ? AND from_company = ? AND to_company = ? AND transfer_date = ?
                """,
                (person_id, from_company, to_company, transfer_date),
            )
            existing = cursor.fetchone()
            if existing:
                return existing[0]

            cursor.execute(
                """
                INSERT INTO transfers (
                    person_id, from_company, to_company, from_title,
                    to_title, transfer_date, gap_days, confidence_score, detection_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    person_id,
                    from_company,
                    to_company,
                    from_title,
                    to_title,
                    transfer_date,
                    gap_days,
                    confidence_score,
                    detection_reason,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_all_transfers(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT t.*, p.name, p.hanja, p.primary_beat
                FROM transfers t
                JOIN persons p ON t.person_id = p.id
                ORDER BY t.transfer_date DESC, t.id DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    # ----------------- Homonyms / Disambiguation -----------------
    def add_homonym_candidate(
        self,
        name: str,
        person_a_id: int,
        person_b_id: int,
        similarity_score: int,
        conflict_reason: str,
    ) -> int:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            p1, p2 = min(person_a_id, person_b_id), max(person_a_id, person_b_id)
            cursor.execute(
                """
                INSERT OR IGNORE INTO homonym_candidates (
                    name, person_a_id, person_b_id, similarity_score, conflict_reason
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (name, p1, p2, similarity_score, conflict_reason),
            )
            conn.commit()
            return cursor.lastrowid

    def get_homonym_candidates(self, status: str = "suspected") -> list[dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT h.*,
                       pa.name as name_a, pa.hanja as hanja_a, pa.current_company as company_a,
                       pa.current_title as title_a, pa.primary_beat as beat_a,
                       pb.name as name_b, pb.hanja as hanja_b, pb.current_company as company_b,
                       pb.current_title as title_b, pb.primary_beat as beat_b
                FROM homonym_candidates h
                JOIN persons pa ON h.person_a_id = pa.id
                JOIN persons pb ON h.person_b_id = pb.id
                WHERE h.status = ?
                ORDER BY h.similarity_score DESC, h.id DESC
                """,
                (status,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def merge_persons(self, target_id: int, source_id: int) -> None:
        """Merge source person profile into target person profile."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE career_records SET person_id = ? WHERE person_id = ?",
                (target_id, source_id),
            )
            cursor.execute(
                "UPDATE transfers SET person_id = ? WHERE person_id = ?",
                (target_id, source_id),
            )
            cursor.execute(
                """
                SELECT company, department, title, rank_level, change_date
                FROM career_records
                WHERE person_id = ?
                ORDER BY change_date DESC, id DESC LIMIT 1
                """,
                (target_id,),
            )
            latest = cursor.fetchone()
            if latest:
                cursor.execute(
                    """
                    UPDATE persons
                    SET current_company = ?, current_department = ?,
                        current_title = ?, current_rank_level = ?,
                        last_updated_date = ?, is_verified = 1
                    WHERE id = ?
                    """,
                    (latest[0], latest[1], latest[2], latest[3], latest[4], target_id),
                )

            cursor.execute(
                """
                UPDATE homonym_candidates
                SET status = 'merged'
                WHERE (person_a_id = ? AND person_b_id = ?)
                   OR (person_a_id = ? AND person_b_id = ?)
                """,
                (target_id, source_id, source_id, target_id),
            )

            cursor.execute("DELETE FROM persons WHERE id = ?", (source_id,))
            conn.commit()

    def confirm_separate_persons(self, person_a_id: int, person_b_id: int) -> None:
        """Mark two persons as confirmed separate homonyms."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE homonym_candidates
                SET status = 'confirmed_separate'
                WHERE (person_a_id = ? AND person_b_id = ?)
                   OR (person_a_id = ? AND person_b_id = ?)
                """,
                (person_a_id, person_b_id, person_b_id, person_a_id),
            )
            cursor.execute("UPDATE persons SET is_verified = 1 WHERE id IN (?, ?)", (person_a_id, person_b_id))
            conn.commit()

    # ----------------- Metadata & Stats -----------------
    def get_filter_options(self, company: str = "") -> dict[str, list[str]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT current_company FROM persons WHERE current_company IS NOT NULL AND current_company != '' ORDER BY current_company")
            companies = [r[0] for r in cursor.fetchall()]

            if company and company != "전체":
                cursor.execute(
                    "SELECT DISTINCT current_department FROM persons WHERE current_company = ? AND current_department IS NOT NULL AND current_department != '' ORDER BY current_department",
                    (company,),
                )
            else:
                cursor.execute("SELECT DISTINCT current_department FROM persons WHERE current_department IS NOT NULL AND current_department != '' ORDER BY current_department")
            depts = [r[0] for r in cursor.fetchall()]

            if company and company != "전체":
                cursor.execute(
                    "SELECT DISTINCT current_title FROM persons WHERE current_company = ? AND current_title IS NOT NULL AND current_title != '' ORDER BY current_title",
                    (company,),
                )
            else:
                cursor.execute("SELECT DISTINCT current_title FROM persons WHERE current_title IS NOT NULL AND current_title != '' ORDER BY current_title")
            titles = [r[0] for r in cursor.fetchall()]

            cursor.execute("SELECT DISTINCT primary_beat FROM persons WHERE primary_beat IS NOT NULL AND primary_beat != '' ORDER BY primary_beat")
            beats = [r[0] for r in cursor.fetchall()]

            return {
                "companies": companies,
                "departments": depts,
                "titles": titles,
                "beats": beats,
            }

    def get_stats(self) -> dict[str, int]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM persons")
            total_persons = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM career_records")
            total_careers = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM transfers")
            total_transfers = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM articles")
            total_articles = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM homonym_candidates WHERE status = 'suspected'")
            suspected_homonyms = cursor.fetchone()[0]

            return {
                "total_persons": total_persons,
                "total_careers": total_careers,
                "total_transfers": total_transfers,
                "total_articles": total_articles,
                "suspected_homonyms": suspected_homonyms,
            }

    # ----------------- Settings / Auth -----------------
    def get_setting(self, key: str, default: str = "") -> str:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO app_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
            conn.commit()
