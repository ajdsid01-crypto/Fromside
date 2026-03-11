import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import plotly.express as px
import streamlit.components.v1 as components
from datetime import datetime
import random
import string

# 1. 🎨 [디자인] NVIDIA 프리미엄 다크 테마 및 전체 스타일 설정
st.set_page_config(page_title="조협클래식 오늘만산다", layout="wide")

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
    .card-label { color: #888; font-size: 12px; margin-bottom: 2px; }
    .card-value { color: #FFF; font-size: 18px; font-weight: bold; color: #76B900; }

    /* 커스텀 테이블 스타일 */
    .custom-table {
        width: 100%; border-collapse: collapse; color: white; background-color: #111;
        border-radius: 10px; overflow: hidden; margin-top: 10px;
    }
    .custom-table th {
        background-color: #1a1a1a; color: #76B900; text-align: left;
        padding: 12px 15px; border-bottom: 2px solid #222; font-size: 0.9rem;
    }
    .custom-table td { padding: 10px 15px; border-bottom: 1px solid #222; text-align: left; font-size: 0.85rem; }

    /* 거래소 카드 스타일 */
    .market-card {
        background: #111; border: 1px solid #222; border-left: 5px solid #76B900;
        padding: 15px; border-radius: 10px; margin-bottom: 8px;
        display: flex; justify-content: space-between; align-items: center;
    }
    </style>
    """, unsafe_allow_html=True)

# 🏆 공통 로직 함수 (순위 메달 및 테이블 출력)
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

def display_custom_table(dataframe, columns_to_show, column_names):
    df_display = dataframe[columns_to_show].copy()
    df_display.columns = column_names
    html = f'<table class="custom-table"><thead><tr>' + "".join([f'<th>{c}</th>' for c in column_names]) + '</tr></thead><tbody>'
    for _, row in df_display.iterrows():
        html += '<tr>' + "".join([f'<td>{val}</td>' for val in row]) + '</tr>'
    st.markdown(html + '</tbody></table>', unsafe_allow_html=True)

# 📂 데이터 로드 (시트 연동 및 데이터 전처리)
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
        
        # 7행이 헤더 (인덱스 6)
        header = all_data[6]
        rows = all_data[7:]
        df = pd.DataFrame(rows, columns=header)
        df = df[df['이름'].str.strip() != ""].copy()
        
        # 거래소 데이터 로드
        market_sheet = spreadsheet.worksheet("거래소")
        m_values = market_sheet.get_all_values()
        market_df = pd.DataFrame(m_values[1:], columns=["판매자", "아이템이름", "가격", "상태"]) if len(m_values) > 1 else pd.DataFrame(columns=["판매자", "아이템이름", "가격", "상태"])

        # 숫자 변환 함수
        def to_int(val):
            clean = re.sub(r'[^0-9]', '', str(val))
            return int(clean) if clean else 0

        df['전투력_v'] = df['전투력'].apply(to_int)
        df['누계_v'] = df['누계'].apply(to_int)
        df['분배금_v'] = df['분배금'].apply(to_int)
        
        # 성장률 값 추출 (정렬용)
        def parse_growth_val(val):
            # 괄호 안의 퍼센트 수치를 찾아 정렬에 사용
            percent = re.search(r'([\d\.]+)(?=%)', str(val))
            return float(percent.group(1)) if percent else 0.0

        df['성장_v'] = df['성장'].apply(parse_growth_val)
        df['정산상태'] = df['정산상태'].apply(lambda x: "정산완료" if str(x).strip() == "정산완료" else "미정산")
        
        return spreadsheet, sheet, df, header, market_sheet, market_df
    except Exception as e: return None, None, str(e), None, None, None

spreadsheet, worksheet, df, sheet_header, market_worksheet, market_df = load_all_guild_data()

# 📊 화면 구성 시작
if isinstance(df, pd.DataFrame):
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    
    # --- 사이드바 영역 ---
    with st.sidebar:
        st.markdown("<div style='text-align:center; padding-bottom:10px;'><img src='https://img.icons8.com/neon/150/shield.png' width='75'></div>", unsafe_allow_html=True)
        
        # 보탐 레이더 타이머
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
        
        if st.button("🔄 최신 데이터 불러오기", use_container_width=True): st.cache_data.clear(); st.rerun()
        st.divider()
        
        st.subheader("📺 실시간 방송")
        youtube_links = [("가미가미", "https://www.youtube.com/@gamigami706", "youtube-play"), ("스트리머왕코", "https://www.youtube.com/@스트리머왕코", "controller"), ("아이엠솔이", "https://www.youtube.com/@아이엠솔이", "microphone")]
        for name, url, icon in youtube_links:
            y1, y2 = st.columns([1, 4])
            with y1: st.image(f"https://img.icons8.com/neon/96/{icon}.png", width=22)
            with y2: st.link_button(name, url, use_container_width=True)
            
        st.divider()
        
        # ADMIN 섹션 (비밀번호 일괄 생성 포함)
        with st.expander("🔐 ADMIN", expanded=st.session_state.authenticated):
            admin_pw = st.text_input("PASSWORD", type="password", key="admin_pw_main")
            if admin_pw == "rkdhkdthfdl12": 
                st.session_state.authenticated = True
                st.markdown("---")
                if st.button("🎲 미설정 비번 일괄 생성", use_container_width=True):
                    try:
                        pw_col_idx = sheet_header.index('비밀번호') + 1
                        update_count = 0
                        for i, row in df.iterrows():
                            if not str(row['비밀번호']).strip():
                                new_pw = ''.join(random.choices(string.digits, k=4))
                                worksheet.update_cell(i + 8, pw_col_idx, new_pw)
                                update_count += 1
                        st.sidebar.success(f"{update_count}명 생성 완료!")
                        st.cache_data.clear(); st.rerun()
                    except: st.error("시트에 '비밀번호' 열이 없습니다.")
                
                if st.checkbox("🔑 비밀번호 명단 보기"):
                    st.dataframe(df[['이름','비밀번호']], hide_index=True)

            if st.session_state.authenticated and st.button("로그아웃"): st.session_state.authenticated = False; st.rerun()

    # --- 메인 본문 ---
    st.title("🛡️ COMMAND CENTER")
    
    # 🔍 검색 섹션 (프로필 카드 기능 유지)
    search_query = st.text_input("🔍 길드원 상세 검색", placeholder="닉네임을 입력하여 프로필 카드를 확인하세요.")
    if search_query:
        search_result = df[df['이름'].str.contains(search_query, case=False, na=False)]
        if not search_result.empty:
            st.markdown("##### 👤 검색된 인원 프로필")
            for _, row in search_result.iterrows():
                c1, c2, c3, c4, c5 = st.columns(5)
                with c1: st.markdown(f"<div class='search-card'><div class='card-label'>닉네임</div><div class='card-value'>{row['이름']}</div></div>", unsafe_allow_html=True)
                with c2: st.markdown(f"<div class='search-card'><div class='card-label'>직업</div><div class='card-value'>{row['직업']}</div></div>", unsafe_allow_html=True)
                with c3: st.markdown(f"<div class='search-card'><div class='card-label'>전투력</div><div class='card-value'>{row['전투력_v']:,}</div></div>", unsafe_allow_html=True)
                with c4: st.markdown(f"<div class='search-card'><div class='card-label'>문파</div><div class='card-value'>{row['문파']}</div></div>", unsafe_allow_html=True)
                with c5: st.markdown(f"<div class='search-card'><div class='card-label'>성장률</div><div class='card-value'>{row['성장']}</div></div>", unsafe_allow_html=True)
        else: st.warning(f"'{search_query}' 닉네임을 찾을 수 없습니다.")

    # 7개 기본 탭 + 투력 갱신 탭
    tabs = st.tabs(["⚔️ 보탐 현황", "🛡️ 투력 현황", "🔥 성장 랭킹", "🏆 직업별 랭킹", "🛍️ 문파 거래소", "📊 분석 통계", "💰 정산 현황", "📝 투력 갱신"])

    with tabs[0]: # ⚔️ 보탐 현황
        st.subheader("🏆 보탐 참여 MVP (Top 3)")
        boss_sorted = df.sort_values(by=["누계_v", "전투력_v"], ascending=[False, False])
        display_top3_fixed(boss_sorted, "누계_v", "회")
        st.divider()
        st.markdown("##### 📜 전체 보탐 참여 명단")
        boss_vis = add_medal_logic(boss_sorted)
        display_custom_table(boss_vis, ['순위', '문파', '이름', '누계_v', '14시', '18시', '22시'], ['순위', '문파', '이름', '누계', '14시', '18시', '22시'])

    with tabs[1]: # 🛡️ 투력 현황
        st.subheader("👑 전투력 순위 (Top 3)")
        display_top3_fixed(df.sort_values(by="전투력_v", ascending=False), "전투력_v")
        st.divider()
        st.markdown("##### 📜 전체 전투력 순위")
        cp_rank = add_medal_logic(df.sort_values(by="전투력_v", ascending=False))
        cp_rank['투력_표시'] = cp_rank['전투력_v'].apply(lambda x: f"{x:,}")
        display_custom_table(cp_rank, ['순위', '문파', '이름', '직업', '투력_표시', '성장'], ['순위', '문파', '이름', '직업', '전투력', '성장'])

    with tabs[2]: # 🔥 성장 랭킹
        st.subheader("🔥 성장률 MVP (Top 3)")
        display_top3_fixed(df.sort_values(by=["성장_v", "전투력_v"], ascending=[False, False]), "성장")
        st.divider()
        st.markdown("##### 📜 전체 성장 랭킹")
        growth_rank = add_medal_logic(df.sort_values(by=["성장_v", "전투력_v"], ascending=[False, False]))
        display_custom_table(growth_rank, ['순위', '문파', '이름', '성장', '전투력'], ['순위', '문파', '이름', '성장', '전투력'])

    with tabs[3]: # 🏆 직업별 랭킹
        job_list = sorted(df['직업'].unique())
        selected_job = st.selectbox("직업 선택", job_list)
        job_df = df[df['직업'] == selected_job].sort_values(by="전투력_v", ascending=False)
        st.subheader(f"🥇 {selected_job} 클래스 Top 3")
        if not job_df.empty: display_top3_fixed(job_df, "전투력_v")
        st.divider()
        st.markdown(f"##### 📜 {selected_job} 전체 명단")
        job_rank = add_medal_logic(job_df)
        job_rank['투력_표시'] = job_rank['전투력_v'].apply(lambda x: f"{x:,}")
        display_custom_table(job_rank, ['순위', '문파', '이름', '투력_표시', '성장'], ['순위', '문파', '이름', '전투력', '성장'])

    with tabs[4]: # 🛍️ 문파 거래소
        st.subheader("🛍️ 문파 실시간 매물")
        m1, m2 = st.columns([1, 2])
        with m1:
            st.markdown("##### 📝 매물 등록")
            with st.form("market_form", clear_on_submit=True):
                ms, mi, mp = st.text_input("판매자"), st.text_input("아이템"), st.text_input("가격")
                if st.form_submit_button("등록") and ms and mi and mp:
                    market_worksheet.append_row([ms, mi, mp, "판매중"]); st.cache_data.clear(); st.rerun()
        with m2:
            st.markdown("##### 📦 판매 리스트")
            for idx, row in market_df.iterrows():
                st.markdown(f"<div class='market-card'><div><b>{row['아이템이름']}</b><br><small>{row['가격']} 다이아 / 판매자: {row['판매자']}</small></div><div>{row['상태']}</div></div>", unsafe_allow_html=True)
                if st.session_state.authenticated:
                    if st.button(f"🤝 완료", key=f"d_{idx}"):
                        try:
                            cell = market_worksheet.find(row['아이템이름'])
                            market_worksheet.update_cell(cell.row, 4, "판매완료"); st.cache_data.clear(); st.rerun()
                        except: st.error("처리 불가")

    with tabs[5]: # 📊 분석 통계
        st.subheader("📊 연합 실시간 분석")
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("통합 전투력", f"{df['전투력_v'].sum():,}")
        sc2.metric("평균 전투력", f"{int(df['전투력_v'].mean()):,}")
        sc3.metric("평균 성장률", f"{df['성장_v'].mean():.2f}%")
        g1, g2 = st.columns(2)
        with g1: st.plotly_chart(px.pie(df, names='문파', values='전투력_v', hole=0.6, title="문파별 전투력 비중"), use_container_width=True)
        with g2: st.plotly_chart(px.bar(df['직업'].value_counts().reset_index(), x='직업', y='count', title="연합 직업 분포"), use_container_width=True)

    with tabs[6]: # 💰 정산 현황
        st.subheader("💰 최다 분배금 대상자 (Top 3)")
        money_df = df[df['전투력_v'] > 1].sort_values(by=["분배금_v", "전투력_v"], ascending=[False, False])
        display_top3_fixed(money_df, "분배금_v", " 다이아")
        st.divider()
        st.markdown("##### 📜 전체 정산 현황 명단")
        money_rank = add_medal_logic(money_df)
        money_rank['분배금_표시'] = money_rank['분배금_v'].apply(lambda x: f"{x:,}")
        money_rank['상태'] = money_rank['정산상태'].apply(lambda x: "✅ 완료" if x == "정산완료" else "⏳ 대기")
        display_custom_table(money_rank, ['순위', '문파', '이름', '분배금_표시', '상태'], ['순위', '문파', '이름', '분배금', '상태'])

    with tabs[7]: # 📝 투력 갱신 (핵심 기능)
        st.subheader("📝 내 전투력 갱신")
        st.info("💡 개인 비밀번호를 입력하면 **전투력**과 **성장률**이 즉시 계산되어 반영됩니다.")
        
        with st.form("user_update_form"):
            u_col1, u_col2 = st.columns(2)
            with u_col1: target_user = st.selectbox("본인 닉네임 선택", ["선택하세요"] + list(df['이름'].unique()))
            with u_col2: user_pwd = st.text_input("개인 비밀번호", type="password")
            new_cp_val = st.number_input("갱신할 현재 전투력 (숫자만)", min_value=0, step=100)
            
            if st.form_submit_button("전투력 및 성장률 갱신"):
                if target_user != "선택하세요":
                    user_row = df[df['이름'] == target_user].iloc[0]
                    if str(user_pwd).strip() == str(user_row['비밀번호']).strip() and user_pwd != "":
                        try:
                            # 1. 인덱스 맵 생성 (열 이름으로 위치 찾기)
                            idx_map = {name: i+1 for i, name in enumerate(sheet_header)}
                            row_idx = df[df['이름'] == target_user].index[0] + 8
                            
                            # 2. 성장률 계산 로직
                            # 현재 시트에 적힌 '전투력'을 이전 값으로 사용
                            old_cp = user_row['전투력_v']
                            diff = new_cp_val - old_cp
                            growth_p = (diff / old_cp * 100) if old_cp > 0 else 0
                            
                            # 성장률 표기: 퍼센트 괄호 밖, 수치 괄호 안 (0.00% (+000))
                            growth_str = f"{growth_p:.2f}% ({diff:+,})"

                            # 3. 구글 시트 업데이트
                            worksheet.update_cell(row_idx, idx_map['전투력'], f"{new_cp_val:,}")
                            worksheet.update_cell(row_idx, idx_map['성장'], growth_str)
                            
                            st.success(f"✅ {target_user}님! {new_cp_val:,}로 업데이트 완료 (성장률: {growth_str})")
                            st.cache_data.clear(); st.rerun()
                        except Exception as e: st.error(f"시트 업데이트 중 오류 발생: {e}")
                    else: st.error("❌ 비밀번호가 올바르지 않거나 닉네임이 잘못되었습니다.")

else: st.error("데이터 로드 실패: 구글 시트 연결을 확인하세요.")



