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
    
    /* 🏆 메달 카드 디자인 (우측 배치용 슬림 사이즈) */
    .medal-box {
        background: rgba(118, 185, 0, 0.08);
        border: 1px solid rgba(118, 185, 0, 0.3);
        border-radius: 10px;
        padding: 10px 15px;
        text-align: center;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .medal-icon { font-size: 24px; margin-bottom: 2px; }
    .medal-name { font-size: 15px; font-weight: bold; color: white; }
    .medal-val { font-size: 13px; color: #76B900; font-weight: bold; }

    /* 👤 검색 프로필 카드 */
    .search-card {
        background: #111;
        border-left: 4px solid #76B900;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
    .card-label { color: #888; font-size: 11px; margin-bottom: 2px; }
    .card-value { color: #FFF; font-size: 16px; font-weight: bold; }

    .custom-table {
        width: 100%; border-collapse: collapse; color: white; background-color: #111;
        border-radius: 10px; overflow: hidden; margin-top: 10px;
    }
    .custom-table th {
        background-color: #1a1a1a; color: #76B900; text-align: left;
        padding: 12px 15px; border-bottom: 2px solid #222; font-size: 0.9rem;
    }
    .custom-table td { padding: 10px 15px; border-bottom: 1px solid #222; text-align: left; font-size: 0.85rem; }
    </style>
    """, unsafe_allow_html=True)

# 🏆 공통 로직 함수
def add_medal_logic(df):
    df = df.reset_index(drop=True)
    df.insert(0, 'Rank', range(1, len(df) + 1))
    df['순위'] = df['Rank'].apply(lambda x: "🥇 1위" if x==1 else "🥈 2위" if x==2 else "🥉 3위" if x==3 else f"{x}위")
    return df.drop(columns=['Rank'])

def display_top3_on_right(df, val_col, unit=""):
    top3 = df.head(3).reset_index()
    m2, m1, m3 = st.columns([1, 1, 1])
    for i, col in enumerate([m1, m2, m3]): # 1위(가운데), 2위(왼쪽), 3위(오른쪽)
        if len(top3) > i:
            with col:
                row = top3.iloc[i]
                val = f"{row[val_col]:,}" if isinstance(row[val_col], (int, float)) else row[val_col]
                icon = "🥇" if i==0 else "🥈" if i==1 else "🥉"
                st.markdown(f"""
                <div class='medal-box'>
                    <div class='medal-icon'>{icon}</div>
                    <div class='medal-name'>{row['이름']}</div>
                    <div class='medal-val'>{val}{unit}</div>
                </div>
                """, unsafe_allow_html=True)

def display_custom_table(dataframe, columns_to_show, column_names):
    df_display = dataframe[columns_to_show].copy()
    df_display.columns = column_names
    html = f'<table class="custom-table"><thead><tr>' + "".join([f'<th>{c}</th>' for c in column_names]) + '</tr></thead><tbody>'
    for _, row in df_display.iterrows():
        html += '<tr>' + "".join([f'<td>{val}</td>' for val in row]) + '</tr>'
    st.markdown(html + '</tbody></table>', unsafe_allow_html=True)

# 📂 데이터 로드 (st.secrets 사용)
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
        m_df = pd.DataFrame(market_sheet.get_all_values()[1:], columns=["판매자", "아이템이름", "가격", "상태"])

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
        df['정산상태'] = df['정산상태'].apply(lambda x: "정산완료" if str(x).strip() == "정산완료" else "미정산")
        return spreadsheet, sheet, df, header, market_sheet, m_df
    except: return None, None, None, None, None, None

spreadsheet, worksheet, df, sheet_header, market_worksheet, market_df = load_all_guild_data()

# 📊 메인 화면 구성
if df is not None:
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    
    with st.sidebar:
        st.markdown("<div style='text-align:center; padding-bottom:10px;'><img src='https://img.icons8.com/neon/150/shield.png' width='70'></div>", unsafe_allow_html=True)
        # 보스 타이머
        timer_html = """
        <div style="background:#111; border:1px solid #76B90066; padding:10px; border-radius:10px; text-align:center; color:#76B900;">
            <div id="sidebar-timer" style="font-size:28px; font-weight:bold; font-family:monospace;">00:00:00</div>
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
        components.html(timer_html, height=100)
        if st.button("🔄 새로고침"): st.cache_data.clear(); st.rerun()
        st.divider()
        st.subheader("📺 방송국")
        for n, u in [("가미가미 TV", "https://www.youtube.com/@gamigami706"), ("왕코 방송국", "https://www.youtube.com/@스트리머왕코"), ("아이엠솔이", "https://www.youtube.com/@아이엠솔이")]:
            st.link_button(n, u, use_container_width=True)
        st.divider()
        with st.expander("🔐 ADMIN"):
            pw = st.text_input("PW", type="password")
            if pw == "rkdhkdthfdl12": st.session_state.authenticated = True
            if st.session_state.authenticated and st.button("로그아웃"): st.session_state.authenticated = False; st.rerun()

    # 🚀 핵심: 헤더와 Top 3 나란히 배치
    header_left, header_right = st.columns([1.2, 2.5])
    
    with header_left:
        st.title("🛡️ COMMAND CENTER")
        search_query = st.text_input("🔍 닉네임 검색 (하단 표 유지)", placeholder="검색 시 상단에 프로필 카드 생성")
    
    # 탭 구성
    tabs = st.tabs(["⚔️ 보탐 현황", "🛡️ 투력 현황", "🔥 성장 랭킹", "🏆 직업별 랭킹", "🛍️ 문파 거래소", "📊 분석 통계", "💰 정산 현황"])

    # 🔍 검색 프로필 카드 (검색 시에만 노출)
    if search_query:
        search_res = df[df['이름'].str.contains(search_query, case=False, na=False)]
        if not search_res.empty:
            st.markdown("##### 👤 검색된 인원 프로필 요약")
            for _, row in search_res.iterrows():
                c1, c2, c3, c4, c5 = st.columns(5)
                with c1: st.markdown(f"<div class='search-card'><div class='card-label'>이름</div><div class='card-value'>{row['이름']}</div></div>", unsafe_allow_html=True)
                with c2: st.markdown(f"<div class='search-card'><div class='card-label'>직업</div><div class='card-value'>{row['직업']}</div></div>", unsafe_allow_html=True)
                with c3: st.markdown(f"<div class='search-card'><div class='card-label'>전투력</div><div class='card-value'>{row['전투력_v']:,}</div></div>", unsafe_allow_html=True)
                with c4: st.markdown(f"<div class='search-card'><div class='card-label'>문파</div><div class='card-value'>{row['문파']}</div></div>", unsafe_allow_html=True)
                with c5: st.markdown(f"<div class='search-card'><div class='card-label'>성장률</div><div class='card-value'>{row['성장']}</div></div>", unsafe_allow_html=True)

    # 탭별 내용 (하단 표는 항상 전체 데이터를 기반으로 출력)
    with tabs[0]: # ⚔️ 보탐
        with header_right: display_top3_on_right(df.sort_values(by=["누계_v", "전투력_v"], ascending=[False, False]), "누계_v", "회")
        st.divider()
        vis = add_medal_logic(df.sort_values(by=["누계_v", "전투력_v"], ascending=[False, False]))
        for c in ["14시", "18시", "22시"]: vis[c] = vis[c].apply(lambda x: "✅" if str(x).lower() in ['o','ㅇ','v'] else "──")
        display_custom_table(vis, ['순위', '문파', '이름', '누계_v', '14시', '18시', '22시'], ['순위', '문파', '이름', '누계', '14시', '18시', '22시'])

    with tabs[1]: # 🛡️ 투력
        with header_right: display_top3_on_right(df.sort_values(by="전투력_v", ascending=False), "전투력_v")
        st.divider()
        vis = add_medal_logic(df.sort_values(by="전투력_v", ascending=False))
        vis['전투력'] = vis['전투력_v'].apply(lambda x: f"{x:,}")
        display_custom_table(vis, ['순위', '문파', '이름', '직업', '전투력', '성장'], ['순위', '문파', '이름', '직업', '전투력', '성장'])

    with tabs[2]: # 🔥 성장
        with header_right: display_top3_on_right(df.sort_values(by=["성장_v", "전투력_v"], ascending=[False, False]), "성장")
        st.divider()
        vis = add_medal_logic(df.sort_values(by=["성장_v", "전투력_v"], ascending=[False, False]))
        display_custom_table(vis, ['순위', '문파', '이름', '성장', '전투력'], ['순위', '문파', '이름', '성장', '전투력'])

    with tabs[3]: # 🏆 직업
        jobs = sorted(df['직업'].unique())
        sel_job = st.selectbox("직업 선택", jobs)
        job_df = df[df['직업'] == sel_job].sort_values(by="전투력_v", ascending=False)
        with header_right: 
            if not job_df.empty: display_top3_on_right(job_df, "전투력_v")
        st.divider()
        vis = add_medal_logic(job_df)
        vis['전투력'] = vis['전투력_v'].apply(lambda x: f"{x:,}")
        display_custom_table(vis, ['순위', '문파', '이름', '전투력', '성장'], ['순위', '문파', '이름', '전투력', '성장'])

    with tabs[4]: # 🛍️ 거래소 (기존 로직 유지)
        m1, m2 = st.columns([1, 2])
        with m1:
            with st.form("m_form"):
                ms, mi, mp = st.text_input("판매자"), st.text_input("아이템"), st.text_input("가격")
                if st.form_submit_button("등록"):
                    market_worksheet.append_row([ms, mi, mp, "판매중"]); st.cache_data.clear(); st.rerun()
        with m2:
            for idx, row in market_df.iterrows():
                st.markdown(f"<div style='background:#111; padding:10px; border-radius:5px; border-left:4px solid #76B900; margin-bottom:5px;'><b>{row['아이템이름']}</b> - {row['가격']} 다이아 (판매자: {row['판매자']})</div>", unsafe_allow_html=True)

    with tabs[5]: # 📊 분석
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("통합 전투력", f"{df['전투력_v'].sum():,}"); sc2.metric("평균 전투력", f"{int(df['전투력_v'].mean()):,}"); sc3.metric("평균 성장률", f"{df['성장_v'].mean():.2f}%")
        g1, g2 = st.columns(2)
        with g1: st.plotly_chart(px.pie(df, names='문파', values='전투력_v', hole=0.6, title="문파별 전투력 비중"), use_container_width=True)
        with g2: st.plotly_chart(px.bar(df['직업'].value_counts().reset_index(), x='직업', y='count', title="연합 직업 분포"), use_container_width=True)

    with tabs[6]: # 💰 정산
        m_df = df[df['전투력_v'] > 1].sort_values(by=["분배금_v", "전투력_v"], ascending=[False, False])
        with header_right: display_top3_on_right(m_df, "분배금_v", "💎")
        st.divider()
        vis = add_medal_logic(m_df)
        vis['분배금_표시'] = vis['분배금_v'].apply(lambda x: f"{x:,}")
        vis['상태'] = vis['정산상태'].apply(lambda x: "✅ 완료" if x == "정산완료" else "⏳ 대기")
        display_custom_table(vis, ['순위', '문파', '이름', '분배금_표시', '상태'], ['순위', '문파', '이름', '분배금', '상태'])

else: st.error("데이터 로드 실패")
