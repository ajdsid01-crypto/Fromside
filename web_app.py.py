import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import plotly.express as px
import streamlit.components.v1 as components

# 1. 🎨 [디자인] NVIDIA 프리미엄 다크 테마 및 좌측 정렬 설정
st.set_page_config(page_title="조협클래식 통합 관리 시스템", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505 !important; color: #FFFFFF !important; }
    h1, h2, h3, [data-testid="stMetricValue"] { color: #76B900 !important; font-weight: bold !important; }
    
    /* 🚨 [핵심] 모든 데이터 좌측 정렬 강제 고정 */
    [data-testid="stDataFrame"] div[data-baseweb="table"] div {
        text-align: left !important;
        justify-content: flex-start !important;
    }
    
    /* 사이드바 여백 및 디자인 */
    [data-testid="stSidebar"] > div:first-child { padding-top: 20px !important; }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.8rem !important; }
    
    /* 🛍️ 카드형 거래소 디자인 */
    .market-card {
        background: #111; border: 1px solid #222; border-left: 5px solid #76B900;
        padding: 15px; border-radius: 10px; margin-bottom: 5px;
        display: flex; justify-content: space-between; align-items: center;
    }
    .sold-out-card { background: #0a0a0a; border-left: 5px solid #444; opacity: 0.4; filter: grayscale(100%); }
    .item-info { flex: 3; }
    .item-name { color: #FFF; font-size: 1.25rem; font-weight: bold; margin-bottom: 3px; }
    .item-price { color: #76B900; font-size: 1.15rem; font-weight: 800; margin-bottom: 6px; }
    .item-seller { color: #888; font-size: 0.9rem; }
    .status-area { flex: 1.5; text-align: right; }
    .status-tag { 
        display: inline-block; padding: 4px 10px; border-radius: 6px; 
        font-size: 0.75rem; font-weight: bold; border: 1px solid #76B900; color: #76B900;
    }

    .mvp-bar {
        background: linear-gradient(90deg, #111, #1a1a1a);
        border: 1px solid #76B900; padding: 10px 20px; border-radius: 8px; text-align: center; margin-bottom: 20px;
    }
    .participant-box {
        background-color: #111; border-left: 4px solid #76B900; padding: 10px; border-radius: 5px; margin-bottom: 10px; min-height: 70px;
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

# 📂 2. 데이터 로드 및 전처리 (로드 실패 방어 및 성장률 복구)
@st.cache_data(ttl=2)
def load_all_guild_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open("조협오산오살")
        
        sheet = spreadsheet.sheet1
        all_data = sheet.get_all_values()
        
        header_idx = 0
        for i, row in enumerate(all_data):
            if "이름" in row:
                header_idx = i
                break
        
        header = all_data[header_idx]
        rows = all_data[header_idx + 1:]
        df = pd.DataFrame(rows, columns=header)
        df = df[df['이름'].str.strip() != ""].copy()
        
        # 거래소 시트 로드
        market_df = pd.DataFrame(columns=["판매자", "아이템이름", "가격", "상태"])
        try:
            market_sheet = spreadsheet.worksheet("거래소")
            m_values = market_sheet.get_all_values()
            if len(m_values) > 1:
                processed_rows = [(row + ["", "", "", ""])[:4] for row in m_values[1:]]
                market_df = pd.DataFrame(processed_rows, columns=["판매자", "아이템이름", "가격", "상태"])
        except: pass

        def to_int(val):
            clean = re.sub(r'[^0-9]', '', str(val))
            return int(clean) if clean else 0

        # 🚨 [복구] 성장률 정밀 파싱 (숫자 추출)
        def parse_growth_val(val):
            val = str(val)
            match = re.search(r'([\d\.]+)(?=%)', val)
            return float(match.group(1)) if match else 0.0

        for col in ['전투력', '누계', '분배금']:
            if col in df.columns: df[f'{col}_v'] = df[col].apply(to_int)
            else: df[f'{col}_v'] = 0

        if '성장' in df.columns:
            df['성장_v'] = df['성장'].apply(parse_growth_val)
            df['성장_표시'] = df['성장']
        else:
            df['성장_v'] = 0.0
            df['성장_표시'] = "-"

        if '정산상태' not in df.columns: df['정산상태'] = "미정산"
        df['정산상태'] = df['정산상태'].apply(lambda x: "정산완료" if str(x).strip() == "정산완료" else "미정산")
        
        def is_p(val): return str(val).strip().lower() in ['o', 'ㅇ', 'v']
        for t in ['14시', '18시', '22시']:
            if t in df.columns: df[f'{t}_p'] = df[t].apply(is_p)
            else: df[f'{t}_p'] = False
        
        return spreadsheet, sheet, df, header, market_df
    except Exception as e:
        return None, None, str(e), None, None

spreadsheet, worksheet, df, sheet_header, market_df = load_all_guild_data()

# 📊 3. 화면 구성
if isinstance(df, pd.DataFrame):
    with st.sidebar:
        st.markdown("<div style='text-align:center; padding-bottom:10px;'><img src='https://img.icons8.com/neon/150/shield.png' width='75'></div>", unsafe_allow_html=True)
        
        # 🕒 실시간 보스 타이머 복구
        timer_html = """
        <div style="background:linear-gradient(135deg,#151515,#0a0a0a); border:1px solid #76B90066; padding:15px; border-radius:10px; text-align:center;">
            <div style="font-size:11px; color:#888; font-weight:bold; margin-bottom:5px;">NEXT BOSS SCAN</div>
            <div id="sidebar-timer" style="font-size:32px; font-weight:900; color:#76B900; font-family:monospace;">00:00:00</div>
        </div>
        <script>
        function up(){
            const n=new Date(new Date().toLocaleString("en-US",{timeZone:"Asia/Seoul"}));
            const b=[14,18,20];let t=null;
            for(let x of b){let d=new Date(n); d.setHours(x,0,0,0); if(n<d){t=d;break;}}
            if(!t){t=new Date(n);t.setDate(n.getDate()+1);t.setHours(14,0,0,0);}
            const diff=t-n;
            const h=String(Math.floor(diff/3600000)).padStart(2,'0'), m=String(Math.floor((diff%3600000)/60000)).padStart(2,'0'), s=String(Math.floor((diff%60000)/1000)).padStart(2,'0');
            document.getElementById('sidebar-timer').innerText=h+":"+m+":"+s;
        }setInterval(up,1000);up();
        </script>
        """
        components.html(timer_html, height=120)
        
        if st.button("🔄 최신 데이터 불러오기", use_container_width=True):
            st.cache_data.clear(); st.rerun()

        st.divider()
        st.subheader("📊 연합 실시간 지표")
        c1, c2 = st.columns(2)
        c1.metric("인원", f"{len(df)}명"); c2.metric("총투력", f"{df['전투력_v'].sum():,}")
        
        st.divider()
        # 📺 유튜브 방송국 링크 복구
        youtube_links = [("가미가미 TV", "https://www.youtube.com/@gamigami706", "youtube-play"),
                         ("왕코 방송국", "https://www.youtube.com/@스트리머왕코", "controller"),
                         ("아이엠솔이", "https://www.youtube.com/@아이엠솔이", "microphone")]
        for name, url, icon in youtube_links:
            y1, y2 = st.columns([1, 4])
            with y1: st.image(f"https://img.icons8.com/neon/96/{icon}.png", width=22)
            with y2: st.link_button(name, url, use_container_width=True)
            
        st.divider()
        with st.expander("🔐 ADMIN", expanded=False):
            admin_pw = st.text_input("PASSWORD", type="password")
            is_admin = (admin_pw == "1234") 

    st.title("🛡️ Chosun Swordsman Classic")
    tabs = st.tabs(["⚔️ 보탐 현황", "🛡️ 투력 현황", "🔥 성장 랭킹", "🏆 직업별 랭킹", "🛍️ 문파 거래소", "📊 분석 통계", "💰 정산 현황"])

    # ⚔️ 보탐 현황
    with tabs[0]:
        max_val = df['누계_v'].max()
        if max_val > 0:
            mvps = df[df['누계_v'] == max_val]['이름'].tolist()
            st.markdown(f"<div class='mvp-bar'>🏆 이번 주 보탐 MVP : {', '.join(mvps)}</div>", unsafe_allow_html=True)
        p_cols = st.columns(3)
        for i, (t_name, p_col) in enumerate([("14시", "14시_p"), ("18시", "18시_p"), ("20시", "22시_p")]):
            with p_cols[i]:
                names = df[df[p_col]]['이름'].tolist() if p_col in df.columns else []
                st.markdown(f"#### 🕒 {t_name}"); st.markdown(f"<div class='participant-box'>{', '.join(names) if names else '참여자 없음'}</div>", unsafe_allow_html=True)
        st.divider()
        boss_vis = df.copy()
        for col in ['14시', '18시', '22시']: 
            if col in boss_vis.columns: boss_vis[col] = boss_vis[col].apply(lambda x: "✅" if str(x).strip().lower() in ['o', 'ㅇ', 'v'] else "──")
        st.dataframe(add_medal_logic(boss_vis.sort_values(by="누계_v", ascending=False))[['순위', '문파', '이름', '14시', '18시', '22시', '누계_v']], use_container_width=True, hide_index=True, height=700)

    # 🛡️ 투력 현황
    with tabs[1]:
        st.dataframe(add_medal_logic(df.sort_values(by="전투력_v", ascending=False))[['순위', '문파', '이름', '직업', '전투력_v']], use_container_width=True, hide_index=True, height=700)

    # 🔥 성장 랭킹 (성장률 복구 완료)
    with tabs[2]:
        st.subheader("🔥 주간 성장률 TOP 랭킹")
        growth_df = add_medal_logic(df.sort_values(by="성장_v", ascending=False))
        st.dataframe(growth_df[['순위', '문파', '이름', '성장_표시', '전투력_v']], use_container_width=True, hide_index=True, height=700)

    # 🏆 직업별 랭킹 (검색 필터 유지)
    with tabs[3]:
        job_list = sorted(df['직업'].unique()) if '직업' in df.columns else []
        selected_job = st.selectbox("직업 선택", job_list)
        job_filtered = add_medal_logic(df[df['직업'] == selected_job].sort_values(by="전투력_v", ascending=False))
        st.dataframe(job_filtered[['순위', '문파', '이름', '전투력_v']], use_container_width=True, hide_index=True, height=600)

    # 🛍️ 문파 거래소
    with tabs[4]:
        if not market_df.empty:
            for idx, row in market_df[market_df['상태'].str.contains("판매중", na=True)].iterrows():
                st.markdown(f'<div class="market-card"><div class="item-info"><div class="item-name">{row["아이템이름"]}</div><div class="item-seller">판매자 : {row["판매자"]}</div></div><div class="status-area"><div class="status-tag">판매중</div><div class="item-price">{row["가격"]}</div></div></div>', unsafe_allow_html=True)

    # 📊 분석 통계 (그래프 복구)
    with tabs[5]:
        st.subheader("📊 연합 실시간 분석")
        g1, g2 = st.columns(2)
        with g1:
            fig_pie = px.pie(df, names='문파', values='전투력_v', hole=0.5, title="🏰 문파별 투력 점유율", color_discrete_sequence=['#76B900', '#007BFF'])
            fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white', showlegend=False); st.plotly_chart(fig_pie, use_container_width=True)
        with g2:
            job_counts = df['직업'].value_counts().reset_index(); job_counts.columns = ['직업', '인원']
            fig_bar = px.bar(job_counts, x='직업', y='인원', title="⚔️ 직업별 인원 분포", text='인원')
            fig_bar.update_traces(marker_color='#76B900', opacity=0.8); fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white', xaxis_title=None, yaxis_title=None); st.plotly_chart(fig_bar, use_container_width=True)

    # 💰 정산 현황
    with tabs[6]:
        elite_df = df[(df['전투력_v'] > 1) & (df['누계_v'] > 0)].copy()
        income = elite_df['분배금_v'].sum()
        st.metric("정예 총 분배금", f"{income:,} 💎")
        st.dataframe(add_medal_logic(elite_df.sort_values(by="분배금_v", ascending=False))[['순위', '이름', '분배금_v', '정산상태']], use_container_width=True, hide_index=True, height=700)

else: st.error("데이터 로드 실패")






