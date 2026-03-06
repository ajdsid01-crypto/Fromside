import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import plotly.express as px

# 1. 🎨 [디자인] NVIDIA 다크 테마 및 왼쪽 정렬 강제 설정
st.set_page_config(page_title="조협클래식 오늘만산다,살자", layout="wide")

st.markdown("""
    <style>
    /* 전체 배경 및 텍스트 설정 */
    .stApp { background-color: #050505 !important; color: #FFFFFF !important; }
    h1, h2, h3, [data-testid="stMetricValue"] { color: #76B900 !important; font-weight: bold !important; text-align: left !important; }
    
    /* 표 내부 모든 셀/헤더 왼쪽 정렬 강제 (숫자 포함) */
    [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th, 
    [data-testid="stDataFrame"] [data-testid="stTable"] div {
        text-align: left !important;
        justify-content: flex-start !important;
    }

    /* 표 배경색 고정 (모바일 흰색 방지) */
    [data-testid="stDataFrame"] { background-color: #111111 !important; }
    
    /* 검색창 스타일 */
    input { background-color: #111 !important; color: #76B900 !important; border: 1px solid #333 !important; }
    
    /* 탭 메뉴 디자인 */
    .stTabs [data-baseweb="tab-list"] { justify-content: flex-start !important; gap: 20px; }
    .stTabs [data-baseweb="tab"] { font-size: 17px !important; color: #666 !important; border: none !important; }
    .stTabs [aria-selected="true"] { color: #76B900 !important; border-bottom: 3px solid #76B900 !important; }
    </style>
    """, unsafe_allow_html=True)

# 📂 2. 데이터 로드 및 정밀 전처리
@st.cache_data(ttl=60)
def load_perfect_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        sheet = client.open("조협오산오살").sheet1
        all_data = sheet.get_all_values()
        
        if len(all_data) < 7: return None, "데이터 부족"

        header, rows = all_data[6], all_data[7:]
        df = pd.DataFrame(rows, columns=header)
        df = df[df['이름'].str.strip() != ""].copy()
        
        # 🛡️ 숫자로 변환하는 함수 (콤마/문자 제거)
        def to_int(val):
            if not val: return 0
            clean = re.sub(r'[^0-9]', '', str(val))
            return int(clean) if clean else 0

        # 🛡️ 성장률 추출 함수
        def get_growth(v):
            match = re.search(r'([\d\.]+)', str(v))
            return float(match.group(1)) if match else 0.0

        # 정렬을 위한 숫자 전용 컬럼 생성 (_v)
        df['전투력_v'] = df['전투력'].apply(to_int)
        df['누계_v'] = df['누계'].apply(to_int)
        df['분배금_v'] = df['분배금'].apply(to_int)
        df['성장_v'] = df['성장'].apply(get_growth)
        
        return all_data[0][0], df
    except Exception as e:
        return None, str(e)

update_time, result = load_perfect_data()

# 📊 표 컬럼 설정 (정렬을 위해 숫자형으로 지정)
column_config = {
    "전투력_v": st.column_config.NumberColumn("전투력", format="%d"),
    "성장_v": st.column_config.NumberColumn("성장(%)", format="%.2f"),
    "누계_v": st.column_config.NumberColumn("보스누계", format="%d"),
    "분배금_v": st.column_config.NumberColumn("분배금", format="%d"),
}

if isinstance(result, pd.DataFrame):
    df = result
    st.title("🛡️ 조협클래식 - 오늘만산다,살자")
    
    # 🔍 검색창
    search_q = st.text_input("🔍 캐릭터명 검색", placeholder="닉네임 입력")
    if search_q:
        res = df[df['이름'].str.contains(search_q, na=False, case=False)].copy()
        st.dataframe(res[['문파', '이름', '직업', '전투력_v', '성장_v']], use_container_width=True, hide_index=True, column_config=column_config)

    st.markdown("<br>", unsafe_allow_html=True)
    tabs = st.tabs(["⚔️ 보스 현황", "🛡️ 연합 전력", "🔥 성장 랭킹", "🏆 직업별 랭킹", "📊 분석 통계", "💰 정산 현황"])

    with tabs[0]: # 보스 현황
        st.subheader("🗓️ 보스 참여 순위")
        boss_df = df.sort_values(by="누계_v", ascending=False)
        st.dataframe(boss_df[['문파', '이름', '14시', '18시', '22시', '누계_v']], 
                     use_container_width=True, hide_index=True, height=600, column_config=column_config)

    with tabs[1]: # 문파 투력
        st.subheader("📈 문파 전투력 명단")
        cp_df = df.sort_values(by="전투력_v", ascending=False)
        st.dataframe(cp_df[['문파', '이름', '직업', '전투력_v', '성장_v', '카톡']], 
                     use_container_width=True, hide_index=True, height=600, column_config=column_config)

    with tabs[2]: # 성장 랭킹
        st.subheader("🔥 실시간 성장률 TOP 랭킹")
        growth_df = df.sort_values(by="성장_v", ascending=False).head(30)
        st.dataframe(growth_df[['문파', '이름', '성장_v', '전투력_v']], 
                     use_container_width=True, hide_index=True, height=600, column_config=column_config)

    with tabs[3]: # 🏆 직업별 랭킹
        st.subheader("👑 직업별 명예의 전당")
        job_list = sorted(df['직업'].unique())
        selected_job = st.selectbox("직업을 선택하세요", job_list)
        job_rank = df[df['직업'] == selected_job].sort_values(by="전투력_v", ascending=False).copy()
        job_rank.insert(0, '순위', range(1, len(job_rank) + 1))
        st.dataframe(job_rank[['순위', '문파', '이름', '전투력_v', '성장_v']], 
                     use_container_width=True, hide_index=True, height=500, column_config=column_config)

    with tabs[4]: # 분석 통계 (기존의 멋진 그래프들 복구)
        st.subheader("📊 연합 핵심 통계")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("실제 총원", f"{len(df)}명")
        c2.metric("통합 전투력", f"{df['전투력_v'].sum():,}")
        c3.metric("평균 전투력", f"{int(df['전투력_v'].mean()):,}")
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
            fig_bar = px.bar(job_c, x='직업', y='count', title="🛡️ 직업 분포", color_discrete_sequence=['#76B900'])
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig_bar, use_container_width=True)

    with tabs[5]: # 정산 현황 (버그 해결된 부분)
        st.subheader("💰 실시간 다이아 분배 예정")
        money_df = df.sort_values(by="분배금_v", ascending=False)
        st.dataframe(money_df[['문파', '이름', '분배금_v']], use_container_width=True, hide_index=True, height=600, column_config=column_config)

else:
    st.error(f"데이터 로드 실패: {result}")
