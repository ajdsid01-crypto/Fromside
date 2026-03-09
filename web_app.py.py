import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import plotly.express as px
import streamlit.components.v1 as components
from datetime import datetime

# 1. 🎨 [디자인] 스타일 설정
st.set_page_config(page_title="조협클래식 오늘만산다,살자", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #050505 !important; color: #FFFFFF !important; }
    h1, h2, h3, [data-testid="stMetricValue"] { color: #76B900 !important; font-weight: bold !important; }
    .medal-box { background: rgba(118, 185, 0, 0.08); border: 1px solid rgba(118, 185, 0, 0.3); border-radius: 12px; padding: 15px; text-align: center; margin-bottom: 20px; }
    .custom-table { width: 100%; border-collapse: collapse; color: white; background-color: #111; border-radius: 10px; overflow: hidden; margin-top: 10px; }
    .custom-table th { background-color: #1a1a1a; color: #76B900; text-align: left; padding: 12px 15px; border-bottom: 2px solid #222; }
    .custom-table td { padding: 10px 15px; border-bottom: 1px solid #222; text-align: left; font-size: 0.85rem; }
    </style>
    """, unsafe_allow_html=True)

# 🏆 공통 로직: 순위 부여
def add_medal_logic(df):
    df = df.reset_index(drop=True)
    df.insert(0, 'Rank', range(1, len(df) + 1))
    df['순위'] = df['Rank'].apply(lambda x: "🥇 1위" if x==1 else "🥈 2위" if x==2 else "🥉 3위" if x==3 else f"{x}위")
    return df.drop(columns=['Rank'])

# 🥇 탭별 상단 Top 3 카드 출력 함수
def display_top3_in_tab(df, val_col, unit=""):
    top3 = df.head(3).reset_index()
    m2, m1, m3 = st.columns([1, 1.2, 1])
    medals = [("🥇", m1, 40, "2px solid #76B900"), ("🥈", m2, 30, "1px solid #76B90033"), ("🥉", m3, 30, "1px solid #76B90033")]
    for i, (icon, col, size, border) in enumerate(medals):
        if len(top3) > i:
            with col:
                row = top3.iloc[i]
                val = f"{row[val_col]:,}" if isinstance(row[val_col], (int, float)) else row[val_col]
                st.markdown(f"<div class='medal-box' style='border:{border};'><div style='font-size:{size}px;'>{icon}</div><div style='font-weight:bold;'>{row['이름']}</div><div style='color:#76B900;'>{val}{unit}</div></div>", unsafe_allow_html=True)

# 📋 커스텀 테이블 출력 함수
def display_custom_table(dataframe, columns_to_show, column_names):
    df_display = dataframe[columns_to_show].copy()
    df_display.columns = column_names
    html = f'<table class="custom-table"><thead><tr>' + "".join([f'<th>{c}</th>' for c in column_names]) + '</tr></thead><tbody>'
    for _, row in df_display.iterrows():
        html += '<tr>' + "".join([f'<td>{val}</td>' for val in row]) + '</tr>'
    st.markdown(html + '</tbody></table>', unsafe_allow_html=True)

# 📂 데이터 로드
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
        df['성장_v'] = df['성장'].apply(lambda x: float(re.search(r'([\d\.]+)', str(x)).group(1)) if re.search(r'([\d\.]+)', str(x)) else 0.0)
        df['정산상태'] = df['정산상태'].apply(lambda x: "정산완료" if str(x).strip() == "정산완료" else "미정산")
        return spreadsheet, sheet, df, header, market_sheet, m_df
    except: return None, None, None, None, None, None

spreadsheet, worksheet, df, sheet_header, market_worksheet, market_df = load_all_guild_data()

# 📊 메인 화면 실행
if df is not None:
    with st.sidebar:
        st.markdown("<div style='text-align:center;'><img src='https://img.icons8.com/neon/150/shield.png' width='70'></div>", unsafe_allow_html=True)
        # 🕒 보스 타이머 로직
        timer_code = """
        <div style="background:#111; border:1px solid #76B90066; padding:10px; border-radius:10px; text-align:center; color:#76B900;">
            <div style="font-size:10px; color:#888;">NEXT BOSS</div>
            <div id="t" style="font-size:28px; font-weight:bold; font-family:monospace;">00:00:00</div>
        </div>
        <script>
        function u(){
            const n=new Date(new Date().toLocaleString("en-US",{timeZone:"Asia/Seoul"}));
            const b=[14,18,22]; let t=null;
            for(let h of b){let x=new Date(n); x.setHours(h,0,0,0); if(n<x){t=x;break;}}
            if(!t){t=new Date(n); t.setDate(n.getDate()+1); t.setHours(14,0,0,0);}
            const d=t-n;
            const h=String(Math.floor(d/3600000)).padStart(2,'0'), m=String(Math.floor((d%3600000)/60000)).padStart(2,'0'), s=String(Math.floor((d%60000)/1000)).padStart(2,'0');
            document.getElementById('t').innerText=h+":"+m+":"+s;
        }setInterval(u,1000); u();
        </script>
        """
        components.html(timer_code, height=100)
        if st.button("🔄 데이터 새로고침", use_container_width=True): st.cache_data.clear(); st.rerun()
        st.divider()
        st.subheader("📺 방송국")
        for n, u in [("가미가미 TV", "https://www.youtube.com/@gamigami706"), ("왕코 방송국", "https://www.youtube.com/@스트리머왕코"), ("아이엠솔이", "https://www.youtube.com/@아이엠솔이")]:
            st.link_button(n, u, use_container_width=True)

    st.title("🛡️ COMMAND CENTER")
    search_query = st.text_input("🔍 길드원 검색", placeholder="닉네임을 입력하면 해당 인원의 순위와 표가 필터링됩니다.")
    f_df = df[df['이름'].str.contains(search_query, case=False, na=False)] if search_query else df.copy()

    tabs = st.tabs(["⚔️ 보탐 현황", "🛡️ 투력 현황", "🔥 성장 랭킹", "🏆 직업별 랭킹", "🛍️ 거래소", "📊 분석 통계", "💰 정산 현황"])

    with tabs[0]: # ⚔️ 보탐 현황 (2중 정렬 적용)
        tab_sorted = f_df.sort_values(by=["누계_v", "전투력_v"], ascending=[False, False])
        display_top3_in_tab(tab_sorted, "누계_v", "회")
        st.divider()
        vis = add_medal_logic(tab_sorted)
        for c in ["14시", "18시", "22시"]: vis[c] = vis[c].apply(lambda x: "✅" if str(x).lower() in ['o','ㅇ','v'] else "──")
        display_custom_table(vis, ['순위', '문파', '이름', '누계_v', '14시', '18시', '22시'], ['순위', '문파', '이름', '누계', '14시', '18시', '22시'])

    with tabs[1]: # 🛡️ 투력 현황
        tab_sorted = f_df.sort_values(by="전투력_v", ascending=False)
        display_top3_in_tab(tab_sorted, "전투력_v")
        st.divider()
        vis = add_medal_logic(tab_sorted)
        vis['전투력'] = vis['전투력_v'].apply(lambda x: f"{x:,}")
        display_custom_table(vis, ['순위', '문파', '이름', '직업', '전투력', '성장'], ['순위', '문파', '이름', '직업', '전투력', '성장'])

    with tabs[2]: # 🔥 성장 랭킹
        tab_sorted = f_df.sort_values(by=["성장_v", "전투력_v"], ascending=[False, False])
        display_top3_in_tab(tab_sorted, "성장")
        st.divider()
        vis = add_medal_logic(tab_sorted)
        display_custom_table(vis, ['순위', '문파', '이름', '성장', '전투력'], ['순위', '문파', '이름', '성장', '전투력'])

    with tabs[3]: # 🏆 직업별 랭킹
        jobs = sorted(df['직업'].unique())
        sel_job = st.selectbox("직업 선택", jobs)
        job_df = f_df[f_df['직업'] == sel_job].sort_values(by="전투력_v", ascending=False)
        if not job_df.empty: display_top3_in_tab(job_df, "전투력_v")
        st.divider()
        vis = add_medal_logic(job_df)
        vis['전투력'] = vis['전투력_v'].apply(lambda x: f"{x:,}")
        display_custom_table(vis, ['순위', '문파', '이름', '전투력', '성장'], ['순위', '문파', '이름', '전투력', '성장'])

    with tabs[4]: # 🛍️ 문파 거래소
        st.subheader("🛍️ 문파 실시간 매물")
        m1, m2 = st.columns([1, 2])
        with m1:
            with st.form("market_form", clear_on_submit=True):
                ms, mi, mp = st.text_input("판매자"), st.text_input("아이템"), st.text_input("가격")
                if st.form_submit_button("등록") and ms and mi and mp:
                    market_worksheet.append_row([ms, mi, mp, "판매중"]); st.cache_data.clear(); st.rerun()
        with m2:
            for idx, row in market_df.iterrows():
                st.markdown(f"<div style='background:#111; padding:10px; border-radius:10px; border-left:4px solid #76B900; margin-bottom:5px;'><b>{row['아이템이름']}</b> - {row['가격']} 다이아 (판매자: {row['판매자']})</div>", unsafe_allow_html=True)

    with tabs[5]: # 📊 분석 통계
        st.subheader("📊 연합 실시간 분석")
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("통합 전투력", f"{df['전투력_v'].sum():,}"); sc2.metric("평균 전투력", f"{int(df['전투력_v'].mean()):,}"); sc3.metric("평균 성장률", f"{df['성장_v'].mean():.2f}%")
        g1, g2 = st.columns(2)
        with g1: st.plotly_chart(px.pie(df, names='문파', values='전투력_v', hole=0.6, title="문파별 전투력 비중"), use_container_width=True)
        with g2: st.plotly_chart(px.bar(df['직업'].value_counts().reset_index(), x='직업', y='count', title="연합 직업 분포"), use_container_width=True)

    with tabs[6]: # 💰 정산 현황
        money_df = f_df[f_df['전투력_v'] > 1].sort_values(by=["분배금_v", "전투력_v"], ascending=[False, False])
        display_top3_in_tab(money_df, "분배금_v", " 💎")
        st.divider()
        vis = add_medal_logic(money_df)
        vis['분배금_표시'] = vis['분배금_v'].apply(lambda x: f"{x:,}")
        vis['상태'] = vis['정산상태'].apply(lambda x: "✅ 완료" if x == "정산완료" else "⏳ 대기")
        display_custom_table(vis, ['순위', '문파', '이름', '분배금_표시', '상태'], ['순위', '문파', '이름', '분배금', '상태'])

else: st.error("데이터 로드 실패")
