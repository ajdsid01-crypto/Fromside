import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import plotly.express as px
import streamlit.components.v1 as components

# 1. 🎨 [디자인] NVIDIA 프리미엄 다크 테마 및 좌측 정렬 강제 설정
st.set_page_config(page_title="조협클래식 통합 관리 시스템", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505 !important; color: #FFFFFF !important; }
    h1, h2, h3, [data-testid="stMetricValue"] { color: #76B900 !important; font-weight: bold !important; }
    
    /* 🚨 [핵심] 모든 표 데이터 좌측 정렬 강제 고정 */
    [data-testid="stDataFrame"] div[data-baseweb="table"] div {
        text-align: left !important;
        justify-content: flex-start !important;
        padding-left: 12px !important;
    }
    
    /* 사이드바 최적화 */
    [data-testid="stSidebar"] > div:first-child { padding-top: 20px !important; }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.8rem !important; }
    
    /* 🛍️ 카드형 거래소 디자인 */
    .market-card {
        background: #111; border: 1px solid #222; border-left: 5px solid #76B900;
        padding: 15px; border-radius: 10px; margin-bottom: 5px;
        display: flex; justify-content: space-between; align-items: center;
    }
    .item-info { flex: 3; }
    .item-name { color: #FFF; font-size: 1.25rem; font-weight: bold; margin-bottom: 3px; }
    .item-price { color: #76B900; font-size: 1.15rem; font-weight: 800; }
    .item-seller { color: #888; font-size: 0.9rem; }
    .status-tag { 
        display: inline-block; padding: 4px 10px; border-radius: 6px; 
        font-size: 0.75rem; font-weight: bold; border: 1px solid #76B900; color: #76B900;
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

# 📂 2. 데이터 로드 및 전처리
@st.cache_data(ttl=2)
def load_all_guild_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open("조협오산오살")
        
        # 메인 데이터
        sheet = spreadsheet.sheet1
        all_data = sheet.get_all_values()
        header_idx = 0
        for i, row in enumerate(all_data):
            if "이름" in [c.strip() for c in row]:
                header_idx = i
                break
        header = [c.strip() for c in all_data[header_idx]]
        df = pd.DataFrame(all_data[header_idx + 1:], columns=header)
        df['sheet_row'] = range(header_idx + 2, header_idx + 2 + len(df))
        df = df[df['이름'].str.strip() != ""].copy()
        
        # 거래소 데이터
        try:
            market_sheet = spreadsheet.worksheet("거래소")
            m_values = market_sheet.get_all_values()
            market_df = pd.DataFrame(m_values[1:], columns=["판매자", "아이템이름", "가격", "상태"])
        except:
            market_sheet = None
            market_df = pd.DataFrame(columns=["판매자", "아이템이름", "가격", "상태"])

        def to_int(val):
            clean = re.sub(r'[^0-9]', '', str(val))
            return int(clean) if clean else 0

        for col in ['전투력', '누계', '분배금']:
            if col in df.columns: df[f'{col}_v'] = df[col].apply(to_int)
            else: df[f'{col}_v'] = 0

        def parse_growth(val):
            val = str(val)
            pct = re.search(r'([\d\.]+)(?=%)', val)
            num = re.search(r'([▲▼]?[\d,]+)', val)
            return (float(pct.group(1)) if pct else 0.0, f"{pct.group(1)}% ({num.group(1)})" if pct and num else "-")

        if '성장' in df.columns:
            growth_res = df['성장'].apply(parse_growth)
            df['성장_v'], df['성장_표시'] = zip(*growth_res)
        
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
        st.divider()
        st.subheader("📊 연합 실시간 지표")
        c1, c2 = st.columns(2)
        c1.metric("인원", f"{len(df)}명"); c2.metric("총투력", f"{df['전투력_v'].sum():,}")
        st.divider()
        with st.expander("🔐 ADMIN", expanded=False):
            admin_pw = st.text_input("PASSWORD", type="password")
            is_admin = (admin_pw == "1234") 

    st.title("🛡️ COMMAND CENTER")
    tabs = st.tabs(["⚔️ 보탐 현황", "🛡️ 투력 현황", "🔥 성장 랭킹", "🏆 직업별 랭킹", "🛍️ 문파 거래소", "📊 분석 통계", "💰 정산 현황"])

    # 1. 보탐 탭
    with tabs[0]:
        boss_vis = df.copy()
        for col in ['14시', '18시', '22시']: 
            if col in boss_vis.columns: boss_vis[col] = boss_vis[col].apply(lambda x: "✅" if str(x).strip().lower() in ['o', 'ㅇ', 'v'] else "──")
        display_df = add_medal_logic(boss_vis.sort_values(by="누계_v", ascending=False)).rename(columns={"누계_v": "참여횟수"})
        st.dataframe(display_df[['순위', '문파', '이름', '14시', '18시', '22시', '참여횟수']], use_container_width=True, hide_index=True, height=700)

    # 2. 투력 탭
    with tabs[1]:
        cp_df = add_medal_logic(df.sort_values(by="전투력_v", ascending=False))
        cp_df['전투력'] = cp_df['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(cp_df[['순위', '문파', '이름', '직업', '전투력']], use_container_width=True, hide_index=True, height=700)

    # 3. 성장 탭
    with tabs[2]:
        growth_df = add_medal_logic(df.sort_values(by="성장_v", ascending=False))
        st.dataframe(growth_df[['순위', '문파', '이름', '성장_표시']], use_container_width=True, hide_index=True, height=700)

    # 5. 거래소 탭 (요청 기능 핵심 복구)
    with tabs[4]:
        m1, m2 = st.columns([1, 2])
        with m1:
            st.markdown("### 📝 아이템 등록")
            with st.form("market_form", clear_on_submit=True):
                ms, mi, mp = st.text_input("판매자"), st.text_input("아이템"), st.text_input("가격")
                if st.form_submit_button("등록") and market_worksheet:
                    market_worksheet.append_row([ms, mi, mp, "판매중"]); st.cache_data.clear(); st.rerun()
        with m2:
            st.markdown("### 📦 매물 목록")
            if not market_df.empty:
                # '판매중' 상태만 필터링
                on_sale = market_df[market_df['상태'].str.contains("판매중", na=True)]
                for idx, row in on_sale.iterrows():
                    with st.container():
                        st.markdown(f'<div class="market-card"><div class="item-info"><div class="item-name">{row["아이템이름"]}</div><div class="item-seller">판매자 : {row["판매자"]}</div></div><div class="status-area"><div class="status-tag">판매중</div><div class="item-price">{row["가격"]}</div></div></div>', unsafe_allow_html=True)
                        
                        btn_col1, btn_col2 = st.columns([1, 4])
                        with btn_col1:
                            # 🚨 문파원 직접 완료 기능: 상태를 '판매완료'로 변경
                            if st.button("🤝 거래완료", key=f"done_{idx}"):
                                market_worksheet.update_cell(idx + 2, 4, "판매완료")
                                st.cache_data.clear(); st.rerun()
                        with btn_col2:
                            # ADMIN 전용: 행 자체를 삭제
                            if is_admin:
                                if st.button("🗑️ 행 삭제", key=f"del_{idx}"):
                                    market_worksheet.delete_rows(idx + 2)
                                    st.cache_data.clear(); st.rerun()

    # 6. 분석 통계 탭
    with tabs[5]:
        st.subheader("📊 연합 실시간 분석")
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("통합 전투력", f"{df['전투력_v'].sum():,}")
        sc2.metric("평균 전투력", f"{int(df['전투력_v'].mean()):,}")
        sc3.metric("최고 전투력", f"{df['전투력_v'].max():,}")
        sc4.metric("연합 인원", f"{len(df)}명")
        st.divider()
        g1, g2 = st.columns(2)
        with g1:
            fig_pie = px.pie(df, names='문파', values='전투력_v', hole=0.5, title="🏰 문파별 투력 점유율", color_discrete_sequence=['#76B900', '#007BFF'])
            fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white'); st.plotly_chart(fig_pie, use_container_width=True)
        with g2:
            job_counts = df['직업'].value_counts().reset_index(); job_counts.columns = ['직업', '인원']
            fig_bar = px.bar(job_counts, x='직업', y='인원', title="⚔️ 직업별 인원 분포", text='인원').update_traces(marker_color='#76B900')
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white'); st.plotly_chart(fig_bar, use_container_width=True)

    # 7. 정산 탭
    with tabs[6]:
        elite_df = df[(df['전투력_v'] > 1) & (df['누계_v'] > 0)].copy()
        st.metric("정예 총 분배금", f"{elite_df['분배금_v'].sum():,} 💎")
        money_df = add_medal_logic(elite_df.sort_values(by="분배금_v", ascending=False))
        money_df['분배금'] = money_df['분배금_v'].apply(lambda x: f"{x:,}")
        st.dataframe(money_df[['순위', '이름', '분배금', '정산상태']], use_container_width=True, hide_index=True)

    # 4. 직업별 랭킹 탭
    with tabs[3]:
        job_list = sorted(df['직업'].unique()) if '직업' in df.columns else []
        selected_job = st.selectbox("직업 선택", job_list)
        job_df = add_medal_logic(df[df['직업'] == selected_job].sort_values(by="전투력_v", ascending=False))
        job_df['전투력'] = job_df['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(job_df[['순위', '문파', '이름', '전투력']], use_container_width=True, hide_index=True)

else: st.error("데이터 로드 실패")
