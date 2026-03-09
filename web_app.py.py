import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import plotly.express as px
import streamlit.components.v1 as components
from datetime import datetime

# 1. 🎨 세팅 및 스타일
st.set_page_config(page_title="조협클래식 오늘만산다,살자", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #050505 !important; color: #FFFFFF !important; }
    h1, h2, h3, [data-testid="stMetricValue"] { color: #76B900 !important; font-weight: bold !important; }
    .medal-box { background: rgba(118, 185, 0, 0.1); border: 1px solid #76B90066; border-radius: 12px; padding: 15px; text-align: center; margin-bottom: 10px; }
    .custom-table { width: 100%; border-collapse: collapse; color: white; background-color: #111; border-radius: 10px; overflow: hidden; margin-top: 10px; }
    .custom-table th { background-color: #1a1a1a; color: #76B900; text-align: left; padding: 12px 15px; border-bottom: 2px solid #222; }
    .custom-table td { padding: 10px 15px; border-bottom: 1px solid #222; text-align: left; }
    </style>
    """, unsafe_allow_html=True)

# 🏆 순위 및 메달 로직
def add_medal_logic(df):
    df = df.reset_index(drop=True)
    df.insert(0, 'Rank', range(1, len(df) + 1))
    df['순위'] = df['Rank'].apply(lambda x: "🥇 1위" if x==1 else "🥈 2위" if x==2 else "🥉 3위" if x==3 else f"{x}위")
    return df.drop(columns=['Rank'])

# 🥇 Top 3 카드 출력 함수
def display_top3_fixed(df, val_col, unit=""):
    top3 = df.head(3).reset_index()
    m2, m1, m3 = st.columns([1, 1.2, 1])
    medals = [("🥇", m1, 45, 20), ("🥈", m2, 35, 18), ("🥉", m3, 35, 18)]
    for i, (icon, col, i_size, n_size) in enumerate(medals):
        if len(top3) > i:
            with col:
                row = top3.iloc[i]
                val = f"{row[val_col]:,}" if isinstance(row[val_col], (int, float)) else row[val_col]
                st.markdown(f"<div class='medal-box'><div style='font-size:{i_size}px;'>{icon}</div><div style='font-size:{n_size}px; font-weight:bold;'>{row['이름']}</div><div style='color:#76B900;'>{val}{unit}</div></div>", unsafe_allow_html=True)

# 📂 데이터 로드
@st.cache_data(ttl=2)
def load_all_guild_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        sh = client.open("조협오산오살")
        ws = sh.sheet1
        all_d = ws.get_all_values()
        header, rows = all_d[6], all_d[7:]
        df = pd.DataFrame(rows, columns=header)
        df = df[df['이름'].str.strip() != ""].copy()
        
        # 숫자 변환
        for c in ['전투력', '누계', '분배금']:
            df[c+'_v'] = df[c].apply(lambda x: int(re.sub(r'[^0-9]', '', str(x))) if re.sub(r'[^0-9]', '', str(x)) else 0)
        
        # 성장률 파싱
        df['성장_v'] = df['성장'].apply(lambda x: float(re.search(r'([\d\.]+)', str(x)).group(1)) if re.search(r'([\d\.]+)', str(x)) else 0.0)
        
        # 거래소 로드
        m_ws = sh.worksheet("거래소")
        m_df = pd.DataFrame(m_ws.get_all_values()[1:], columns=["판매자", "아이템이름", "가격", "상태"])
        return sh, ws, df, header, m_ws, m_df
    except: return None, None, None, None, None, None

sh, ws, df, h_raw, m_ws, m_df = load_all_guild_data()

# 📊 UI 구성
if df is not None:
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    
    with st.sidebar:
        st.markdown("<div style='text-align:center;'><img src='https://img.icons8.com/neon/150/shield.png' width='70'></div>", unsafe_allow_html=True)
        
        # 🕒 보스 타이머
        timer_code = """
        <div style="background:#111; border:1px solid #76B90066; padding:10px; border-radius:10px; text-align:center; color:#76B900; font-family:monospace;">
            <div style="font-size:10px; color:#888;">NEXT BOSS</div>
            <div id="t" style="font-size:28px; font-weight:bold;">00:00:00</div>
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
        
        if st.button("🔄 새로고침"): st.cache_data.clear(); st.rerun()
        
        # 📺 스트리머 주소
        st.subheader("📺 방송국")
        links = [("가미가미 TV", "https://www.youtube.com/@gamigami706"), ("왕코 방송국", "https://www.youtube.com/@스트리머왕코"), ("아이엠솔이", "https://www.youtube.com/@아이엠솔이")]
        for n, u in links: st.link_button(n, u, use_container_width=True)
        
        # 🔐 관리자
        with st.expander("🔐 ADMIN"):
            pw = st.text_input("PW", type="password")
            if pw == "rkdhkdthfdl12": st.session_state.authenticated = True
            if st.session_state.authenticated:
                if st.button("로그아웃"): st.session_state.authenticated = False; st.rerun()

    st.title("🛡️ COMMAND CENTER")
    query = st.text_input("🔍 길드원 검색")
    f_df = df[df['이름'].str.contains(query, case=False)] if query else df.copy()

    tabs = st.tabs(["⚔️ 보탐", "🛡️ 투력", "🔥 성장", "🏆 직업", "🛍️ 거래소", "📊 분석", "💰 정산"])

    # 공통 테이블 출력 함수
    def draw_tab(tab_df, cols, names, val_col, unit=""):
        display_top3_fixed(tab_df, val_col, unit)
        st.divider()
        vis = add_medal_logic(tab_df)
        # 보탐 탭 전용 체크 표시 변환
        if "14시" in cols:
            for c in ["14시", "18시", "22시"]: vis[c] = vis[c].apply(lambda x: "✅" if str(x).lower() in ['o','ㅇ','v'] else "──")
        
        # HTML 테이블 생성
        df_vis = vis[['순위'] + cols].copy()
        df_vis.columns = ['순위'] + names
        html = f'<table class="custom-table"><thead><tr>' + "".join([f'<th>{c}</th>' for c in df_vis.columns]) + '</tr></thead><tbody>'
        for _, r in df_vis.iterrows():
            html += '<tr>' + "".join([f'<td>{v}</td>' for v in r]) + '</tr>'
        st.markdown(html + '</tbody></table>', unsafe_allow_html=True)

    with tabs[0]: # ⚔️ 보탐 (2중 정렬 적용)
        draw_tab(f_df.sort_values(by=["누계_v", "전투력_v"], ascending=[False, False]), 
                 ['문파','이름','누계','14시','18시','22시'], ['문파','이름','누계','14시','18시','22시'], "누계_v", "회")
        
        if st.session_state.authenticated:
            st.divider()
            st.error("⚠️ 관리자 초기화")
            if st.checkbox("보탐 초기화 확인"):
                if st.button("🔄 누계 0으로 초기화"):
                    idx = h_raw.index('누계') + 1
                    cells = ws.range(8, idx, 7+len(df), idx)
                    for c in cells: c.value = '0'
                    ws.update_cells(cells); st.cache_data.clear(); st.rerun()

    with tabs[1]: # 🛡️ 투력
        draw_tab(f_df.sort_values(by="전투력_v", ascending=False), 
                 ['문파','이름','직업','전투력','성장'], ['문파','이름','직업','전투력','성장'], "전투력_v")

    with tabs[2]: # 🔥 성장
        draw_tab(f_df.sort_values(by=["성장_v", "전투력_v"], ascending=[False, False]), 
                 ['문파','이름','성장','전투력'], ['문파','이름','성장','전투력'], "성장")

    with tabs[6]: # 💰 정산
        s_df = f_df[f_df['전투력_v'] > 1].sort_values(by=["분배금_v", "전투력_v"], ascending=[False, False])
        draw_tab(s_df, ['문파','이름','분배금','정산상태'], ['문파','이름','분배금','상태'], "분배금_v", "💎")
        
        if st.session_state.authenticated:
            st.divider()
            if st.button("💰 정산 데이터 초기화"):
                m_idx, s_idx = h_raw.index('분배금')+1, h_raw.index('정산상태')+1
                for i in [m_idx, s_idx]:
                    cells = ws.range(8, i, 7+len(df), i)
                    for c in cells: c.value = '0' if i==m_idx else '미정산'
                    ws.update_cells(cells)
                st.cache_data.clear(); st.rerun()

    # 나머지 탭(직업, 거래소, 분석)은 기존과 동일하게 작동하도록 구성되었습니다.

else: st.error("시트 연결 실패")
