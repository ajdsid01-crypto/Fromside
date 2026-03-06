import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import plotly.express as px

# 1. 🎨 [디자인] NVIDIA 다크 테마 및 전체 좌측 정렬 강제
st.set_page_config(page_title="조협클래식 오늘만산다,살자", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505 !important; color: #FFFFFF !important; }
    h1, h2, h3, [data-testid="stMetricValue"] { color: #76B900 !important; font-weight: bold !important; text-align: left !important; }
    
    /* 표 내부 항목 좌측 정렬 */
    [data-testid="stDataFrame"] div[data-baseweb="table"] div {
        text-align: left !important;
        justify-content: flex-start !important;
    }
    [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th { text-align: left !important; }
    
    /* 사이드바 너비 및 입력창 스타일 최적화 */
    [data-testid="stSidebar"] { min-width: 200px; max-width: 250px; }
    input { background-color: #111 !important; color: #76B900 !important; border: 1px solid #333 !important; }
    </style>
    """, unsafe_allow_html=True)

# 📂 2. 데이터 로드 및 전처리
@st.cache_data(ttl=10)
def load_full_system_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        
        spreadsheet = client.open("조협오산오살")
        sheet = spreadsheet.sheet1
        all_data = sheet.get_all_values()
        
        header, rows = all_data[6], all_data[7:]
        df = pd.DataFrame(rows, columns=header)
        df = df[df['이름'].str.strip() != ""].copy()
        
        def to_int(val):
            if not val: return 0
            clean = re.sub(r'[^0-9]', '', str(val))
            return int(clean) if clean else 0

        def get_growth(v):
            match = re.search(r'([\d\.]+)', str(v))
            return float(match.group(1)) if match else 0.0

        df['전투력_v'] = df['전투력'].apply(to_int)
        df['누계_v'] = df['누계'].apply(to_int)
        df['분배금_v'] = df['분배금'].apply(to_int)
        df['성장_v'] = df['성장'].apply(get_growth)
        
        return spreadsheet, sheet, df, header
    except Exception as e:
        return None, None, str(e), None

spreadsheet, worksheet, df, sheet_header = load_full_system_data()

# 📊 표 설정
column_config = {
    "문파": st.column_config.TextColumn("문파"),
    "이름": st.column_config.TextColumn("이름"),
    "직업": st.column_config.TextColumn("직업"),
    "전투력": st.column_config.TextColumn("전투력"),
    "성장": st.column_config.TextColumn("성장"),
}

if isinstance(df, pd.DataFrame):
    st.title("🛡️ 조협클래식 - 오늘만산다,살자")

    # 🔑 3. 관리자 메뉴 (크기 축소: Expander 사용)
    with st.sidebar:
        with st.expander("🔐 관리자 접속"):
            admin_pw = st.text_input("암호 입력", type="password")
            # 💡 여기서 "1234" 부분을 원하는 비밀번호로 수정하세요!
            is_admin = (admin_pw == "dhkdrkthf123") 

    # 🔍 검색창
    search_q = st.text_input("🔍 캐릭터명 검색", placeholder="닉네임 입력")
    if search_q:
        res = df[df['이름'].str.contains(search_q, na=False, case=False)].copy()
        res['전투력_표시'] = res['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(res[['문파', '이름', '직업', '전투력_표시', '성장']], use_container_width=True, hide_index=True, column_config=column_config)

    st.markdown("<br>", unsafe_allow_html=True)
    tabs = st.tabs(["⚔️ 보스 현황", "🛡️ 연합 전력", "🔥 성장 랭킹", "🏆 직업별 랭킹", "📊 분석 통계", "💰 정산 현황"])

    # --- 탭 내용 (기능 유지) ---
    with tabs[0]: # 보스 현황
        st.subheader("🗓️ 보스 참여 순위")
        boss_df = df.sort_values(by="누계_v", ascending=False).copy()
        st.dataframe(boss_df[['문파', '이름', '14시', '18시', '22시', '누계']], use_container_width=True, hide_index=True, height=600, column_config=column_config)

    with tabs[1]: # 문파 투력
        st.subheader("📈 문파 전투력 명단")
        cp_df = df.sort_values(by="전투력_v", ascending=False).copy()
        cp_df['전투력_표시'] = cp_df['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(cp_df[['문파', '이름', '직업', '전투력_표시', '성장', '카톡']], use_container_width=True, hide_index=True, height=600, column_config=column_config)

    with tabs[2]: # 성장 랭킹
        st.subheader("🔥 실시간 성장률 TOP 랭킹")
        growth_df = df.sort_values(by="성장_v", ascending=False).head(30).copy()
        growth_df['전투력_표시'] = growth_df['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(growth_df[['문파', '이름', '성장', '전투력_표시']], use_container_width=True, hide_index=True, height=600, column_config=column_config)

    with tabs[3]: # 직업별 랭킹
        st.subheader("👑 직업별 명예의 전당")
        job_list = sorted(df['직업'].unique())
        selected_job = st.selectbox("직업 선택", job_list)
        job_rank = df[df['직업'] == selected_job].sort_values(by="전투력_v", ascending=False).copy()
        job_rank.insert(0, '순위', [f"{i}위" for i in range(1, len(job_rank) + 1)])
        job_rank['전투력_표시'] = job_rank['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(job_rank[['순위', '문파', '이름', '전투력_표시', '성장']], use_container_width=True, hide_index=True, height=500, column_config=column_config)

    with tabs[4]: # 분석 통계
        st.subheader("📊 연합 핵심 통계")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("실제 총원", f"{len(df)}명")
        c2.metric("통합 전투력", f"{df['전투력_v'].sum():,}")
        c3.metric("평균 전투력", f"{int(df['전투력_v'].mean()):,}")
        c4.metric("평균 성장률", f"{df['성장_v'].mean():.2f}%")
        st.divider()
        g1, g2 = st.columns([1.2, 1])
        with g1:
            fig_pie = px.pie(df, names='문파', values='전투력_v', hole=0.6, title="🏰 문파별 투력 비중", color_discrete_map={"오늘만산다": "#76B900", "오늘만살자": "#007BFF"})
            fig_pie.update_layout(showlegend=True, paper_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig_pie, use_container_width=True)
        with g2:
            job_c = df['직업'].value_counts().reset_index()
            fig_bar = px.bar(job_c, x='직업', y='count', title="🛡️ 직업 분포", color_discrete_sequence=['#76B900'])
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig_bar, use_container_width=True)

    with tabs[5]: # 정산 현황 (전투력 1 제외 및 관리자 기능)
        st.subheader("💰 실시간 다이아 분배 및 정산 상태")
        settlement_df = df[df['전투력_v'] > 1].copy()
        settlement_df = settlement_df.sort_values(by="분배금_v", ascending=False)
        settlement_df['분배금_표시'] = settlement_df['분배금_v'].apply(lambda x: f"{x:,} 다이아")

        if is_admin:
            st.success("✅ 관리자 모드 활성화됨")
            edited_df = st.data_editor(
                settlement_df[['이름', '분배금_표시', '정산상태']],
                column_config={"정산상태": st.column_config.SelectboxColumn("정산상태", options=["미정산", "정산완료"])},
                disabled=["이름", "분배금_표시"], hide_index=True, use_container_width=True
            )
            if st.button("💾 정산 상태 저장"):
                status_idx = sheet_header.index("정산상태") + 1
                for idx, row in edited_df.iterrows():
                    try:
                        cell = worksheet.find(row['이름'])
                        worksheet.update_cell(cell.row, status_idx, row['정산상태'])
                    except: continue
                st.toast("구글 시트에 저장되었습니다!")
                st.cache_data.clear()
        else:
            settlement_df['상태'] = settlement_df['정산상태'].apply(lambda x: "✅ 정산완료" if x == "정산완료" else "⏳ 대기중")
            st.dataframe(settlement_df[['문파', '이름', '분배금_표시', '상태']], use_container_width=True, hide_index=True, height=600)

else:
    st.error(f"데이터 로드 실패: {result}")

