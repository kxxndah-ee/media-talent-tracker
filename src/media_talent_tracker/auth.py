"""Authentication and private access gate for PC and mobile access."""

import socket
import streamlit as st
try:
    from .db.repository import Repository
except ImportError:
    from media_talent_tracker.db.repository import Repository


def get_local_ip() -> str:
    """Get the local network IP address for mobile browser connection."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def check_authentication(repo: Repository) -> bool:
    """Render PIN/Password gate if not authenticated. Returns True if authenticated."""
    if st.session_state.get("authenticated", False):
        return True

    # Center-aligned mobile-friendly login card
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            """
            <div style="text-align: center; padding: 2.5rem 1.5rem; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                <div style="font-size: 3rem; margin-bottom: 0.5rem;">🔒</div>
                <h2 style="margin: 0; color: #1e293b; font-size: 1.5rem;">언론사 인사이동 트래커</h2>
                <p style="color: #64748b; font-size: 0.9rem; margin-top: 0.5rem; margin-bottom: 1.5rem;">
                    본인 전용 비공개 데이터베이스입니다.<br/>접속 PIN(비밀번호)을 입력해주세요.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")
        with st.form("login_form", clear_on_submit=False):
            pin_input = st.text_input(
                "보안 PIN / 비밀번호",
                type="password",
                placeholder="기본 PIN: 1234",
                help="설정 탭에서 언제든지 변경할 수 있습니다.",
            )
            submitted = st.form_submit_button("인증하고 접속하기", use_container_width=True)

            if submitted:
                stored_pin = repo.get_setting("auth_pin", default="1234")
                if pin_input.strip() == stored_pin.strip():
                    st.session_state["authenticated"] = True
                    st.success("인증에 성공했습니다. 접속 중...")
                    st.rerun()
                else:
                    st.error("PIN 번호가 일치하지 않습니다. 다시 입력해주세요.")

        st.markdown(
            """
            <div style="text-align: center; font-size: 0.8rem; color: #94a3b8; margin-top: 1.5rem;">
                💡 <b>모바일 접속 팁</b>: 스마트폰과 PC가 동일한 와이파이(Wi-Fi)에 연결되어 있으면 스마트폰 브라우저에서 바로 열람 가능합니다.
            </div>
            """,
            unsafe_allow_html=True,
        )

    return False


def render_auth_settings(repo: Repository) -> None:
    """Render PIN change form in settings tab."""
    st.subheader("🔑 보안 및 접속 PIN 관리")
    st.caption("외부인의 접근을 차단하기 위한 전용 잠금 PIN을 변경합니다.")

    with st.form("change_pin_form"):
        current_pin = st.text_input("현재 PIN", type="password")
        new_pin = st.text_input("새 PIN (숫자 4자리 이상 또는 비밀번호)", type="password")
        new_pin_confirm = st.text_input("새 PIN 확인", type="password")
        change_btn = st.form_submit_button("PIN 변경 저장")

        if change_btn:
            stored_pin = repo.get_setting("auth_pin", default="1234")
            if current_pin != stored_pin:
                st.error("현재 PIN이 일치하지 않습니다.")
            elif not new_pin or len(new_pin.strip()) < 4:
                st.error("새 PIN은 최소 4자리 이상이어야 합니다.")
            elif new_pin != new_pin_confirm:
                st.error("새 PIN 확인이 일치하지 않습니다.")
            else:
                repo.set_setting("auth_pin", new_pin.strip())
                st.success("✅ 접속 PIN이 성공적으로 변경되었습니다!")


def render_mobile_access_guide() -> None:
    """Display IP and instructions for mobile device access."""
    local_ip = get_local_ip()
    st.subheader("📱 PC & 모바일 접속 안내")
    st.markdown(
        f"""
        이 앱은 반응형 웹으로 제작되어 **PC와 스마트폰(모바일 브라우저)** 모두에서 쾌적하게 사용할 수 있습니다.

        #### 1. 동일 Wi-Fi 환경 접속 주소
        스마트폰에서 아래 주소로 접속하면 즉시 열립니다:
        ```text
        http://{local_ip}:8501
        ```

        #### 2. 모바일 홈 화면 바로가기 추가 (앱처럼 사용하기)
        - **아이폰 (Safari)**: 하단 공유 버튼 클릭 $\rightarrow$ **[홈 화면에 추가]**
        - **안드로이드 (Chrome)**: 우측 상단 메뉴(⋮) 클릭 $\rightarrow$ **[홈 화면에 추가]** 또는 **[앱 설치]**
        - 홈 화면 아이콘을 누르면 주소창 없는 독립형 앱(PWA 스타일)처럼 편리하게 사용할 수 있습니다.
        """
    )
