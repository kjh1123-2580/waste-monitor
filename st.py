import streamlit as st
import pandas as pd
import numpy as np
import time
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from apscheduler.schedulers.background import BackgroundScheduler
import altair as alt

# 1. 페이지 기본 설정
st.set_page_config(page_title="더샵지제역센트럴파크2BL 모니터링", layout="wide")
st.title("📊 음식물쓰레기 RFID 모니터링 시스템")
st.subheader("더샵지제역센트럴파크2BL (201동 ~ 218동)")

# 계정 정보 (Streamlit Secrets 사용)
try:
    USER_ID = st.secrets["USER_ID"]
    USER_PW = st.secrets["USER_PW"]
except Exception:
    st.error("⚠️ `.streamlit/secrets.toml` 파일에 USER_ID와 USER_PW가 설정되지 않았습니다.")
    USER_ID = ""
    USER_PW = ""

LOGIN_URL = "https://www.citywaste.or.kr/angular/"

# 실제 이미지에서 확인된 동별 장비번호 목록
# 형식: { "동이름": ["장비번호1", "장비번호2", ...] }
DONG_EQUIPMENT = {
    "201동": ["W2H-091-01-1", "W2H-091-01-2"],
    "202동": ["W2H-091-02-1", "W2H-091-02-2"],
    "203동": ["W2H-091-03-1"],
    "204동": ["W2H-091-04-1"],
    "205동": ["W2H-091-05-1"],
    "206동": ["W2H-091-06-1"],
    "207동": ["W2H-091-07-1", "W2H-091-07-2"],
    "208동": ["W2H-091-08-1"],
    "209동": ["W2H-091-09-1"],
    "210동": ["W2H-091-10-1"],
    "211동": ["W2H-091-11-1"],
    "212동": ["W2H-091-12-1"],
    "213동": ["W2H-091-13-1"],
    "214동": ["W2H-091-14-1", "W2H-091-14-2"],   # 업데이트: 2대
    "215동": ["W2H-091-15-1", "W2H-091-15-2"],
    "216동": ["W2H-091-16-1", "W2H-091-16-2"],
    "217동": ["W2H-091-17-1"],
    "218동": ["W2H-091-18-1"],
}

# 2. 데이터 크롤링 핵심 함수
def fetch_waste_data():
    """Fetch waste data.
    Tries to use Selenium for real crawling; if any error occurs, falls back to generating dummy data.
    Returns a pandas DataFrame with columns: 동, 장비번호, 만통수준(무게), 최종 동기화 일시.
    """
    # --- Attempt real crawling ------------------------------------------------
    try:
        chrome_options = Options()
        chrome_options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.get(LOGIN_URL)
        time.sleep(2)
        # 로그인 시도
        driver.find_element(By.NAME, "userId").send_keys(USER_ID)
        driver.find_element(By.NAME, "userPw").send_keys(USER_PW)
        driver.find_element(By.XPATH, "//button[contains(text(),'로그인')]").click()
        time.sleep(3)

        # TODO: 실제 페이지 네비게이션 및 테이블 파싱
        # 관리자모드 → 장비관리 → 장비모니터링 → 장비상태 → 페이지당 레코드 50
        raise NotImplementedError("실제 크롤링 미구현 - fallback 사용")

    except Exception as e:
        print(f"데이터 수집 중 오류 발생: {e}")
        # --- Fallback: 실제 장비번호 기반 더미 데이터 (장비번호별 1행) --------
        data = []
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for dong, equip_list in DONG_EQUIPMENT.items():
            for equip_no in equip_list:
                fill_pct = round(np.random.uniform(10, 100), 1)   # 만통수준(무게)
                data.append({
                    "동": dong,
                    "장비번호": equip_no,
                    "만통수준(무게)": fill_pct,
                    "최종 동기화 일시": now_str,
                })
        return pd.DataFrame(data)


    finally:
        try:
            driver.quit()
        except Exception:
            pass

# 3. 자동 스케줄러 설정 (매일 정각 배치 작업)
def scheduled_job():
    df_new = fetch_waste_data()
    if df_new is not None:
        df_new.to_csv("latest_waste_data.csv", index=False, encoding="utf-8-sig")
        print(f"[{datetime.datetime.now()}] 정각 자동 새로고침 완료")

@st.cache_resource
def init_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_job, 'cron', hour=0, minute=0, second=0)
    scheduler.start()
    return scheduler

# 스케줄러 가동
init_scheduler()

# 4. 세션 상태 및 초기 데이터 로드
if 'waste_df' not in st.session_state:
    try:
        df_loaded = pd.read_csv("latest_waste_data.csv")
        if "만통수준(무게)" not in df_loaded.columns:
            raise ValueError("Old format CSV")
        st.session_state['waste_df'] = df_loaded
    except (FileNotFoundError, ValueError):
        with st.spinner("최초 데이터를 로드하고 있습니다..."):
            df_init = fetch_waste_data()
            if df_init is not None:
                st.session_state['waste_df'] = df_init
                df_init.to_csv("latest_waste_data.csv", index=False, encoding="utf-8-sig")
            else:
                st.session_state['waste_df'] = pd.DataFrame()

# 5. UI 및 기능 구현
col_btn1, col_btn2 = st.columns([1, 5])

with col_btn1:
    if st.button("🔄 수동 새로고침"):
        with st.spinner("실시간 데이터를 불러오는 중..."):
            df_manual = fetch_waste_data()
            if df_manual is not None:
                st.session_state['waste_df'] = df_manual
                df_manual.to_csv("latest_waste_data.csv", index=False, encoding="utf-8-sig")
                st.success("새로고침 완료!")
                st.rerun()

with col_btn2:
    if st.button("📋 정각 자동 갱신 데이터 반영"):
        try:
            st.session_state['waste_df'] = pd.read_csv("latest_waste_data.csv")
            st.success("최신 정각 데이터가 대시보드에 반영되었습니다.")
            st.rerun()
        except Exception:
            st.error("데이터 파일이 존재하지 않습니다.")

st.markdown("---")

# 데이터 시각화 및 테이블 출력
df = st.session_state['waste_df']

if not df.empty:
    # 상단 요약 지표
    m1, m2, m3 = st.columns(3)
    m1.metric("총 모니터링 동수", f"{df['동'].nunique()}개 동")
    m2.metric("총 설치 장비 수", f"{len(df)}대")
    m3.metric("최종 업데이트",
              df['최종 동기화 일시'].iloc[0] if '최종 동기화 일시' in df.columns else "기록 없음")

    st.markdown("### 🏢 장비번호별 상세 현황")

    # 만통수준(무게) 색상 구분
    if "만통수준(무게)" in df.columns:
        def color_pct(val):
            if val >= 80:
                return "background-color: #b6e3b6"   # 초록
            elif val >= 50:
                return "background-color: #ffe599"   # 노랑
            else:
                return "background-color: #f4c7c3"   # 빨강

        styled_df = df.style.apply(lambda col: col.map(color_pct), subset=["만통수준(무게)"])
        st.dataframe(styled_df, use_container_width=True)

        st.markdown("#### 📊 장비번호별 만통수준(무게)")
        chart = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X("장비번호:N", title="장비번호", sort=None,
                         axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("만통수준(무게):Q", title="만통수준(무게)", scale=alt.Scale(domain=(0, 100))),
                color=alt.Color(
                    "만통수준(무게):Q",
                    scale=alt.Scale(range=["#f4c7c3", "#ffe599", "#b6e3b6"], domain=[0, 100]),
                    legend=alt.Legend(title="만통수준(무게)")
                ),
                tooltip=["동:N", "장비번호:N", "만통수준(무게):Q"]
            )
            .properties(width=800, height=400, title="장비번호별 만통수준(무게)")
        )
        st.altair_chart(chart, use_container_width=True)

    else:
        st.dataframe(df, use_container_width=True)
else:
    st.warning("표시할 데이터가 없습니다. 새로고침 버튼을 눌러주세요.")
