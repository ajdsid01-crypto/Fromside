import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import random
import string
from datetime import datetime
import streamlit.components.v1 as components

# 1. 🎨 [디자인] NVIDIA 프리미엄 다크 테마 및 스타일 설정
st.set_page_config(page_title="조협클래식 제네시스 마스터 v12.9", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505 !important; color: #FFFFFF !important; }
    h1, h2, h3, [data-testid="stMetricValue"] { color: #76B900 !important; font-weight: bold !important; }
    
    /* 🏆 메달 카드 디자인 */
    .medal-box {
        background: rgba(118, 185, 0, 0.08);
        border: 1px solid rgba(118, 185, 0, 0.3);
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        margin-bottom: 20px;
    }
    .medal-icon { font-size: 30px; margin-bottom: 5px; }
    .medal-name { font-size: 18px; font-weight: bold; color: white; }
    .medal-val { font-size: 14px; color: #76B900; font-weight: bold; }

    /* 📊 테이블 디자인 */
    .custom-table {
        width: 100%; border-collapse: collapse; color: white; background-color: #111;
        border-radius: 10px; overflow: hidden; margin-top: 10px;
    }
    .custom-table th {
        background-color: #1a1a1a; color: #76B900; text-align: left;
        padding: 12px 15px; border-bottom: 2px solid #222; font-size: 0.9rem;
    }
    .custom-table td { padding: 10px 15px; border-bottom: 1px solid #222; text-align: left; font-size: 0.85rem; }
    
    /* 🛍️ 거래소 카드 */
    .market-card {
        background: #111; border: 1px solid #222; border-left: 5px solid #76B900;
        padding: 15px; border-radius: 10px; margin-bottom: 8px;
        display: flex; justify-content: space-between; align-items: center;
    }
    </style>
    """, unsafe_allow_html=True)

# 🏆 공통 로직 함수
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
                st.markdown(f"<div class='medal-box'><div class='medal-icon'>{icon}</div><div class='medal-name'>{row['이름']}</div><div class='medal-val'>{val}{unit}</div></div>", unsafe_allow_html=True)

def display_custom_table(dataframe, columns_to_show, column_names):
    df_display = dataframe[columns_to_show].copy()
    df_display.columns = column_names
    html = f'<table class="custom-table"><thead><tr>' + "".join([f'<th>{c}</th>' for c in column_names]) + '</tr></thead><tbody>'
    for _, row in df_display.iterrows():
        html += '<tr>' + "".join([f'<td>{val}</td>' for val in row]) + '</tr>'
    st.markdown(html + '</tbody></table>', unsafe_allow_html=True)

# 📂 데이터 로드 및 전처리
@st.cache_data(ttl=2)
def load_all_data():
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
        
        for c in ['전투력', '누계', '분배금']:
            df[c+'_v'] = df[c].apply(lambda x: int(re.sub(r'[^0-9]', '', str(x))) if re.sub(r'[^0-9]', '', str(x)) else 0)
        df['성장_v'] = df['성장'].apply(lambda x: float(re.search(r'([\d\.]+)', str(x)).group(1)) if re.search(r'([\d\.]+)', str(x)) else 0.0)
        
        m_ws = sh.worksheet("거래소")
        m_df = pd.DataFrame(m_ws.get_all_values()[1:], columns=["판매자", "아이템이름", "가격", "상태"])
        return sh, ws, df, header, m_ws, m_df
    except Exception as e:
        return None, None, None, None, None, None

sh, ws, df, h_raw, m_ws, m_df = load_all_data()

# 📊 UI 구성
if df is not None:
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    
    with st.sidebar:
        st.markdown("<div style='text-align:center;'><img src='https://img.icons8.com/neon/150/shield.png' width='70'></div>", unsafe_allow_html=True)
        # 🕒 보스 타이머
        timer_code = """<div style="background:#111; border:1px solid #76B90066; padding:10px; border-radius:10px; text-align:center; color:#76B900; font-family:monospace;"><div id="t" style="font-size:28px; font-weight:bold;">00:00:00</div></div><script>function u(){const n=new Date(new Date().toLocaleString("en-US",{timeZone:"Asia/Seoul"}));const b=[14,18,22]; let t=null;for(let h of b){let x=new Date(n); x.setHours(h,0,0,0); if(n<x){t=x;break;}}if(!t){t=new Date(n); t.setDate(n.getDate()+1); t.setHours(14,0,0,0);}const d=t-n;const h=String(Math.floor(d/3600000)).padStart(2,'0'), m=String(Math.floor((d%3600000)/60000)).padStart(2,'0'), s=String(Math.floor((d%60000)/1000)).padStart(2,'0');document.getElementById('t').innerText=h+":"+m+":"+s;}setInterval(u,1000); u();</script>"""
        components.html(timer_code, height=100)
        if st.button("🔄 최신 데이터 새로고침", use_container_width=True): st.cache_data.clear(); st.rerun()
        st.divider()
        st.subheader("📺 방송국")
        for n, u in [("가미가미 TV", "https://www.youtube.com/@gamigami706"), ("왕코 방송국", "https://www.youtube.com/@스트리머왕코"), ("아이엠솔이", "https://www.youtube.com/@아이엠솔이")]:
            st.link_button(n, u, use_container_width=True)
        st.divider()
        with st.expander("🔐 ADMIN", expanded=st.session_state.authenticated):
            admin_pw = st.text_input("PASSWORD", type="password")
            if admin_pw == "rkdhkdthfdl12": st.session_state.authenticated = True
            if st.session_state.authenticated and st.button("로그아웃"): st.session_state.authenticated = False; st.rerun()

    st.title("🛡️ COMMAND CENTER")
    tabs = st.tabs(["⚔️ 보탐 현황", "🛡️ 투력 현황", "✨ 투력 갱신", "🔥 성장 랭킹", "🏆 직업별 랭킹", "🛍️ 거래소", "📊 분석", "💰 정산 현황"])

    # --- ⚔️ 보탐 탭 ---
    with tabs[0]:
        display_top3_fixed(df.sort_values(by=["누계_v", "전투력_v"], ascending=[False, False]), "누계_v", "회")
        st.divider()
        vis = add_medal_logic(df.sort_values(by=["누계_v", "전투력_v"], ascending=[False, False]))
        for c in ["14시", "18시", "22시"]: vis[c] = vis[c].apply(lambda x: "✅" if str(x).lower() in ['o','ㅇ','v'] else "──")
        display_custom_table(vis, ['순위', '문파', '이름', '누계_v', '14시', '18시', '22시'], ['순위', '문파', '이름', '누계', '14시', '18시', '22시'])

    # --- ✨ 투력 갱신 탭 (보안 강화) ---
    with tabs[2]:
        st.subheader("✨ 본인 전투력 직접 업데이트")
        c1, c2 = st.columns(2)
        with c1:
            target_u = st.selectbox("본인 닉네임 선택", ["선택하세요"] + sorted(df['이름'].tolist()))
            new_cp_val = st.number_input("새로운 전투력 입력", min_value=0, step=100)
        with c2:
            my_pw = st.text_input("개인 비밀번호 입력", type="password")
            if st.button("🚀 업데이트 실행", use_container_width=True):
                if target_u != "선택하세요" and my_pw:
                    user_data = df[df['이름'] == target_u].iloc[0]
                    if str(my_pw).strip() == str(user_data['비밀번호']).strip():
                        cell = ws.find(target_u)
                        cp_idx, date_idx = h_raw.index('전투력') + 1, h_raw.index('갱신일') + 1
                        now_str = datetime.now().strftime("%m/%d %H:%M")
                        ws.update_cell(cell.row, cp_idx, str(new_cp_val))
                        ws.update_cell(cell.row, date_idx, now_str)
                        st.success(f"✅ {target_u}님 업데이트 성공!"); st.cache_data.clear(); st.rerun()
                    else: st.error("❌ 비밀번호가 틀렸습니다.")

    # --- 💰 정산 현황 탭 (갱신일 추가 버전) ---
    with tabs[7]:
        st.subheader("💰 최다 분배금 대상자 (Top 3)")
        money_df = df[df['전투력_v'] > 1].sort_values(by=["분배금_v", "전투력_v"], ascending=[False, False])
        display_top3_fixed(money_df, "분배금_v", " 💎")
        st.divider()
        m_vis = add_medal_logic(money_df)
        m_vis['분배금_표시'] = m_vis['분배금_v'].apply(lambda x: f"{x:,}")
        m_vis['상태'] = m_vis['정산상태'].apply(lambda x: "✅ 완료" if str(x).strip() == "정산완료" else "⏳ 대기")
        
        # 🟢 오늘 갱신한 사람 강조 로직
        today_prefix = datetime.now().strftime("%m/%d")
        m_vis['최근활동'] = m_vis['갱신일'].apply(lambda x: f"🟢 {x}" if str(x).startswith(today_prefix) else (x if x else "-"))
        
        display_custom_table(m_vis, ['순위', '문파', '이름', '분배금_표시', '상태', '최근활동'], ['순위', '문파', '이름', '분배금', '정산상태', '최근 갱신일'])

    # --- 📊 분석 및 💰 관리 도구 (인증 시 노출) ---
    with tabs[6]:
        if st.session_state.authenticated:
            st.subheader("🔑 관리자 보안 도구")
            if st.button("🎲 전원 랜덤 비밀번호 부여"):
                if st.checkbox("정말 실행하시겠습니까?"):
                    pw_idx = h_raw.index('비밀번호') + 1
                    cells = ws.range(8, pw_idx, 7+len(df), pw_idx)
                    for c in cells: c.value = "".join(random.choices(string.digits, k=4))
                    ws.update_cells(cells); st.success("비밀번호 랜덤 생성 완료"); st.cache_data.clear(); st.rerun()
            st.dataframe(df[['이름', '비밀번호', '갱신일']], use_container_width=True, hide_index=True)
        else: st.info("관리자 인증이 필요합니다.")

    # (기타 투력현황, 성장, 직업, 거래소 탭은 기존 로직대로 작동합니다)
    with tabs[1]: # 투력 현황
        vis_cp = add_medal_logic(df.sort_values(by="전투력_v", ascending=False))
        vis_cp['전투력'] = vis_cp['전투력_v'].apply(lambda x: f"{x:,}")
        display_custom_table(vis_cp, ['순위', '문파', '이름', '직업', '전투력', '성장'], ['순위', '문파', '이름', '직업', '전투력', '성장'])
    with tabs[3]: # 성장
        vis_gr = add_medal_logic(df.sort_values(by=["성장_v", "전투력_v"], ascending=[False, False]))
        display_custom_table(vis_gr, ['순위', '문파', '이름', '성장', '전투력'], ['순위', '문파', '이름', '성장', '전투력'])
    with tabs[4]: # 직업
        jobs = sorted(df['직업'].unique()); sel_j = st.selectbox("직업 선택", jobs)
        j_df = df[df['직업'] == sel_j].sort_values(by="전투력_v", ascending=False)
        display_custom_table(add_medal_logic(j_df), ['순위', '문파', '이름', '전투력', '성장'], ['순위', '문파', '이름', '전투력', '성장'])
    with tabs[5]: # 거래소
        c1, c2 = st.columns([1, 2])
        with c1: 
            with st.form("m"):
                u, i, p = st.text_input("판매자"), st.text_input("아이템"), st.text_input("가격")
                if st.form_submit_button("등록"): m_ws.append_row([u,i,p,"판매중"]); st.rerun()
        with c2: 
            for _, r in m_df.iterrows(): st.markdown(f"<div class='market-card'><b>{r['아이템이름']}</b> ({r['가격']}) - {r['판매자']}</div>", unsafe_allow_html=True)

else: st.error("데이터 로드 실패")
