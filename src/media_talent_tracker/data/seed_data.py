"""Realistic seed dataset and loader for Media Talent Tracker."""

from ..db.schema import init_db
from ..db.repository import Repository
from ..parser.regex_parser import MediaNoticeParser
from ..tracking.transfer_detector import TransferDetectorPipeline

SAMPLE_ARTICLES = [
    {
        "title": "[인사] 조선일보",
        "media_company": "조선일보",
        "published_date": "2024-03-01",
        "url": "https://news.example.com/chosun/20240301",
        "content": """[인사] 조선일보
◇승진
▲편집국 정치부 차장대우 홍길동(洪吉童)
▲사회부장 최현우(崔賢宇)
▲경제부 차장 정우성(鄭雨盛)
▲문화부장 강민서
◇전보
▲국제부장 이영희(李英姬)
▲디지털콘텐츠국장 박성훈
▲논설위원실 논설위원 김철수(金哲洙)
"""
    },
    {
        "title": "[인사] 중앙일보",
        "media_company": "중앙일보",
        "published_date": "2024-06-01",
        "url": "https://news.example.com/joongang/20240601",
        "content": """[인사] 중앙일보
◇승진
▲경제국 금융증권부 차장 김민준(金民俊)
▲정치팀장(차장대우) 송태현
▲디지털스페셜팀장 유호진
◇전보
▲사회데스크 부장 배서윤
▲논설위원실 논설위원 윤도현
"""
    },
    {
        "title": "[인사] 매일경제",
        "media_company": "매일경제",
        "published_date": "2024-04-15",
        "url": "https://news.example.com/mk/20240415",
        "content": """[인사] 매일경제
◇승진
▲증권부 차장 박지훈(朴智勳)
▲산업부 부장대우 장수현
▲유통경제부장 황정민
◇전보
▲벤처과학부장 서진우
▲부국장 겸 지식부장 신동엽
"""
    },
    {
        "title": "[인사] 한겨레",
        "media_company": "한겨레",
        "published_date": "2024-05-10",
        "url": "https://news.example.com/hani/20240510",
        "content": """[인사] 한겨레
◇전보
▲사회정책부 차장 이진우(李振宇)
▲정치에디터실 부에디터 문소희
▲탐사보도팀장 권혁준
▲전국부장 오현택
"""
    },
    {
        "title": "[인사] 경향신문",
        "media_company": "경향신문",
        "published_date": "2024-11-20",
        "url": "https://news.example.com/khan/20241120",
        "content": """[인사] 경향신문
◇승진
▲문화부 부장 이진우(李鎭雨)
▲정치부 차장 백승호
▲산업부 부장대우 김다은
◇전보
▲오피니언팀장 손예진
▲기획에디터 조진웅
"""
    },
    {
        "title": "[인사] 동아일보",
        "media_company": "동아일보",
        "published_date": "2025-01-05",
        "url": "https://news.example.com/donga/20250105",
        "content": """[인사] 동아일보
◇승진
▲산업2부 부장 박지훈(朴智勳)
▲정치부 부장대우 차승원
▲사회부 차장 안성기
◇전보
▲편집국 부국장 임수정
▲디지털뉴스팀장 구교환
"""
    },
    {
        "title": "[인사] 조선일보",
        "media_company": "조선일보",
        "published_date": "2025-01-10",
        "url": "https://news.example.com/chosun/20250110",
        "content": """[인사] 조선일보
◇승진
▲정치부 부장 홍길동(洪吉童)
▲경제부 부장 정우성(鄭雨盛)
▲수습기자 정우성
▲사회부 차장 서강준
◇전보
▲논설위원실 논설위원 최현우(崔賢宇)
▲편집국 부국장 이영희(李英姬)
"""
    },
    {
        "title": "[인사] 한국경제신문",
        "media_company": "한국경제신문",
        "published_date": "2025-02-10",
        "url": "https://news.example.com/hankyung/20250210",
        "content": """[인사] 한국경제신문
◇영입
▲금융부 부장 김민준(전 중앙일보 차장)
▲디지털전략총괄 부국장 손석희
◇승진
▲산업부 차장 유재석
▲증권부 부장 하정우
◇전보
▲논설위원실 논설위원 전도연
▲편집국장 주지훈
"""
    },
    {
        "title": "[인사] SBS",
        "media_company": "SBS",
        "published_date": "2025-07-01",
        "url": "https://news.example.com/sbs/20250701",
        "content": """[인사] SBS
◇승진
▲보도본부 정치부 부장대우 송태현
▲사회부 차장 김태리
▲뉴미디어제작부장 남궁민
◇전보
▲논설위원실장 조인성
▲탐사보도에디터 박은빈
"""
    },
    {
        "title": "[인사] 조선일보",
        "media_company": "조선일보",
        "published_date": "2026-02-15",
        "url": "https://news.example.com/chosun/20260215",
        "content": """[인사] 조선일보
◇승진
▲논설위원실 논설위원 홍길동(洪吉童)
▲산업부장(부국장대우) 정우성(鄭雨盛)
▲정치부장 서강준
◇전보
▲편집국장 최현우(崔賢宇)
▲디지털총괄본부장 이영희(李英姬)
"""
    },
    {
        "title": "[인사] 연합뉴스",
        "media_company": "연합뉴스",
        "published_date": "2026-03-01",
        "url": "https://news.example.com/yna/20260301",
        "content": """[인사] 연합뉴스
◇승진
▲경제부 부장 박보검
▲정치부 차장 아이유
▲사회부 부장 송강호
◇영입
▲글로벌콘텐츠센터 에디터 유호진(전 중앙일보 팀장)
"""
    }
]


def load_seed_data(repo: Repository | None = None) -> dict[str, int]:
    """Load realistic seed articles and run the parsing & transfer tracking pipeline."""
    if repo is None:
        init_db()
        repo = Repository()

    parser = MediaNoticeParser()
    pipeline = TransferDetectorPipeline(repo)

    total_articles = 0
    total_entries = 0

    for item in SAMPLE_ARTICLES:
        # Check if already inserted
        existing_articles = repo.get_articles(limit=100)
        already_has = any(a["title"] == item["title"] and a["published_date"] == item["published_date"] for a in existing_articles)
        if already_has:
            continue

        art_id = repo.add_article(
            title=item["title"],
            media_company=item["media_company"],
            published_date=item["published_date"],
            content=item["content"],
            url=item.get("url"),
        )
        total_articles += 1

        entries = parser.parse_article(
            article_text=item["content"],
            default_company=item["media_company"],
            published_date=item["published_date"],
        )
        total_entries += len(entries)

        pipeline.ingest_entries(
            entries=entries,
            published_date=item["published_date"],
            article_id=art_id,
        )

    return {
        "articles_loaded": total_articles,
        "entries_processed": total_entries,
    }


if __name__ == "__main__":
    init_db()
    repo = Repository()
    res = load_seed_data(repo)
    print("Seed data loaded successfully:", res)
    stats = repo.get_stats()
    print("Current DB Stats:", stats)
