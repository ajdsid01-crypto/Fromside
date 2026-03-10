import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import random
import string
from datetime import datetime
import streamlit.components.v1 as components

# 1. 🎨 [디자인] NVIDIA 프리미엄 다크 테마 설정
st.set_page_config(page_title="조협클래식 오늘만산다,살자", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505 !important; color: #FFFFFF !important; }
    h1, h2, h3, [data-testid="stMetricValue"] { color: #76B900 !important; font-weight: bold !important; }
    
    .medal-box {
        background: rgba(118, 185, 0, 0.08);
        border: 1px solid rgba(118, 185, 0, 0.3);
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        margin-bottom: 20px;
    }
    .search-card {
        background: #111;
        border-left: 5px solid #76B900;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# 🏆 공통 함수
def add_medal_logic(df):
    df = df.reset_index(drop=True)
    df.insert(0, 'Rank', range(1, len(df) + 1))
    df['순위'] = df['Rank'].apply(lambda x: "🥇 1위" if x==1 else "🥈 2위" if x==2 else "🥉 3위" if x==3 else f"{x}위")
    return df.drop(columns=['Rank'])

def display_top3_fixed(df, val_col, unit=""):
    top3 = df.head(3).reset_index()
    m2, m1, m3 = st.columns([1, 1.2, 1])
    for i, col in enumerate([m1, m2, m3]):
        if len(top3) > i:
            with col:
                row = top3.iloc[i]
                val = f"{row[val_col]:,}" if isinstance(row[val_col], (int, float)) else row[val_col]
                icon = "🥇" if i==0 else "🥈" if i==1 else "🥉"
                st.markdown(f"<div class='medal-box'><div style='font-size:30px;'>{icon}</div><div style='font-weight:bold;'>{row['이름']}</div><div style='color:#76B900;'>{val}{unit}</div></div>", unsafe_allow_html=True)

# 📂 데이터 로드
@st.cache_data(ttl=2)
def load_all_guild_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open("조협오산오살")
        sheet = spreadsheet.sheet1
        all_data = sheet.get_all_values()
        header, rows = all_data[6], all_data[7:]
        df = pd.DataFrame(rows, columns=header)
        df = df[df['이름'].str.strip() != ""].copy()

        for col in ['전투력', '누계', '분배금']:
            df[col+'_v'] = df[col].apply(lambda x: int(re.sub(r'[^0-9]', '', str(x))) if re.sub(r'[^0-9]', '', str(x)) else 0)

        def parse_growth(val):
            pct_match = re.search(r'([\d\.]+)%', str(val))
            val_match = re.search(r'\(?([\d,]+)\)?', str(val))
            pct = float(pct_match.group(1)) if pct_match else 0.0
            num = int(re.sub(r'[^0-9]', '', val_match.group(1))) if val_match else 0
            return pct, num

        df[['성장_pct', '성장_val']] = df['성장'].apply(lambda x: pd.Series(parse_growth(x)))
        
        m_ws = spreadsheet.worksheet("거래소")
        m_df = pd.DataFrame(m_ws.get_all_values()[1:], columns=["판매자", "아이템이름", "가격", "상태"])
        return spreadsheet, sheet, df, header, m_ws, m_df
    except Exception as e:
        return None, None, None, None, None, None

spreadsheet, worksheet, df, sheet_header, market_ws, market_df = load_all_guild_data()

# 📊 UI 시작
if df is not None:
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    
    with st.sidebar:
        st.markdown("<div style='text-align:center;'><img src='https://img.icons8.com/neon/150/shield.png' width='70'></div>", unsafe_allow_html=True)
        timer_code = """<div style="background:#111; border:1px solid #76B90066; padding:10px; border-radius:10px; text-align:center; color:#76B900; font-family:monospace;"><div id="t" style="font-size:28px; font-weight:bold;">00:00:00</div></div><script>function u(){const n=new Date(new Date().toLocaleString("en-US",{timeZone:"Asia/Seoul"}));const b=[14,18,22]; let t=null;for(let h of b){let x=new Date(n); x.setHours(h,0,0,0); if(n<x){t=x;break;}}if(!t){t=new Date(n); t.setDate(n.getDate()+1); t.setHours(14,0,0,0);}const d=t-n;const h=String(Math.floor(d/3600000)).padStart(2,'0'), m=String(Math.floor((d%3600000)/60000)).padStart(2,'0'), s=String(Math.floor((d%60000)/1000)).padStart(2,'0');document.getElementById('t').innerText=h+":"+m+":"+s;}setInterval(u,1000); u();</script>"""
        components.html(timer_code, height=100)
        if st.button("🔄 최신 데이터 불러오기", use_container_width=True): st.cache_data.clear(); st.rerun()
        st.divider()
        st.subheader("📺 실시간 방송")
        for n, u in [("가미가미 TV", "https://www.youtube.com/@gamigami706"), ("왕코 방송국", "https://www.youtube.com/@스트리머왕코"), ("아이엠솔이", "https://www.youtube.com/@아이엠솔이")]:
            st.link_button(n, u, use_container_width=True)
        st.divider()
        with st.expander("🔐 ADMIN 인증", expanded=st.session_state.authenticated):
            admin_pw = st.text_input("PASSWORD", type="password")
            if admin_pw == "rkdhkdthfdl12": st.session_state.authenticated = True
            if st.session_state.authenticated and st.button("로그아웃"): st.session_state.authenticated = False; st.rerun()

    # --- 🔍 캐릭터 검색창 (복구) ---
    st.title("🛡️ COMMAND CENTER")
    search_query = st.text_input("🔍 캐릭터 검색", placeholder="닉네임을 입력하세요.")
    if search_query:
        search_res = df[df['이름'].str.contains(search_query, case=False, na=False)]
        if not search_res.empty:
            for _, row in search_res.iterrows():
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.markdown(f"<div class='search-card'>이름: <b>{row['이름']}</b></div>", unsafe_allow_html=True)
                with c2: st.markdown(f"<div class='search-card'>투력: <b>{row['전투력_v']:,}</b></div>", unsafe_allow_html=True)
                with c3: st.markdown(f"<div class='search-card'>직업: <b>{row['직업']}</b></div>", unsafe_allow_html=True)
                with c4: st.markdown(f"<div class='search-card'>성장: <b>{row['성장_pct']}% ({row['성장_val']:,})</b></div>", unsafe_allow_html=True)

    tabs = st.tabs(["⚔️ 보탐 현황", "🛡️ 투력 현황", "✨ 투력 갱신", "🔥 성장 랭킹", "🏆 직업별 랭킹", "🛍️ 거래소", "💰 정산 현황"])

    # 1. 보탐 탭
    with tabs[0]:
        boss_sorted = df.sort_values(by=["누계_v", "전투력_v"], ascending=[False, False])
        display_top3_fixed(boss_sorted, "누계_v", "회")
        vis_boss = add_medal_logic(boss_sorted)
        for c in ["14시", "18시", "22시"]: vis_boss[c] = vis_boss[c].apply(lambda x: "✅" if str(x).lower() in ['o','ㅇ','v'] else "──")
        st.table(vis_boss[['순위', '문파', '이름', '누계', '14시', '18시', '22시']])

    # 2. 투력 현황
    with tabs[1]:
        cp_sorted = df.sort_values(by="전투력_v", ascending=False)
        display_top3_fixed(cp_sorted, "전투력_v")
        st.table(add_medal_logic(cp_sorted)[['순위', '문파', '이름', '직업', '전투력', '성장']])

    # 3. ✨ 투력 갱신
    with tabs[2]:
        st.subheader("✨ 본인 전투력 직접 갱신")
        c1, c2 = st.columns(2)
        with c1:
            sel_u = st.selectbox("본인 닉네임 선택", ["선택하세요"] + sorted(df['이름'].tolist()))
            new_cp = st.number_input("현재 전투력 입력", min_value=0, step=100)
        with c2:
            my_pw = st.text_input("개인 비밀번호", type="password")
            if st.button("🚀 업데이트 실행", use_container_width=True):
                if sel_u != "선택하세요" and my_pw:
                    u_data = df[df['이름'] == sel_u].iloc[0]
                    if str(my_pw).strip() == str(u_data['비밀번호']).strip():
                        cell = worksheet.find(sel_u)
                        cp_idx, dt_idx = sheet_header.index('전투력')+1, sheet_header.index('갱신일')+1
                        now = datetime.now().strftime("%m/%d %H:%M")
                        worksheet.update_cell(cell.row, cp_idx, str(new_cp))
                        worksheet.update_cell(cell.row, dt_idx, now)
                        st.success("✅ 업데이트 성공!"); st.cache_data.clear(); st.rerun()
                    else: st.error("❌ 비밀번호 불일치")

    # 4. 🔥 성장 랭킹 (요청 사항 준수)
    with tabs[3]:
        growth_sorted = df.sort_values(by=["성장_pct", "전투력_v"], ascending=[False, False])
        display_top3_fixed(growth_sorted, "성장_pct", "%")
        st.divider()
        vis_growth = add_medal_logic(growth_sorted)
        vis_growth['성장률(수치)'] = vis_growth.apply(lambda r: f"{r['성장_pct']}% ({r['성장_val']:,})", axis=1)
        st.table(vis_growth[['순위', '문파', '이름', '성장률(수치)', '전투력']])

    # 5. 🏆 직업별 랭킹 (복구 완료!)
    with tabs[4]:
        job_list = sorted(df['직업'].unique())
        selected_job = st.selectbox("직업을 선택하세요", job_list)
        job_df = df[df['직업'] == selected_job].sort_values(by="전투력_v", ascending=False)
        st.subheader(f"🥇 {selected_job} 클래스 순위")
        if not job_df.empty:
            display_top3_fixed(job_df, "전투력_v")
            st.divider()
            vis_job = add_medal_logic(job_df)
            st.table(vis_job[['순위', '문파', '이름', '전투력', '성장']])
        else:
            st.write("해당 직업의 인원이 없습니다.")

    # 6. 🛍️ 거래소
    with tabs[5]:
        c1, c2 = st.columns([1, 2])
        with c1:
            with st.form("market"):
                ms, mi, mp = st.text_input("판매자"), st.text_input("아이템"), st.text_input("가격")
                if st.form_submit_button("등록"):
                    market_ws.append_row([ms, mi, mp, "판매중"]); st.rerun()
        with c2:
            for _, r in market_df.iterrows():
                st.markdown(f"<div style='background:#111; padding:10px; border-radius:5px; border-left:4px solid #76B900; margin-bottom:5px;'><b>{r['아이템이름']}</b> ({r['가격']}) - {r['판매자']}</div>", unsafe_allow_html=True)

    # 7. 💰 정산 현황
    with tabs[6]:
        m_df = df[df['전투력_v'] > 1].sort_values(by=["분배금_v", "전투력_v"], ascending=[False, False])
        display_top3_fixed(m_df, "분배금_v", " 💎")
        m_vis = add_medal_logic(m_df)
        today = datetime.now().strftime("%m/%d")
        m_vis['최근갱신'] = m_vis['갱신일'].apply(lambda x: f"🟢 {x}" if str(x).startswith(today) else (x if x else "-"))
        st.table(m_vis[['순위', '문파', '이름', '분배금', '정산상태', '최근갱신']])
        
        if st.session_state.authenticated:
            st.divider()
            if st.button("🎲 전원 랜덤 비밀번호 부여"):
                if st.checkbox("동의 시 클릭"):
                    p_idx = sheet_header.index('비밀번호')+1
                    cells = worksheet.range(8, p_idx, 7+len(df), p_idx)
                    for c in cells: c.value = "".join(random.choices(string.digits, k=4))
                    worksheet.update_cells(cells); st.success("갱신 완료"); st.rerun()
            st.write("📋 **비밀번호 마스터 리스트**")
            st.dataframe(df[['이름', '비밀번호', '갱신일']], use_container_width=True, hide_index=True)

else: st.error("데이터 로드 실패")
