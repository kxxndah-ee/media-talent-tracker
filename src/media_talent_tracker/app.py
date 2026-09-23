"""Media Talent Tracker - Streamlit Application

언론사 인사이동 기사 분석, 인물 프로필 트래킹, 타사 이직 포착, 동명이인 필터링 전용 앱.
"""

from datetime import date, datetime
import streamlit as st
import pandas as pd

import sys
from pathlib import Path

# Add src to sys.path so modules can be imported directly when run via streamlit run
_src_dir = str(Path(__file__).resolve().parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

try:
    from .db.schema import init_db
    from .db.repository import Repository
    from .parser.regex_parser import MediaNoticeParser
    from .tracking.transfer_detector import TransferDetectorPipeline
    from .data.seed_data import load_seed_data
    from .auth import render_mobile_access_guide
except ImportError:
    from media_talent_tracker.db.schema import init_db
    from media_talent_tracker.db.repository import Repository
    from media_talent_tracker.parser.regex_parser import MediaNoticeParser
    from media_talent_tracker.tracking.transfer_detector import TransferDetectorPipeline
    from media_talent_tracker.data.seed_data import load_seed_data
    from media_talent_tracker.auth import render_mobile_access_guide

# Page configuration
st.set_page_config(
    page_title="언론사 인사이동 트래커",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom styling for mobile and desktop responsiveness
st.markdown(
    """
    <style>
    /* Responsive card style */
    .metric-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #0f172a;
    }
    .metric-label {
        font-size: 0.82rem;
        color: #64748b;
        margin-top: 0.2rem;
    }
    .badge-promotion {
        background-color: #dcfce7;
        color: #15803d;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-transfer {
        background-color: #f3e8ff;
        color: #7e22ce;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-move {
        background-color: #e0f2fe;
        color: #0369a1;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-homonym {
        background-color: #fee2e2;
        color: #b91c1c;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    /* Mobile optimization */
    @media (max-width: 768px) {
        .metric-value { font-size: 1.3rem; }
        .stTabs [data-baseweb="tab-list"] { gap: 4px; }
        .stTabs [data-baseweb="tab"] { font-size: 0.85rem; padding: 6px 10px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_repository() -> Repository:
    init_db()
    repo = Repository()
    # Check if empty, then auto load seed data
    stats = repo.get_stats()
    if stats["total_persons"] == 0:
        load_seed_data(repo)
    return repo


def main():
    repo = get_repository()

    # Header section
    st.title("📰 언론사 인사이동 트래커")
    st.caption("인사 기사 분석 · 인물 경력 추적 · 타사 이직 포착 · 동명이인 필터링")

    # Top KPI Metrics bar
    stats = repo.get_stats()
    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)
    with kpi_col1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value">{stats["total_persons"]}명</div><div class="metric-label">총 등록 언론인</div></div>',
            unsafe_allow_html=True,
        )
    with kpi_col2:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value">{stats["total_careers"]}건</div><div class="metric-label">인사이동 이력</div></div>',
            unsafe_allow_html=True,
        )
    with kpi_col3:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value" style="color: #7e22ce;">{stats["total_transfers"]}건</div><div class="metric-label">타사 이직 포착</div></div>',
            unsafe_allow_html=True,
        )
    with kpi_col4:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value">{stats["total_articles"]}건</div><div class="metric-label">수집 인사 기사</div></div>',
            unsafe_allow_html=True,
        )
    with kpi_col5:
        homonym_color = "#b91c1c" if stats["suspected_homonyms"] > 0 else "#64748b"
        st.markdown(
            f'<div class="metric-card"><div class="metric-value" style="color: {homonym_color};">{stats["suspected_homonyms"]}건</div><div class="metric-label">동명이인 관리 대상</div></div>',
            unsafe_allow_html=True,
        )

    st.write("")

    # Navigation Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔍 인물 검색 & 프로필",
        "🚀 이직 포착 레이더",
        "👥 동명이인 관리",
        "📝 인사 기사 분석/등록",
        "📱 모바일 접속 & 데이터 관리",
    ])

    # -------------------------------------------------------------
    # TAB 1: 통합 검색 & 인물 프로필
    # -------------------------------------------------------------
    with tab1:
        st.subheader("인물 및 경력 검색")

        filter_opts = repo.get_filter_options()
        f_col1, f_col2, f_col3, f_col4 = st.columns([1.5, 1.5, 1.5, 2])

        with f_col1:
            company_filter = st.selectbox("언론사", ["전체"] + filter_opts["companies"])
        with f_col2:
            dept_filter = st.selectbox("부서/국", ["전체"] + filter_opts["departments"])
        with f_col3:
            title_filter = st.selectbox("직급/직책", ["전체"] + filter_opts["titles"])
        with f_col4:
            search_query = st.text_input("이름 또는 통합 키워드 검색", placeholder="예: 홍길동, 정치, 금융")

        sel_company = "" if company_filter == "전체" else company_filter
        sel_dept = "" if dept_filter == "전체" else dept_filter
        sel_title = "" if title_filter == "전체" else title_filter

        persons = repo.search_persons(
            name=search_query if search_query else "",
            company=sel_company,
            department=sel_dept,
            title=sel_title,
            keyword=search_query if search_query and not (sel_company or sel_dept or sel_title) else "",
        )

        st.caption(f"검색 결과: 총 {len(persons)}명의 언론인이 조회되었습니다.")

        if not persons:
            st.info("검색 조건에 일치하는 인물이 없습니다.")
        else:
            # Table / Selection layout
            view_col1, view_col2 = st.columns([1.3, 1.7])

            with view_col1:
                st.write("**인물 목록** (선택 시 우측에 상세 프로필 표시)")
                person_options = {
                    f"{p['name']}{'(' + p['hanja'] + ')' if p.get('hanja') else ''} | {p.get('current_company', '')} {p.get('current_title', '')} [#{p['id']}]": p['id']
                    for p in persons
                }
                selected_label = st.radio(
                    "인물 선택",
                    options=list(person_options.keys()),
                    label_visibility="collapsed",
                )
                selected_person_id = person_options[selected_label] if selected_label else persons[0]["id"]

            with view_col2:
                # Render detailed profile
                person_data = repo.get_person(selected_person_id)
                if person_data:
                    career_records = repo.get_person_career(selected_person_id)

                    hanja_disp = f"({person_data['hanja']})" if person_data.get("hanja") else ""
                    st.markdown(
                        f"""
                        <div style="background: #ffffff; padding: 1.2rem; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 1rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <h3 style="margin: 0; color: #1e293b;">{person_data['name']} <span style="font-size: 1rem; color: #64748b;">{hanja_disp}</span></h3>
                                    <div style="margin-top: 0.3rem; font-size: 1.05rem; font-weight: 600; color: #2563eb;">
                                        {person_data.get('current_company', '-')} · {person_data.get('current_department', '-')} · {person_data.get('current_title', '-')}
                                    </div>
                                </div>
                                <div>
                                    <span class="badge-promotion">분야: {person_data.get('primary_beat', '일반')}</span>
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Career timeline
                    st.write("##### 📅 인사이동 경력 타임라인")
                    if not career_records:
                        st.info("등록된 인사이동 이력이 없습니다.")
                    else:
                        for rec in career_records:
                            action = rec["action_type"]
                            badge_cls = "badge-move"
                            if "승진" in action:
                                badge_cls = "badge-promotion"
                            elif "이직" in action or "영입" in action:
                                badge_cls = "badge-transfer"

                            with st.container():
                                st.markdown(
                                    f"""
                                    <div style="border-left: 3px solid #cbd5e1; padding-left: 1rem; margin-left: 0.5rem; margin-bottom: 1rem;">
                                        <div style="font-size: 0.82rem; color: #64748b;">{rec['change_date']}</div>
                                        <div style="font-size: 0.98rem; font-weight: 600; color: #1e293b; margin-top: 2px;">
                                            <span class="{badge_cls}">{action}</span> {rec['company']} · {rec.get('department', '')} {rec['title']}
                                        </div>
                                        <div style="font-size: 0.8rem; color: #475569; margin-top: 3px; font-style: italic;">
                                            "{rec.get('raw_text', '')}"
                                        </div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )

    # -------------------------------------------------------------
    # TAB 2: 이직 포착 레이더 (Transfer Radar)
    # -------------------------------------------------------------
    with tab2:
        st.subheader("🚀 타사 이직 포착 레이더")
        st.caption("최근 한 언론사에서 다른 언론사로 이직한 기자 및 간부들의 이동 내역을 시계열 및 직급 연속성으로 감지합니다.")

        transfers = repo.get_all_transfers(limit=50)

        if not transfers:
            st.info("포착된 타사 이직 내역이 아직 없습니다.")
        else:
            for t in transfers:
                conf = t["confidence_score"]
                conf_color = "#15803d" if conf >= 85 else "#d97706"
                gap_text = f"{t['gap_days']}일 간격" if t.get("gap_days") is not None else "직접 영입"
                hanja_str = f"({t['hanja']})" if t.get("hanja") else ""

                with st.expander(
                    f"🔄 [{t['transfer_date']}] {t['name']}{hanja_str}: {t['from_company']} ➔ {t['to_company']} (신뢰도: {conf}%)",
                    expanded=True,
                ):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(
                            f"""
                            **이동 경로**: `{t['from_company']}` ({t.get('from_title', '소속')}) ➔ `{t['to_company']}` ({t.get('to_title', '소속')})<br/>
                            **이직 확인일**: `{t['transfer_date']}` ({gap_text})<br/>
                            **감지 사유**: {t.get('detection_reason', '-')}
                            """,
                            unsafe_allow_html=True,
                        )
                    with c2:
                        st.markdown(
                            f"""
                            <div style="text-align: center; padding: 0.5rem; background: #faf5ff; border: 1px solid #e9d5ff; border-radius: 8px;">
                                <div style="font-size: 0.75rem; color: #7e22ce;">이직 판정 지수</div>
                                <div style="font-size: 1.4rem; font-weight: 700; color: {conf_color};">{conf}%</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

    # -------------------------------------------------------------
    # TAB 3: 동명이인 관리 센터
    # -------------------------------------------------------------
    with tab3:
        st.subheader("👥 동명이인 관리 및 프로필 정리")
        st.caption("시스템이 동일한 한글 성명 중 한자 상이, 사내 동시 발령, 또는 직급 비약으로 인해 분리한 인물들입니다. 직접 확인 후 동일인으로 합치거나 분리를 확정할 수 있습니다.")

        homonyms = repo.get_homonym_candidates(status="suspected")

        if not homonyms:
            st.success("✅ 현재 확인이 필요한 동명이인 의심 케이스가 없습니다. 모든 프로필이 깔끔하게 정렬되어 있습니다.")
        else:
            for item in homonyms:
                cand_id = item["id"]
                p_a = item["person_a_id"]
                p_b = item["person_b_id"]

                with st.container():
                    st.markdown(
                        f"""
                        <div style="background: #fff1f2; border: 1px solid #fecdd3; border-radius: 10px; padding: 1rem; margin-bottom: 0.5rem;">
                            <div style="display: flex; justify-content: space-between;">
                                <h4 style="margin: 0; color: #9f1239;">동명이인 의심: 성명 '{item['name']}'</h4>
                                <span class="badge-homonym">유사도: {item['similarity_score']}점</span>
                            </div>
                            <div style="font-size: 0.85rem; color: #881337; margin-top: 0.3rem;">
                                <b>분리 근거:</b> {item.get('conflict_reason', '-')}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    col_a, col_b, col_act = st.columns([2, 2, 1.5])
                    with col_a:
                        st.markdown(
                            f"""
                            **[인물 A] #{p_a}**<br/>
                            - 성명(한자): {item['name_a']} {f"({item['hanja_a']})" if item.get('hanja_a') else '(한자 미상)'}<br/>
                            - 소속: {item.get('company_a', '-')} {item.get('title_a', '-')}<br/>
                            - 분야: {item.get('beat_a', '일반')}
                            """,
                            unsafe_allow_html=True,
                        )
                    with col_b:
                        st.markdown(
                            f"""
                            **[인물 B] #{p_b}**<br/>
                            - 성명(한자): {item['name_b']} {f"({item['hanja_b']})" if item.get('hanja_b') else '(한자 미상)'}<br/>
                            - 소속: {item.get('company_b', '-')} {item.get('title_b', '-')}<br/>
                            - 분야: {item.get('beat_b', '일반')}
                            """,
                            unsafe_allow_html=True,
                        )
                    with col_act:
                        st.write("")
                        if st.button("🔗 동일인으로 합치기", key=f"merge_{cand_id}", use_container_width=True):
                            repo.merge_persons(target_id=p_a, source_id=p_b)
                            st.success(f"'{item['name']}' 인물 프로필을 성공적으로 병합했습니다.")
                            st.rerun()

                        if st.button("✂️ 동명이인 확정", key=f"separate_{cand_id}", use_container_width=True):
                            repo.confirm_separate_persons(person_a_id=p_a, person_b_id=p_b)
                            st.info("동명이인으로 확정 처리되었습니다.")
                            st.rerun()

                    st.markdown("<hr style='margin: 1rem 0; border: 0; border-top: 1px solid #f1f5f9;'/>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # TAB 4: 인사 기사 분석 및 실시간 등록
    # -------------------------------------------------------------
    with tab4:
        st.subheader("📝 인사 기사 실시간 분석 및 수집")
        st.caption("포털 뉴스나 언론사 홈페이지의 인사 기사를 붙여넣으면 즉시 파싱하여 인물 프로필을 생성하고 타사 이직을 감지합니다.")

        with st.form("article_ingest_form"):
            in_title = st.text_input("기사 제목", placeholder="예: [인사] 조선일보 / [인사] 2026년 3월 25일")
            in_col1, in_col2 = st.columns(2)
            with in_col1:
                in_company = st.text_input("언론사명 (본문 내 명시된 경우 비워둬도 무방)", placeholder="예: 조선일보")
            with in_col2:
                in_date = st.date_input("발령일 / 기사 게재일", value=date.today())

            in_url = st.text_input("기사 URL (선택)", placeholder="https://...")
            in_content = st.text_area(
                "기사 본문 내용",
                height=220,
                placeholder="[인사] 한국일보\n◇승진\n▲정치부장 홍길동\n▲사회부 차장 김철수\n◇영입\n▲산업부장 이영희(전 매일경제 부장)",
            )

            parse_btn = st.form_submit_button("🔍 기사 분석 및 미리보기", use_container_width=True)

        if parse_btn and in_content:
            parser = MediaNoticeParser()
            parsed_entries = parser.parse_article(
                article_text=in_content,
                default_company=in_company,
                published_date=str(in_date),
            )

            st.session_state["last_parsed"] = {
                "title": in_title or f"[인사] {in_company or '언론사'}",
                "company": in_company,
                "date": str(in_date),
                "url": in_url,
                "content": in_content,
                "entries": parsed_entries,
            }

        if "last_parsed" in st.session_state:
            last = st.session_state["last_parsed"]
            entries = last["entries"]

            st.write(f"##### 분석 결과: 총 {len(entries)}건의 인사이동 항목 추출")

            if not entries:
                st.warning("기사 본문에서 유효한 인사이동 항목을 찾지 못했습니다. 본문 서식(불릿 ▲, 부서/직책/성명 등)을 확인해주세요.")
            else:
                preview_data = [
                    {
                        "언론사": e.company,
                        "구분": e.action_type,
                        "부서": e.department,
                        "직급": e.title,
                        "성명": e.name,
                        "한자": e.hanja or "-",
                        "직급레벨": f"Lv.{e.rank_level}",
                        "분야": e.beat,
                        "전 직장(이직)": e.previous_company or "-",
                    }
                    for e in entries
                ]
                st.dataframe(pd.DataFrame(preview_data), use_container_width=True)

                if st.button("💾 데이터베이스에 저장 및 이직/프로필 즉시 반영", type="primary", use_container_width=True):
                    pipeline = TransferDetectorPipeline(repo)
                    art_id = repo.add_article(
                        title=last["title"],
                        media_company=last["company"] or (entries[0].company if entries else "미지정"),
                        published_date=last["date"],
                        content=last["content"],
                        url=last["url"],
                    )
                    res = pipeline.ingest_entries(
                        entries=entries,
                        published_date=last["date"],
                        article_id=art_id,
                    )
                    st.success(
                        f"✅ 반영 완료! 신규 인물: {res['created_persons']}명, 경력 업데이트: {res['updated_persons']}명, 이직 감지: {res['detected_transfers']}건, 동명이인 의심: {res['suspected_homonyms']}건"
                    )
                    del st.session_state["last_parsed"]
                    st.rerun()

    # -------------------------------------------------------------
    # TAB 5: 모바일 접속 안내 및 데이터 관리
    # -------------------------------------------------------------
    with tab5:
        render_mobile_access_guide()
        st.write("---")
        st.subheader("📦 데이터베이스 관리")
        st.caption("초기 시드 데이터를 다시 불러오거나 데이터베이스를 새로고침할 수 있습니다.")
        if st.button("샘플 인사 데이터 다시 로드"):
            load_seed_data(repo)
            st.success("샘플 데이터가 다시 로드되었습니다.")
            st.rerun()


if __name__ == "__main__":
    main()
