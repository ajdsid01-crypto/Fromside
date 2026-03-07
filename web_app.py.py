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
    
    /* 사이드바 최적화 */
    [data-testid="stSidebar"] > div:first-child { padding-top: 20px !important; }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.8rem !important; }
    .stDivider { margin: 0.8rem 0 !important; }
    
    /* 🚨 표 내부 데이터 좌측 정렬 강제 (HTML 테이블용) */
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
    .custom-table tr:hover { background-color: #151515; }

    /* 🛍️ 카드형 거래소 디자인 */
    .market-card {
        background: #111; border: 1px solid #222; border-left: 5px solid #76B900;
        padding: 18px; border-radius: 12px; margin-bottom: 5px;
        display: flex; justify-content: space-between; align-items: center;
    }
    .sold-out-card { background: #0a0a0a; border-left: 5px solid #444; opacity: 0.4; filter: grayscale(100%); }
    .item-info { flex: 3; }
    .item-name { color: #FFF; font-size: 1.25rem; font-weight: bold; margin-bottom: 3px; }
    .item-price { color: #76B900; font-size: 1.15rem; font-weight: 800; margin-bottom: 6px; }
    .status-tag { display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: bold; border: 1px solid #76B900; color: #76B900; }
    
    .stButton>button { width: 100%; border-radius: 6px; font-size: 0.85rem !important; height: 35px; }
    .mvp-bar { background: linear-gradient(90deg, #111, #1a1a1a); border: 1px solid #76B900; padding: 10px 20px; border-radius: 8px; text-align: center; margin-bottom: 20px; }
    .participant-box { background-color: #111; border-left: 4px solid #76B900; padding: 10px; border-radius: 5px; margin-bottom: 10px; min-height: 70px; }
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
        df['14_p'] = df['14시'].apply(lambda x: str(x).strip().lower() in ['o', 'ㅇ', 'v'])
        df['18_p'] = df['18시'].apply(lambda x: str(x).strip().lower() in ['o', 'ㅇ', 'v'])
        df['22_p'] = df['22시'].apply(lambda x: str(x).strip().lower() in ['o', 'ㅇ', 'v'])
        
        return spreadsheet, sheet, df, header, market_sheet, market_df
    except Exception as e:
        return None, None, str(e), None, None, None

spreadsheet, worksheet, df, sheet_header, market_worksheet, market_df = load_all_guild_data()

# 📊 3. 화면 구성 및 인증 상태 확인
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if isinstance(df, pd.DataFrame):
    with st.sidebar:
        st.markdown("<div style='text-align:center; padding-bottom:10px;'><img src='https://img.icons8.com/neon/150/shield.png' width='75'></div>", unsafe_allow_html=True)
        
        timer_html = """
        <div style="background:linear-gradient(135deg,#151515,#0a0a0a); border:1px solid #76B90066; padding:15px; border-radius:10px; text-align:center;">
            <div style="font-size:11px; color:#888; font-weight:bold; margin-bottom:5px;">NEXT BOSS RADAR</div>
            <div id="sidebar-timer" style="font-size:32px; font-weight:900; color:#76B900; font-family:monospace;">00:00:00</div>
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
        components.html(timer_html, height=120)
        
        if st.button("🔄 최신 데이터 불러오기", use_container_width=True):
            st.cache_data.clear(); st.rerun()
        st.divider()
        st.subheader("📊 실시간 지표")
        c1, c2 = st.columns(2)
        c1.metric("인원", f"{len(df)}명"); c2.metric("총투력", f"{df['전투력_v'].sum():,}")
        st.divider()
        youtube_links = [("가미가미 TV", "https://www.youtube.com/@gamigami706", "youtube-play"), ("왕코 방송국", "https://www.youtube.com/@스트리머왕코", "controller"), ("아이엠솔이", "https://www.youtube.com/@아이엠솔이", "microphone")]
        for name, url, icon in youtube_links:
            y1, y2 = st.columns([1, 4])
            with y1: st.image(f"https://img.icons8.com/neon/96/{icon}.png", width=22)
            with y2: st.link_button(name, url, use_container_width=True)
        st.divider()
        
        with st.expander("🔐 ADMIN", expanded=st.session_state.authenticated):
            admin_pw = st.text_input("PASSWORD", type="password", key="admin_input")
            if admin_pw == "rkdhkdthfdl12":
                st.session_state.authenticated = True
                st.success("인증되었습니다.")
            elif admin_pw != "":
                st.error("비밀번호가 틀립니다.")
            if st.session_state.authenticated:
                if st.button("로그아웃"):
                    st.session_state.authenticated = False
                    st.rerun()

    st.title("🛡️ COMMAND CENTER")

    # 🔍 상단 검색창
    search_query = st.text_input("🔍 길드원 닉네임으로 검색", placeholder="검색어를 입력하면 프로필 요약과 함께 아래 표가 필터링됩니다.")
    if search_query:
        filtered_df = df[df['이름'].str.contains(search_query, case=False, na=False)]
    else:
        filtered_df = df.copy()

    # ==========================================
    # 🚨 [신규 추가] 캐릭터 검색 결과 '종합 프로필 카드' 표시 영역
    # ==========================================
    if search_query and not filtered_df.empty:
        st.markdown("#### 🧑‍🎤 캐릭터 통합 프로필")
        for _, row in filtered_df.iterrows():
            st.markdown(f"""
            <div style="background-color: #111; border: 1px solid #222; border-left: 5px solid #76B900; padding: 20px; border-radius: 10px; margin-bottom: 15px;">
                <h3 style="margin-top: 0; color: #FFF !important; display: flex; align-items: center; gap: 10px;">
                    <span style="color: #76B900; font-size: 1.1rem;">[{row.get('문파', '무소속')}]</span> 
                    {row['이름']} 
                    <span style="font-size: 0.9rem; color: #888; border: 1px solid #444; padding: 2px 8px; border-radius: 12px;">{row.get('직업', '-')}</span>
                </h3>
                <div style="display: flex; justify-content: flex-start; flex-wrap: wrap; gap: 30px; margin-top: 15px;">
                    <div>
                        <div style="color: #76B900; font-size: 0.85rem; font-weight: bold; margin-bottom: 3px;">⚔️ 전투력</div>
                        <div style="font-size: 1.3rem; font-weight: bold; color: white;">{row.get('전투력', '0')}</div>
                    </div>
                    <div>
                        <div style="color: #76B900; font-size: 0.85rem; font-weight: bold; margin-bottom: 3px;">🔥 성장률</div>
                        <div style="font-size: 1.3rem; font-weight: bold; color: white;">{row.get('성장', '0%')}</div>
                    </div>
                    <div>
                        <div style="color: #76B900; font-size: 0.85rem; font-weight: bold; margin-bottom: 3px;">👑 보탐 참여(누계)</div>
                        <div style="font-size: 1.3rem; font-weight: bold; color: white;">{row.get('누계_v', 0)} 회</div>
                    </div>
                    <div>
                        <div style="color: #76B900; font-size: 0.85rem; font-weight: bold; margin-bottom: 3px;">💰 분배금</div>
                        <div style="font-size: 1.3rem; font-weight: bold; color: white;">{row.get('분배금_v', 0):,} <span style="font-size: 0.8rem; color:#888;">({row.get('정산상태', '미정산')})</span></div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.divider()
    elif search_query and filtered_df.empty:
        st.warning(f"'{search_query}'에 해당하는 길드원을 찾을 수 없습니다.")
    # ==========================================

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
        max_val = df['누계_v'].max()
        if max_val > 0:
            mvps = df[df['누계_v'] == max_val]['이름'].tolist()
            st.markdown(f"<div class='mvp-bar'><span style='color:#76B900; font-weight:bold;'>🏆 MVP : </span>{', '.join(mvps)}</div>", unsafe_allow_html=True)
        p_cols = st.columns(3)
        for i, (t_name, p_col) in enumerate([("14시", "14_p"), ("18시", "18_p"), ("22시", "22_p")]):
            with p_cols[i]:
                names = df[df[p_col]]['이름'].tolist()
                st.markdown(f"#### 🕒 {t_name}")
                st.markdown(f"<div class='participant-box'>{', '.join(names) if names else '──'}</div>", unsafe_allow_html=True)
        st.divider()
        boss_vis = add_medal_logic(filtered_df.sort_values(by="누계_v", ascending=False))
        for col in ['14시', '18시', '22시']: boss_vis[col] = boss_vis[col].apply(lambda x: "✅" if str(x).strip().lower() in ['o', 'ㅇ', 'v'] else "──")
        display_custom_table(boss_vis, ['순위', '문파', '이름', '누계_v', '14시', '18시', '22시'], ['순위', '문파', '이름', '누계', '14시', '18시', '22시'])

        # ==========================================
        # 🚨 [신규 추가] 관리자 전용 누계 초기화 로직
        # ==========================================
        if st.session_state.authenticated:
            st.markdown("<br>", unsafe_allow_html=True)
            st.error("⚠️ **관리자 전용 : 보탐 누계 초기화**")
            
            reset_c1, reset_c2 = st.columns([3, 1])
            with reset_c1:
                st.info("새로운 주간/월간 보탐 기록을 위해 모든 인원의 '누계' 점수를 0으로 일괄 초기화합니다.")
                confirm_reset = st.checkbox("위 내용을 확인했으며, 전체 초기화를 진행합니다.")
                
            with reset_c2:
                if st.button("🔄 누계 0으로 초기화", disabled=not confirm_reset, use_container_width=True):
                    with st.spinner("데이터 초기화 중..."):
                        try:
                            # 1. 시트 헤더에서 '누계' 컬럼의 위치 파악 (1-based index)
                            col_idx = sheet_header.index('누계') + 1
                            # 2. 업데이트할 셀 범위 설정 (8행부터 시작)
                            cell_list = worksheet.range(8, col_idx, 7 + len(df), col_idx)
                            # 3. 셀 값 0으로 변경
                            for cell in cell_list:
                                cell.value = '0'
                            # 4. 일괄 업데이트 (속도 최적화)
                            worksheet.update_cells(cell_list)
                            st.cache_data.clear()
                            st.success("✅ 모든 인원의 누계가 성공적으로 초기화되었습니다.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"초기화 중 오류가 발생했습니다: {e}")
        # ==========================================

    with tabs[1]: # 🛡️ 투력 현황
        cp_rank = add_medal_logic(filtered_df.sort_values(by="전투력_v", ascending=False))
        cp_rank['전투력'] = cp_rank['전투력_v'].apply(lambda x: f"{x:,}")
        display_custom_table(cp_rank, ['순위', '문파', '이름', '직업', '전투력', '성장'], ['순위', '문파', '이름', '직업', '전투력', '성장'])

    with tabs[4]: # 🛍️ 문파 거래소
        m1, m2 = st.columns([1, 2])
        with m1:
            with st.form("market_form", clear_on_submit=True):
                ms, mi, mp = st.text_input("판매자"), st.text_input("아이템"), st.text_input("가격")
                if st.form_submit_button("등록"):
                    if market_worksheet: market_worksheet.append_row([ms, mi, mp, "판매중"]); st.cache_data.clear(); st.rerun()
        with m2:
            display_market = market_df[market_df['판매자'].str.contains(search_query, case=False, na=False)] if search_query else market_df
            if not display_market.empty:
                for idx, row in display_market.iterrows():
                    is_sold = "판매완료" in row['상태']
                    st.markdown(f'<div class="market-card {"sold-out-card" if is_sold else ""}"><div class="item-info"><div class="item-name">{row["아이템이름"]}</div><div class="item-price">{row["가격"]}</div><div class="item-seller">판매자 : {row["판매자"]}</div></div><div class="status-area"><div class="status-tag">{"판매완료" if is_sold else "판매중"}</div></div></div>', unsafe_allow_html=True)
                    b1, b2 = st.columns(2)
                    if not is_sold and b1.button(f"🤝 거래완료", key=f"done_{idx}"):
                        cell = market_worksheet.find(row["아이템이름"])
                        market_worksheet.update_cell(cell.row, 4, "판매완료")
                        st.cache_data.clear(); st.rerun()
                    if st.session_state.authenticated and b2.button(f"🗑️ 매물삭제", key=f"del_{idx}"):
                        try:
                            cell = market_worksheet.find(row["아이템이름"])
                            market_worksheet.delete_rows(cell.row)
                            st.cache_data.clear(); st.success("삭제되었습니다."); st.rerun()
                        except:
                            st.error("삭제 중 오류가 발생했습니다. 수동으로 시트를 확인해주세요.")

    with tabs[6]: # 💰 정산 현황
        income, paid = df['분배금_v'].sum(), df[df['정산상태'] == "정산완료"]['분배금_v'].sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("총 분배금", f"{income:,}"); m2.metric("정산 완료", f"{paid:,}"); m3.metric("남은 금액", f"{income-paid:,}")
        money_rank = add_medal_logic(filtered_df[filtered_df['전투력_v'] > 1].sort_values(by="분배금_v", ascending=False))
        money_rank['분배금_표시'] = money_rank['분배금_v'].apply(lambda x: f"{x:,}")
        money_rank['상태'] = money_rank['정산상태'].apply(lambda x: "✅ 완료" if x == "정산완료" else "⏳ 대기")
        
        if st.session_state.authenticated:
            st.info("🔓 관리자 모드 활성화")
            edited = st.data_editor(money_rank[['순위', '이름', '분배금_표시', '정산상태']], column_config={"정산상태": st.column_config.SelectboxColumn("상태", options=["미정산", "정산완료"])}, disabled=["순위", "이름", "분배금_표시"], hide_index=True, use_container_width=True)
            if st.button("💾 정산 상태 저장"):
                idx = sheet_header.index("정산상태") + 1
                for _, row in edited.iterrows():
                    cell = worksheet.find(row['이름']); worksheet.update_cell(cell.row, idx, row['정산상태'])
                st.cache_data.clear(); st.success("저장되었습니다!"); st.rerun()
        else:
            display_custom_table(money_rank, ['순위', '문파', '이름', '분배금_표시', '상태'], ['순위', '문파', '이름', '분배금', '상태'])

    with tabs[2]: # 🔥 성장 랭킹
        growth_rank = add_medal_logic(filtered_df.sort_values(by="성장_v", ascending=False))
        growth_rank['전투력'] = growth_rank['전투력_v'].apply(lambda x: f"{x:,}")
        display_custom_table(growth_rank, ['순위', '문파', '이름', '성장', '전투력'], ['순위', '문파', '이름', '성장', '전투력'])
        
    with tabs[3]: # 🏆 직업별 랭킹
        job_list = sorted(df['직업'].unique())
        selected_job = st.selectbox("직업 선택", job_list)
        job_rank = add_medal_logic(filtered_df[filtered_df['직업'] == selected_job].sort_values(by="전투력_v", ascending=False))
        job_rank['전투력'] = job_rank['전투력_v'].apply(lambda x: f"{x:,}")
        display_custom_table(job_rank, ['순위', '문파', '이름', '전투력', '성장'], ['순위', '문파', '이름', '전투력', '성장'])
        
    with tabs[5]: # 📊 분석 통계
        st.subheader("📊 연합 실시간 분석")
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("통합 전투력", f"{df['전투력_v'].sum():,}"); sc2.metric("평균 전투력", f"{int(df['전투력_v'].mean()):,}"); sc3.metric("평균 성장률", f"{df['성장_v'].mean():.2f}%")
        g1, g2 = st.columns(2)
        with g1: st.plotly_chart(px.pie(df, names='문파', values='전투력_v', hole=0.6, title="문파별 투력 비중"), use_container_width=True)
        with g2: st.plotly_chart(px.bar(df['직업'].value_counts().reset_index(), x='직업', y='count', title="연합 직업 분포"), use_container_width=True)

else: st.error("데이터 로드 실패")

