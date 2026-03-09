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
    
    /* 🏆 메달 카드 디자인 (레이아웃 최적화) */
    .medal-box {
        background: rgba(118, 185, 0, 0.1);
        border: 1px solid rgba(118, 185, 0, 0.4);
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        margin-bottom: 10px;
        transition: transform 0.2s;
    }
    .medal-box:hover { transform: translateY(-5px); border-color: #76B900; }
    .medal-icon { font-size: 35px; margin-bottom: 5px; }
    .medal-name { font-size: 18px; font-weight: bold; color: white; margin-bottom: 3px; }
    .medal-val { font-size: 14px; color: #76B900; font-weight: bold; }

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

# 🥇 Top 3 시각화 함수 (가로 정렬 보정형)
def display_top3_fixed(df, val_col, unit=""):
    top3 = df.head(3).reset_index()
    # 2위, 1위, 3위 순서로 배치 (시각적 안정감)
    m2, m1, m3 = st.columns([1, 1.2, 1])
    
    # 1위 (가운데)
    if len(top3) > 0:
        with m1:
            row = top3.iloc[0]
            val = f"{row[val_col]:,}" if isinstance(row[val_col], (int, float)) else row[val_col]
            st.markdown(f"<div class='medal-box' style='border: 2px solid #76B900; background: rgba(118,185,0,0.2);'><div class='medal-icon' style='font-size:45px;'>🥇</div><div class='medal-name' style='font-size:20px;'>{row['이름']}</div><div class='medal-val' style='font-size:16px;'>{val}{unit}</div></div>", unsafe_allow_html=True)
    # 2위 (왼쪽)
    if len(top3) > 1:
        with m2:
            row = top3.iloc[1]
            val = f"{row[val_col]:,}" if isinstance(row[val_col], (int, float)) else row[val_col]
            st.markdown(f"<div class='medal-box'><div class='medal-icon'>🥈</div><div class='medal-name'>{row['이름']}</div><div class='medal-val'>{val}{unit}</div></div>", unsafe_allow_html=True)
    # 3위 (오른쪽)
    if len(top3) > 2:
        with m3:
            row = top3.iloc[2]
            val = f"{row[val_col]:,}" if isinstance(row[val_col], (int, float)) else row[val_col]
            st.markdown(f"<div class='medal-box'><div class='medal-icon'>🥉</div><div class='medal-name'>{row['이름']}</div><div class='medal-val'>{val}{unit}</div></div>", unsafe_allow_html=True)

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
        return spreadsheet, sheet, df, header, market_sheet, market_df
    except Exception as e:
        return None, None, str(e), None, None, None

spreadsheet, worksheet, df, sheet_header, market_worksheet, market_df = load_all_guild_data()

# 📊 3. 화면 구성
if isinstance(df, pd.DataFrame):
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    
    with st.sidebar:
        st.markdown("<div style='text-align:center;'><img src='https://img.icons8.com/neon/150/shield.png' width='75'></div>", unsafe_allow_html=True)
        if st.button("🔄 최신 데이터 불러오기", use_container_width=True):
            st.cache_data.clear(); st.rerun()
        st.divider()
        with st.expander("🔐 ADMIN", expanded=st.session_state.authenticated):
            admin_pw = st.text_input("PASSWORD", type="password")
            if admin_pw == "rkdhkdthfdl12": st.session_state.authenticated = True
            if st.session_state.authenticated:
                if st.button("로그아웃"): st.session_state.authenticated = False; st.rerun()

    st.title("🛡️ COMMAND CENTER")
    search_query = st.text_input("🔍 길드원 검색", placeholder="닉네임을 입력하세요.")
    filtered_df = df[df['이름'].str.contains(search_query, case=False, na=False)] if search_query else df.copy()

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
        st.subheader("🏆 보탐 참여 MVP (Top 3)")
        display_top3_fixed(filtered_df.sort_values(by="누계_v", ascending=False), "누계_v", "회")
        st.divider()
        boss_vis = add_medal_logic(filtered_df.sort_values(by="누계_v", ascending=False))
        display_custom_table(boss_vis, ['순위', '문파', '이름', '누계_v', '14시', '18시', '22시'], ['순위', '문파', '이름', '누계', '14시', '18시', '22시'])

    with tabs[1]: # 🛡️ 투력 현황
        st.subheader("👑 연합 전투력 서열 (Top 3)")
        display_top3_fixed(filtered_df.sort_values(by="전투력_v", ascending=False), "전투력_v")
        st.divider()
        cp_rank = add_medal_logic(filtered_df.sort_values(by="전투력_v", ascending=False))
        cp_rank['전투력'] = cp_rank['전투력_v'].apply(lambda x: f"{x:,}")
        display_custom_table(cp_rank, ['순위', '문파', '이름', '직업', '전투력', '성장'], ['순위', '문파', '이름', '직업', '전투력', '성장'])

    with tabs[2]: # 🔥 성장 랭킹
        st.subheader("🔥 성장률 MVP (Top 3)")
        display_top3_fixed(filtered_df.sort_values(by="성장_v", ascending=False), "성장")
        st.divider()
        growth_rank = add_medal_logic(filtered_df.sort_values(by="성장_v", ascending=False))
        display_custom_table(growth_rank, ['순위', '문파', '이름', '성장', '전투력'], ['순위', '문파', '이름', '성장', '전투력'])

    with tabs[3]: # 🏆 직업별 랭킹
        job_list = sorted(df['직업'].unique())
        selected_job = st.selectbox("직업 선택", job_list)
        job_df = filtered_df[filtered_df['직업'] == selected_job].sort_values(by="전투력_v", ascending=False)
        st.subheader(f"🥇 {selected_job} 클래스 Top 3")
        if not job_df.empty: display_top3_fixed(job_df, "전투력_v")
        st.divider()
        job_rank = add_medal_logic(job_df)
        job_rank['전투력'] = job_rank['전투력_v'].apply(lambda x: f"{x:,}")
        display_custom_table(job_rank, ['순위', '문파', '이름', '전투력', '성장'], ['순위', '문파', '이름', '전투력', '성장'])

    with tabs[4]: # 🛍️ 문파 거래소
        st.subheader("🛍️ 문파 실시간 매물")
        # (기존 거래소 코드 유지)
        m1, m2 = st.columns([1, 2])
        with m1:
            with st.form("market_form"):
                ms, mi, mp = st.text_input("판매자"), st.text_input("아이템"), st.text_input("가격")
                if st.form_submit_button("등록"):
                    market_worksheet.append_row([ms, mi, mp, "판매중"]); st.cache_data.clear(); st.rerun()
        with m2:
            for idx, row in market_df.iterrows():
                st.write(f"[{row['상태']}] {row['아이템이름']} - {row['가격']} (판매자: {row['판매자']})")

    with tabs[5]: # 📊 분석 통계
        st.subheader("📊 실시간 분석")
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("통합 전투력", f"{df['전투력_v'].sum():,}")
        sc2.metric("평균 전투력", f"{int(df['전투력_v'].mean()):,}")
        sc3.metric("평균 성장률", f"{df['성장_v'].mean():.2f}%")
        st.plotly_chart(px.pie(df, names='문파', values='전투력_v', hole=0.6, title="문파별 투력 비중"), use_container_width=True)

    with tabs[6]: # 💰 정산 현황
        st.subheader("💰 최다 분배금 대상자 (Top 3)")
        money_df = filtered_df[filtered_df['전투력_v'] > 1].sort_values(by="분배금_v", ascending=False)
        display_top3_fixed(money_df, "분배금_v", " 다이아")
        st.divider()
        money_rank = add_medal_logic(money_df)
        money_rank['분배금_표시'] = money_rank['분배금_v'].apply(lambda x: f"{x:,}")
        display_custom_table(money_rank, ['순위', '문파', '이름', '분배금_표시', '정산상태'], ['순위', '문파', '이름', '분배금', '상태'])

else: st.error("데이터 로드 실패")
