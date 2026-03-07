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
    
    /* 🚨 모든 표의 데이터(글자, 숫자) 좌측 정렬 강제 고정 */
    [data-testid="stDataFrame"] div[data-baseweb="table"] div {
        text-align: left !important;
        justify-content: flex-start !important;
        padding-left: 10px !important;
    }
    
    /* 사이드바 최적화 */
    [data-testid="stSidebar"] > div:first-child { padding-top: 20px !important; }
    
    /* 🛍️ 카드형 거래소 디자인 */
    .market-card {
        background: #111; border: 1px solid #222; border-left: 5px solid #76B900;
        padding: 15px; border-radius: 10px; margin-bottom: 5px;
        display: flex; justify-content: space-between; align-items: center;
    }
    .item-name { color: #FFF; font-size: 1.25rem; font-weight: bold; }
    .item-price { color: #76B900; font-size: 1.15rem; font-weight: 800; }
    
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
        
        sheet = spreadsheet.sheet1
        all_data = sheet.get_all_values()
        
        header_idx = 0
        for i, row in enumerate(all_data):
            if "이름" in row and "문파" in row:
                header_idx = i
                break
        
        header = all_data[header_idx]
        rows = all_data[header_idx + 1:]
        df = pd.DataFrame(rows, columns=header)
        df['sheet_row'] = range(header_idx + 2, header_idx + 2 + len(df))
        df = df[df['이름'].str.strip() != ""].copy()
        
        # 거래소 시트 로드
        market_df = pd.DataFrame(columns=["판매자", "아이템이름", "가격", "상태"])
        try:
            market_sheet = spreadsheet.worksheet("거래소")
            m_values = market_sheet.get_all_values()
            if len(m_values) > 1:
                processed_rows = [(row + ["", "", "", ""])[:4] for row in m_values[1:]]
                market_df = pd.DataFrame(processed_rows, columns=["판매자", "아이템이름", "가격", "상태"])
        except: market_sheet = None

        def to_int(val):
            clean = re.sub(r'[^0-9]', '', str(val))
            return int(clean) if clean else 0

        for col in ['전투력', '누계', '분배금']:
            if col in df.columns: df[f'{col}_v'] = df[col].apply(to_int)
            else: df[f'{col}_v'] = 0

        # 성장률 파싱 복구
        def parse_growth(val):
            val = str(val)
            pct = re.search(r'([\d\.]+)(?=%)', val)
            num = re.search(r'([▲▼]?[\d,]+)', val)
            p_val = float(pct.group(1)) if pct else 0.0
            n_val = num.group(1) if num else "0"
            return p_val, f"{p_val}% ({n_val})"

        if '성장' in df.columns:
            growth_res = df['성장'].apply(parse_growth)
            df['성장_v'] = [x[0] for x in growth_res]
            df['성장_표시'] = [x[1] for x in growth_res]
        
        df['정산상태'] = df['정산상태'].apply(lambda x: "정산완료" if str(x).strip() == "정산완료" else "미정산") if '정산상태' in df.columns else "미정산"
        
        def is_p(val): return str(val).strip().lower() in ['o', 'ㅇ', 'v']
        for t in ['14시', '18시', '22시']:
            if t in df.columns: df[f'{t}_p'] = df[t].apply(is_p)
            else: df[f'{t}_p'] = False
        
        return spreadsheet, sheet, df, header, market_sheet, market_df
    except Exception as e:
        return None, None, str(e), None, None, None

spreadsheet, worksheet, df, sheet_header, market_worksheet, market_df = load_all_guild_data()

# 📊 3. 화면 구성
if isinstance(df, pd.DataFrame):
    with st.sidebar:
        st.markdown("<div style='text-align:center; padding-bottom:10px;'><img src='https://img.icons8.com/neon/150/shield.png' width='75'></div>", unsafe_allow_html=True)
        
        # 타이머
        timer_html = """
        <div style="background:linear-gradient(135deg,#151515,#0a0a0a); border:1px solid #76B90066; padding:15px; border-radius:10px; text-align:center;">
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
        components.html(timer_html, height=100)
        
        if st.button("🔄 최신 데이터 불러오기", use_container_width=True):
            st.cache_data.clear(); st.rerun()

        st.divider()
        st.subheader("📊 연합 실시간 지표")
        c1, c2 = st.columns(2)
        c1.metric("인원", f"{len(df)}명"); c2.metric("총투력", f"{df['전투력_v'].sum():,}")
        
        st.divider()
        for name, url, icon in [("가미가미 TV", "https://www.youtube.com/@gamigami706", "youtube-play"), ("왕코 방송국", "https://www.youtube.com/@스트리머왕코", "controller"), ("아이엠솔이", "https://www.youtube.com/@아이엠솔이", "microphone")]:
            y1, y2 = st.columns([1, 4])
            with y1: st.image(f"https://img.icons8.com/neon/96/{icon}.png", width=22)
            with y2: st.link_button(name, url, use_container_width=True)

    st.title("🛡️ COMMAND CENTER")
    tabs = st.tabs(["⚔️ 보탐 현황", "🛡️ 투력 현황", "🔥 성장 랭킹", "🏆 직업별 랭킹", "🛍️ 문파 거래소", "📊 분석 통계", "💰 정산 현황"])

    with tabs[0]: # ⚔️ 보탐 현황 (누계 -> 참여횟수 변경 및 좌측 정렬)
        boss_vis = df.copy()
        for col in ['14시', '18시', '22시']: 
            if col in boss_vis.columns: boss_vis[col] = boss_vis[col].apply(lambda x: "✅" if str(x).strip().lower() in ['o', 'ㅇ', 'v'] else "──")
        
        display_df = add_medal_logic(boss_vis.sort_values(by="누계_v", ascending=False))
        display_df = display_df.rename(columns={"누계_v": "참여횟수"})
        
        st.dataframe(
            display_df[['순위', '문파', '이름', '14시', '18시', '22시', '참여횟수']],
            column_config={"참여횟수": st.column_config.NumberColumn("참여횟수", alignment="left")},
            use_container_width=True, hide_index=True, height=700
        )

    with tabs[1]: # 🛡️ 투력 현황
        cp_rank = add_medal_logic(df.sort_values(by="전투력_v", ascending=False))
        st.dataframe(
            cp_rank[['순위', '문파', '이름', '직업', '전투력_v']],
            column_config={"전투력_v": st.column_config.NumberColumn("전투력", alignment="left")},
            use_container_width=True, hide_index=True, height=700
        )

    with tabs[2]: # 🔥 성장 랭킹
        growth_df = add_medal_logic(df.sort_values(by="성장_v", ascending=False))
        st.dataframe(
            growth_df[['순위', '문파', '이름', '성장_표시', '전투력_v']],
            column_config={"전투력_v": st.column_config.NumberColumn("전투력", alignment="left")},
            use_container_width=True, hide_index=True, height=700
        )

    with tabs[5]: # 📊 분석 통계 (풀 지표 복구)
        st.subheader("📊 연합 분석 대시보드")
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("통합 전투력", f"{df['전투력_v'].sum():,}")
        sc2.metric("평균 전투력", f"{int(df['전투력_v'].mean()):,}")
        sc3.metric("최고 전투력", f"{df['전투력_v'].max():,}")
        sc4.metric("연합 인원", f"{len(df)}명")
        
        st.divider()
        g1, g2 = st.columns(2)
        with g1:
            guild_sum = df.groupby('문파')['전투력_v'].sum().reset_index()
            fig_pie = px.pie(guild_sum, names='문파', values='전투력_v', hole=0.5, title="🏰 문파별 투력 점유율", color_discrete_sequence=['#76B900', '#007BFF'])
            fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig_pie, use_container_width=True)
        with g2:
            job_counts = df['직업'].value_counts().reset_index()
            job_counts.columns = ['직업', '인원']
            fig_bar = px.bar(job_counts, x='직업', y='인원', title="⚔️ 직업별 인원 분포", text='인원')
            fig_bar.update_traces(marker_color='#76B900', opacity=0.8)
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig_bar, use_container_width=True)

    with tabs[6]: # 💰 정산 현황 (분배금_v -> 분배금 변경 및 좌측 정렬)
        elite_df = df[(df['전투력_v'] > 1) & (df['누계_v'] > 0)].copy()
        st.markdown(f"### 💰 정산 리스트 <img src='https://img.icons8.com/neon/96/money-transfer.png' width='40' style='vertical-align:middle;'>", unsafe_allow_html=True)
        st.metric("정예 총 분배금", f"{elite_df['분배금_v'].sum():,} 💎")
        
        money_rank = add_medal_logic(elite_df.sort_values(by="분배금_v", ascending=False))
        money_rank = money_rank.rename(columns={"분배금_v": "분배금"})
        
        if is_admin:
            edited_df = st.data_editor(money_rank[['순위', '이름', '분배금', '정산상태', 'sheet_row']], 
                                       column_config={"분배금": st.column_config.NumberColumn("분배금", alignment="left"), "sheet_row": None},
                                       disabled=['순위', '이름', '분배금'], hide_index=True, use_container_width=True)
            if st.button("💾 정산 상태 저장"):
                idx = sheet_header.index("정산상태") + 1
                for _, row in edited_df.iterrows():
                    worksheet.update_cell(int(row['sheet_row']), idx, row['정산상태'])
                st.cache_data.clear(); st.rerun()
        else:
            money_rank['상태'] = money_rank['정산상태'].apply(lambda x: "✅ 완료" if x == "정산완료" else "⏳ 대기")
            st.dataframe(money_rank[['순위', '이름', '분배금', '상태']], 
                         column_config={"분배금": st.column_config.NumberColumn("분배금", alignment="left")},
                         use_container_width=True, hide_index=True, height=700)

    # 🛍️ 거래소 & 나머지 탭 유지
    with tabs[4]: # 🛍️ 문파 거래소
        m_col1, m_col2 = st.columns([1, 2])
        with m_col1:
            st.markdown("### 📝 아이템 등록")
            with st.form("market_form", clear_on_submit=True):
                ms, mi, mp = st.text_input("판매자"), st.text_input("아이템"), st.text_input("가격")
                if st.form_submit_button("등록") and spreadsheet:
                    try: spreadsheet.worksheet("거래소").append_row([ms, mi, mp, "판매중"]); st.cache_data.clear(); st.rerun()
                    except: st.error("거래소 시트가 없습니다.")
        with m_col2:
            if not market_df.empty:
                for idx, row in market_df[market_df['상태'].str.contains("판매중", na=True)].iterrows():
                    st.markdown(f'<div class="market-card"><div class="item-info"><div class="item-name">{row["아이템이름"]}</div><div class="item-seller">판매자 : {row["판매자"]}</div></div><div class="status-area"><div class="status-tag">판매중</div><div class="item-price">{row["가격"]}</div></div></div>', unsafe_allow_html=True)

    with tabs[3]: # 🏆 직업별 랭킹
        job_list = sorted(df['직업'].unique()) if '직업' in df.columns else []
        selected_job = st.selectbox("직업 선택", job_list)
        job_df = add_medal_logic(df[df['직업'] == selected_job].sort_values(by="전투력_v", ascending=False))
        st.dataframe(job_df[['순위', '문파', '이름', '전투력_v']], column_config={"전투력_v": st.column_config.NumberColumn("전투력", alignment="left")}, use_container_width=True, hide_index=True)

else: st.error(f"데이터 로드 실패: {df}")
