import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import re
import plotly.express as px

# 1. 🎨 [디자인] NVIDIA 다크 테마 & 개방형 레이아웃
st.set_page_config(page_title="조협클래식 오늘만산다,살자", layout="wide")

st.markdown("""
    <style>
    /* 전체 배경 및 텍스트 설정 */
    .stApp { background-color: #050505 !important; color: #FFFFFF !important; }
    h1, h2, h3, [data-testid="stMetricValue"] { color: #76B900 !important; font-weight: bold !important; text-align: left !important; }
    
    /* 표 내부의 모든 텍스트 강제 왼쪽 정렬 */
    [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th {
        text-align: left !important;
    }
    
    /* 검색창 스타일 */
    input { background-color: #111 !important; color: #76B900 !important; border: 1px solid #333 !important; }
    
    /* 탭 메뉴 디자인 */
    .stTabs [data-baseweb="tab-list"] { justify-content: flex-start !important; gap: 20px; }
    .stTabs [data-baseweb="tab"] { font-size: 17px !important; color: #666 !important; border: none !important; }
    .stTabs [aria-selected="true"] { color: #76B900 !important; border-bottom: 3px solid #76B900 !important; }
    </style>
    """, unsafe_allow_html=True)

# 📂 2. 데이터 로드 (보안 설정 적용)
@st.cache_data(ttl=60) # 1분 간격 갱신으로 최적화
def load_perfect_alignment_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # [핵심 변경] 파일 대신 Streamlit Secrets에 입력한 딕셔너리를 사용합니다.
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        
        client = gspread.authorize(creds)
        sheet = client.open("조협오산오살").sheet1
        all_data = sheet.get_all_values()
        
        # 데이터가 비어있는지 확인
        if len(all_data) < 7:
            return None, "구글 시트의 데이터 형식이 올바르지 않습니다 (최소 7행 이상 필요)."

        header, rows = all_data[6], all_data[7:]
        df = pd.DataFrame(rows, columns=header)
        
        # 🛡️ 빈 행 제거 및 데이터 전처리
        df = df[df['이름'].str.strip() != ""].copy()
        
        def clean_to_int(val):
            if not val: return 0
            clean = re.sub(r'[^0-9.]', '', str(val))
            return int(float(clean)) if clean else 0

        df['전투력_v'] = df['전투력'].apply(clean_to_int)
        df['누계_v'] = df['누계'].apply(clean_to_int)
        
        def get_growth(v):
            match = re.search(r'\(([\d\.]+)\%\)', str(v))
            return float(match.group(1)) if match else 0.0
        df['성장_v'] = df['성장'].apply(get_growth)
        
        return all_data[0][0], df
    except Exception as e:
        return None, str(e)

update_time, result = load_perfect_alignment_data()

# 화면 표시용 설정
column_config = {
    "문파": st.column_config.TextColumn("문파"),
    "이름": st.column_config.TextColumn("이름"),
    "직업": st.column_config.TextColumn("직업"),
    "전투력": st.column_config.TextColumn("전투력"),
    "성장": st.column_config.TextColumn("성장"),
    "누계": st.column_config.TextColumn("누계"),
}

if isinstance(result, pd.DataFrame):
    df = result
    
    st.title("🛡️ 조협클래식 - 오늘만산다,살자")
    
    # 🔍 검색창
    search_q = st.text_input("🔍 캐릭터명 검색", placeholder="닉네임 입력")
    if search_q:
        res = df[df['이름'].str.contains(search_q, na=False, case=False)].copy()
        res['전투력'] = res['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(res[['문파', '이름', '직업', '전투력', '성장']], use_container_width=True, hide_index=True, column_config=column_config)

    st.markdown("<br>", unsafe_allow_html=True)
    
    tabs = st.tabs(["⚔️ 보스 현황", "🛡️ 연합 전력", "🔥 성장 랭킹", "🏆 직업별 랭킹", "📊 분석 통계", "💰 정산 현황"])

    with tabs[0]: # 보스 현황
        st.subheader("🗓️ 보스 참여 순위")
        boss_df = df.sort_values(by="누계_v", ascending=False).copy()
        boss_df['누계'] = boss_df['누계_v'].astype(str)
        st.dataframe(boss_df[['문파', '이름', '14시', '18시', '22시', '누계']], 
                     use_container_width=True, hide_index=True, height=750, column_config=column_config)

    with tabs[1]: # 문파 투력
        st.subheader("📈 문파 전투력 명단")
        cp_df = df.sort_values(by="전투력_v", ascending=False).copy()
        cp_df['전투력'] = cp_df['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(cp_df[['문파', '이름', '직업', '전투력', '성장', '카톡']], 
                     use_container_width=True, hide_index=True, height=750, column_config=column_config)

    with tabs[2]: # 성장 랭킹
        st.subheader("🔥 실시간 성장률 TOP 랭킹")
        growth_df = df.sort_values(by="성장_v", ascending=False).head(30).copy()
        growth_df['전투력'] = growth_df['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(growth_df[['문파', '이름', '성장', '전투력']], 
                     use_container_width=True, hide_index=True, height=750, column_config=column_config)

    with tabs[3]: # 🏆 직업별 랭킹
        st.subheader("👑 직업별 명예의 전당")
        job_list = sorted(df['직업'].unique())
        selected_job = st.selectbox("직업을 선택하세요", job_list)
        job_rank = df[df['직업'] == selected_job].sort_values(by="전투력_v", ascending=False).copy()
        job_rank.insert(0, '순위', [f"{i}위" for i in range(1, len(job_rank) + 1)])
        job_rank['전투력'] = job_rank['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(job_rank[['순위', '문파', '이름', '전투력', '성장']], 
                     use_container_width=True, hide_index=True, height=600, column_config=column_config)

    with tabs[4]: # 분석 통계
        st.subheader("📊 연합 핵심 통계")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("실제 총원", f"{len(df)}명")
        c2.metric("통합 전투력", f"{df['전투력_v'].sum():,}")
        c3.metric("평균 전투력", f"{int(df['전투력_v'].mean()) if len(df)>0 else 0:,}")
        c4.metric("최고 전투력", f"{df['전투력_v'].max() if len(df)>0 else 0:,}")
        st.divider()
        g1, g2 = st.columns([1.2, 1])
        with g1:
            fig_pie = px.pie(df, names='문파', values='전투력_v', hole=0.6, title="🏰 문파별 투력 비중",
                             color_discrete_map={"오늘만산다": "#76B900", "오늘만살자": "#007BFF"})
            fig_pie.update_layout(showlegend=True, legend=dict(y=0.5, x=1.1), paper_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig_pie, use_container_width=True)
        with g2:
            job_c = df['직업'].value_counts().reset_index()
            job_c.columns = ['직업', '인원']
            fig_bar = px.bar(job_c, x='직업', y='인원', title="🛡️ 직업 분포", color_discrete_sequence=['#76B900'])
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig_bar, use_container_width=True)

    with tabs[5]: # 정산 현황
        st.subheader("💰 실시간 다이아 분배 예정")
        money_df = df.sort_values(by="전투력_v", ascending=False).copy()
        st.dataframe(money_df[['문파', '이름', '분배금']], use_container_width=True, hide_index=True, height=750, column_config=column_config)

else:
    st.error(f"데이터 로드 실패: {result}")