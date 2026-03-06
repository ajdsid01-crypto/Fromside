import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import plotly.express as px

# 1. 🎨 [디자인] NVIDIA 다크 테마 및 전체 좌측 정렬 강제 설정
st.set_page_config(page_title="조협클래식 오늘만산다,살자", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505 !important; color: #FFFFFF !important; }
    h1, h2, h3, [data-testid="stMetricValue"] { color: #76B900 !important; font-weight: bold !important; text-align: left !important; }
    
    /* 표 내부 항목 좌측 정렬 */
    [data-testid="stDataFrame"] div[data-baseweb="table"] div {
        text-align: left !important;
        justify-content: flex-start !important;
    }
    [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th { text-align: left !important; }

    /* 사이드바 스타일 */
    [data-testid="stSidebar"] { min-width: 260px; }
    input { background-color: #111 !important; color: #76B900 !important; border: 1px solid #333 !important; }
    
    /* 탭 메뉴 디자인 */
    .stTabs [data-baseweb="tab-list"] { justify-content: flex-start !important; gap: 20px; }
    .stTabs [data-baseweb="tab"] { font-size: 17px !important; color: #666 !important; border: none !important; }
    .stTabs [aria-selected="true"] { color: #76B900 !important; border-bottom: 3px solid #76B900 !important; }
    
    /* 참여자 명단 박스 스타일 */
    .participant-box {
        background-color: #111;
        border-left: 5px solid #76B900;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 10px;
        min-height: 150px;
    }
    </style>
    """, unsafe_allow_html=True)

# 📂 2. 데이터 로드 및 전처리
@st.cache_data(ttl=10)
def load_boss_optimized_data():
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
        
        def to_int(val):
            if not val: return 0
            clean = re.sub(r'[^0-9]', '', str(val))
            return int(clean) if clean else 0

        df['전투력_v'] = df['전투력'].apply(to_int)
        df['누계_v'] = df['누계'].apply(to_int)
        df['분배금_v'] = df['분배금'].apply(to_int)
        
        # 🛡️ 참여 여부 판단 (대문자 O, 소문자 o, 한글 오 등 대응)
        def is_participated(val):
            return str(val).strip().lower() in ['o', 'ㅇ', 'v']

        df['14시_p'] = df['14시'].apply(is_participated)
        df['18시_p'] = df['18시'].apply(is_participated)
        df['22시_p'] = df['22시'].apply(is_participated)
        
        return spreadsheet, sheet, df, header
    except Exception as e:
        return None, None, str(e), None

spreadsheet, worksheet, df, sheet_header = load_boss_optimized_data()

# 📊 3. 화면 구성 및 사이드바
if isinstance(df, pd.DataFrame):
    with st.sidebar:
        st.markdown("<h2 style='text-align: center; color: #76B900;'>오늘만산다,살자</h2>", unsafe_allow_html=True)
        st.divider()
        st.subheader("📊 연합 현황")
        st.metric("총 인원", f"{len(df)}명")
        st.metric("연합 총 투력", f"{df['전투력_v'].sum():,}")
        st.divider()
        
        st.subheader("📺 연합 방송 센터")
        st.link_button("🎥 가미가미[gamigami]", "https://www.youtube.com/@gamigami706")
        st.link_button("🎥 스트리머왕코", "https://www.youtube.com/@스트리머왕코")
        st.link_button("🎥 아이엠솔이 I AM SOLEE", "https://www.youtube.com/@아이엠솔이")
        st.divider()

        with st.expander("🔐 관리자 전용"):
            admin_pw = st.text_input("암호 입력", type="password")
            is_admin = (admin_pw == "1234") 
            if st.button("🔄 데이터 강제 새로고침"):
                st.cache_data.clear()
                st.rerun()

    st.title("🛡️ 조협클래식 통합 관리 시스템")
    
    tabs = st.tabs(["⚔️ 보스 현황", "🛡️ 연합 전력", "🔥 성장 랭킹", "🏆 직업별 랭킹", "📊 분석 통계", "💰 정산 현황"])

    with tabs[0]: # 보스 현황 (개선된 레이아웃)
        st.subheader("⚔️ 시간대별 보스 참여자 명단")
        
        # 🟢 상단: 시간별 참여자 요약 리스트
        p_cols = st.columns(3)
        times = [("14시", "14시_p"), ("18시", "18시_p"), ("22시", "22시_p")]
        
        for i, (time_name, p_col) in enumerate(times):
            with p_cols[i]:
                # 해당 시간에 참여한 사람 명단 추출
                participants = df[df[p_col]]['이름'].tolist()
                count = len(participants)
                
                st.markdown(f"#### 🕒 {time_name} ({count}명)")
                if count > 0:
                    names_str = ", ".join(participants)
                    st.markdown(f"""<div class='participant-box'>{names_str}</div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div class='participant-box' style='color:#666;'>참여자가 없습니다.</div>""", unsafe_allow_html=True)

        st.divider()
        
        # 🟡 하단: 기존 상세 o/x 표 (아래로 이동)
        st.subheader("🗓️ 참여 상세 기록 (o/x)")
        boss_detail = df.sort_values(by="누계_v", ascending=False).copy()
        st.dataframe(boss_detail[['문파', '이름', '14시', '18시', '22시', '누계']], 
                     use_container_width=True, hide_index=True, height=500)

    with tabs[1]: # 연합 전력
        st.subheader("📈 문파 전투력 명단")
        cp_df = df.sort_values(by="전투력_v", ascending=False).copy()
        cp_df['전투력_표시'] = cp_df['전투력_v'].apply(lambda x: f"{x:,}")
        st.dataframe(cp_df[['문파', '이름', '직업', '전투력_표시', '성장', '카톡']], 
                     use_container_width=True, hide_index=True, height=600)

    with tabs[4]: # 분석 통계
        st.subheader("📊 연합 핵심 통계")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("실제 총원", f"{len(df)}명")
        c2.metric("통합 전투력", f"{df['전투력_v'].sum():,}")
        c3.metric("평균 전투력", f"{int(df['전투력_v'].mean()) if len(df)>0 else 0:,}")
        c4.metric("최고 전투력", f"{df['전투력_v'].max() if len(df)>0 else 0:,}")
        st.divider()
        g1, g2 = st.columns(2)
        with g1:
            fig_pie = px.pie(df, names='문파', values='전투력_v', hole=0.6, title="🏰 문파별 투력 비중", color_discrete_map={"오늘만산다": "#76B900", "오늘만살자": "#007BFF"})
            st.plotly_chart(fig_pie, use_container_width=True)
        with g2:
            job_c = df['직업'].value_counts().reset_index()
            fig_bar = px.bar(job_c, x='직업', y='count', title="🛡️ 직업 분포", color_discrete_sequence=['#76B900'])
            st.plotly_chart(fig_bar, use_container_width=True)

    with tabs[5]: # 정산 현황
        st.subheader("💰 실시간 다이아 분배 및 정산 상태")
        settlement_df = df[df['전투력_v'] > 1].copy()
        settlement_df = settlement_df.sort_values(by="분배금_v", ascending=False)
        settlement_df['분배금_표시'] = settlement_df['분배금_v'].apply(lambda x: f"{x:,} 다이아")

        if is_admin:
            st.success("✅ 관리자 모드")
            edited_df = st.data_editor(
                settlement_df[['이름', '분배금_표시', '정산상태']],
                column_config={"정산상태": st.column_config.SelectboxColumn("정산상태", options=["미정산", "정산완료"])},
                disabled=["이름", "분배금_표시"], hide_index=True, use_container_width=True
            )
            if st.button("💾 정산 결과 저장"):
                status_idx = sheet_header.index("정산상태") + 1
                for idx, row in edited_df.iterrows():
                    try:
                        cell = worksheet.find(row['이름'])
                        worksheet.update_cell(cell.row, status_idx, row['정산상태'])
                    except: continue
                st.toast("저장 완료!")
                st.cache_data.clear()
        else:
            settlement_df['상태'] = settlement_df['정산상태'].apply(lambda x: "✅ 완료" if x == "정산완료" else "⏳ 대기")
            st.dataframe(settlement_df[['문파', '이름', '분배금_표시', '상태']], use_container_width=True, hide_index=True, height=600)

else:
    st.error(f"데이터 로드 실패: {df}")




