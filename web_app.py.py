import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import plotly.express as px
import streamlit.components.v1 as components
from datetime import datetime

# 1. 🎨 [디자인] NVIDIA 프리미엄 다크 테마 및 스타일 설정
st.set_page_config(page_title="조협클래식 오늘만산다,살자", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505 !important; color: #FFFFFF !important; }
    h1, h2, h3, [data-testid="stMetricValue"] { color: #76B900 !important; font-weight: bold !important; }
    
    [data-testid="stSidebar"] > div:first-child { padding-top: 20px !important; }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.8rem !important; }
    .stDivider { margin: 0.8rem 0 !important; }
    
    .custom-table {
        width: 100%; border-collapse: collapse; color: white; background-color: #111;
        border-radius: 10px; overflow: hidden; margin-top: 10px;
    }
    .custom-table th {
        background-color: #1a1a1a; color: #76B900; text-align: left;
        padding: 12px 15px; border-bottom: 2px solid #222; font-size: 0.9rem;
    }
    .custom-table td {
        padding: 10px 15px; border-bottom: 1px solid #222; text-align: left; font-size: 0.85rem;
    }
    .custom-table tr:hover { background-color: #151515; }

    .market-card {
        background: #111; border: 1px solid #222; border-left: 5px solid #76B900;
        padding: 18px; border-radius: 12px; margin-bottom: 5px;
        display: flex; justify-content: space-between; align-items: center;
    }
    .sold-out-card { background: #0a0a0a; border-left: 5px solid #444; opacity: 0.4; filter: grayscale(100%); }
    .item-info { flex: 3; }
    .item-name { color: #FFF; font-size: 1.25rem; font-weight: bold; margin-bottom: 3px; }
    .item-price { color: #76B900; font-size: 1.15rem; font-weight: 800; margin-bottom: 6px; }
    .status-tag { display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: bold; border: 1px solid #76B900; color: #76B900; }
    
    .stButton>button { width: 100%; border-radius: 6px; font-size: 0.85rem !important; height: 35px; }
    .mvp-bar { background: linear-gradient(90deg, #111, #1a1a1a); border: 1px solid #76B900; padding: 10px 20px; border-radius: 8px; text-align: center; margin-bottom: 20px; }
    .participant-box { background-color: #111; border-left: 4px solid #76B900; padding: 10px; border-radius: 5px; margin-bottom: 10px; min-height: 70px; }
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
        header, rows = all_data[6], all_data[7:]
        df = pd.DataFrame(rows, columns=header)
        df = df[df['이름'].str.strip() != ""].copy()
        
        market_sheet = spreadsheet.worksheet("거래소")
        m_values = market_sheet.get_all_values()
        market_df = pd.DataFrame(m_values[1:], columns=["판매자", "아이템이름", "가격", "상태"]) if len(m_values) > 1 else pd.DataFrame(columns=["판매자", "아이템이름", "가격", "상태"])

        def to_int(val):
            clean = re.sub(r'[^0-9]', '', str(val))
            return int(clean) if clean else 0

        df['전투력_v'] = df['전투력'].apply(to_int)
        df['누계_v'] = df['누계'].apply(to_int)
        df['분배금_v'] = df['분배금'].apply(to_int)
        
        def parse_growth(val):
            percent = re.search(r'([\d\.]+)(?=%)', str(val))
            value = re.search(r'\(([^)]+)\)', str(val))
            return (float(percent.group(1)) if percent else 0.0, f"{percent.group(1)}% ({value.group(1)})" if percent and value else "-")

        df['성장_v'], df['성장'] = zip(*df['성장'].apply(parse_growth))
        df['정산상태'] = df['정산상태'].apply(lambda x: "정산완료" if str(x).strip() == "정산완료" else "미정산") if '정산상태' in df.columns else "미정산"
        
        for col in ['14시', '18시', '22시']:
            df[f'{col}_p'] = df[col].apply(lambda x: str(x).strip().lower() in ['o', 'ㅇ', 'v'])
        
        return spreadsheet, sheet, df, header, market_sheet, market_df
    except Exception as e:
        return None, None, str(e), None, None, None

spreadsheet, worksheet, df, sheet_header, market_worksheet, market_df = load_all_guild_data()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if isinstance(df, pd.DataFrame):
    # 사이드바 생략 (동일함)
    with st.sidebar:
        st.markdown("<div style='text-align:center; padding-bottom:10px;'><img src='https://img.icons8.com/neon/150/shield.png' width='75'></div>", unsafe_allow_html=True)
        timer_html = """
        <div style="background:linear-gradient(135deg,#151515,#0a0a0a); border:1px solid #76B90066; padding:15px; border-radius:10px; text-align:center;">
            <div style="font-size:11px; color:#888; font-weight:bold; margin-bottom:5px;">NEXT BOSS RADAR</div>
            <div id="sidebar-timer" style="font-size:32px; font-weight:900; color:#76B900; font-family:monospace;">00:00:00</div>
        </div>
        <script>
        function up(){
            const n=new Date(new Date().toLocaleString("en-US",{timeZone:"Asia/Seoul"}));
            const b=[14,18,22];let t=null;
            for(let h of b){let x=new Date(n);x.setHours(h,0,0,0);if(n<x){t=x;break;}}
            if(!t){t=new Date(n);t.setDate(n.getDate()+1);t.setHours(14,0,0,0);}
            const d=t-n;
            const h=String(Math.floor(d/3600000)).padStart(2,'0'), m=String(Math.floor((d%3600000)/60000)).padStart(2,'0'), s=String(Math.floor((d%60000)/1000)).padStart(2,'0');
            document.getElementById('sidebar-timer').innerText=h+":"+m+":"+s;
        }setInterval(up,1000);up();
        </script>
        """
        components.html(timer_html, height=120)
        if st.button("🔄 최신 데이터 불러오기", use_container_width=True):
            st.cache_data.clear(); st.rerun()
        st.divider()
        st.subheader("📊 실시간 지표")
        c1, c2 = st.columns(2)
        c1.metric("인원", f"{len(df)}명"); c2.metric("총투력", f"{df['전투력_v'].sum():,}")
        st.divider()
        youtube_links = [("가미가미", "https://www.youtube.com/@gamigami706", "youtube-play"), ("왕코 방송국", "https://www.youtube.com/@스트리머왕코", "controller"), ("아이엠솔이", "https://www.youtube.com/@아이엠솔이", "microphone")]
        for name, url, icon in youtube_links:
            y1, y2 = st.columns([1, 4])
            with y1: st.image(f"https://img.icons8.com/neon/96/{icon}.png", width=22)
            with y2: st.link_button(name, url, use_container_width=True)
        st.divider()
        with st.expander("🔐 ADMIN", expanded=st.session_state.authenticated):
            admin_pw = st.text_input("PASSWORD", type="password", key="admin_input")
            if admin_pw == "rkdhkdthfdl12":
                st.session_state.authenticated = True
                st.success("인증되었습니다.")
            elif admin_pw != "":
                st.error("비밀번호가 틀립니다.")
            if st.session_state.authenticated:
                if st.button("로그아웃"):
                    st.session_state.authenticated = False
                    st.rerun()

    st.title("🛡️ COMMAND CENTER")

    search_query = st.text_input("🔍 길드원 닉네임으로 검색", placeholder="검색어를 입력하면 아래 표가 필터링됩니다.")
    if search_query:
        filtered_df = df[df['이름'].str.contains(search_query, case=False, na=False)]
    else:
        filtered_df = df.copy()

    tabs = st.tabs(["⚔️ 보탐 현황", "🛡️ 투력 현황", "🔥 성장 랭킹", "🏆 직업별 랭킹", "🛍️ 문파 거래소", "📊 분석 통계", "💰 정산 현황"])

    def display_custom_table(dataframe, columns_to_show, column_names):
        df_display = dataframe[columns_to_show].copy()
        df_display.columns = column_names
        html = f'<table class="custom-table"><thead><tr>'
        for col in column_names: html += f'<th>{col}</th>'
        html += '</tr></thead><tbody>'
        for _, row in df_display.iterrows():
            html += '<tr>'
            for val in row: html += f'<td>{val}</td>'
            html += '</tr>'
        html += '</tbody></table>'
        st.markdown(html, unsafe_allow_html=True)

    with tabs[0]: # ⚔️ 보탐 현황
        boss_vis = add_medal_logic(filtered_df.sort_values(by="누계_v", ascending=False))
        for col in ['14시', '18시', '22시']: boss_vis[col] = boss_vis[col].apply(lambda x: "✅" if str(x).strip().lower() in ['o', 'ㅇ', 'v'] else "──")
        display_custom_table(boss_vis, ['순위', '문파', '이름', '누계_v', '14시', '18시', '22시'], ['순위', '문파', '이름', '누계', '14시', '18시', '22시'])

        # 🚨 [중요] 관리자 전용 초기화 센터
        if st.session_state.authenticated:
            st.markdown("<br>", unsafe_allow_html=True)
            st.error("⚠️ **관리자 전용 : 주간 데이터 초기화 센터**")
            
            init_c1, init_c2 = st.columns(2)
            
            with init_c1:
                st.info("**1. 보탐 누계 초기화**\n\n모든 인원의 보탐 참여 횟수를 0으로 만듭니다.")
                confirm_reset_boss = st.checkbox("보탐 초기화 확인", key="reset_boss_check")
                if st.button("🔄 보탐 누계 0으로 초기화", disabled=not confirm_reset_boss, use_container_width=True):
                    with st.spinner("초기화 중..."):
                        col_idx = sheet_header.index('누계') + 1
                        cell_list = worksheet.range(8, col_idx, 7 + len(df), col_idx)
                        for cell in cell_list: cell.value = '0'
                        worksheet.update_cells(cell_list)
                        st.cache_data.clear(); st.success("보탐 누계가 초기화되었습니다."); st.rerun()

            with init_c2:
                st.info("**2. 정산 데이터 초기화**\n\n모든 인원의 분배금을 0으로, 상태를 미정산으로 만듭니다.")
                confirm_reset_money = st.checkbox("정산 초기화 확인", key="reset_money_check")
                if st.button("💰 정산 데이터 초기화", disabled=not confirm_reset_money, use_container_width=True):
                    with st.spinner("초기화 중..."):
                        # 분배금 컬럼과 정산상태 컬럼 초기화
                        try:
                            m_idx = sheet_header.index('분배금') + 1
                            s_idx = sheet_header.index('정산상태') + 1
                            # 분배금 0으로
                            m_cells = worksheet.range(8, m_idx, 7 + len(df), m_idx)
                            for c in m_cells: c.value = '0'
                            worksheet.update_cells(m_cells)
                            # 정산상태 미정산으로
                            s_cells = worksheet.range(8, s_idx, 7 + len(df), s_idx)
                            for c in s_cells: c.value = '미정산'
                            worksheet.update_cells(s_cells)
                            
                            st.cache_data.clear(); st.success("정산 데이터가 초기화되었습니다."); st.rerun()
                        except Exception as e:
                            st.error(f"정산 초기화 중 오류: {e}")

    # (이하 탭 생략 - 정산 탭 로직 동일함)
    with tabs[6]: # 💰 정산 현황
        money_rank = add_medal_logic(filtered_df[filtered_df['전투력_v'] > 1].sort_values(by="분배금_v", ascending=False))
        money_rank['분배금_표시'] = money_rank['분배금_v'].apply(lambda x: f"{x:,}")
        
        if st.session_state.authenticated:
            metrics_placeholder = st.empty()
            st.divider()
            edited = st.data_editor(money_rank[['순위', '이름', '분배금_표시', '정산상태']], column_config={"정산상태": st.column_config.SelectboxColumn("상태", options=["미정산", "정산완료"])}, disabled=["순위", "이름", "분배금_표시"], hide_index=True, use_container_width=True)
            
            income = df['분배금_v'].sum()
            merged_for_calc = pd.merge(edited, money_rank[['이름', '분배금_v']], on='이름')
            paid = merged_for_calc[merged_for_calc['정산상태'] == "정산완료"]['분배금_v'].sum()
            
            with metrics_placeholder.container():
                m1, m2, m3 = st.columns(3)
                m1.metric("총 분배금", f"{income:,}"); m2.metric("정산 완료", f"{paid:,}"); m3.metric("남은 금액", f"{income-paid:,}")

            if st.button("💾 정산 상태 저장", key="save_money_status"):
                with st.spinner("저장 중..."):
                    idx = sheet_header.index("정산상태") + 1
                    for _, row in edited.iterrows():
                        original_status = money_rank[money_rank['이름'] == row['이름']]['정산상태'].values[0]
                        if original_status != row['정산상태']:
                            cell = worksheet.find(row['이름'])
                            worksheet.update_cell(cell.row, idx, row['정산상태'])
                    st.cache_data.clear(); st.success("저장되었습니다!"); st.rerun()
        else:
            income, paid = df['분배금_v'].sum(), df[df['정산상태'] == "정산완료"]['분배금_v'].sum()
            m1, m2, m3 = st.columns(3)
            m1.metric("총 분배금", f"{income:,}"); m2.metric("정산 완료", f"{paid:,}"); m3.metric("남은 금액", f"{income-paid:,}")
            st.divider()
            money_rank['상태'] = money_rank['정산상태'].apply(lambda x: "✅ 완료" if x == "정산완료" else "⏳ 대기")
            display_custom_table(money_rank, ['순위', '문파', '이름', '분배금_표시', '상태'], ['순위', '문파', '이름', '분배금', '상태'])

    # (이하 생략...)
    with tabs[1]: # 🛡️ 투력 현황
        cp_rank = add_medal_logic(filtered_df.sort_values(by="전투력_v", ascending=False))
        cp_rank['전투력'] = cp_rank['전투력_v'].apply(lambda x: f"{x:,}")
        display_custom_table(cp_rank, ['순위', '문파', '이름', '직업', '전투력', '성장'], ['순위', '문파', '이름', '직업', '전투력', '성장'])
    with tabs[2]: # 🔥 성장 랭킹
        growth_rank = add_medal_logic(filtered_df.sort_values(by="성장_v", ascending=False))
        growth_rank['전투력'] = growth_rank['전투력_v'].apply(lambda x: f"{x:,}")
        display_custom_table(growth_rank, ['순위', '문파', '이름', '성장', '전투력'], ['순위', '문파', '이름', '성장', '전투력'])
    with tabs[3]: # 🏆 직업별 랭킹
        job_list = sorted(df['직업'].unique())
        selected_job = st.selectbox("직업 선택", job_list)
        job_rank = add_medal_logic(filtered_df[filtered_df['직업'] == selected_job].sort_values(by="전투력_v", ascending=False))
        job_rank['전투력'] = job_rank['전투력_v'].apply(lambda x: f"{x:,}")
        display_custom_table(job_rank, ['순위', '문파', '이름', '전투력', '성장'], ['순위', '문파', '이름', '전투력', '성장'])
    with tabs[5]: # 📊 분석 통계
        st.subheader("📊 연합 실시간 분석")
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("통합 전투력", f"{df['전투력_v'].sum():,}"); sc2.metric("평균 전투력", f"{int(df['전투력_v'].mean()):,}"); sc3.metric("평균 성장률", f"{df['성장_v'].mean():.2f}%")
        g1, g2 = st.columns(2)
        with g1: st.plotly_chart(px.pie(df, names='문파', values='전투력_v', hole=0.6, title="문파별 투력 비중"), use_container_width=True)
        with g2: st.plotly_chart(px.bar(df['직업'].value_counts().reset_index(), x='직업', y='count', title="연합 직업 분포"), use_container_width=True)

else: st.error("데이터 로드 실패")
