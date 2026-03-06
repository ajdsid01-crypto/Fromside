import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import plotly.express as px

# 1. 🎨 [디자인] NVIDIA 다크 테마 및 전체 좌측 정렬 강제 설정
st.set_page_config(page_title="조협클래식 오늘만산다,살자", layout="wide")

st.markdown("""
    <style>
    /* 전체 배경 및 텍스트 설정 */
    .stApp { background-color: #050505 !important; color: #FFFFFF !important; }
    h1, h2, h3, [data-testid="stMetricValue"] { color: #76B900 !important; font-weight: bold !important; text-align: left !important; }
    
    /* 🚨 표 내부의 모든 셀(숫자 포함)과 헤더를 강제로 왼쪽 정렬 */
    [data-testid="stDataFrame"] div[data-baseweb="table"] div {
        text-align: left !important;
        justify-content: flex-start !important;
    }
    [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th { text-align: left !important; }

    /* 사이드바 스타일 최적화 */
    [data-testid="stSidebar"] { min-width: 260px; }
    input { background-color: #111 !important; color: #76B900 !important; border: 1px solid #333 !important; }
    
    /* 탭 메뉴 디자인 */
    .stTabs [data-baseweb="tab-list"] { justify-content: flex-start !important; gap: 20px; }
    .stTabs [data-baseweb="tab"] { font-size: 17px !important; color: #666 !important; border: none !important; }
    .stTabs [aria-selected="true"] { color: #76B900 !important; border-bottom: 3px solid #76B900 !important; }
    </style>
    """, unsafe_allow_html=True)

# 📂 2. 데이터 로드 및 정밀 전처리 (캐시 10초로 설정하여 정산 반영 속도 최적화)
@st.cache_data(ttl=10)
def load_full_integrated_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        
        spreadsheet = client.open("조협오산오살")
        sheet = spreadsheet.sheet1
        all_data = sheet.get_all_values()
        
        # 7행 헤더, 8행부터 데이터 시작
        header, rows = all_data[6], all_data[7:]
        df = pd.DataFrame(rows, columns=header)
        df = df[df['이름'].str.strip() != ""].copy()
        
        # 🛡️ 숫자 변환 함수 (콤마/문자 제거 후 진짜 숫자로)
        def to_int(val):
            if not val: return 0
            clean = re.sub(r'[^0-9]', '', str(val))
            return int(clean) if clean else 0

        # 🛡️ 성장률 추출 함수
        def get_growth(v):
            match = re.search(r'([\d\.]+)', str(v))
            return float(match.group(1)) if match else 0.0

        # 정렬 및 계산을 위한 숫자 전용 컬럼 생성
        df['전투력_v'] = df['전투력'].apply(to_int)
        df['누계_v'] = df['누계'].apply(to_int)
        df['분배금_v'] = df['분배금'].apply(to_int)
        df['성장_v'] = df['성장'].apply(get_growth)
        
        return spreadsheet, sheet, df, header
    except Exception as e:
        return None, None, str(e), None

spreadsheet, worksheet, df, sheet_header = load_full_integrated_data()

# 📊 3. 화면 구성 및 사이드바 보강
if isinstance(df, pd.DataFrame):
    # --- 사이드바 영역 ---
    with st.sidebar:
        st.markdown("<h2 style='text-align: center; color: #76B900;'>오늘만산다,살자</h2>", unsafe_allow_html=True)
        st.divider()

        # 📊 연합 현황 요약
        st.subheader("📊 연합 현황")
        st.metric("총 인원", f"{len(df)}명")
        st.metric("연합 총 투력", f"{df['전투력_v'].sum():,}")
        st.divider()

        # 📺 연합 방송 센터 (아이콘 버전)
        st.subheader("📺 연합 방송 센터")
        
        # 가미가미
        c1, c2 = st.columns([1, 4])
        with c1: st.image("https://img.icons8.com/neon/96/youtube-play.png", width=35)
        with c2: st.link_button("가미가미[gamigami]", "https://www.youtube.com/@gamigami706", use_container_width=True)

        # 스트리머왕코
        c1, c2 = st.columns([1, 4])
        with c1: st.image("https://img.icons8.com/neon/96/controller.png", width=35)
        with c2: st.link_button("스트리머왕코", "https://www.youtube.com/@스트리머왕코", use_container_width=True)

        # 아이엠솔이
        c1, c2 = st.columns([1, 4])
        with c1: st.image("https://img.icons8.com/neon/96/microphone.png", width=35)
        with c2: st.link_button("아이엠솔이 I AM SOLEE", "https://www.youtube.com/@아이엠솔이", use_container_width=True)
        
        st.divider()

        # 🔐 관리자 접속 (축소형)
        with st.expander("🔐 관리자 전용"):
            admin_pw = st.text_input("암호 입력", type="password")
            # 💡 비밀번호를 여기서 수정하세요 (기본: 1234)
            is_admin = (admin_pw == "1234") 
            if st.button("🔄 데이터 강제 새로고침"):
                st.cache_data.clear()
                st.rerun()

    # --- 메인 영역 ---
    st.title("🛡️ 조협클래식 통합 관리 시스템")
    
    # 공통 컬럼 설정 (좌측 정렬 보장)
    column_config = {
        "문파": st.column_config.TextColumn("문파"),
        "이름": st.column_config.TextColumn("이름"),
        "직업": st.column_config.TextColumn("직업"),
        "전투력_표시": st.column_config.TextColumn("전투력"),
        "분배금_표시": st.column_config.TextColumn("분배금"),
        "성장_v": st.column_config.NumberColumn("성장률(%)", format="%.2f"),
        "누계_v": st.column_config.NumberColumn("보스참여", format="%d"),
    }

    # 🔍 검색창
    search_q = st.text_input("🔍 캐릭터명 검색", placeholder="닉네임 입력")
    if search_q:
        res = df[df['이름'].str.contains(search_q, na=False, case=False)].copy()
        res['전투력_표시'] = res['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(res[['문파', '이름', '직업', '전투력_표시', '성장']], use_container_width=True, hide_index=True, column_config=column_config)

    st.markdown("<br>", unsafe_allow_html=True)
    tabs = st.tabs(["⚔️ 보스 현황", "🛡️ 연합 전력", "🔥 성장 랭킹", "🏆 직업별 랭킹", "📊 분석 통계", "💰 정산 현황"])

    with tabs[0]: # 보스 현황
        st.subheader("🗓️ 보스 참여 순위")
        boss_df = df.sort_values(by="누계_v", ascending=False).copy()
        st.dataframe(boss_df[['문파', '이름', '14시', '18시', '22시', '누계_v']], 
                     use_container_width=True, hide_index=True, height=600, column_config=column_config)

    with tabs[1]: # 연합 전력
        st.subheader("📈 문파 전투력 명단")
        cp_df = df.sort_values(by="전투력_v", ascending=False).copy()
        cp_df['전투력_표시'] = cp_df['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(cp_df[['문파', '이름', '직업', '전투력_표시', '성장', '카톡']], 
                     use_container_width=True, hide_index=True, height=600, column_config=column_config)

    with tabs[2]: # 성장 랭킹
        st.subheader("🔥 실시간 성장률 TOP 랭킹")
        growth_df = df.sort_values(by="성장_v", ascending=False).head(30).copy()
        growth_df['전투력_표시'] = growth_df['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(growth_df[['문파', '이름', '성장_v', '전투력_표시']], 
                     use_container_width=True, hide_index=True, height=600, column_config=column_config)

    with tabs[3]: # 직업별 랭킹
        st.subheader("👑 직업별 명예의 전당")
        job_list = sorted(df['직업'].unique())
        selected_job = st.selectbox("직업을 선택하세요", job_list)
        job_rank = df[df['직업'] == selected_job].sort_values(by="전투력_v", ascending=False).copy()
        job_rank.insert(0, '순위', [f"{i}위" for i in range(1, len(job_rank) + 1)])
        job_rank['전투력_표시'] = job_rank['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(job_rank[['순위', '문파', '이름', '전투력_표시', '성장']], 
                     use_container_width=True, hide_index=True, height=500, column_config=column_config)

    with tabs[4]: # 분석 통계
        st.subheader("📊 연합 핵심 통계")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("실제 총원", f"{len(df)}명")
        c2.metric("통합 전투력", f"{df['전투력_v'].sum():,}")
        c3.metric("평균 전투력", f"{int(df['전투력_v'].mean()) if len(df)>0 else 0:,}")
        c4.metric("평균 성장률", f"{df['성장_v'].mean():.2f}%")
        st.divider()
        g1, g2 = st.columns([1.2, 1])
        with g1:
            fig_pie = px.pie(df, names='문파', values='전투력_v', hole=0.6, title="🏰 문파별 투력 비중",
                             color_discrete_map={"오늘만산다": "#76B900", "오늘만살자": "#007BFF"})
            fig_pie.update_layout(showlegend=True, paper_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig_pie, use_container_width=True)
        with g2:
            job_c = df['직업'].value_counts().reset_index()
            job_c.columns = ['직업', '인원']
            fig_bar = px.bar(job_c, x='직업', y='인원', title="🛡️ 직업 분포", color_discrete_sequence=['#76B900'])
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig_bar, use_container_width=True)

    with tabs[5]: # 정산 현황 (전투력 1 제외 및 관리자 기능)
        st.subheader("💰 실시간 다이아 분배 및 정산 상태")
        
        # 1. 전투력이 1보다 큰 참여자만 필터링 (미보고자 제외)
        settlement_df = df[df['전투력_v'] > 1].copy()
        settlement_df = settlement_df.sort_values(by="분배금_v", ascending=False)
        settlement_df['분배금_표시'] = settlement_df['분배금_v'].apply(lambda x: f"{x:,} 다이아")

        if is_admin:
            st.success("✅ 관리자 모드: 정산 상태를 수정하고 [저장]을 누르세요.")
            edited_df = st.data_editor(
                settlement_df[['이름', '분배금_표시', '정산상태']],
                column_config={"정산상태": st.column_config.SelectboxColumn("정산상태", options=["미정산", "정산완료"])},
                disabled=["이름", "분배금_표시"], hide_index=True, use_container_width=True
            )
            
            if st.button("💾 정산 결과 저장하기"):
                with st.spinner("구글 시트 업데이트 중..."):
                    try:
                        status_idx = sheet_header.index("정산상태") + 1
                        for idx, row in edited_df.iterrows():
                            cell = worksheet.find(row['이름'])
                            worksheet.update_cell(cell.row, status_idx, row['정산상태'])
                        st.toast("✅ 구글 시트 저장 완료!")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"저장 오류: {e}. 시트에 '정산상태' 열이 있는지 확인하세요.")
        else:
            # 일반 유저용 화면
            settlement_df['상태'] = settlement_df['정산상태'].apply(lambda x: "✅ 정산완료" if x == "정산완료" else "⏳ 대기중")
            st.info(f"💡 현재 전투력을 보고한 {len(settlement_df)}명만 분배 대상입니다.")
            st.dataframe(settlement_df[['문파', '이름', '분배금_표시', '상태']], 
                         use_container_width=True, hide_index=True, height=600, column_config=column_config)

else:
    st.error(f"데이터 로드 실패: {df}")

