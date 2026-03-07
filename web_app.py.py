import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import plotly.express as px
import streamlit.components.v1 as components
from datetime import datetime

# 1. 🎨 [디자인] NVIDIA 프리미엄 다크 테마 및 카드 레이아웃
st.set_page_config(page_title="조협클래식 오늘만산다,살자", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505 !important; color: #FFFFFF !important; }
    h1, h2, h3, [data-testid="stMetricValue"] { color: #76B900 !important; font-weight: bold !important; }
    
    [data-testid="stSidebar"] > div:first-child { padding-top: 20px !important; }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.8rem !important; }
    .stDivider { margin: 0.8rem 0 !important; }
    
    .market-card {
        background: #111; border: 1px solid #222; border-left: 5px solid #76B900;
        padding: 18px; border-radius: 12px; margin-bottom: 5px;
        display: flex; justify-content: space-between; align-items: center;
    }
    .item-info { flex: 3; }
    .item-name { color: #FFF; font-size: 1.25rem; font-weight: bold; margin-bottom: 3px; }
    .item-price { color: #76B900; font-size: 1.15rem; font-weight: 800; margin-bottom: 6px; }
    .status-tag { 
        display: inline-block; padding: 4px 10px; border-radius: 6px; 
        font-size: 0.75rem; font-weight: bold; border: 1px solid #76B900; color: #76B900;
    }

    /* 🚨 표 스타일 - 모든 셀 좌측 정렬 강제 고정 */
    [data-testid="stDataFrame"] { background-color: #111111 !important; }
    div[data-testid="stDataFrame"] div[data-baseweb="table"] div {
        background-color: #111111 !important; color: white !important; 
        text-align: left !important; justify-content: flex-start !important;
        padding-left: 10px !important;
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

# 📂 2. 데이터 로드 및 전처리 (오류 방지 강화)
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
        
        # 🚨 [오류 수정] "이름" 헤더 위치를 자동으로 찾습니다.
        header_idx = 0
        for i, row in enumerate(all_data):
            if "이름" in row:
                header_idx = i
                break
        
        header = all_data[header_idx]
        rows = all_data[header_idx + 1:]
        df = pd.DataFrame(rows, columns=header)
        df = df[df['이름'].str.strip() != ""].copy()
        
        # 거래소 시트 로드
        market_sheet = spreadsheet.worksheet("거래소")
        m_values = market_sheet.get_all_values()
        market_df = pd.DataFrame(m_values[1:], columns=["판매자", "아이템이름", "가격", "상태"]) if len(m_values) > 1 else pd.DataFrame(columns=["판매자", "아이템이름", "가격", "상태"])

        def to_int(val):
            clean = re.sub(r'[^0-9]', '', str(val))
            return int(clean) if clean else 0
        def parse_growth(val):
            percent = re.search(r'([\d\.]+)(?=%)', str(val))
            value = re.search(r'\(([^)]+)\)', str(val))
            return (float(percent.group(1)) if percent else 0.0, value.group(1) if value else "0")

        # 컬럼 존재 확인 후 파싱
        if '전투력' in df.columns: df['전투력_v'] = df['전투력'].apply(to_int)
        if '누계' in df.columns: df['누계_v'] = df['누계'].apply(to_int)
        if '분배금' in df.columns: df['분배금_v'] = df['분배금'].apply(to_int)
        if '성장' in df.columns:
            growth_res = df['성장'].apply(parse_growth)
            df['성장_v'] = [x[0] for x in growth_res]
            df['성장_표시'] = [f"{x[0]}% ({x[1]})" for x in growth_res]
        
        df['정산상태'] = df['정산상태'].apply(lambda x: "정산완료" if str(x).strip() == "정산완료" else "미정산") if '정산상태' in df.columns else "미정산"
        df['14_p'], df['18_p'], df['22_p'] = df['14시'].apply(lambda x: str(x).strip().lower() in ['o', 'ㅇ', 'v']), df['18시'].apply(lambda x: str(x).strip().lower() in ['o', 'ㅇ', 'v']), df['22시'].apply(lambda x: str(x).strip().lower() in ['o', 'ㅇ', 'v'])
        
        return spreadsheet, sheet, df, header, market_sheet, market_df
    except Exception as e:
        return None, None, str(e), None, None, None

spreadsheet, worksheet, df, sheet_header, market_worksheet, market_df = load_all_guild_data()

# 📊 3. 화면 구성
if isinstance(df, pd.DataFrame):
    with st.sidebar:
        st.markdown("<div style='text-align:center; padding-bottom:10px;'><img src='https://img.icons8.com/neon/150/shield.png' width='75'></div>", unsafe_allow_html=True)
        if st.button("🔄 최신 데이터 불러오기", use_container_width=True):
            st.cache_data.clear(); st.rerun()

    st.title("🛡️ COMMAND CENTER")
    tabs = st.tabs(["⚔️ 보탐 현황", "🛡️ 투력 현황", "🔥 성장 랭킹", "🏆 직업별 랭킹", "🛍️ 문파 거래소", "📊 분석 통계", "💰 정산 현황"])

    # 🚨 공통 UI 설정: 항목명 변경 및 좌측 정렬
    UI_CONFIG = {
        "누계_v": st.column_config.NumberColumn("누계", alignment="left"),
        "전투력_표시": st.column_config.TextColumn("전투력", alignment="left"),
        "성장_표시": st.column_config.TextColumn("성장", alignment="left"),
        "분배금_표시": st.column_config.TextColumn("분배금", alignment="left")
    }

    with tabs[0]: # ⚔️ 보스 현황
        boss_vis = df.copy()
        for col in ['14시', '18시', '22시']: boss_vis[col] = boss_vis[col].apply(lambda x: "✅" if str(x).strip().lower() in ['o', 'ㅇ', 'v'] else "──")
        st.dataframe(add_medal_logic(boss_vis.sort_values(by="누계_v", ascending=False))[['순위', '문파', '이름', '14시', '18시', '22시', '누계_v']], use_container_width=True, hide_index=True, height=700, column_config=UI_CONFIG)

    with tabs[1]: # 🛡️ 투력 현황
        cp_rank = add_medal_logic(df.sort_values(by="전투력_v", ascending=False))
        cp_rank['전투력_표시'] = cp_rank['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(cp_rank[['순위', '문파', '이름', '직업', '전투력_표시', '성장_표시']], use_container_width=True, hide_index=True, height=700, column_config=UI_CONFIG)

    with tabs[2]: # 🔥 성장 랭킹
        st.dataframe(add_medal_logic(df.sort_values(by="성장_v", ascending=False))[['순위', '문파', '이름', '성장_표시', '전투력']], use_container_width=True, hide_index=True, height=700, column_config=UI_CONFIG)

    with tabs[3]: # 🏆 직업별 랭킹
        selected_job = st.selectbox("직업 선택", sorted(df['직업'].unique()))
        job_rank = add_medal_logic(df[df['직업'] == selected_job].sort_values(by="전투력_v", ascending=False))
        job_rank['전투력_표시'] = job_rank['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(job_rank[['순위', '문파', '이름', '전투력_표시', '성장_표시']], use_container_width=True, hide_index=True, height=700, column_config=UI_CONFIG)

    with tabs[4]: # 🛍️ 문파 거래소
        m1, m2 = st.columns([1, 2])
        with m1:
            with st.form("market_form", clear_on_submit=True):
                ms, mi, mp = st.text_input("판매자"), st.text_input("아이템"), st.text_input("가격")
                if st.form_submit_button("등록"):
                    if market_worksheet: market_worksheet.append_row([ms, mi, mp, "판매중"]); st.cache_data.clear(); st.rerun()
        with m2:
            if not market_df.empty:
                for idx, row in market_df.iterrows():
                    is_sold = "판매완료" in row['상태']
                    st.markdown(f'<div class="market-card {"sold-out-card" if is_sold else ""}"><div class="item-info"><div class="item-name">{row["아이템이름"]}</div><div class="item-price">{row["가격"]}</div><div class="item-seller">판매자 : {row["판매자"]}</div></div><div class="status-area"><div class="status-tag">{"판매완료" if is_sold else "판매중"}</div></div></div>', unsafe_allow_html=True)
                    b1, b2 = st.columns(2)
                    if not is_sold and b1.button(f"🤝 거래완료", key=f"d_{idx}"):
                        market_worksheet.update_cell(idx + 2, 4, "판매완료"); st.cache_data.clear(); st.rerun()
                    if is_admin and b2.button(f"🗑️ 매물삭제", key=f"x_{idx}"):
                        market_worksheet.delete_rows(idx + 2); st.cache_data.clear(); st.rerun()

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

    with tabs[6]: # 💰 정산 현황
        income, paid = df['분배금_v'].sum(), df[df['정산상태'] == "정산완료"]['분배금_v'].sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("총 분배금", f"{income:,} 💎"); m2.metric("정산 완료", f"{paid:,} 💎"); m3.metric("남은 금액", f"{income-paid:,} 💎", delta_color="inverse")
        money_rank = add_medal_logic(df[df['전투력_v'] > 1].sort_values(by="분배금_v", ascending=False))
        money_rank['분배금_표시'] = money_rank['분배금_v'].apply(lambda x: f"{x:,} 다이아")
        if is_admin:
            edited = st.data_editor(money_rank[['순위', '이름', '분배금_표시', '정산상태']], column_config={"정산상태": st.column_config.SelectboxColumn("상태", options=["미정산", "정산완료"]), **UI_CONFIG}, disabled=["순위", "이름"], hide_index=True, use_container_width=True, height=700)
            if st.button("💾 정산 상태 저장"):
                idx = sheet_header.index("정산상태") + 1
                for _, row in edited.iterrows():
                    cell = worksheet.find(row['이름']); worksheet.update_cell(cell.row, idx, row['정산상태'])
                st.cache_data.clear(); st.rerun()
        else:
            money_rank['상태'] = money_rank['정산상태'].apply(lambda x: "✅ 완료" if x == "정산완료" else "⏳ 대기")
            st.dataframe(money_rank[['순위', '문파', '이름', '분배금_표시', '상태']], use_container_width=True, hide_index=True, height=700, column_config=UI_CONFIG)

else: st.error(f"데이터 로드 실패: {df}")
