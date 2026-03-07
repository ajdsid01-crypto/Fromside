import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import plotly.express as px
import streamlit.components.v1 as components
from datetime import datetime

# 1. 🎨 [디자인] NVIDIA 프리미엄 다크 테마 및 카드 레이아웃 설정
st.set_page_config(page_title="조협클래식 오늘만산다,살자", layout="wide")

st.markdown("""
    <style>
    /* 전체 배경 및 텍스트 스타일 */
    .stApp { background-color: #050505 !important; color: #FFFFFF !important; }
    h1, h2, h3, [data-testid="stMetricValue"] { color: #76B900 !important; font-weight: bold !important; }
    
    /* 사이드바 여백 최적화 */
    [data-testid="stSidebar"] > div:first-child { padding-top: 20px !important; }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.8rem !important; }
    
    /* 🛍️ 카드형 거래소 디자인 (요청하신 사진 느낌) */
    .market-card {
        background: linear-gradient(145deg, #151515, #0d0d0d);
        border: 1px solid #222;
        border-left: 5px solid #76B900;
        padding: 18px;
        border-radius: 12px;
        margin-bottom: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.6);
        display: flex;
        justify-content: space-between;
        align-items: center;
        transition: transform 0.2s;
    }
    .market-card:hover { transform: translateY(-2px); border-color: #333; }
    .item-info { flex-grow: 1; }
    .item-name { color: #FFFFFF; font-size: 1.25rem; font-weight: 800; margin-bottom: 6px; letter-spacing: -0.5px; }
    .item-seller { color: #777; font-size: 0.9rem; font-weight: 500; }
    .item-price-area { text-align: right; min-width: 120px; }
    .item-price { color: #76B900; font-size: 1.4rem; font-weight: 900; margin-top: 4px; }
    .item-status-tag { 
        display: inline-block;
        background: rgba(118, 185, 0, 0.15); 
        color: #76B900; 
        padding: 3px 10px; 
        border-radius: 6px; 
        font-size: 0.75rem; 
        font-weight: 800;
        border: 1px solid rgba(118, 185, 0, 0.3);
        margin-bottom: 5px;
    }

    /* 표(DataFrame) 스타일 강제 고정 */
    [data-testid="stDataFrame"] { background-color: #111111 !important; }
    div[data-testid="stDataFrame"] div[data-baseweb="table"] div {
        background-color: #111111 !important;
        color: white !important;
        text-align: left !important;
    }

    .mvp-bar {
        background: linear-gradient(90deg, #111, #1a1a1a);
        border: 1px solid #76B900;
        padding: 10px 20px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 20px;
    }
    .participant-box {
        background-color: #111;
        border-left: 4px solid #76B900;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        min-height: 70px;
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

# 📂 2. 데이터 로드 및 전처리 (실시간성 강화)
@st.cache_data(ttl=2) # 2초 캐시로 거의 실시간 반영
def load_all_guild_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open("조협오산오살")
        
        # 메인 시트 로드
        sheet = spreadsheet.sheet1
        all_data = sheet.get_all_values()
        header, rows = all_data[6], all_data[7:]
        df = pd.DataFrame(rows, columns=header)
        df = df[df['이름'].str.strip() != ""].copy()
        
        # 🚨 거래소 로드 (데이터 위치 강제 매칭)
        market_sheet = None
        market_df = pd.DataFrame(columns=["판매자", "아이템이름", "가격", "상태"])
        try:
            market_sheet = spreadsheet.worksheet("거래소")
            m_values = market_sheet.get_all_values()
            if len(m_values) > 1:
                processed_rows = []
                for row in m_values[1:]:
                    fixed_row = (row + ["", "", "", ""])[:4] 
                    processed_rows.append(fixed_row)
                market_df = pd.DataFrame(processed_rows, columns=["판매자", "아이템이름", "가격", "상태"])
            else:
                market_df = pd.DataFrame(columns=["판매자", "아이템이름", "가격", "상태"])
        except: pass

        def to_int(val):
            clean = re.sub(r'[^0-9]', '', str(val))
            return int(clean) if clean else 0
        df['전투력_v'] = df['전투력'].apply(to_int)
        df['누계_v'] = df['누계'].apply(to_int)
        df['분배금_v'] = df['분배금'].apply(to_int)
        
        if '정산상태' in df.columns:
            df['정산상태'] = df['정산상태'].apply(lambda x: "정산완료" if str(x).strip() == "정산완료" else "미정산")
        else:
            df['정산상태'] = "미정산"

        def is_p(val): return str(val).strip().lower() in ['o', 'ㅇ', 'v']
        df['14_p'], df['18_p'], df['22_p'] = df['14시'].apply(is_p), df['18시'].apply(is_p), df['22시'].apply(is_p)
        
        return spreadsheet, sheet, df, header, market_sheet, market_df
    except Exception as e:
        return None, None, str(e), None, None, None

spreadsheet, worksheet, df, sheet_header, market_worksheet, market_df = load_all_guild_data()

# 📊 3. 화면 구성
if isinstance(df, pd.DataFrame):
    with st.sidebar:
        st.markdown("<div style='text-align:center; padding-bottom:15px;'><img src='https://img.icons8.com/neon/150/shield.png' width='75'></div>", unsafe_allow_html=True)
        
        # 🕒 보스 타이머
        timer_html = """
        <div style="background:linear-gradient(135deg,#151515,#0a0a0a); border:1px solid #76B90066; padding:15px; border-radius:10px; text-align:center;">
            <div style="font-size:11px; color:#888; font-weight:bold; margin-bottom:5px;">NEXT BOSS SCAN</div>
            <div id="sidebar-timer" style="font-size:32px; font-weight:900; color:#76B900; font-family:monospace;">00:00:00</div>
        </div>
        <script>
        function up() {
            const n = new Date(new Date().toLocaleString("en-US",{timeZone:"Asia/Seoul"}));
            const b = [14, 18, 20]; let t = null;
            for(let h of b){ let x=new Date(n); x.setHours(h,0,0,0); if(n<x){t=x;break;}}
            if(!t){t=new Date(n); t.setDate(n.getDate()+1); t.setHours(14,0,0,0);}
            const d = t-n;
            const h = String(Math.floor(d/3600000)).padStart(2,'0');
            const m = String(Math.floor((d%3600000) / 60000)).padStart(2,'0');
            const s = String(Math.floor((d%60000) / 1000)).padStart(2,'0');
            document.getElementById('sidebar-timer').innerText = h+":"+m+":"+s;
        } setInterval(up,1000); up();
        </script>
        """
        components.html(timer_html, height=120)
        
        # 🔄 수동 리로드 버튼 (백업용)
        if st.button("🔄 최신 데이터 불러오기", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        with st.expander("🔐 ADMIN", expanded=False):
            admin_pw = st.text_input("PASSWORD", type="password")
            is_admin = (admin_pw == "1234") 

    st.title("🛡️ COMMAND CENTER")
    tabs = st.tabs(["⚔️ 보탐 현황", "🛡️ 투력 현황", "🛍️ 문파 거래소", "📊 분석 통계", "💰 정산 현황"])

    TABLE_HEIGHT = 700 

    with tabs[2]: # 🛍️ 문파 거래소 (카드형 레이아웃 및 자동 반영)
        st.subheader("🛍️ 문파 전용 아이템 거래소")
        
        m_col1, m_col2 = st.columns([1, 2])
        
        with m_col1:
            st.markdown("### 📝 아이템 등록")
            with st.form("market_form", clear_on_submit=True):
                m_seller = st.text_input("판매자 닉네임", placeholder="내 아이디")
                m_item = st.text_input("아이템 이름", placeholder="아이템명")
                m_price = st.text_input("가격", placeholder="예: 500, 무료나눔")
                
                if st.form_submit_button("아이템 등록하기"):
                    if market_worksheet:
                        # 🚨 등록 즉시 시트에 추가
                        market_worksheet.append_row([m_seller, m_item, m_price, "판매중"])
                        st.success("등록되었습니다!")
                        # 🚨 캐시 삭제 후 자동 페이지 리런 (리로드를 누를 필요 없음)
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("거래소 시트를 찾을 수 없습니다.")

        with m_col2:
            st.markdown("### 📦 매물 목록")
            if not market_df.empty:
                # '판매중' 상태만 필터링
                display_items = market_df[market_df['상태'].str.contains("판매중", na=True)]
                
                if display_items.empty:
                    st.info("현재 판매 중인 아이템이 없습니다.")
                else:
                    for idx, row in display_items.iterrows():
                        # 🛍️ 카드형 HTML 렌더링 (사진 느낌 반영)
                        st.markdown(f"""
                            <div class="market-card">
                                <div class="item-info">
                                    <div class="item-name">{row['아이템이름']}</div>
                                    <div class="item-seller">Seller: {row['판매자']}</div>
                                </div>
                                <div class="item-price-area">
                                    <div class="item-status-tag">판매중</div>
                                    <div class="item-price">{row['가격']} 💎</div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # 관리자 모드 버튼
                        if is_admin:
                            if st.button(f"🗑️ {row['아이템이름']} 삭제", key=f"del_{idx}"):
                                market_worksheet.delete_rows(idx + 2)
                                st.cache_data.clear()
                                st.rerun()
            else:
                st.info("등록된 매물이 없습니다.")

    with tabs[0]: # ⚔️ 보스 현황
        max_val = df['누계_v'].max()
        if max_val > 0:
            mvps = df[df['누계_v'] == max_val]['이름'].tolist()
            st.markdown(f"<div class='mvp-bar'><span style='color:#76B900; font-weight:bold;'>🏆 이번 주 보탐 MVP : </span>{', '.join(mvps)}</div>", unsafe_allow_html=True)
        p_cols = st.columns(3)
        t_info = [("14시", "14_p"), ("18시", "18_p"), ("20시", "22_p")]
        for i, (t_name, p_col) in enumerate(t_info):
            with p_cols[i]:
                names = df[df[p_col]]['이름'].tolist()
                st.markdown(f"#### 🕒 {t_name}")
                st.markdown(f"<div class='participant-box'>{', '.join(names) if names else '참여자 없음'}</div>", unsafe_allow_html=True)
        st.divider()
        boss_vis = df.copy()
        for col in ['14시', '18시', '22시']: boss_vis[col] = boss_vis[col].apply(lambda x: "✅" if str(x).strip().lower() in ['o', 'ㅇ', 'v'] else "──")
        st.dataframe(add_medal_logic(boss_vis.sort_values(by="누계_v", ascending=False))[['순위', '문파', '이름', '14시', '18시', '22시', '누계_v']], use_container_width=True, hide_index=True, height=TABLE_HEIGHT)

    with tabs[1]: # 🛡️ 투력 현황
        cp_rank = add_medal_logic(df.sort_values(by="전투력_v", ascending=False))
        cp_rank['전투력_표시'] = cp_rank['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(cp_rank[['순위', '문파', '이름', '직업', '전투력_표시']], use_container_width=True, hide_index=True, height=TABLE_HEIGHT)

    with tabs[3]: # 📊 분석 통계
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("통합 전투력", f"{df['전투력_v'].sum():,}")
        sc2.metric("평균 전투력", f"{int(df['전투력_v'].mean()):,}")
        sc3.metric("총 인원", f"{len(df)}명")
        st.divider()
        g1, g2 = st.columns(2)
        with g1: st.plotly_chart(px.pie(df, names='문파', values='전투력_v', hole=0.6, title="문파별 투력 비중"), use_container_width=True)
        with g2: st.plotly_chart(px.bar(df['직업'].value_counts().reset_index(), x='직업', y='count', title="연합 직업 분포"), use_container_width=True)

    with tabs[4]: # 💰 정산 현황
        income = df['분배금_v'].sum()
        paid = df[df['정산상태'] == "정산완료"]['분배금_v'].sum()
        st.subheader("💰 정산 관리 대시보드")
        m1, m2, m3 = st.columns(3)
        m1.metric("총 분배금", f"{income:,} 💎")
        m2.metric("정산 완료", f"{paid:,} 💎")
        m3.metric("남은 금액", f"{income-paid:,} 💎", delta_color="inverse")
        st.divider()
        money_rank = add_medal_logic(df[df['전투력_v'] > 1].sort_values(by="분배금_v", ascending=False))
        money_rank['분배금_표시'] = money_rank['분배금_v'].apply(lambda x: f"{x:,} 다이아")
        if is_admin:
            edited_df = st.data_editor(money_rank[['순위', '이름', '분배금_표시', '정산상태']], column_config={"정산상태": st.column_config.SelectboxColumn("상태", options=["미정산", "정산완료"])}, disabled=["순위", "이름", "분배금_표시"], hide_index=True, use_container_width=True, height=TABLE_HEIGHT)
            if st.button("💾 정산 상태 저장"):
                idx = sheet_header.index("정산상태") + 1
                for _, row in edited_df.iterrows():
                    cell = worksheet.find(row['이름'])
                    worksheet.update_cell(cell.row, idx, row['정산상태'])
                st.cache_data.clear()
                st.rerun()
        else:
            money_rank['상태'] = money_rank['정산상태'].apply(lambda x: "✅ 완료" if x == "정산완료" else "⏳ 대기")
            st.dataframe(money_rank[['순위', '문파', '이름', '분배금_표시', '상태']], use_container_width=True, hide_index=True, height=TABLE_HEIGHT)

else: st.error("데이터 로드 실패")
















