import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import plotly.express as px
import streamlit.components.v1 as components
from datetime import datetime

# 1. 🎨 [디자인] NVIDIA 프리미엄 다크 테마 및 카드 레이아웃 설정
st.set_page_config(page_title="조협클래식 오늘만산다,살자", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505 !important; color: #FFFFFF !important; }
    h1, h2, h3, [data-testid="stMetricValue"] { color: #76B900 !important; font-weight: bold !important; }
    
    /* 사이드바 여백 최적화 */
    [data-testid="stSidebar"] > div:first-child { padding-top: 20px !important; }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.8rem !important; }
    .stDivider { margin: 0.8rem 0 !important; }
    
    /* 🛍️ 카드형 거래소 디자인 */
    .market-card {
        background: linear-gradient(145deg, #151515, #0d0d0d);
        border: 1px solid #222;
        border-left: 5px solid #76B900;
        padding: 18px;
        border-radius: 12px;
        margin-bottom: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.6);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .item-info { flex-grow: 1; }
    .item-name { color: #FFFFFF; font-size: 1.25rem; font-weight: 800; margin-bottom: 6px; }
    .item-seller { color: #777; font-size: 0.9rem; }
    .item-price-area { text-align: right; min-width: 120px; }
    .item-price { color: #76B900; font-size: 1.4rem; font-weight: 900; }
    .item-status-tag { 
        background: rgba(118, 185, 0, 0.15); 
        color: #76B900; 
        padding: 3px 10px; 
        border-radius: 6px; 
        font-size: 0.75rem; 
        font-weight: 800;
        border: 1px solid rgba(118, 185, 0, 0.3);
        margin-bottom: 5px;
    }

    /* 표(DataFrame) 스타일 강제 고정 */
    [data-testid="stDataFrame"] { background-color: #111111 !important; }
    div[data-testid="stDataFrame"] div[data-baseweb="table"] div {
        background-color: #111111 !important;
        color: white !important;
        text-align: left !important;
    }

    .mvp-bar {
        background: linear-gradient(90deg, #111, #1a1a1a);
        border: 1px solid #76B900;
        padding: 10px 20px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 20px;
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
@st.cache_data(ttl=2)
def load_all_guild_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open("조협오산오살")
        
        # 메인 시트 로드
        sheet = spreadsheet.sheet1
        all_data = sheet.get_all_values()
        header, rows = all_data[6], all_data[7:]
        df = pd.DataFrame(rows, columns=header)
        df = df[df['이름'].str.strip() != ""].copy()
        
        # 거래소 시트 로드 (인덱스 기반 매칭)
        market_sheet = None
        market_df = pd.DataFrame(columns=["판매자", "아이템이름", "가격", "상태"])
        try:
            market_sheet = spreadsheet.worksheet("거래소")
            m_values = market_sheet.get_all_values()
            if len(m_values) > 1:
                processed_rows = []
                for row in m_values[1:]:
                    fixed_row = (row + ["", "", "", ""])[:4] 
                    processed_rows.append(fixed_row)
                market_df = pd.DataFrame(processed_rows, columns=["판매import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import plotly.express as px
import streamlit.components.v1 as components

# 1. 🎨 [디자인] NVIDIA 프리미엄 다크 테마 및 카드 레이아웃
st.set_page_config(page_title="조협클래식 통합 관리 시스템", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505 !important; color: #FFFFFF !important; }
    h1, h2, h3, [data-testid="stMetricValue"] { color: #76B900 !important; font-weight: bold !important; }
    
    /* 사이드바 여백 최적화 */
    [data-testid="stSidebar"] > div:first-child { padding-top: 20px !important; }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.8rem !important; }
    .stDivider { margin: 0.8rem 0 !important; }
    
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
        font-size: 0.75rem; font-weight: bold; border: 1px solid #76B900; color: #76B900; margin-bottom: 12px;
    }
    .status-tag-sold { border-color: #555; color: #555; }
    
    /* 표 스타일 */
    [data-testid="stDataFrame"] { background-color: #111111 !important; }
    div[data-testid="stDataFrame"] div[data-baseweb="table"] div {
        background-color: #111111 !important; color: white !important; text-align: left !important;
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

# 📂 2. 데이터 로드 및 전처리
@st.cache_data(ttl=2)
def load_all_guild_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open("조협오산오살")
        
        # 메인 시트 로드
        sheet = spreadsheet.sheet1
        all_data = sheet.get_all_values()
        header, rows = all_data[6], all_data[7:]
        df = pd.DataFrame(rows, columns=header)
        df = df[df['이름'].str.strip() != ""].copy()
        
        # 거래소 시트 로드
        market_sheet = None
        market_df = pd.DataFrame(columns=["판매자", "아이템이름", "가격", "상태"])
        try:
            market_sheet = spreadsheet.worksheet("거래소")
            m_values = market_sheet.get_all_values()
            if len(m_values) > 1:
                processed_rows = []
                for row in m_values[1:]:
                    fixed_row = (row + ["", "", "", ""])[:4] 
                    processed_rows.append(fixed_row)
                market_df = pd.DataFrame(processed_rows, columns=["판매자", "아이템이름", "가격", "상태"])
        except: pass

        # 숫자 및 성장률 데이터 정제
        def to_int(val):
            clean = re.sub(r'[^0-9]', '', str(val))
            return int(clean) if clean else 0
        def parse_growth(val):
            percent = re.search(r'([\d\.]+)(?=%)', str(val))
            value = re.search(r'\(([^)]+)\)', str(val))
            return float(percent.group(1)) if percent else 0.0, value.group(1) if value else "0"

        df['전투력_v'] = df['전투력'].apply(to_int)
        df['누계_v'] = df['누계'].apply(to_int)
        df['분배금_v'] = df['분배금'].apply(to_int)
        
        growth_parsed = df['성장'].apply(parse_growth)
        df['성장_v'] = [x[0] for x in growth_parsed]
        df['성장_표시'] = [f"{x[0]}% ({x[1]})" for x in growth_parsed]
        df['정산상태'] = df['정산상태'].apply(lambda x: "정산완료" if str(x).strip() == "정산완료" else "미정산")
        
        def is_p(val): return str(val).strip().lower() in ['o', 'ㅇ', 'v']
        df['14_p'], df['18_p'], df['22_p'] = df['14시'].apply(is_p), df['18시'].apply(is_p), df['22시'].apply(is_p)
        
        return spreadsheet, sheet, df, header, market_sheet, market_df
    except Exception as e:
        return None, None, str(e), None, None, None

spreadsheet, worksheet, df, sheet_header, market_worksheet, market_df = load_all_guild_data()

# 📊 3. 화면 구성
if isinstance(df, pd.DataFrame):
    with st.sidebar:
        st.markdown("<div style='text-align:center; padding-bottom:10px;'><img src='https://img.icons8.com/neon/150/shield.png' width='75'></div>", unsafe_allow_html=True)
        
        # 보스 타이머
        timer_html = """
        <div style="background:linear-gradient(135deg,#151515,#0a0a0a); border:1px solid #76B90066; padding:15px; border-radius:10px; text-align:center;">
            <div style="font-size:11px; color:#888; font-weight:bold; margin-bottom:5px;">NEXT BOSS SCAN</div>
            <div id="sidebar-timer" style="font-size:32px; font-weight:900; color:#76B900; font-family:monospace;">00:00:00</div>
        </div>
        <script>
        function up() {
            const n = new Date(new Date().toLocaleString("en-US",{timeZone:"Asia/Seoul"}));
            const b = [14, 18, 20]; let t = null;
            for(let h of b){ let x=new Date(n); x.setHours(h,0,0,0); if(n<x){t=x;break;}}
            if(!t){t=new Date(n); t.setDate(n.getDate()+1); t.setHours(14,0,0,0);}
            const d = t-n;
            const h = String(Math.floor(d/3600000)).padStart(2,'0');
            const m = String(Math.floor((d%3600000) / 60000)).padStart(2,'0');
            const s = String(Math.floor((d%60000) / 1000)).padStart(2,'0');
            document.getElementById('sidebar-timer').innerText = h+":"+m+":"+s;
        } setInterval(up,1000); up();
        </script>
        """
        components.html(timer_html, height=120)
        
        if st.button("🔄 최신 데이터 불러오기", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        st.subheader("📊 연합 실시간 지표")
        c1, c2 = st.columns(2)
        c1.metric("인원", f"{len(df)}명")
        c2.metric("총투력", f"{df['전투력_v'].sum():,}")
        
        st.divider()
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

    st.title("🛡️ COMMAND CENTER")
    tabs = st.tabs(["⚔️ 보탐 현황", "🛡️ 투력 현황", "🔥 성장 랭킹", "🏆 직업별 랭킹", "🛍️ 문파 거래소", "📊 분석 통계", "💰 정산 현황"])

    TABLE_HEIGHT = 700 

    with tabs[0]: # ⚔️ 보탐 현황
        max_val = df['누계_v'].max()
        if max_val > 0:
            mvps = df[df['누계_v'] == max_val]['이름'].tolist()
            st.markdown(f"<div class='mvp-bar'><span style='color:#76B900; font-weight:bold;'>🏆 이번 주 보탐 MVP : </span>{', '.join(mvps)}</div>", unsafe_allow_html=True)
        p_cols = st.columns(3)
        t_info = [("14시", "14_p"), ("18시", "18_p"), ("20시", "22_p")]
        for i, (t_name, p_col) in enumerate(t_info):
            with p_cols[i]:
                names = df[df[p_col]]['이름'].tolist()
                st.markdown(f"#### 🕒 {t_name}")
                st.markdown(f"<div class='participant-box'>{', '.join(names) if names else '참여자 없음'}</div>", unsafe_allow_html=True)
        st.divider()
        boss_vis = df.copy()
        for col in ['14시', '18시', '22시']: boss_vis[col] = boss_vis[col].apply(lambda x: "✅" if str(x).strip().lower() in ['o', 'ㅇ', 'v'] else "──")
        st.dataframe(add_medal_logic(boss_vis.sort_values(by="누계_v", ascending=False))[['순위', '문파', '이름', '14시', '18시', '22시', '누계_v']], use_container_width=True, hide_index=True, height=TABLE_HEIGHT)

    with tabs[1]: # 🛡️ 투력 현황
        cp_rank = add_medal_logic(df.sort_values(by="전투력_v", ascending=False))
        cp_rank['전투력_표시'] = cp_rank['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(cp_rank[['순위', '문파', '이름', '직업', '전투력_표시', '성장_표시']], use_container_width=True, hide_index=True, height=TABLE_HEIGHT)

    with tabs[2]: # 🔥 성장 랭킹
        growth_rank = add_medal_logic(df.sort_values(by="성장_v", ascending=False))
        st.dataframe(growth_rank[['순위', '문파', '이름', '성장_표시', '전투력']], use_container_width=True, hide_index=True, height=TABLE_HEIGHT)

    with tabs[3]: # 🏆 직업별 랭킹
        job_list = sorted(df['직업'].unique())
        selected_job = st.selectbox("직업 선택", job_list)
        job_rank = add_medal_logic(df[df['직업'] == selected_job].sort_values(by="전투력_v", ascending=False))
        job_rank['전투력_표시'] = job_rank['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(job_rank[['순위', '문파', '이름', '전투력_표시', '성장_표시']], use_container_width=True, hide_index=True, height=TABLE_HEIGHT)

    with tabs[4]: # 🛍️ 문파 거래소 (카드형 & 자율형)
        m_col1, m_col2 = st.columns([1, 2])
        with m_col1:
            with st.form("market_form", clear_on_submit=True):
                m_seller = st.text_input("판매자 닉네임", placeholder="내 아이디")
                m_item = st.text_input("아이템 이름", placeholder="아이템명")
                m_price = st.text_input("가격", placeholder="예: 500 💎")
                if st.form_submit_button("등록하기"):
                    if market_worksheet:
                        market_worksheet.append_row([m_seller, m_item, m_price, "판매중"])
                        st.success("등록되었습니다!")
                        st.cache_data.clear()
                        st.rerun()
        with m_col2:
            if not market_df.empty:
                for idx, row in market_df.iterrows():
                    is_sold = "판매완료" in row['상태']
                    card_class = "market-card sold-out-card" if is_sold else "market-card"
                    st.markdown(f"""
                        <div class="{card_class}">
                            <div class="item-info"><div class="item-name">{row['아이템이름']}</div><div class="item-seller">판매자 : {row['판매자']}</div></div>
                            <div class="status-area"><div class="status-tag {'status-tag-sold' if is_sold else ''}">{'판매완료' if is_sold else '판매중'}</div><div class="item-price">{row['가격']}</div></div>
                        </div>
                    """, unsafe_allow_html=True)
                    b_c1, b_c2 = st.columns(2)
                    if not is_sold:
                        if b_c1.button(f"🤝 거래완료", key=f"done_{idx}"):
                            market_worksheet.update_cell(idx + 2, 4, "판매완료"); st.cache_data.clear(); st.rerun()
                    if is_admin:
                        if b_c2.button(f"🗑️ 매물삭제", key=f"del_{idx}"):
                            market_worksheet.delete_rows(idx + 2); st.cache_data.clear(); st.rerun()
            else: st.info("매물이 없습니다.")

    with tabs[5]: # 📊 분석 통계
        st.subheader("📊 연합 실시간 분석")
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("통합 전투력", f"{df['전투력_v'].sum():,}")
        sc2.metric("평균 전투력", f"{int(df['전투력_v'].mean()):,}")
        sc3.metric("평균 성장률", f"{df['성장_v'].mean():.2f}%")
        st.divider()
        g1, g2 = st.columns(2)
        with g1: st.plotly_chart(px.pie(df, names='문파', values='전투력_v', hole=0.6, title="문파별 투력 비중"), use_container_width=True)
        with g2: st.plotly_chart(px.bar(df['직업'].value_counts().reset_index(), x='직업', y='count', title="연합 직업 분포"), use_container_width=True)

    with tabs[6]: # 💰 정산 현황 (정예 인원 필터링 적용)
        st.subheader("💰 정예 인원 정산 관리")
        
        # 🚨 [논리 수정] 전투력 > 1 이고 보탐 참여(누계) > 0 인 인원만 정산 대상으로 확정
        elite_df = df[(df['전투력_v'] > 1) & (df['누계_v'] > 0)].copy()
        
        income = elite_df['분배금_v'].sum()
        paid = elite_df[elite_df['정산상태'] == "정산완료"]['분배금_v'].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("정예 총 분배금", f"{income:,} 💎", help="전투력 기입 & 보탐 참여자 합계")
        m2.metric("정산 완료", f"{paid:,} 💎")
        m3.metric("남은 금액", f"{income-paid:,} 💎", delta_color="inverse")
        st.caption(f"※ 제외 인원: {len(df) - len(elite_df)}명 (투력 미기입 또는 보탐 미참여)")
        st.divider()

        money_rank = add_medal_logic(elite_df.sort_values(by="분배금_v", ascending=False))
        money_rank['분배금_표시'] = money_rank['분배금_v'].apply(lambda x: f"{x:,} 다이아")
        
        if is_admin:
            edited_df = st.data_editor(money_rank[['순위', '이름', '분배금_표시', '정산상태']], 
                                       column_config={"정산상태": st.column_config.SelectboxColumn("상태", options=["미정산", "정산완료"])}, 
                                       disabled=["순위", "이름", "분배금_표시"], 
                                       hide_index=True, use_container_width=True, height=700)
            if st.button("💾 정산 상태 저장"):
                idx = sheet_header.index("정산상태") + 1
                for _, row in edited_df.iterrows():
                    cell = worksheet.find(row['이름'])
                    worksheet.update_cell(cell.row, idx, row['정산상태'])
                st.cache_data.clear(); st.rerun()
        else:
            money_rank['상태'] = money_rank['정산상태'].apply(lambda x: "✅ 완료" if x == "정산완료" else "⏳ 대기")
            st.dataframe(money_rank[['순위', '문파', '이름', '분배금_표시', '상태']], use_container_width=True, hide_index=True, height=700)

else: st.error("데이터 로드 실패")





