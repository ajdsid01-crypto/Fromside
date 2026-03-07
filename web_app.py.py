import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import plotly.express as px
import streamlit.components.v1 as components

# 1. 🎨 [디자인] NVIDIA 프리미엄 다크 테마 및 균형 잡힌 레이아웃
st.set_page_config(page_title="조협클래식 오늘만산다,살자", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505 !important; color: #FFFFFF !important; }
    h1, h2, h3, [data-testid="stMetricValue"] { color: #76B900 !important; font-weight: bold !important; text-align: left !important; }
    
    /* 사이드바: 답답함 없는 밸런스 조정 */
    [data-testid="stSidebar"] > div:first-child { padding-top: 20px !important; }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.8rem !important; }
    .stDivider { margin: 1rem 0 !important; }
    
    /* 표(DataFrame) 스타일 강제 고정 */
    [data-testid="stDataFrame"] { background-color: #111111 !important; }
    div[data-testid="stDataFrame"] div[data-baseweb="table"] div {
        background-color: #111111 !important;
        color: white !important;
        text-align: left !important;
    }

    /* 🏆 MVP 및 참여자 명단 스타일 */
    .mvp-bar {
        background: linear-gradient(90deg, #111, #1a1a1a);
        border: 1px solid #76B900;
        padding: 10px 20px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 0 10px rgba(118, 185, 0, 0.2);
    }
    .participant-box {
        background-color: #111;
        border-left: 4px solid #76B900;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        min-height: 70px;
    }
    </style>
    """, unsafe_allow_html=True)

# 🏆 순위 메달 부여 함수
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

# 📂 2. 데이터 로드 및 전처리
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
        df['성장_v'] = [x[0] for x in growth_parsed]
        df['성장_표시'] = [f"{x[0]}% ({x[1]})" for x in growth_parsed]

        if '정산상태' in df.columns:
            df['정산상태'] = df['정산상태'].apply(lambda x: "정산완료" if str(x).strip() == "정산완료" else "미정산")
        else:
            df['정산상태'] = "미정산"

        def is_p(val): return str(val).strip().lower() in ['o', 'ㅇ', 'v']
        df['14_p'], df['18_p'], df['22_p'] = df['14시'].apply(is_p), df['18시'].apply(is_p), df['22시'].apply(is_p)
        
        return spreadsheet, sheet, df, header
    except Exception as e:
        return None, None, str(e), None

spreadsheet, worksheet, df, sheet_header = load_all_guild_data()

# 📊 3. 화면 구성
if isinstance(df, pd.DataFrame):
    # --- 사이드바 영역 ---
    with st.sidebar:
        st.markdown(f"""
            <div style="text-align: center; padding: 15px 0 20px 0;">
                <img src="https://img.icons8.com/neon/150/shield.png" width="80" style="filter: drop-shadow(0 0 8px #76B900);">
                <div style="margin-top: 15px; display: flex; justify-content: center; gap: 6px;">
                    <span style="background: rgba(118,185,0,0.1); border: 1px solid #76B900; color: #76B900; font-size: 10px; padding: 2px 10px; border-radius: 5px; font-weight: bold;">ALLIANCE</span>
                    <span style="background: rgba(118,185,0,0.1); border: 1px solid #76B900; color: #76B900; font-size: 10px; padding: 2px 10px; border-radius: 5px; font-weight: bold;">ACTIVE</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        timer_html = """
        <div id="boss-timer-hq" style="
            background: linear-gradient(135deg, #151515 0%, #0a0a0a 100%);
            border: 1px solid rgba(118, 185, 0, 0.4);
            padding: 18px 10px; border-radius: 12px; text-align: center; font-family: sans-serif;
        ">
            <div style="display: flex; align-items: center; justify-content: center; gap: 6px; margin-bottom: 8px;">
                <div style="width: 7px; height: 7px; background: #ff4b4b; border-radius: 50%; animation: blink 1.5s infinite;"></div>
                <span id="target-label" style="font-size: 12px; font-weight: bold; color: #888; letter-spacing: 1px;">NEXT BOSS SCAN</span>
            </div>
            <div id="countdown-val" style="
                font-size: 34px; font-weight: 900; color: #76B900; 
                font-family: 'Courier New', monospace; text-shadow: 0 0 10px rgba(118, 185, 0, 0.5);
                margin: 5px 0;
            ">00:00:00</div>
            <div style="font-size: 10px; color: #444; letter-spacing: 2px; margin-top: 8px; border-top: 1px solid #222; padding-top: 8px;">REMAINING TIME</div>
        </div>
        <style> @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } } </style>
        <script>
        function updateTimer() {
            const now = new Date(new Date().toLocaleString("en-US", {timeZone: "Asia/Seoul"}));
            const bossTimes = [14, 18, 20];
            let target = null;
            for (let hour of bossTimes) {
                let t = new Date(now); t.setHours(hour, 0, 0, 0);
                if (now < t) { target = t; break; }
            }
            if (!target) { target = new Date(now); target.setDate(now.getDate() + 1); target.setHours(14, 0, 0, 0); }
            const diff = target - now;
            const h = String(Math.floor(diff / 3600000)).padStart(2, '0');
            const m = String(Math.floor((diff % 3600000) / 60000)).padStart(2, '0');
            const s = String(Math.floor((diff % 60000) / 1000)).padStart(2, '0');
            document.getElementById('target-label').innerText = target.getHours() + ":00 BOSS RADAR";
            document.getElementById('countdown-val').innerText = h + ":" + m + ":" + s;
        }
        setInterval(updateTimer, 1000); updateTimer();
        </script>
        """
        components.html(timer_html, height=160)
        
        st.subheader("📊 연합 실시간 지표")
        sc1, sc2 = st.columns(2)
        sc1.metric("인원", f"{len(df)}명")
        sc2.metric("총투력", f"{df['전투력_v'].sum():,}")
        st.divider()
        
        youtube_links = [("가미가미 TV", "https://www.youtube.com/@gamigami706", "youtube-play"),
                         ("왕코 방송국", "https://www.youtube.com/@스트리머왕코", "controller"),
                         ("아이엠솔이", "https://www.youtube.com/@아이엠솔이", "microphone")]
        for name, url, icon in youtube_links:
            y1, y2 = st.columns([1, 4])
            with y1: st.image(f"https://img.icons8.com/neon/96/{icon}.png", width=25)
            with y2: st.link_button(name, url, use_container_width=True)
            
        st.divider()
        with st.expander("🔐 ADMIN", expanded=False):
            admin_pw = st.text_input("PASSWORD", type="password")
            is_admin = (admin_pw == "1234") 
            if st.button("SYSTEM RELOAD"):
                st.cache_data.clear()
                st.rerun()

    # --- 메인 영역 ---
    st.title("🛡️ COMMAND CENTER")
    
    search_q = st.text_input("🔍 연합원 검색", placeholder="닉네임을 입력하세요")
    if search_q:
        res = df[df['이름'].str.contains(search_q, na=False, case=False)].copy()
        if not res.empty:
            res['전투력_표시'] = res['전투력_v'].apply(lambda x: f"{x:,}")
            st.dataframe(res[['문파', '이름', '직업', '전투력_표시', '성장_표시']], use_container_width=True, hide_index=True)
        st.divider()

    tabs = st.tabs(["⚔️ 보탐 현황", "🛡️ 투력 현황", "🔥 성장 랭킹", "🏆 직업별 랭킹", "📊 분석 통계", "💰 정산 현황"])

    # 📏 높이 변수 설정 (원하시는 만큼 조절 가능합니다)
    TABLE_HEIGHT = 700 

    with tabs[0]: # ⚔️ 보스 현황
        max_val = df['누계_v'].max()
        if max_val > 0:
            mvps = df[df['누계_v'] == max_val]['이름'].tolist()
            st.markdown(f"<div class='mvp-bar'><span style='color:#76B900; font-weight:bold;'>🏆 이번 주 보탐 MVP : </span><span style='color:white;'>{', '.join(mvps)}</span> <small>({max_val}회 참여)</small></div>", unsafe_allow_html=True)
        
        p_cols = st.columns(3)
        t_info = [("14시", "14_p"), ("18시", "18_p"), ("20시", "22_p")]
        for i, (t_name, p_col) in enumerate(t_info):
            with p_cols[i]:
                names = df[df[p_col]]['이름'].tolist()
                st.markdown(f"#### 🕒 {t_name} ({len(names)}명)")
                st.markdown(f"<div class='participant-box'>{', '.join(names) if names else '참여자 없음'}</div>", unsafe_allow_html=True)
        
        st.divider()
        boss_vis = df.copy()
        for col in ['14시', '18시', '22시']:
            boss_vis[col] = boss_vis[col].apply(lambda x: "✅" if str(x).strip().lower() in ['o', 'ㅇ', 'v'] else "──")
        boss_rank = add_medal_logic(boss_vis.sort_values(by="누계_v", ascending=False))
        st.dataframe(
            boss_rank[['순위', '문파', '이름', '14시', '18시', '22시', '누계_v']], 
            use_container_width=True, hide_index=True, height=TABLE_HEIGHT,
            column_config={"누계_v": st.column_config.ProgressColumn("참여도", format="%d회", min_value=0, max_value=int(max_val) if max_val > 0 else 21)}
        )

    with tabs[1]: # 🛡️ 투력 현황
        cp_rank = add_medal_logic(df.sort_values(by="전투력_v", ascending=False))
        cp_rank['전투력_표시'] = cp_rank['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(cp_rank[['순위', '문파', '이름', '직업', '전투력_표시', '성장_표시']], use_container_width=True, hide_index=True, height=TABLE_HEIGHT)

    with tabs[2]: # 🔥 성장 랭킹 (높이 확장 적용)
        st.subheader("🔥 실시간 성장률 TOP 랭킹")
        growth_rank = add_medal_logic(df.sort_values(by="성장_v", ascending=False))
        st.dataframe(growth_rank[['순위', '문파', '이름', '성장_표시', '전투력']], use_container_width=True, hide_index=True, height=TABLE_HEIGHT)

    with tabs[3]: # 🏆 직업별 랭킹
        job_list = sorted(df['직업'].unique())
        selected_job = st.selectbox("직업 선택", job_list)
        job_rank = add_medal_logic(df[df['직업'] == selected_job].sort_values(by="전투력_v", ascending=False))
        job_rank['전투력_표시'] = job_rank['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(job_rank[['순위', '문파', '이름', '전투력_표시', '성장_표시']], use_container_width=True, hide_index=True, height=TABLE_HEIGHT)

    with tabs[4]: # 📊 분석 통계
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("통합 전투력", f"{df['전투력_v'].sum():,}")
        sc2.metric("평균 전투력", f"{int(df['전투력_v'].mean()):,}")
        sc3.metric("평균 성장률", f"{df['성장_v'].mean():.2f}%")
        st.divider()
        g1, g2 = st.columns(2)
        with g1:
            fig_pie = px.pie(df, names='문파', values='전투력_v', hole=0.6, title="문파별 투력 비중", color_discrete_map={"오늘만산다": "#76B900", "오늘만살자": "#007BFF"})
            st.plotly_chart(fig_pie, use_container_width=True)
        with g2:
            fig_bar = px.bar(df['직업'].value_counts().reset_index(), x='직업', y='count', title="연합 직업 분포", color_discrete_sequence=['#76B900'])
            st.plotly_chart(fig_bar, use_container_width=True)

    with tabs[5]: # 💰 정산 현황
        money_rank = add_medal_logic(df[df['전투력_v'] > 1].sort_values(by="분배금_v", ascending=False))
        money_rank['분배금_표시'] = money_rank['분배금_v'].apply(lambda x: f"{x:,} 다이아")
        if is_admin:
            edited_df = st.data_editor(
                money_rank[['순위', '이름', '분배금_표시', '정산상태']], 
                column_config={"정산상태": st.column_config.SelectboxColumn("상태", options=["미정산", "정산완료"])}, 
                disabled=["순위", "이름", "분배금_표시"], hide_index=True, use_container_width=True, height=TABLE_HEIGHT
            )
            if st.button("💾 정산 데이터 저장"):
                status_idx = sheet_header.index("정산상태") + 1
                for _, row in edited_df.iterrows():
                    cell = worksheet.find(row['이름'])
                    worksheet.update_cell(cell.row, status_idx, row['정산상태'])
                st.cache_data.clear()
                st.rerun()
        else:
            money_rank['상태'] = money_rank['정산상태'].apply(lambda x: "✅ 완료" if x == "정산완료" else "⏳ 대기")
            st.dataframe(money_rank[['순위', '문파', '이름', '분배금_표시', '상태']], use_container_width=True, hide_index=True, height=TABLE_HEIGHT)

else:
    st.error("데이터 로드 실패")



















