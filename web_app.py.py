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
st.set_page_config(page_title="조협클래식 오늘만산다,살자", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505 !important; color: #FFFFFF !important; }
    h1, h2, h3, [data-testid="stMetricValue"] { color: #76B900 !important; font-weight: bold !important; }
    
    /* 🏆 메달 및 검색 카드 디자인 */
    .medal-box, .search-card {
        background: rgba(118, 185, 0, 0.08);
        border: 1px solid rgba(118, 185, 0, 0.3);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin-bottom: 20px;
    }
    .search-card {
        text-align: left;
        border-left: 5px solid #76B900;
        background: #111;
    }

    /* 📏 표 디자인 및 칸 크기 고정 */
    .custom-table {
        width: 100%; border-collapse: collapse; color: white; background-color: #111;
        border-radius: 10px; overflow: hidden; margin-top: 10px; table-layout: fixed;
    }
    .custom-table th {
        background-color: #1a1a1a; color: #76B900; text-align: center;
        padding: 12px 15px; border-bottom: 2px solid #222; font-size: 0.9rem;
    }
    .custom-table td { 
        padding: 10px 15px; border-bottom: 1px solid #222; text-align: center; 
        font-size: 0.85rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    </style>
    """, unsafe_allow_html=True)

# 🏆 공통 로직 함수
def add_medal_logic(df):
    if df.empty: return df
    df = df.reset_index(drop=True)
    df.insert(0, 'Rank', range(1, len(df) + 1))
    df['순위'] = df['Rank'].apply(lambda x: "🥇 1위" if x==1 else "🥈 2위" if x==2 else "🥉 3위" if x==3 else f"{x}위")
    return df.drop(columns=['Rank'])

def display_top3_fixed(df, val_col, unit=""):
    if df.empty: return
    top3 = df.head(3).reset_index()
    m2, m1, m3 = st.columns([1, 1.2, 1])
    for i, col in enumerate([m1, m2, m3]):
        if len(top3) > i:
            with col:
                row = top3.iloc[i]
                val = f"{row[val_col]:,}" if isinstance(row[val_col], (int, float)) else row[val_col]
                icon = "🥇" if i==0 else "🥈" if i==1 else "🥉"
                st.markdown(f"<div class='medal-box'><div style='font-size:30px;'>{icon}</div><div style='font-weight:bold;'>{row['이름']}</div><div style='color:#76B900;'>{val}{unit}</div></div>", unsafe_allow_html=True)

def display_custom_table(dataframe, columns_to_show, column_names):
    if dataframe.empty: 
        st.write("표시할 데이터가 없습니다.")
        return
    df_display = dataframe[columns_to_show].copy()
    df_display.columns = column_names
    html = f'<table class="custom-table"><thead><tr>' + "".join([f'<th>{c}</th>' for c in column_names]) + '</tr></thead><tbody>'
    for _, row in df_display.iterrows():
        html += '<tr>' + "".join([f'<td>{val}</td>' for val in row]) + '</tr>'
    st.markdown(html + '</tbody></table>', unsafe_allow_html=True)

# 📂 데이터 로드 및 전처리
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
        
        # 숫자 및 성장 데이터 전처리 (오류 방지 로직 강화)
        def to_int(val):
            clean = re.sub(r'[^0-9]', '', str(val))
            return int(clean) if clean else 0

        def parse_growth(val):
            percent = re.search(r'([\d\.]+)(?=%)', str(val))
            value = re.search(r'\(?([\d,]+)\)?', str(val))
            p_val = float(percent.group(1)) if percent else 0.0
            v_val = value.group(1) if value else "0"
            return p_val, f"{p_val}% ({v_val})"

        df['전투력_v'] = df['전투력'].apply(to_int)
        df['누계_v'] = df['누계'].apply(to_int)
        df['분배금_v'] = df['분배금'].apply(to_int)
        df['성장_v'], df['성장_표시'] = zip(*df['성장'].apply(parse_growth))
        
        df['정산상태'] = df['정산상태'].apply(lambda x: "정산완료" if str(x).strip() == "정산완료" else "미정산")
        
        market_sheet = spreadsheet.worksheet("거래소")
        m_values = market_sheet.get_all_values()
        market_df = pd.DataFrame(m_values[1:], columns=["판매자", "아이템이름", "가격", "상태"]) if len(m_values) > 1 else pd.DataFrame(columns=["판매자", "아이템이름", "가격", "상태"])

        return spreadsheet, sheet, df, header, market_sheet, market_df
    except Exception as e:
        return None, None, str(e), None, None, None

spreadsheet, worksheet, df, sheet_header, market_worksheet, market_df = load_all_guild_data()

# 📊 화면 구성
if isinstance(df, pd.DataFrame):
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    
    with st.sidebar:
        st.markdown("<div style='text-align:center; padding-bottom:10px;'><img src='https://img.icons8.com/neon/150/shield.png' width='75'></div>", unsafe_allow_html=True)
        # 보스 타이머
        timer_html = """<div style="background:linear-gradient(135deg,#151515,#0a0a0a); border:1px solid #76B90066; padding:15px; border-radius:10px; text-align:center;"><div style="font-size:11px; color:#888; font-weight:bold; margin-bottom:5px;">NEXT BOSS RADAR</div><div id="sidebar-timer" style="font-size:32px; font-weight:900; color:#76B900; font-family:monospace;">00:00:00</div></div><script>function up(){const n=new Date(new Date().toLocaleString("en-US",{timeZone:"Asia/Seoul"}));const b=[14,18,22];let t=null;for(let h of b){let x=new Date(n);x.setHours(h,0,0,0);if(n<x){t=x;break;}}if(!t){t=new Date(n);t.setDate(n.getDate()+1);t.setHours(14,0,0,0);}const d=t-n;const h=String(Math.floor(d/3600000)).padStart(2,'0'), m=String(Math.floor((d%3600000)/60000)).padStart(2,'0'), s=String(Math.floor((d%60000)/1000)).padStart(2,'0');document.getElementById('sidebar-timer').innerText=h+":"+m+":"+s;}setInterval(up,1000);up();</script>"""
        components.html(timer_html, height=120)
        if st.button("🔄 최신 데이터 불러오기", use_container_width=True): st.cache_data.clear(); st.rerun()
        st.divider()
        st.subheader("📺 실시간 방송")
        for name, url in [("가미가미", "https://www.youtube.com/@gamigami706"), ("스트리머왕코", "https://www.youtube.com/@스트리머왕코"), ("아이엠솔이", "https://www.youtube.com/@아이엠솔이")]:
            st.link_button(name, url, use_container_width=True)
        st.divider()
        with st.expander("🔐 ADMIN", expanded=st.session_state.authenticated):
            admin_pw = st.text_input("PASSWORD", type="password", key="admin_pw_main")
            if admin_pw == "rkdhkdthfdl12": st.session_state.authenticated = True
            if st.session_state.authenticated and st.button("로그아웃"): st.session_state.authenticated = False; st.rerun()

    st.title("🛡️ COMMAND CENTER")
    
    # 🔍 검색 섹션 (복구 완료)
    search_query = st.text_input("🔍 길드원 상세 검색", placeholder="닉네임을 입력하세요.")
    if search_query:
        search_result = df[df['이름'].str.contains(search_query, case=False, na=False)]
        if not search_result.empty:
            st.markdown("##### 👤 검색된 인원 프로필")
            for _, row in search_result.iterrows():
                c1, c2, c3, c4, c5 = st.columns(5)
                with c1: st.markdown(f"<div class='search-card'><b>{row['이름']}</b></div>", unsafe_allow_html=True)
                with c2: st.markdown(f"<div class='search-card'>{row['직업']}</div>", unsafe_allow_html=True)
                with c3: st.markdown(f"<div class='search-card'>{row['전투력_v']:,}</div>", unsafe_allow_html=True)
                with c4: st.markdown(f"<div class='search-card'>{row['문파']}</div>", unsafe_allow_html=True)
                with c5: st.markdown(f"<div class='search-card'>{row['성장_표시']}</div>", unsafe_allow_html=True)

    tabs = st.tabs(["⚔️ 보탐 현황", "🛡️ 투력 현황", "🔥 성장 랭킹", "🏆 직업별 랭킹", "🛍️ 문파 거래소", "📊 분석 통계", "💰 정산 현황", "✨ 투력 갱신"])

    # 1. 보탐 탭
    with tabs[0]:
        st.subheader("🏆 보탐 참여 MVP (Top 3)")
        boss_sorted = df.sort_values(by=["누계_v", "전투력_v"], ascending=[False, False])
        display_top3_fixed(boss_sorted, "누계_v", "회")
        st.divider()
        boss_vis = add_medal_logic(boss_sorted)
        display_custom_table(boss_vis, ['순위', '문파', '이름', '누계_v', '14시', '18시', '22시'], ['순위', '문파', '이름', '누계', '14시', '18시', '22시'])

    # 2. 투력 현황
    with tabs[1]:
        st.subheader("👑 전투력 순위 (Top 3)")
        cp_sorted = df.sort_values(by="전투력_v", ascending=False)
        display_top3_fixed(cp_sorted, "전투력_v")
        st.divider()
        cp_rank = add_medal_logic(cp_sorted)
        cp_rank['전투력_표시'] = cp_rank['전투력_v'].apply(lambda x: f"{x:,}")
        display_custom_table(cp_rank, ['순위', '문파', '이름', '직업', '전투력_표시', '성장_표시'], ['순위', '문파', '이름', '직업', '전투력', '성장'])

    # 3. 성장 랭킹 (내림차순 정렬 및 퍼센트 우선 표기)
    with tabs[2]:
        st.subheader("🔥 성장률 MVP (Top 3)")
        growth_sorted = df.sort_values(by=["성장_v", "전투력_v"], ascending=[False, False])
        display_top3_fixed(growth_sorted, "성장_v", "%")
        st.divider()
        growth_rank = add_medal_logic(growth_sorted)
        display_custom_table(growth_rank, ['순위', '문파', '이름', '성장_표시', '전투력'], ['순위', '문파', '이름', '성장률(수치)', '전투력'])

    # 4. 직업별 랭킹
    with tabs[3]:
        job_list = sorted(df['직업'].unique())
        selected_job = st.selectbox("직업 선택", job_list)
        job_df = df[df['직업'] == selected_job].sort_values(by="전투력_v", ascending=False)
        if not job_df.empty:
            display_top3_fixed(job_df, "전투력_v")
            st.divider()
            job_rank = add_medal_logic(job_df)
            job_rank['전투력_표시'] = job_rank['전투력_v'].apply(lambda x: f"{x:,}")
            display_custom_table(job_rank, ['순위', '문파', '이름', '전투력_표시', '성장_표시'], ['순위', '문파', '이름', '전투력', '성장'])

    # 5. 거래소
    with tabs[4]:
        st.subheader("🛍️ 문파 실시간 매물")
        c1, c2 = st.columns([1, 2])
        with c1:
            with st.form("market_form", clear_on_submit=True):
                ms, mi, mp = st.text_input("판매자"), st.text_input("아이템"), st.text_input("가격")
                if st.form_submit_button("등록") and ms and mi and mp:
                    market_worksheet.append_row([ms, mi, mp, "판매중"]); st.cache_data.clear(); st.rerun()
        with c2:
            for idx, row in market_df.iterrows():
                st.markdown(f"<div style='background:#111; padding:10px; border-radius:10px; border-left:4px solid #76B900; margin-bottom:5px;'><b>{row['아이템이름']}</b> - {row['가격']} / {row['판매자']}</div>", unsafe_allow_html=True)

    # 6. 분석 통계
    with tabs[5]:
        st.subheader("📊 연합 실시간 분석")
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("통합 전투력", f"{df['전투력_v'].sum():,}")
        sc2.metric("평균 전투력", f"{int(df['전투력_v'].mean()):,}")
        sc3.metric("평균 성장률", f"{df['성장_v'].mean():.2f}%")
        g1, g2 = st.columns(2)
        with g1: st.plotly_chart(px.pie(df, names='문파', values='전투력_v', hole=0.6, title="문파별 전투력 비중"), use_container_width=True)
        with g2: st.plotly_chart(px.bar(df['직업'].value_counts().reset_index(), x='직업', y='count', title="연합 직업 분포"), use_container_width=True)

    # 7. 정산 현황
    with tabs[6]:
        st.subheader("💰 최다 분배금 대상자 (Top 3)")
        money_df = df[df['전투력_v'] > 1].sort_values(by=["분배금_v", "전투력_v"], ascending=[False, False])
        display_top3_fixed(money_df, "분배금_v", " 다이아")
        st.divider()
        money_rank = add_medal_logic(money_df)
        money_rank['분배금_표시'] = money_rank['분배금_v'].apply(lambda x: f"{x:,}")
        money_rank['상태'] = money_rank['정산상태'].apply(lambda x: "✅ 완료" if x == "정산완료" else "⏳ 대기")
        today = datetime.now().strftime("%m/%d")
        money_rank['최근활동'] = df['갱신일'].apply(lambda x: f"🟢 {x}" if str(x).startswith(today) else (x if x else "-"))
        display_custom_table(money_rank, ['순위', '문파', '이름', '분배금_표시', '상태', '최근활동'], ['순위', '문파', '이름', '분배금', '상태', '최근 갱신일'])

    # 8. ✨ 투력 갱신 (비밀번호 보안)
    with tabs[7]:
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
        
        if st.session_state.authenticated:
            st.divider()
            if st.button("🎲 전원 랜덤 비밀번호 부여"):
                if st.checkbox("동의 시 클릭"):
                    p_idx = sheet_header.index('비밀번호')+1
                    cells = worksheet.range(8, p_idx, 7+len(df), p_idx)
                    for c in cells: c.value = "".join(random.choices(string.digits, k=4))
                    worksheet.update_cells(cells); st.success("비밀번호 랜덤 생성 완료"); st.cache_data.clear(); st.rerun()
            st.write("📋 마스터 비번 리스트")
            st.dataframe(df[['이름', '비밀번호', '갱신일']], use_container_width=True, hide_index=True)

else: st.error("데이터 로드 실패")
