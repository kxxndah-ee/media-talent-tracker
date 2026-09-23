"""Cross-company transfer detector and appointment ingestion pipeline."""

from datetime import datetime
from typing import Any
from ..parser.regex_parser import ParsedPersonnelEntry
from .disambiguation import calculate_match_score


class TransferDetectorPipeline:
    def __init__(self, repository):
        self.repo = repository

    def ingest_entries(
        self,
        entries: list[ParsedPersonnelEntry],
        published_date: str,
        article_id: int | None = None,
    ) -> dict[str, Any]:
        """Ingest a list of parsed appointment entries into the database.

        Performs:
        1. Homonym disambiguation against existing profiles
        2. Intra-company promotions/transfers recording
        3. Inter-company transfer detection (이직 포착)
        4. Registration of suspected homonym pairs for human-in-the-loop review
        """
        created_persons = 0
        updated_persons = 0
        detected_transfers = 0
        suspected_homonyms = 0

        for entry in entries:
            # 1. Search existing persons with exact same Hangul name
            existing_candidates = self.repo.search_persons(name=entry.name, limit=20)

            best_match = None
            best_score = -999
            best_explanation = ""

            for cand in existing_candidates:
                score, explanation = calculate_match_score(entry, cand, published_date)
                if score > best_score:
                    best_score = score
                    best_match = cand
                    best_explanation = explanation

            # 2. Decision Logic
            if best_match and best_score >= 65:
                # High confidence same person!
                person_id = best_match["id"]
                old_company = best_match.get("current_company") or ""
                new_company = entry.company

                # Check if company changed -> Inter-company Transfer
                is_transfer = old_company and (old_company != new_company)
                action_type = entry.action_type

                if is_transfer:
                    action_type = "이직/영입" if "영입" not in action_type else action_type

                    # Calculate gap days
                    gap_days = None
                    last_date_str = best_match.get("last_updated_date")
                    if last_date_str and published_date:
                        try:
                            d1 = datetime.strptime(last_date_str[:10], "%Y-%m-%d")
                            d2 = datetime.strptime(published_date[:10], "%Y-%m-%d")
                            gap_days = (d2 - d1).days
                        except Exception:
                            gap_days = None

                    # Confidence score for transfer
                    transfer_conf = min(98, max(65, best_score))
                    reason = f"타사 이직 감지: {old_company}({best_match.get('current_title')}) -> {new_company}({entry.title}). [{best_explanation}]"

                    self.repo.add_transfer(
                        person_id=person_id,
                        from_company=old_company,
                        to_company=new_company,
                        transfer_date=published_date,
                        from_title=best_match.get("current_title"),
                        to_title=entry.title,
                        gap_days=gap_days,
                        confidence_score=transfer_conf,
                        detection_reason=reason,
                    )
                    detected_transfers += 1

                # Record career
                self.repo.add_career_record(
                    person_id=person_id,
                    change_date=published_date,
                    company=new_company,
                    department=entry.department,
                    title=entry.title,
                    rank_level=entry.rank_level,
                    action_type=action_type,
                    article_id=article_id,
                    raw_text=entry.raw_text,
                )

                # Update current profile
                self.repo.update_person_current(
                    person_id=person_id,
                    company=new_company,
                    department=entry.department,
                    title=entry.title,
                    rank_level=entry.rank_level,
                    date=published_date,
                    hanja=entry.hanja,
                    beat=entry.beat if entry.beat != "일반" else None,
                )
                updated_persons += 1

            elif best_match and 35 <= best_score < 65:
                # Ambiguous / Suspected Homonym
                # Create separate person profile, but record candidate pair
                new_person_id = self.repo.add_person(
                    name=entry.name,
                    hanja=entry.hanja,
                    company=entry.company,
                    department=entry.department,
                    title=entry.title,
                    rank_level=entry.rank_level,
                    beat=entry.beat,
                    date=published_date,
                    notes=f"동명이인 의심 자동 분리 (기존 #{best_match['id']}와 유사도 {best_score}점)",
                )

                self.repo.add_career_record(
                    person_id=new_person_id,
                    change_date=published_date,
                    company=entry.company,
                    department=entry.department,
                    title=entry.title,
                    rank_level=entry.rank_level,
                    action_type=entry.action_type,
                    article_id=article_id,
                    raw_text=entry.raw_text,
                )

                self.repo.add_homonym_candidate(
                    name=entry.name,
                    person_a_id=best_match["id"],
                    person_b_id=new_person_id,
                    similarity_score=best_score,
                    conflict_reason=best_explanation,
                )
                created_persons += 1
                suspected_homonyms += 1

            else:
                # New person entity
                new_person_id = self.repo.add_person(
                    name=entry.name,
                    hanja=entry.hanja,
                    company=entry.company,
                    department=entry.department,
                    title=entry.title,
                    rank_level=entry.rank_level,
                    beat=entry.beat,
                    date=published_date,
                )

                self.repo.add_career_record(
                    person_id=new_person_id,
                    change_date=published_date,
                    company=entry.company,
                    department=entry.department,
                    title=entry.title,
                    rank_level=entry.rank_level,
                    action_type=entry.action_type,
                    article_id=article_id,
                    raw_text=entry.raw_text,
                )
                created_persons += 1

        return {
            "created_persons": created_persons,
            "updated_persons": updated_persons,
            "detected_transfers": detected_transfers,
            "suspected_homonyms": suspected_homonyms,
            "total_entries": len(entries),
        }
