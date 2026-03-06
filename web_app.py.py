import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import plotly.express as px

# 1. 🎨 [디자인] NVIDIA 다크 테마 및 전체 레이아웃 설정 (PC/모바일 통합)
st.set_page_config(page_title="", layout="wide")

st.markdown("""
    <style>
    /* 전체 배경 및 텍스트 고정 */
    .stApp { background-color: #050505 !important; color: #FFFFFF !important; }
    h1, h2, h3, [data-testid="stMetricValue"] { color: #76B900 !important; font-weight: bold !important; text-align: left !important; }
    
    /* 표(DataFrame) 스타일 강제 고정 (다크모드 강제) */
    [data-testid="stDataFrame"] { background-color: #111111 !important; }
    [data-testid="stDataFrame"] div[data-baseweb="table"] div {
        text-align: left !important;
        justify-content: flex-start !important;
        background-color: #111111 !important;
        color: white !important;
    }

    /* 🏆 슬림 MVP 바 스타일 */
    .mvp-bar {
        background: linear-gradient(90deg, #111, #1a1a1a);
        border: 1px solid #76B900;
        padding: 10px 20px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 0 10px rgba(118, 185, 0, 0.2);
    }
    
    /* 참여자 명단 박스 */
    .participant-box {
        background-color: #111;
        border-left: 4px solid #76B900;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        min-height: 80px;
    }
    </style>
    """, unsafe_allow_html=True)

# 🏆 순위에 따른 메달 부여 함수
def add_medal_logic(df):
    df = df.reset_index(drop=True)
    df.insert(0, 'Rank', range(1, len(df) + 1))
    def medal_icon(rank):
        if rank == 1: return "🥇 1위"
        elif rank == 2: return "🥈 2위"
        elif rank == 3: return "🥉 3위"
        else: return f"{rank}위"
    df['순위'] = df['Rank'].apply(medal_icon)
    return df.drop(columns=['Rank'])

# 📂 2. 데이터 로드 및 정밀 전처리
@st.cache_data(ttl=10)
def load_all_guild_data():
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
            clean = re.sub(r'[^0-9]', '', str(val))
            return int(clean) if clean else 0

        # 성장률(%)과 실제수치 분리 로직 (가독성 요청 반영)
        def parse_growth(val):
            percent = re.search(r'([\d\.]+)(?=%)', str(val))
            value = re.search(r'\(([^)]+)\)', str(val))
            p_val = float(percent.group(1)) if percent else 0.0
            v_val = value.group(1) if value else "0"
            return p_val, v_val

        df['전투력_v'] = df['전투력'].apply(to_int)
        df['누계_v'] = df['누계'].apply(to_int)
        df['분배금_v'] = df['분배금'].apply(to_int)
        
        growth_parsed = df['성장'].apply(parse_growth)
        df['성장_v'] = [x[0] for x in growth_parsed] # 정렬용 숫자
        df['성장_표시'] = [f"{x[0]}% ({x[1]})" for x in growth_parsed] # 화면 표시용 (요청사항)

        def is_p(val): return str(val).strip().lower() in ['o', 'ㅇ', 'v']
        df['14_p'], df['18_p'], df['22_p'] = df['14시'].apply(is_p), df['18시'].apply(is_p), df['22시'].apply(is_p)
        
        return spreadsheet, sheet, df, header
    except Exception as e:
        return None, None, str(e), None

spreadsheet, worksheet, df, sheet_header = load_all_guild_data()

# 📊 3. 화면 구성 및 사이드바
if isinstance(df, pd.DataFrame):
    with st.sidebar:
        st.markdown("<h2 style='text-align: center; color: #76B900;'>오늘만산다,살자</h2>", unsafe_allow_html=True)
        st.divider()
        st.subheader("📊 연합 현황")
        st.metric("총 인원", f"{len(df)}명")
        st.metric("연합 총 투력", f"{df['전투력_v'].sum():,}")
        st.divider()
        
        st.subheader("📺 연합 방송 센터")
        youtube_links = [
            ("가미가미 TV", "https://www.youtube.com/@gamigami706", "youtube-play"),
            ("왕코 방송국", "https://www.youtube.com/@스트리머왕코", "controller"),
            ("아이엠솔이", "https://www.youtube.com/@아이엠솔이", "microphone")
        ]
        for name, url, icon in youtube_links:
            c1, c2 = st.columns([1, 4])
            with c1: st.image(f"https://img.icons8.com/neon/96/{icon}.png", width=30)
            with c2: st.link_button(name, url, use_container_width=True)
        
        st.divider()
        with st.expander("🔐 관리자 접속"):
            admin_pw = st.text_input("암호 입력", type="password")
            is_admin = (admin_pw == "1234") 
            if st.button("🔄 데이터 강제 새로고침"):
                st.cache_data.clear()
                st.rerun()

    # --- 메인 영역 ---
    st.title("🛡️ 조협클래식 오늘만산다/살자")
    
    # 🔍 검색창
    search_q = st.text_input("🔍 캐릭터명 검색 (닉네임 입력)", placeholder="예: 가미가미")
    if search_q:
        search_res = df[df['이름'].str.contains(search_q, na=False, case=False)].copy()
        if not search_res.empty:
            search_res['전투력_표시'] = search_res['전투력_v'].apply(lambda x: f"{x:,}")
            st.dataframe(search_res[['문파', '이름', '직업', '전투력_표시', '성장_표시']], use_container_width=True, hide_index=True)
        st.divider()

    tabs = st.tabs(["⚔️ 보스 현황", "🛡️ 연합 전력", "🔥 성장 랭킹", "🏆 직업별 랭킹", "📊 분석 통계", "💰 정산 현황"])

    with tabs[0]: # ⚔️ 보스 현황
        max_val = df['누계_v'].max()
        if max_val > 0:
            mvps = df[df['누계_v'] == max_val]['이름'].tolist()
            st.markdown(f"<div class='mvp-bar'><span style='color:#76B900; font-weight:bold;'>🏆 이번 주 보탐 MVP : </span><span style='color:white;'>{', '.join(mvps)}</span> <small>({max_val}회 참여)</small></div>", unsafe_allow_html=True)
        
        p_cols = st.columns(3)
        t_info = [("14시", "14_p"), ("18시", "18_p"), ("22시", "22_p")]
        for i, (t_name, p_col) in enumerate(t_info):
            with p_cols[i]:
                names = df[df[p_col]]['이름'].tolist()
                st.markdown(f"#### 🕒 {t_name} ({len(names)}명)")
                st.markdown(f"<div class='participant-box'>{', '.join(names) if names else '참여자 없음'}</div>", unsafe_allow_html=True)
        
        st.divider()
        boss_rank = add_medal_logic(df.sort_values(by="누계_v", ascending=False))
        st.dataframe(boss_rank[['순위', '문파', '이름', '14시', '18시', '22시', '누계']], use_container_width=True, hide_index=True)

    with tabs[1]: # 🛡️ 연합 전력
        st.subheader("📈 연합 전투력 명예의 전당")
        cp_rank = add_medal_logic(df.sort_values(by="전투력_v", ascending=False))
        cp_rank['전투력_표시'] = cp_rank['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(cp_rank[['순위', '문파', '이름', '직업', '전투력_표시', '성장_표시']], use_container_width=True, hide_index=True)

    with tabs[2]: # 🔥 성장 랭킹 (개선된 정렬 적용)
        st.subheader("🔥 실시간 성장률 TOP 랭킹")
        growth_rank = add_medal_logic(df.sort_values(by="성장_v", ascending=False))
        st.dataframe(growth_rank[['순위', '문파', '이름', '성장_표시', '전투력']], use_container_width=True, hide_index=True)

    with tabs[3]: # 🏆 직업별 랭킹
        st.subheader("👑 직업별 명예의 전당")
        job_list = sorted(df['직업'].unique())
        selected_job = st.selectbox("직업을 선택하세요", job_list)
        job_rank = add_medal_logic(df[df['직업'] == selected_job].sort_values(by="전투력_v", ascending=False))
        job_rank['전투력_표시'] = job_rank['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(job_rank[['순위', '문파', '이름', '전투력_표시', '성장_표시']], use_container_width=True, hide_index=True)

    with tabs[4]: # 📊 분석 통계
        st.subheader("📊 연합 핵심 지표 분석")
        c1, c2, c3 = st.columns(3)
        c1.metric("통합 전투력", f"{df['전투력_v'].sum():,}")
        c2.metric("평균 전투력", f"{int(df['전투력_v'].mean()):,}")
        c3.metric("평균 성장률", f"{df['성장_v'].mean():.2f}%")
        st.divider()
        g1, g2 = st.columns(2)
        with g1:
            fig_pie = px.pie(df, names='문파', values='전투력_v', hole=0.6, title="문파별 투력 비중", color_discrete_map={"오늘만산다": "#76B900", "오늘만살자": "#007BFF"})
            st.plotly_chart(fig_pie, use_container_width=True)
        with g2:
            fig_bar = px.bar(df['직업'].value_counts().reset_index(), x='직업', y='count', title="연합 직업 분포", color_discrete_sequence=['#76B900'])
            st.plotly_chart(fig_bar, use_container_width=True)

    with tabs[5]: # 💰 정산 현황
        st.subheader("💰 다이아 분배 현황 (미보고자 제외)")
        money_rank = add_medal_logic(df[df['전투력_v'] > 1].sort_values(by="분배금_v", ascending=False))
        money_rank['분배금_표시'] = money_rank['분배금_v'].apply(lambda x: f"{x:,} 다이아")
        
        if is_admin:
            edited_df = st.data_editor(money_rank[['순위', '이름', '분배금_표시', '정산상태']], column_config={"정산상태": st.column_config.SelectboxColumn("상태", options=["미정산", "정산완료"])}, disabled=["순위", "이름", "분배금_표시"], hide_index=True, use_container_width=True)
            if st.button("💾 정산 데이터 저장"):
                status_idx = sheet_header.index("정산상태") + 1
                for _, row in edited_df.iterrows():
                    cell = worksheet.find(row['이름'])
                    worksheet.update_cell(cell.row, status_idx, row['정산상태'])
                st.cache_data.clear()
                st.rerun()
        else:
            money_rank['상태'] = money_rank['정산상태'].apply(lambda x: "✅ 완료" if x == "정산완료" else "⏳ 대기")
            st.dataframe(money_rank[['순위', '문파', '이름', '분배금_표시', '상태']], use_container_width=True, hide_index=True)

else:
    st.error(f"데이터 로드 실패: {df}")












