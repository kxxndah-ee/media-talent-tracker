"""SQLite Database schema and initialization for Media Talent Tracker."""

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "media_tracker.db"


def get_db_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Path | str | None = None) -> None:
    """Initialize database tables and indexes."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 1. Articles table (인사 기사 원문 및 메타데이터)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        media_company TEXT NOT NULL,
        published_date TEXT NOT NULL, -- YYYY-MM-DD
        content TEXT NOT NULL,
        url TEXT,
        parsed_status TEXT DEFAULT 'parsed', -- 'pending', 'parsed', 'failed'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Persons table (식별된 고유 인물 엔티티)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS persons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        hanja TEXT,                     -- 한자 표기 (예: 洪吉童)
        current_company TEXT,           -- 현재 소속사
        current_department TEXT,        -- 현재 부서/국
        current_title TEXT,             -- 현재 직책/직급
        current_rank_level INTEGER DEFAULT 2, -- 1~7 직급 레벨
        primary_beat TEXT,              -- 주요 전문분야 (정치, 경제, 사회, IT 등)
        last_updated_date TEXT,         -- 마지막 인사이동 확인일
        is_verified INTEGER DEFAULT 0,  -- 사용자 수동 검증 여부 (1=검증완료)
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. Career Records table (개별 인사이동 기록)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS career_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_id INTEGER NOT NULL,
        article_id INTEGER,
        change_date TEXT NOT NULL,       -- 발령일 또는 기사 게재일 (YYYY-MM-DD)
        company TEXT NOT NULL,           -- 소속 언론사
        department TEXT,                 -- 부서/국 (예: 편집국 정치부)
        title TEXT NOT NULL,             -- 직책/직급 (예: 부장, 논설위원)
        rank_level INTEGER DEFAULT 2,    -- 1:수습/사원, 2:기자, 3:차장, 4:부장, 5:부국장, 6:국장/논설위원, 7:임원/주필
        action_type TEXT NOT NULL,       -- 승진, 전보, 보임, 이직, 영입, 퇴임, 파견 등
        raw_text TEXT,                   -- 기사 내 원문 줄
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE CASCADE,
        FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE SET NULL
    );
    """)

    # 4. Transfers table (타사 이직 감지 및 기록)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transfers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_id INTEGER NOT NULL,
        from_company TEXT NOT NULL,
        to_company TEXT NOT NULL,
        from_title TEXT,
        to_title TEXT,
        transfer_date TEXT NOT NULL,      -- 이직 확인일
        gap_days INTEGER,                -- 이전 회사 마지막 활동과 새 회사 등장 간의 간격(일)
        confidence_score INTEGER DEFAULT 80, -- 0~100 신뢰도 지수
        detection_reason TEXT,            -- 이직 판정 근거 (직접 표기, 타임라인 윈도우+직급 연속성 등)
        is_confirmed INTEGER DEFAULT 0,  -- 사용자 최종 확정 여부
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE CASCADE
    );
    """)

    # 5. Homonym Candidates table (동명이인 의심 및 관리)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS homonym_candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        person_a_id INTEGER NOT NULL,
        person_b_id INTEGER NOT NULL,
        similarity_score INTEGER,        -- 0~100 유사도 점수 (동일인일 가능성)
        conflict_reason TEXT,            -- 동명이인으로 분리된 사유 (한자 불일치, 직급 역전, 시기 중복 등)
        status TEXT DEFAULT 'suspected', -- 'suspected', 'merged', 'confirmed_separate'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (person_a_id) REFERENCES persons(id) ON DELETE CASCADE,
        FOREIGN KEY (person_b_id) REFERENCES persons(id) ON DELETE CASCADE
    );
    """)

    # 6. App Settings (비밀번호 및 시스템 설정)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)

    # 기본 비밀번호 PIN (초기값: 1234)
    cursor.execute("""
    INSERT OR IGNORE INTO app_settings (key, value)
    VALUES ('auth_pin', '1234');
    """)

    # 인덱스 생성
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_persons_name ON persons(name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_persons_company ON persons(current_company);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_career_person_id ON career_records(person_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_career_date ON career_records(change_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transfers_person ON transfers(person_id);")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DEFAULT_DB_PATH)
