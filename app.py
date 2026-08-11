import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import json
import google.generativeai as genai
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 0. 🔑 API 키 및 클라우드 인증 금고
# ==========================================
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    GEMINI_API_KEY = None

def get_gsheet_client():
    try:
        if "GCP_CREDENTIALS" not in st.secrets: return None
        creds_json = json.loads(st.secrets["GCP_CREDENTIALS"])
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
        return gspread.authorize(creds)
    except:
        return None

# ==========================================
# 1. 모바일 최적화 및 직관적 UI CSS
# ==========================================
st.set_page_config(page_title="브쌤's Diet 비서", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    input, select, textarea { font-size: 16px !important; }
    [data-testid="stHeaderActionElements"] { display: none !important; }
    header { background: transparent !important; }
    
    [data-testid="stSidebar"] label p { 
        font-size: 1.3rem !important; font-weight: 900 !important; color: #2C3E50 !important; padding: 5px 0;
    }
    
    .block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; }
    .stTextInput input, .stSelectbox div { border-radius: 8px !important; font-weight: 600 !important; }
    [data-testid="stDecoration"] { display: none; }
    
    /* 서브 버튼 */
    [data-testid="baseButton-secondary"] {
        background-color: #2C3E50 !important;
        border: none !important;
        border-radius: 8px !important;
        color: white !important;
        font-weight: 800 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="baseButton-secondary"]:active {
        transform: scale(0.98) !important;
    }
    
    /* 메인 버튼 (입력 저장용) */
    [data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #FF6B6B, #C0392B) !important;
        border: none !important;
        border-radius: 10px !important;
        color: white !important;
        font-size: 1.15rem !important;
        font-weight: 900 !important;
        height: 55px !important;
        box-shadow: 0 4px 10px rgba(192, 57, 43, 0.25) !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="baseButton-primary"]:active {
        transform: scale(0.98) !important;
    }
    
    /* 대시보드 디자인 */
    .status-dashboard { padding: 22px; border-radius: 12px; text-align: center; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); color: white;}
    .status-fasting { background: linear-gradient(135deg, #1ABC9C, #16A085); }
    .status-eating { background: linear-gradient(135deg, #E67E22, #D35400); }
    .status-wait { background: linear-gradient(135deg, #7F8C8D, #95A5A6); box-shadow: none; }
    .status-title { font-size: 1.1rem; font-weight: bold; margin-bottom: 8px; opacity: 0.9;}
    .status-time { font-size: 2.2rem; font-weight: 900; letter-spacing: 1px; margin-bottom: 5px;}
    .status-msg { font-size: 1rem; font-weight: bold; background: rgba(0,0,0,0.2); border-radius: 20px; padding: 6px 15px; display: inline-block; margin-top: 5px;}
    
    [data-testid="stCameraInput"] { width: 100% !important; padding: 0 !important; margin: 0 !important; }
    [data-testid="stCameraInput"] video, [data-testid="stCameraInput"] img { width: 100% !important; max-width: 100% !important; object-fit: cover !important; border-radius: 12px; }
    
    .report-box { background-color:#FFFFFF; padding:25px; border-radius:12px; border:1px solid #E5E7E9; margin-top:15px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); }
    .report-title { font-size: 1.2rem; font-weight: 900; color: #1A5276; margin-top: 25px; margin-bottom: 15px; border-bottom: 2px solid #1ABC9C; padding-bottom: 6px; letter-spacing: -0.3px;}
    .report-p { font-size: 1.05rem; line-height: 1.8; color: #34495E; margin-bottom: 15px; word-break: keep-all; }
    
    .dashboard-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top:10px; margin-bottom: 15px;}
    .macro-box { padding: 15px 5px; border-radius: 10px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .macro-title { font-size: 0.9rem; font-weight: bold; color: #7F8C8D; margin-bottom: 5px;}
    .macro-val { font-size: 1.1rem; font-weight: 900; color: #2C3E50;}
    .macro-diff { font-size: 0.85rem; font-weight: bold; margin-top: 5px; }
    .status-green { background-color: #EAFAF1; border: 1px solid #27AE60; }
    .status-red { background-color: #FDEDEC; border: 1px solid #E74C3C; }
    
    .micro-box { background-color:#FDFEFE; padding:10px; border-radius:8px; border:1px dashed #BDC3C7; text-align:center; font-size:0.9rem; color:#34495E; margin-bottom: 20px;}
    
    .diet-table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.95rem; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .diet-table th { background-color: #34495E; color: white; padding: 12px 5px; text-align: center; font-weight: 800; font-size: 0.9rem;}
    .diet-table td { padding: 14px 5px; text-align: center; border-bottom: 1px solid #E5E7E9; vertical-align: middle; background-color: white;}
    .badge { padding: 4px 8px; border-radius: 6px; font-weight: 900; font-size: 0.85rem; white-space: nowrap;}
    
    h1 { font-size: 1.65rem !important; font-weight: 900 !important; color: #2C3E50; text-align: center; margin-bottom: 5px; white-space: nowrap; letter-spacing: -0.5px;}
    .date-display { text-align:center; font-size:1.15rem; font-weight:900; color:#7F8C8D; margin-bottom:20px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1.5 카테고리 정의
# ==========================================
BEV_CATEGORIES = [
    "아메리카노 / 에스프레소", "차류 (녹차, 홍차, 콤부차 등)", "제로 칼로리 음료 (제로콜라 등)",
    "단백질 보충 액상", "일반 우유 / 무가당 두유", "일반 탄산음료 (콜라, 사이다)",
    "달콤한 커피류 (믹스커피, 바닐라라떼 등)", "과일 주스 / 스무디", "가향 우유 (초코우유, 바나나우유 등)", "기타 당류 포함 액상"
]

# ==========================================
# 2. 데이터베이스 스키마 및 마이그레이션
# ==========================================
@st.cache_resource
def init_diet_db():
    conn = sqlite3.connect('my_diet.db', check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS user_profile (
        id INTEGER PRIMARY KEY, gender TEXT, age INTEGER, height REAL, weight REAL, target_weight REAL,
        activity_level TEXT, exercise_type TEXT, target_calories INTEGER, target_carb INTEGER, target_protein INTEGER, target_fat INTEGER,
        meal_count TEXT, first_meal_hr TEXT, last_meal_hr TEXT, water_unit TEXT, water_cnt REAL, bev_type TEXT, bev_unit TEXT, bev_cnt REAL,
        carb_type TEXT, snack_type TEXT, snack_freq TEXT, snack_time TEXT, snack_amt TEXT, sleep_bed_hr TEXT, sleep_wake_hr TEXT, last_period_date TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS daily_habits (
        date TEXT PRIMARY KEY, bed_time TEXT, wake_time TEXT, water_unit TEXT, water_amt REAL, bev_name TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS beverage_logs (
        id INTEGER PRIMARY KEY, date TEXT, bev_name TEXT, amount REAL, unit TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS exercise_logs (
        id INTEGER PRIMARY KEY, date TEXT, ex_name TEXT, duration INTEGER, calories_burned INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS diet_logs (
        id INTEGER PRIMARY KEY, date TEXT, meal_type TEXT, menu_name TEXT, calories REAL DEFAULT 0, carb REAL DEFAULT 0, 
        protein REAL DEFAULT 0, fat REAL DEFAULT 0, sugar REAL DEFAULT 0, sat_fat REAL DEFAULT 0, trans_fat REAL DEFAULT 0, 
        sodium REAL DEFAULT 0, fiber REAL DEFAULT 0, meal_time TEXT, meal_end_time TEXT, quality TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS daily_weight (id INTEGER PRIMARY KEY, date TEXT, weight REAL)''')
    conn.commit()
    return conn

conn = init_diet_db()

def sync_from_sheets(conn):
    client = get_gsheet_client()
    if not client: return False
    try: sheet = client.open("my_diet_db")
    except: return False
    
    tables = ['user_profile', 'daily_habits', 'beverage_logs', 'exercise_logs', 'diet_logs', 'daily_weight']
    success = False
    for t in tables:
        try:
            ws = sheet.worksheet(t)
            records = ws.get_all_records()
            if records:
                df = pd.DataFrame(records)
                c = conn.cursor()
                c.execute(f"DELETE FROM {t}")
                df.to_sql(t, conn, if_exists='append', index=False)
                success = True
        except: pass
    return success

def commit_and_sync(conn, table_names=None):
    conn.commit()
    client = get_gsheet_client()
    if not client: 
        return
    try: sheet = client.open("my_diet_db")
    except Exception: 
        return
    
    tables = table_names if table_names else ['user_profile', 'daily_habits', 'beverage_logs', 'exercise_logs', 'diet_logs', 'daily_weight']
    for t in tables:
        try: ws = sheet.worksheet(t)
        except: ws = sheet.add_worksheet(title=t, rows="100", cols="30")
        try:
            df = pd.read_sql(f"SELECT * FROM {t}", conn)
            ws.clear()
            if not df.empty:
                clean_df = df.fillna("").astype(str).replace(["nan", "NaN", "None", "<NA>"], "")
                data = [clean_df.columns.values.tolist()] + clean_df.values.tolist()
                try: ws.update(data)
                except: ws.update('A1', data)
        except: pass

if 'db_synced' not in st.session_state:
    with st.spinner("☁️ 클라우드 데이터베이스와 안전하게 동기화 중입니다..."):
        sync_from_sheets(conn)
        st.session_state.db_synced = True

c = conn.cursor()
c.execute("PRAGMA table_info(diet_logs)")
columns = [col[1] for col in c.fetchall()]
if "meal_end_time" not in columns:
    c.execute("ALTER TABLE diet_logs ADD COLUMN meal_end_time TEXT")
    conn.commit()

now = datetime.utcnow() + timedelta(hours=9)
today_str = now.strftime("%Y-%m-%d")
wd_map = {0:'월', 1:'화', 2:'수', 3:'목', 4:'금', 5:'토', 6:'일'}
date_display = f"{now.strftime('%y - %m - %d')} ( {wd_map[now.weekday()]} )"

def safe_get(val, default_val): return val if pd.notna(val) else default_val

# ==========================================
# 3. 진단 리포트 생성 함수 
# ==========================================
def generate_master_feedback(p):
    h = float(safe_get(p.get('height'), 160.0))
    w = float(safe_get(p.get('weight'), 60.0))
    t_w = float(safe_get(p.get('target_weight'), 55.0))
    a = int(safe_get(p.get('age'), 30))
    g = str(safe_get(p.get('gender'), '여성'))
    
    act = str(safe_get(p.get('activity_level'), '1단계 (주로 앉아서 생활)'))
    exc = str(safe_get(p.get('exercise_type'), '운동 안 함'))
    meal_cnt = str(safe_get(p.get('meal_count'), '3끼'))
    carb = str(safe_get(p.get('carb_type'), '다이어트 정식'))
    snack = str(safe_get(p.get('snack_type'), '안 먹음'))
    snack_freq = str(safe_get(p.get('snack_freq'), '안 먹음'))
    snack_time = str(safe_get(p.get('snack_time'), '없음'))
    snack_amt = str(safe_get(p.get('snack_amt'), '없음'))
    bed_hr = str(safe_get(p.get('sleep_bed_hr'), '23:30'))
    wake_hr = str(safe_get(p.get('sleep_wake_hr'), '07:00'))
    f_hr = str(safe_get(p.get('first_meal_hr'), '08:00'))
    l_hr = str(safe_get(p.get('last_meal_hr'), '19:00'))
    w_unit = str(safe_get(p.get('water_unit'), '잔'))
    w_cnt = float(safe_get(p.get('water_cnt'), 8.0))
    b_type = str(safe_get(p.get('bev_type'), '안 마심'))
    b_unit = str(safe_get(p.get('bev_unit'), '작은 캔'))
    b_cnt = float(safe_get(p.get('bev_cnt'), 1.0))
    
    h_m = h / 100
    bmr = (10 * w) + (6.25 * h) - (5 * a) + (5 if g == "남성" else -161)
    
    base_multi = 1.2
    if "2단계" in act: base_multi = 1.375
    elif "3단계" in act: base_multi = 1.55
    elif "4단계" in act: base_multi = 1.725
    
    if exc in ["고강도 웨이트/파워리프팅", "철인 3종/마라톤 훈련", "엘리트 체육/프로 선수 훈련", "인터벌 러닝/크로스핏"]: 
        base_multi += 0.1
    elif exc in ["웨이트 트레이닝 (머신/프리웨이트)", "격렬한 구기 종목 (축구, 농구 등)", "가벼운 조깅/러닝", "자전거/수영 (저강도)"]: 
        base_multi += 0.05
    
    tdee = bmr * base_multi
    deficit = 500 if w > t_w else 0
    target_cal = max(int(tdee - deficit), int(bmr) + 100)
    
    p_ratio = 1.8
    if "웨이트" in exc or "고강도" in exc or "크로스핏" in exc or "마라톤" in exc:
        p_ratio = 2.0
        
    protein_g = int(t_w * p_ratio) 
    fat_g = int((target_cal * 0.25) / 9)
    carb_g = int((target_cal - (protein_g * 4) - (fat_g * 9)) / 4)

    adv = f"<div class='report-title'>📌 Section 1. [ 체성분 및 활동 대사량 산출 ]</div>"
    adv += f"<div class='report-p'>현재 고객님의 기초대사량은 <b>{int(bmr)} kcal</b>입니다.<br><br><b>[{act}]</b> 활동량과 <b>[{exc}]</b> 훈련 종목을 반영한 일일 총 에너지 소모량(TDEE)은 <b>{int(tdee)} kcal</b>로 분석되었습니다.<br><br>목표 체중({t_w}kg) 도달을 위해 <b>1일 권장 섭취량을 {target_cal} kcal</b>로 설정합니다.</div>"
    return target_cal, carb_g, protein_g, fat_g, adv

# ==========================================
# 4. 앱 강제 라우팅 및 좌측 사이드바 마크다운 메뉴
# ==========================================
p_df = pd.read_sql("SELECT * FROM user_profile ORDER BY id DESC LIMIT 1", conn)
is_new_user = p_df.empty

if is_new_user:
    st.markdown("<h1>🥑 브쌤's Diet 일지</h1>", unsafe_allow_html=True)
    st.warning("⚠️ 최초 1회 [정밀 대사 진단]을 완료해야 앱 메뉴가 활성화됩니다.")
    menu = "⚙️ 정밀 대사 재진단"
else:
    p = p_df.iloc[0]
    st.sidebar.markdown("### 📌 메뉴 이동")
    menu_options = ["📝 일일 기록 (메인)", "📅 달력 조회", "📋 대사 진단 리포트", "⚙️ 정밀 대사 재진단"]
    menu = st.sidebar.radio("", menu_options, label_visibility="collapsed")

# ==========================================
# 5. 페이지 렌더링
# ==========================================

# ------------------------------------------
# [메뉴 1] 일일 기록 (기본 화면) 
# ------------------------------------------
if menu == "📝 일일 기록 (메인)":
    st.markdown("<h1>🥑 브쌤's Diet 일지</h1>", unsafe_allow_html=True)
    st.markdown(f"<div class='date-display'>{date_display}</div>", unsafe_allow_html=True)
    
    # [수정됨] NaN, None 등의 결측치 문자를 완벽하게 잡아내어 무조건 식사 중으로 인식하게 함
    c.execute("SELECT date, meal_time, meal_end_time, menu_name FROM diet_logs ORDER BY date DESC, meal_time DESC, id DESC LIMIT 1")
    latest_meal = c.fetchone()
    
    if latest_meal:
        lm_date, lm_start, lm_end, lm_name = latest_meal
        if not lm_end or str(lm_end).strip() == "" or str(lm_end).strip().lower() in ["nan", "none", "null"]:
            st.markdown(f"""
            <div class='status-dashboard status-eating'>
                <div class='status-title'>🍽️ 현재 식사 중입니다: {lm_name}</div>
                <div class='status-time'>시작: {lm_start}</div>
                <div class='status-msg'>식사를 마치셨다면 [📅 달력 조회] 탭에서 '식사 종료' 버튼을 눌러주세요.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            try:
                last_dt = datetime.strptime(f"{lm_date} {lm_end}", "%Y-%m-%d %H:%M")
                fasting_delta = now - last_dt
                f_hours = int(fasting_delta.total_seconds() // 3600)
                f_mins = int((fasting_delta.total_seconds() % 3600) // 60)
                
                if f_hours >= 12: f_msg = "🔥 췌장 휴식 완료! 체지방 연소 모드 진입"
                elif f_hours >= 4: f_msg = "🟢 인슐린 안정화 구간"
                elif f_hours < 0: f_hours, f_mins, f_msg = 0, 0, "🟡 음식물 소화 및 혈당 처리 중"
                else: f_msg = "🟡 음식물 소화 및 혈당 처리 중"
                
                st.markdown(f"""
                <div class='status-dashboard status-fasting'>
                    <div class='status-title'>마지막 식사로부터 공복 유지</div>
                    <div class='status-time'>{f_hours}시간 {f_mins}분 째</div>
                    <div class='status-msg'>{f_msg}</div>
                </div>
                """, unsafe_allow_html=True)
            except:
                st.markdown(f"<div class='status-dashboard status-wait'><div class='status-title'>타이머 대기 중</div><div class='status-msg'>시간 기록 오류.</div></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='status-dashboard status-wait'><div class='status-title'>타이머 대기 중</div><div class='status-msg'>식사 기록이 없습니다. 첫 식사를 기록해주세요.</div></div>", unsafe_allow_html=True)

    # --- 서브 탭 영역 ---
    tab_list = ["🥗 식단 기록", "⏰ 습관", "🏋️ 운동", "📉 체중"]
    if p.get('gender') == '여성': tab_list.append("🩸 주기")
    tabs = st.tabs(tab_list)
    
    with tabs[0]: 
        st.markdown("##### 🍽️ 새로운 식사 시작 (입력)")
        
        col_t1, col_t2 = st.columns(2)
        with col_t1: 
            user_start_time = st.text_input("식사 시작 시각 (예: 12:00)", value=now.strftime("%H:%M"))
        with col_t2: 
            meal_type = st.selectbox("식사 구분", ["아침", "점심", "저녁", "간식", "야식"])

        if 'camera_on' not in st.session_state: st.session_state.camera_on = False
        if 'ai_menu' not in st.session_state:
            st.session_state.ai_menu = ""
            st.session_state.ai_calories = 0
            for k in ['carb', 'protein', 'fat', 'sugar', 'sat_fat', 'trans_fat', 'sodium', 'fiber']: st.session_state[f'ai_{k}'] = 0
            st.session_state.ai_quality = "좋은 음식"
            
        col_btn, _ = st.columns([1, 1])
        with col_btn:
            if not st.session_state.camera_on:
                if st.button("📷 스마트 카메라 켜기"):
                    st.session_state.camera_on = True
                    st.rerun()
            else:
                if st.button("❌ 카메라 닫기"):
                    st.session_state.camera_on = False
                    st.rerun()
                    
        if st.session_state.camera_on:
            uploaded_file = st.camera_input("알아서 인식합니다", label_visibility="collapsed")
            if uploaded_file is not None:
                if st.button("🔍 AI 심층 영양소 분석"):
                    if not GEMINI_API_KEY: st.error("API 금고가 비어있습니다.")
                    else:
                        with st.spinner("AI가 질감과 재료의 다각적 변수를 분석 중입니다..."):
                            try:
                                genai.configure(api_key=GEMINI_API_KEY)
                                model = genai.GenerativeModel('gemini-3.6-flash')
                                
                                prompt = '''너는 수십 년 경력의 임상 영양학자이자 AI 데이터 분석가야.
                                사진이나 제품 패키지를 보고 아래의 [필수 사고 과정] 1~7단계를 반드시 내재적으로 거친 후, 8단계의 JSON 결과만 출력해.

                                [필수 사고 과정]
                                1. 단계별 필수 추론: 음식의 카테고리(예: 빙과류인지, 우유가 섞인 아이스밀크인지, 튀김인지 구이인지)와 주요 원재료의 질감을 확정하라.
                                2. 값의 다각화: 사진 표면에 드러나지 않는 이면의 재료(소스 내 당류, 식용유, 첨가물, 보존제 비율)를 폭넓게 추정하라.
                                3. 변수들의 연결: 1단계의 주원료 카테고리와 2단계의 숨은 요소가 결합될 때 발생하는 매크로(탄/단/지) 파이를 연결하라.
                                4. 통합화: 위 과정을 통해 1차 총 칼로리 및 기본 영양소 구성비를 구성하라.
                                5. 오차 발생 변수 특정: 이 식품군에서 영양소 오차를 가장 크게 유발할 핵심 변수 1~2개 찾아내라.
                                6. 변수값 중앙값(Median) 부여: 5단계 변수의 최소치와 최대치를 가늠하고, 그 절대적인 중간값(Median)을 실제 적용 값으로 확정하라. 단백질과 식이섬유는 보수적으로 낮게 잡고, 지방과 당류는 카테고리에 맞춰 정밀하게 반영할 것.
                                7. 재통합화: 6단계의 중간값을 토대로 칼로리와 탄/단/지/당류 등의 최종 수치를 현실적이고 논리적으로 밸런스를 맞춰 재조정하라.
                                8. 결과값 표시: 도출된 최종 수치를 바탕으로 마크다운 기호(```json) 없이 오직 아래 형식의 순수 JSON 데이터만 출력하라.

                                {"name": "음식명", "calories": 0, "carb": 0, "protein": 0, "fat": 0, "sugar": 0, "sat_fat": 0, "trans_fat": 0, "sodium": 0, "fiber": 0, "quality": "좋은 음식/주의 음식/위험 음식"}'''
                                
                                img = Image.open(uploaded_file)
                                response = model.generate_content([prompt, img])
                                
                                result_text = response.text
                                start_idx, end_idx = result_text.find('{'), result_text.rfind('}')
                                if start_idx != -1 and end_idx != -1:
                                    ai_data = json.loads(result_text[start_idx:end_idx+1])
                                    st.session_state.ai_menu = ai_data.get("name", "")
                                    st.session_state.ai_calories = float(ai_data.get("calories", 0))
                                    for k in ['carb', 'protein', 'fat', 'sugar', 'sat_fat', 'trans_fat', 'sodium', 'fiber']:
                                        st.session_state[f'ai_{k}'] = float(ai_data.get(k, 0))
                                    st.session_state.ai_quality = ai_data.get("quality", "좋은 음식")
                                    st.success(f"✅ 정밀 분석 완료! (메뉴: {st.session_state.ai_menu})")
                                else: st.error("데이터 인식 실패.")
                            except Exception as e: st.error(f"통신 에러: {e}")

        with st.expander("✍️ 수동 입력 및 추출된 영양성분 확인", expanded=True):
            with st.form("diet_tracking_form"):
                c01, c02 = st.columns(2)
                with c01: menu_name = st.text_input("메뉴 이름", st.session_state.ai_menu)
                with c02: calories_v = st.text_input("총 칼로리(kcal)", value=str(st.session_state.ai_calories))
                
                c1, c2, c3 = st.columns(3)
                with c1: carb_v = st.text_input("탄수화물(g)", value=str(st.session_state.ai_carb))
                with c2: protein_v = st.text_input("단백질(g)", value=str(st.session_state.ai_protein))
                with c3: fat_v = st.text_input("지방(g)", value=str(st.session_state.ai_fat))
                
                c4, c5, c6 = st.columns(3)
                with c4: sugar_v = st.text_input("당류(g)", value=str(st.session_state.ai_sugar))
                with c5: sodium_v = st.text_input("나트륨(mg)", value=str(st.session_state.ai_sodium))
                with c6: fiber_v = st.text_input("식이섬유(g)", value=str(st.session_state.ai_fiber))
                
                sat_fat_v = st.session_state.ai_sat_fat
                trans_fat_v = st.session_state.ai_trans_fat
                
                if st.form_submit_button("식단 기록 시작 (클라우드 임시저장)", type="primary"):
                    try:
                        cal = float(calories_v)
                        carb, protein, fat = float(carb_v), float(protein_v), float(fat_v)
                        sugar, sodium, fiber = float(sugar_v), float(sodium_v), float(fiber_v)
                        
                        m_name = menu_name.strip() if menu_name.strip() else "직접 입력 식단"
                        q = st.session_state.ai_quality
                        
                        c.execute('SELECT id FROM diet_logs WHERE date=? AND meal_time=? AND menu_name=?', (today_str, user_start_time.strip(), m_name))
                        if c.fetchone():
                            st.error("⚠️ 방금 동일한 시간과 메뉴로 기록된 데이터가 있습니다. (중복 클릭 방지)")
                        else:
                            c.execute('INSERT INTO diet_logs (date, meal_type, menu_name, calories, carb, protein, fat, sugar, sat_fat, trans_fat, sodium, fiber, meal_time, meal_end_time, quality) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                                      (today_str, meal_type, m_name, cal, carb, protein, fat, sugar, sat_fat_v, trans_fat_v, sodium, fiber, user_start_time.strip(), "", q))
                            
                            conn.commit()
                            commit_and_sync(conn, ['diet_logs'])
                            
                            st.session_state.ai_menu = ""
                            st.session_state.ai_calories = 0
                            for k in ['carb', 'protein', 'fat', 'sugar', 'sat_fat', 'trans_fat', 'sodium', 'fiber']: st.session_state[f'ai_{k}'] = 0
                            
                            st.session_state.meal_start_success = True
                            st.rerun() 
                    except ValueError: 
                        st.error("수치는 반드시 숫자만 입력해주세요.")
            
            if st.session_state.get("meal_start_success"):
                st.success("✅ 저장이 완료되었습니다! 편안한 식사 후 [📅 달력 조회] 탭에서 '식사 종료' 버튼을 눌러주세요.")
                st.session_state.meal_start_success = False

    with tabs[1]: 
        if 'habit_msg' in st.session_state:
            st.success(st.session_state.habit_msg)
            del st.session_state.habit_msg
            
        w_df = pd.read_sql(f"SELECT * FROM daily_habits WHERE date='{today_str}'", conn)
        curr_w = w_df.iloc[0]['water_amt'] if not w_df.empty and pd.notna(w_df.iloc[0]['water_amt']) else 0.0
        curr_w_un = w_df.iloc[0]['water_unit'] if not w_df.empty and pd.notna(w_df.iloc[0]['water_unit']) else "잔"
        curr_bed = w_df.iloc[0]['bed_time'] if not w_df.empty and pd.notna(w_df.iloc[0]['bed_time']) else ""
        curr_wake = w_df.iloc[0]['wake_time'] if not w_df.empty and pd.notna(w_df.iloc[0]['wake_time']) else ""
        
        st.markdown("### ⏰ 습관 데이터 누적 기록")
        st.markdown("##### 💧 수분 즉시 추가")
        st.info(f"**오늘 누적 생수:** {curr_w} 단위")
        col_w1, col_w2 = st.columns(2)
        with col_w1:
            if st.button("💧 작은 컵 (+1)", use_container_width=True):
                if w_df.empty: c.execute(f"INSERT INTO daily_habits (date, water_unit, water_amt) VALUES ('{today_str}', '잔', 1.0)")
                else: c.execute(f"UPDATE daily_habits SET water_amt = coalesce(water_amt, 0) + 1.0 WHERE date='{today_str}'")
                conn.commit() 
                st.session_state.habit_msg = "💧 생수 1단위가 로컬에 추가되었습니다."
                st.rerun()
        with col_w2:
            if st.button("💧 큰 컵 (+2)", use_container_width=True):
                if w_df.empty: c.execute(f"INSERT INTO daily_habits (date, water_unit, water_amt) VALUES ('{today_str}', '잔', 2.0)")
                else: c.execute(f"UPDATE daily_habits SET water_amt = coalesce(water_amt, 0) + 2.0 WHERE date='{today_str}'")
                conn.commit() 
                st.session_state.habit_msg = "💧 생수 2단위가 로컬에 추가되었습니다."
                st.rerun()
                
        st.markdown("<hr style='margin:15px 0;'>", unsafe_allow_html=True)
        st.markdown("##### ☕ 음료 카테고리 누적")
        selected_b_name = st.selectbox("마신 음료 분류 선택", BEV_CATEGORIES)
        
        b_df = pd.read_sql(f"SELECT * FROM beverage_logs WHERE date='{today_str}' AND bev_name='{selected_b_name}'", conn)
        curr_b_amt = b_df.iloc[0]['amount'] if not b_df.empty else 0.0
        curr_b_un = b_df.iloc[0]['unit'] if not b_df.empty else "작은 캔"
        st.warning(f"**[{selected_b_name}] 오늘 누적량:** {curr_b_amt} 단위")
        
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("☕ 작은 캔 (+1)", use_container_width=True):
                if b_df.empty: c.execute(f"INSERT INTO beverage_logs (date, bev_name, amount, unit) VALUES ('{today_str}', '{selected_b_name}', 1.0, '작은 캔')")
                else: c.execute(f"UPDATE beverage_logs SET amount = amount + 1.0 WHERE id={b_df.iloc[0]['id']}")
                conn.commit() 
                st.session_state.habit_msg = f"☕ [{selected_b_name}] 1단위가 로컬에 추가되었습니다."
                st.rerun()
        with col_b2:
            if st.button("☕ 큰 캔 (+2)", use_container_width=True):
                if b_df.empty: c.execute(f"INSERT INTO beverage_logs (date, bev_name, amount, unit) VALUES ('{today_str}', '{selected_b_name}', 2.0, '큰 캔')")
                else: c.execute(f"UPDATE beverage_logs SET amount = amount + 2.0 WHERE id={b_df.iloc[0]['id']}")
                conn.commit() 
                st.session_state.habit_msg = f"☕ [{selected_b_name}] 2단위가 로컬에 추가되었습니다."
                st.rerun()

        st.markdown("<hr style='margin:15px 0;'>", unsafe_allow_html=True)
        with st.form("habit_tracker_form"):
            st.markdown("##### 🛠️ 습관 데이터 수기 변경 및 일괄 수정")
            ch1, ch2 = st.columns(2)
            with ch1: bed_t_str = st.text_input("취침 시간 (미입력 시 비워두기)", value=curr_bed)
            with ch2: wake_t_str = st.text_input("기상 시간", value=curr_wake)
            
            cw1, cw2 = st.columns(2)
            w_idx = ["잔", "컵", "리터(L)"].index(curr_w_un) if curr_w_un in ["잔", "컵", "리터(L)"] else 0
            with cw1: w_unit = st.selectbox("생수 단위 (전체)", ["잔", "컵", "리터(L)"], index=w_idx)
            with cw2: water_manual_str = st.text_input("생수 총 섭취량 (수기 조작)", value=str(curr_w))
            
            cb1, cb2 = st.columns(2)
            b_idx = ["잔", "작은 캔", "큰 캔"].index(curr_b_un) if curr_b_un in ["잔", "작은 캔", "큰 캔"] else 0
            with cb1: b_unit = st.selectbox(f"[{selected_b_name}] 단위", ["잔", "작은 캔", "큰 캔"], index=b_idx)
            with cb2: bev_manual_str = st.text_input(f"[{selected_b_name}] 섭취량 (수기 조작)", value=str(curr_b_amt))
            
            if st.form_submit_button("로컬 데이터베이스 업데이트"):
                try:
                    w_man_amt = float(water_manual_str)
                    b_man_amt = float(bev_manual_str)
                    
                    c.execute(f"SELECT date FROM daily_habits WHERE date='{today_str}'")
                    if c.fetchone():
                        c.execute(f"""UPDATE daily_habits SET bed_time='{bed_t_str}', wake_time='{wake_t_str}', water_unit='{w_unit}', water_amt={w_man_amt} WHERE date='{today_str}'""")
                    else:
                        c.execute(f"""INSERT INTO daily_habits (date, bed_time, wake_time, water_unit, water_amt) VALUES ('{today_str}', '{bed_t_str}', '{wake_t_str}', '{w_unit}', {w_man_amt})""")
                    
                    if b_man_amt > 0:
                        if b_df.empty: c.execute(f"INSERT INTO beverage_logs (date, bev_name, amount, unit) VALUES ('{today_str}', '{selected_b_name}', {b_man_amt}, '{b_unit}')")
                        else: c.execute(f"UPDATE beverage_logs SET amount={b_man_amt}, unit='{b_unit}' WHERE id={b_df.iloc[0]['id']}")
                    elif b_man_amt == 0 and not b_df.empty:
                        c.execute(f"DELETE FROM beverage_logs WHERE id={b_df.iloc[0]['id']}")
                        
                    conn.commit() 
                    st.success("로컬 데이터베이스에 완벽히 업데이트되었습니다!")
                except ValueError:
                    st.error("섭취량은 숫자만 입력해야 합니다.")

    with tabs[2]: 
        st.markdown("### 🏋️ 운동 기록 및 실시간 타이머")
        st.info("운동 종목을 먼저 선택한 후 타이머를 돌리거나, 아래 폼에서 수동으로 시간을 직접 기입하세요.")
        
        ex_options = {"걷기/산책 (MET 3.8)": 3.8, "자전거/수영 (MET 7.0)": 7.0, "러닝/조깅 (MET 8.0)": 8.0, "웨이트 트레이닝 (MET 5.0)": 5.0, "요가/스트레칭 (MET 3.0)": 3.0, "천국의 계단/스텝밀 (MET 9.0)": 9.0}
        
        if 'active_ex_name' not in st.session_state: st.session_state.active_ex_name = list(ex_options.keys())[0]
        selected_ex = st.selectbox("1️⃣ 수행할 운동 종목 선택", list(ex_options.keys()), index=list(ex_options.keys()).index(st.session_state.active_ex_name))
        st.session_state.active_ex_name = selected_ex
        
        st.markdown("##### 2️⃣ 실시간 타이머 가동")
        if 'ex_start' not in st.session_state: st.session_state.ex_start = None
        if 'ex_mins' not in st.session_state: st.session_state.ex_mins = 0
        
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            if st.button("▶️ 타이머 시작", use_container_width=True):
                st.session_state.ex_start = datetime.now()
                st.rerun()
        with t_col2:
            if st.button("⏹️ 타이머 종료", use_container_width=True):
                if st.session_state.ex_start:
                    diff = datetime.now() - st.session_state.ex_start
                    st.session_state.ex_mins = max(1, int(diff.total_seconds() / 60))
                    st.session_state.ex_start = None
                    st.rerun()
                else: st.warning("진행 중인 타이머가 없습니다.")
                    
        if st.session_state.ex_start:
            st.success(f"🏃 [{st.session_state.active_ex_name}] 진행 중... (시작: {st.session_state.ex_start.strftime('%H:%M')})")
        
        st.markdown("<hr style='margin:15px 0;'>", unsafe_allow_html=True)

        with st.form("exercise_tracker"):
            st.markdown("##### 3️⃣ 시간 확정 및 저장")
            ex_min_str = st.text_input("수행한 운동 시간 (분)", value=str(st.session_state.ex_mins if st.session_state.ex_mins > 0 else 30))
            
            if st.form_submit_button("로컬 데이터베이스 저장"):
                try:
                    ex_min = int(ex_min_str)
                    met = ex_options[st.session_state.active_ex_name]
                    user_w = float(safe_get(p.get('weight'), 60.0))
                    burned_cal = int((met * 3.5 * user_w * ex_min) / 200)
                    
                    c.execute("INSERT INTO exercise_logs (date, ex_name, duration, calories_burned) VALUES (?, ?, ?, ?)", (today_str, st.session_state.active_ex_name.split(' (')[0], ex_min, burned_cal))
                    conn.commit() 
                    st.session_state.ex_mins = 0
                    st.success(f"🔥 총 {burned_cal}kcal 소모 기록 완료!")
                except ValueError: st.error("숫자만 입력해주세요.")

    with tabs[3]:
        st.markdown("##### 📉 오늘의 체중 입력")
        curr_w_df = pd.read_sql(f"SELECT weight FROM daily_weight WHERE date='{today_str}'", conn)
        default_w = str(curr_w_df.iloc[0]['weight']) if not curr_w_df.empty else str(p.get('weight', 60.0))
        
        with st.form("weight_form_main"):
            today_w_str = st.text_input("체중 (kg)", value=default_w)
            if st.form_submit_button("로컬 데이터베이스 업데이트"):
                try:
                    today_w = float(today_w_str)
                    c.execute(f"SELECT id FROM daily_weight WHERE date='{today_str}'")
                    if c.fetchone():
                        c.execute(f"UPDATE daily_weight SET weight = {today_w} WHERE date='{today_str}'")
                    else:
                        c.execute(f"INSERT INTO daily_weight (date, weight) VALUES ('{today_str}', {today_w})")
                        
                    if not is_new_user:
                        c.execute(f"UPDATE user_profile SET weight = {today_w} WHERE id = {p['id']}")
                    conn.commit() 
                    st.success("로컬에 안전하게 저장되었습니다.")
                except ValueError: st.error("숫자만 입력해주세요.")

    if len(tabs) == 5: 
        with tabs[4]:
            st.markdown("##### 🩸 주기 업데이트")
            with st.form("period_tracker"):
                last_p_date = st.text_input("최근 생리 시작일 (예: 2026-08-01)", value=str(safe_get(p.get('last_period_date'), "")))
                if st.form_submit_button("로컬 저장"):
                    try:
                        valid_date = datetime.strptime(last_p_date.strip(), "%Y-%m-%d")
                        c.execute(f"UPDATE user_profile SET last_period_date = '{last_p_date}' WHERE id = {p['id']}")
                        conn.commit() 
                        st.success("저장 완료.")
                    except ValueError: st.error("날짜 형식을 맞춰주세요.")

# ------------------------------------------
# [메뉴 2] 📅 달력 조회 (데이터베이스 통합본)
# ------------------------------------------
elif menu == "📅 달력 조회":
    st.markdown("<h1>🥑 브쌤's Diet 일지</h1>", unsafe_allow_html=True)
    
    selected_date = st.date_input("📅 조회할 데이터베이스 날짜를 선택하세요", value=now.date())
    view_date_str = selected_date.strftime("%Y-%m-%d")
    
    st.markdown(f"<div class='report-title'>📊 [{view_date_str}] 클라우드 데이터 종합 내역</div>", unsafe_allow_html=True)
    
    start_date = selected_date - timedelta(days=6)
    start_str = start_date.strftime("%Y-%m-%d")
    
    try:
        week_logs = pd.read_sql(f"SELECT date, SUM(calories) as cal, SUM(protein) as p FROM diet_logs WHERE date BETWEEN '{start_str}' AND '{view_date_str}' GROUP BY date", conn)
        avg_cal = int(week_logs['cal'].fillna(0).mean()) if not week_logs.empty else 0
        avg_p = int(week_logs['p'].fillna(0).mean()) if not week_logs.empty else 0
    except:
        avg_cal = 0
        avg_p = 0
    
    st.markdown(f"""
    <div class='trend-box'>
        <div style='font-size:1.1rem; font-weight:900; color:#2C3E50; margin-bottom:5px;'>📈 주간 대사 트렌드 (최근 7일 평균)</div>
        <b>🔥 일평균 섭취 칼로리:</b> {avg_cal} kcal <br>
        <b>💪 일평균 단백질 섭취:</b> {avg_p} g <br>
        <span style='font-size:0.9rem; color:#7F8C8D; margin-top:8px; display:block;'>※ 다이어트의 성패는 하루의 오차가 아닌 주간 평균이 결정합니다. 트렌드를 지속 모니터링하세요.</span>
    </div>
    """, unsafe_allow_html=True)
    
    t_cal_base, t_c_base, t_p_base, t_f_base, _ = generate_master_feedback(p)
    
    ex_df = pd.read_sql(f"SELECT * FROM exercise_logs WHERE date='{view_date_str}'", conn)
    burned_cal = ex_df['calories_burned'].sum() if not ex_df.empty else 0
    
    t_cal = t_cal_base + burned_cal
    t_c = t_c_base + int((burned_cal * 0.6) / 4)
    t_p = t_p_base + int((burned_cal * 0.4) / 4)
    t_f = t_f_base
    
    try:
        # 👉 SELECT rowid as db_rowid, * 로 변경하여 숨겨진 절대 고유번호를 강제로 가져옵니다.
        logs = pd.read_sql(f"SELECT rowid as db_rowid, * FROM diet_logs WHERE date='{view_date_str}'", conn)
        e_cal = logs['calories'].sum() if not logs.empty and 'calories' in logs.columns else 0
        e_c = logs['carb'].sum() if not logs.empty and 'carb' in logs.columns else 0
        e_p = logs['protein'].sum() if not logs.empty and 'protein' in logs.columns else 0
        e_f = logs['fat'].sum() if not logs.empty and 'fat' in logs.columns else 0
        e_sodium = logs['sodium'].sum() if not logs.empty and 'sodium' in logs.columns else 0
        e_fiber = logs['fiber'].sum() if not logs.empty and 'fiber' in logs.columns else 0
    except:
        logs = pd.DataFrame()
        e_cal, e_c, e_p, e_f, e_sodium, e_fiber = 0, 0, 0, 0, 0, 0
    
    diff_cal = t_cal - e_cal
    cal_class = "status-green" if diff_cal >= 0 else "status-red"
    
    if burned_cal > 0:
        st.info(f"🏋️ 해당 일자에 운동으로 **{int(burned_cal)}kcal**를 추가 소모하여 목표 허용량이 재설정되었습니다.")
    
    st.markdown("##### 🎯 칼로리 및 매크로 섭취 결과")
    st.markdown(f"<div class='macro-box {cal_class}'><div class='macro-title'>목표 {t_cal} kcal ── 섭취 {int(e_cal)} kcal</div><div class='macro-val'>{'잔여: +' + str(int(diff_cal)) if diff_cal >= 0 else '초과: ' + str(int(abs(diff_cal)))} kcal</div></div>", unsafe_allow_html=True)
    
    def get_macro_html(name, target, eaten):
        diff = target - eaten
        c_class = "status-green" if diff >= 0 else "status-red"
        d_txt = f"+ {int(diff)}g 잔여" if diff >= 0 else f"{int(abs(diff))}g 초과"
        return f"<div class='macro-box {c_class}'><div class='macro-title'>{name}</div><div style='font-size:0.8rem; color:#7F8C8D;'>기준: {int(target)}g</div><div class='macro-val'>{int(eaten)}g</div><div class='macro-diff'>{d_txt}</div></div>"
        
    st.markdown(f"<div class='dashboard-grid'>{get_macro_html('탄수화물', t_c, e_c)}{get_macro_html('단백질', t_p, e_p)}{get_macro_html('지방', t_f, e_f)}</div>", unsafe_allow_html=True)
    
    st.markdown(f"<div class='micro-box'>🔬 <b>미량 영양소 추적:</b> 나트륨 <b>{int(e_sodium)}mg</b> (권장 2000mg 이하) &nbsp; | &nbsp; 식이섬유 <b>{int(e_fiber)}g</b> (권장 25g 이상)</div>", unsafe_allow_html=True)

    c.execute(f"SELECT id, menu_name, meal_time FROM diet_logs WHERE date='{view_date_str}' AND (meal_end_time IS NULL OR meal_end_time = '' OR LOWER(meal_end_time) IN ('nan', 'none', 'null')) ORDER BY id DESC LIMIT 1")
    active_meal = c.fetchone()
    
    st.markdown("##### 🍽 식단 기록 목록")
    if active_meal:
        am_id, am_name, am_start = active_meal
        st.markdown(f"<div style='background:#FFF3CD; padding:8px 12px; border-radius:6px; border-left:4px solid #F1C40F; margin-bottom:12px;'><span style='font-size:0.9rem; font-weight:bold; color:#7D6608;'>⏳ 현재 진행 중: {am_name} (시작: {am_start} ~ )</span></div>", unsafe_allow_html=True)

    table_html = "<table class='diet-table'><tr><th style='width:25%;'>시간</th><th style='width:50%;'>메뉴</th><th style='width:25%;'>평가</th></tr>"
    if logs.empty: table_html += "<tr><td colspan='3' style='color:#7F8C8D; padding:20px 0;'>기록된 식단이 없습니다.</td></tr>"
    else:
        for idx, row in logs.iterrows():
            q = str(row['quality'])
            if "좋은" in q: badge = "<span class='badge' style='background:#D5F5E3; color:#1E8449;'>🟢 좋은 음식</span>"
            elif "주의" in q: badge = "<span class='badge' style='background:#FCF3CF; color:#D4AC0D;'>🟡 주의 음식</span>"
            else: badge = "<span class='badge' style='background:#FADBD8; color:#C0392B;'>🚨 위험 음식</span>"
            
            if pd.notna(row['meal_end_time']) and str(row['meal_end_time']).strip() != "" and str(row['meal_end_time']).strip().lower() not in ["nan", "none", "null"]:
                end_t = f"~ {row['meal_end_time']}"
            else:
                end_t = "<span style='color:#E74C3C;'>(식사 중)</span>"
                
            table_html += f"<tr><td><b>{row['meal_time']}</b><br><span style='font-size:0.75rem; color:#7F8C8D;'>{end_t}</span></td><td><b style='color:#2C3E50;'>{row['menu_name']}</b></td><td>{badge}</td></tr>"
    table_html += "</table>"
    st.markdown(table_html, unsafe_allow_html=True)
    
    if active_meal:
        col_blank, col_end_btn = st.columns([7, 3])
        with col_end_btn:
            if st.button("🏁 식사 종료", key="end_meal_btn_bottom", type="primary", use_container_width=True):
                now_str = now.strftime("%H:%M")
                c.execute("UPDATE diet_logs SET meal_end_time=? WHERE id=?", (now_str, am_id))
                conn.commit()
                commit_and_sync(conn, ['diet_logs', 'daily_habits', 'beverage_logs', 'exercise_logs', 'daily_weight'])
                st.session_state.meal_end_success = True
                st.rerun()

    if st.session_state.get("meal_end_success"):
        st.success("✅ 식사가 종료 되었습니다. 공복 타이머가 가동됩니다.")
        st.session_state.meal_end_success = False
    
    if not logs.empty:
        with st.expander("🛠️ 식단 삭제하기"):
            with st.form("delete_diet_form"):
                # 👉 빈 칸이 될 수 있는 id 대신 절대 고유번호인 db_rowid 사용
                del_options = {f"[{row['meal_time']}] {row['menu_name']} (고유번호: {row['db_rowid']})": row['db_rowid'] for idx, row in logs.iterrows()}
                selected_del_key = st.selectbox("삭제할 식단 선택", options=list(del_options.keys()))
                if st.form_submit_button("영구 삭제"):
                    # 👉 id가 아닌 rowid를 기준으로 삭제
                    c.execute("DELETE FROM diet_logs WHERE rowid = ?", (del_options[selected_del_key],))
                    commit_and_sync(conn, ['diet_logs'])
                    st.rerun()

    st.markdown("##### 🏃 운동 기록 목록")
    ex_table = "<table class='diet-table'><tr><th style='width:50%;'>운동 종목</th><th style='width:25%;'>시간</th><th style='width:25%;'>소모량</th></tr>"
    if ex_df.empty: ex_table += "<tr><td colspan='3' style='color:#7F8C8D; padding:20px 0;'>기록된 운동이 없습니다.</td></tr>"
    else:
        for idx, row in ex_df.iterrows():
            ex_table += f"<tr><td><b style='color:#2C3E50;'>{row['ex_name']}</b></td><td><b>{row['duration']}</b>분</td><td><span class='badge' style='background:#FADBD8; color:#C0392B;'>🔥 {row['calories_burned']}</span></td></tr>"
    ex_table += "</table>"
    st.markdown(ex_table, unsafe_allow_html=True)
    
    if not ex_df.empty:
        with st.expander("🛠️ 운동 기록 삭제하기"):
            with st.form("delete_ex_form"):
                ex_del_opts = {f"{row['ex_name']} ({row['duration']}분)": row['id'] for idx, row in ex_df.iterrows()}
                selected_ex_key = st.selectbox("삭제할 운동 선택", options=list(ex_del_opts.keys()))
                if st.form_submit_button("영구 삭제"):
                    c.execute("DELETE FROM exercise_logs WHERE id = ?", (ex_del_opts[selected_ex_key],))
                    commit_and_sync(conn, ['exercise_logs'])
                    st.rerun()

    st.markdown("##### 📋 습관 및 체중 피드백")
    habit_df = pd.read_sql(f"SELECT * FROM daily_habits WHERE date='{view_date_str}'", conn)
    bev_df = pd.read_sql(f"SELECT * FROM beverage_logs WHERE date='{view_date_str}'", conn)
    
    habit_table = "<table class='diet-table'><tr><th style='width:25%;'>항목</th><th style='width:20%;'>상태</th><th style='width:55%;'>전문가 피드백</th></tr>"
    
    if not habit_df.empty:
        h_row = habit_df.iloc[0]
        bed_str = h_row['bed_time'] if pd.notna(h_row['bed_time']) else ""
        wake_str = h_row['wake_time'] if pd.notna(h_row['wake_time']) else ""
        w_amt = h_row['water_amt'] if pd.notna(h_row['water_amt']) else 0.0
        w_un = h_row['water_unit'] if pd.notna(h_row['water_unit']) else "잔"
        
        if bed_str and wake_str:
            try:
                t_b, t_w = datetime.strptime(bed_str.strip(), "%H:%M"), datetime.strptime(wake_str.strip(), "%H:%M")
                sleep_mins = (t_w.hour * 60 + t_w.minute) - (t_b.hour * 60 + t_b.minute)
                if sleep_mins < 0: sleep_mins += 24 * 60
                sleep_hrs = round(sleep_mins / 60, 1)
                
                if sleep_hrs >= 7.0: s_badge, s_msg = "<span class='badge' style='background:#D5F5E3; color:#1E8449;'>🟢 적정</span>", f"{sleep_hrs}시간 수면, 회복 양호"
                elif sleep_hrs >= 6.0: s_badge, s_msg = "<span class='badge' style='background:#FCF3CF; color:#D4AC0D;'>🟡 주의</span>", f"{sleep_hrs}시간 수면, 대사 저하 우려"
                else: s_badge, s_msg = "<span class='badge' style='background:#FADBD8; color:#C0392B;'>🚨 위험</span>", f"{sleep_hrs}시간 수면, 코르티솔 위험"
                habit_table += f"<tr><td><b>수면</b><br><span style='font-size:0.75rem; color:#7F8C8D;'>{bed_str}~{wake_str}</span></td><td>{s_badge}</td><td style='text-align:left; font-size:0.85rem;'>{s_msg}</td></tr>"
            except: pass

        if w_amt > 0:
            target_water = 8.0 if w_un == "잔" else (6.0 if w_un == "컵" else 2.0)
            w_badge = "<span class='badge' style='background:#D5F5E3; color:#1E8449;'>🟢 적정</span>" if w_amt >= target_water else ("<span class='badge' style='background:#FCF3CF; color:#D4AC0D;'>🟡 주의</span>" if w_amt >= target_water * 0.7 else "<span class='badge' style='background:#FADBD8; color:#C0392B;'>🚨 위험</span>")
            w_msg = f"생수 {w_amt}{w_un} 섭취 완료. " + ("수분 대사 원활." if w_amt >= target_water else "수분 부족.")
            habit_table += f"<tr><td><b>수분</b></td><td>{w_badge}</td><td style='text-align:left; font-size:0.85rem;'>{w_msg}</td></tr>"

    for idx, b_row in bev_df.iterrows():
        b_name, b_amt, b_un = b_row['amount'], b_row['amount'], b_row['unit']
        if b_name in ["아메리카노 / 에스프레소", "차류 (녹차, 홍차, 콤부차 등)", "제로 칼로리 음료 (제로콜라 등)"]:
            b_badge, b_msg = "<span class='badge' style='background:#D5F5E3; color:#1E8449;'>🟢 적정</span>", f"{b_amt}{b_un} 섭취. 당류가 없어 안전합니다."
        elif b_name in ["단백질 보충 액상", "일반 우유 / 무가당 두유"]:
            b_badge, b_msg = "<span class='badge' style='background:#FCF3CF; color:#D4AC0D;'>🟡 주의</span>", f"{b_amt}{b_un} 섭취. 잉여 칼로리에 유의하세요."
        else:
            b_badge, b_msg = "<span class='badge' style='background:#FADBD8; color:#C0392B;'>🚨 위험</span>", f"{b_amt}{b_un} 섭취. 당류 스파이크 발생."
        habit_table += f"<tr><td><b>음료</b><br><span style='font-size:0.7rem; color:#7F8C8D;'>{b_name}</span></td><td>{b_badge}</td><td style='text-align:left; font-size:0.85rem;'>{b_msg}</td></tr>"
    
    w_hist_df = pd.read_sql(f"SELECT weight FROM daily_weight WHERE date='{view_date_str}'", conn)
    if not w_hist_df.empty:
        day_w = w_hist_df.iloc[0]['weight']
        
        prev_w_df = pd.read_sql(f"SELECT weight FROM daily_weight WHERE date < '{view_date_str}' ORDER BY date DESC LIMIT 1", conn)
        
        if not prev_w_df.empty:
            prev_w = prev_w_df.iloc[0]['weight']
            diff = round(day_w - prev_w, 1)
            
            if diff <= -0.1:
                w_badge = "<span class='badge' style='background:#D5F5E3; color:#1E8449;'>🟢 감량</span>"
                w_msg = f"전일 대비 <b>{abs(diff)}kg 감량</b>되었습니다. 체지방 연소가 원활한 긍정적 지표입니다. 현재 대사 상태를 유지하세요."
                w_disp = f"{day_w}kg <span style='color:#1E8449; font-weight:bold;'>(⬇ {abs(diff)}kg)</span>"
            elif diff >= 0.1:
                w_badge = "<span class='badge' style='background:#FADBD8; color:#C0392B;'>🚨 증가</span>"
                w_msg = f"전일 대비 <b>{diff}kg 증가</b>했습니다. 단순 수분 정체 및 글리코겐 로딩일 확률이 높으니 스트레스 받지 마시고, 전날 나트륨 섭취량을 점검하세요."
                w_disp = f"{day_w}kg <span style='color:#C0392B; font-weight:bold;'>(⬆ {diff}kg)</span>"
            else:
                w_badge = "<span class='badge' style='background:#FCF3CF; color:#D4AC0D;'>🟡 유지/정체</span>"
                w_msg = "전일과 체중이 동일합니다. 대사 적응기이거나 수분 정체기일 수 있습니다. 충분한 수분 섭취와 활동량 유지가 필요합니다."
                w_disp = f"{day_w}kg <span style='color:#D4AC0D; font-weight:bold;'>( - )</span>"
        else:
            w_badge = "<span class='badge' style='background:#F2F3F4; color:#2C3E50;'>기록 시작</span>"
            w_msg = "비교할 전일 데이터가 없습니다. 내일부터 일일 변화량 및 전문 피드백이 제공됩니다."
            w_disp = f"{day_w}kg"

        habit_table += f"<tr><td><b>체중</b></td><td>{w_badge}</td><td style='text-align:left; font-size:0.85rem;'><b>{w_disp}</b><br><span style='color:#7F8C8D;'>{w_msg}</span></td></tr>"
    
    habit_table += "</table>"
    if habit_df.empty and w_hist_df.empty and bev_df.empty:
        st.info("해당 일자의 습관 및 체중 기록이 없습니다.")
    else:
        st.markdown(habit_table, unsafe_allow_html=True)

# ------------------------------------------
# [메뉴 3] 대사 진단 리포트
# ------------------------------------------
elif menu == "📋 대사 진단 리포트":
    st.markdown("<h1>🥑 브쌤's Diet 일지</h1>", unsafe_allow_html=True)
    st.markdown("### 📋 정밀 대사 진단 리포트")
    _, _, _, _, f_text = generate_master_feedback(p)
    st.markdown(f"<div class='report-box'>{f_text}</div>", unsafe_allow_html=True)

# ------------------------------------------
# [메뉴 4] 정밀 대사 재진단
# ------------------------------------------
elif menu == "⚙️ 정밀 대사 재진단":
    st.markdown("<h1>🥑 브쌤's Diet 일지</h1>", unsafe_allow_html=True)
    st.markdown("### ⚙️ 20개 변수 기반 정밀 대사 진단")
    st.info("이곳에서 분석된 데이터는 클라우드 데이터베이스에 절대 목표치로 영구 저장됩니다.")
    
    st.markdown("##### 👤 체성분 및 목표 설정")
    c1, c2 = st.columns(2)
    with c1: g_val = st.selectbox("성별", ["여성", "남성"], index=["여성", "남성"].index(p.get('gender', '여성')) if not is_new_user else 0)
    with c2: a_val_str = st.text_input("만 나이", value=str(p.get('age', 30)))
    
    c3, c4, c5 = st.columns(3)
    with c3: h_val_str = st.text_input("신장 (cm)", value=str(p.get('height', 160.0)))
    with c4: w_val_str = st.text_input("현재 체중 (kg)", value=str(p.get('weight', 60.0)))
    with c5: t_w_val_str = st.text_input("🎯 목표 체중 (kg)", value=str(p.get('target_weight', 55.0)))
    
    st.markdown("##### 🚶‍♂️ 일일 활동 및 식사 패턴")
    act_options = [
        "1단계 (주로 앉아서 생활)", 
        "2단계 (가벼운 활동/운동)", 
        "3단계 (보통 수준의 활동/운동)", 
        "4단계 (육체노동 또는 강도 높은 운동)"
    ]
    try: act_idx = act_options.index(p.get('activity_level', '1단계 (주로 앉아서 생활)'))
    except: act_idx = 0
    
    act_val = st.selectbox("일과 중 활동량", act_options, index=act_idx)
    
    if "1단계" in act_val:
        st.markdown("<div style='background-color:#F8F9FA; padding:10px; border-radius:8px; font-size:0.9rem; color:#34495E; margin-bottom:15px; line-height: 1.6;'>✔️ 출퇴근 외에는 걷는 시간이 거의 없음<br>✔️ 하루 1만 보 미만<br>✔️ 사무직, 학생 등</div>", unsafe_allow_html=True)
        exc_options = ["운동 안 함", "가벼운 산책(30분 내외)", "맨몸 스트레칭"]
    elif "2단계" in act_val:
        st.markdown("<div style='background-color:#F8F9FA; padding:10px; border-radius:8px; font-size:0.9rem; color:#34495E; margin-bottom:15px; line-height: 1.6;'>✔️ 주 1~3회 가벼운 운동<br>✔️ 하루 1만 보 이상 걷기<br>✔️ 서서 일하는 직업 (교사, 서비스직 등)</div>", unsafe_allow_html=True)
        exc_options = ["가벼운 조깅/러닝", "홈트레이닝/요가", "자전거/수영 (저강도)"]
    elif "3단계" in act_val:
        st.markdown("<div style='background-color:#F8F9FA; padding:10px; border-radius:8px; font-size:0.9rem; color:#34495E; margin-bottom:15px; line-height: 1.6;'>✔️ 주 3~5회 규칙적인 땀나는 운동<br>✔️ 1시간 이상 중강도 훈련<br>✔️ 활동량 많은 직업 (택배, 영업 등)</div>", unsafe_allow_html=True)
        exc_options = ["웨이트 트레이닝 (머신/프리웨이트)", "인터벌 러닝/크로스핏", "격렬한 구기 종목 (축구, 농구 등)"]
    else:
        st.markdown("<div style='background-color:#F8F9FA; padding:10px; border-radius:8px; font-size:0.9rem; color:#34495E; margin-bottom:15px; line-height: 1.6;'>✔️ 주 6회 이상 고강도 훈련<br>✔️ 하루 2시간 이상 운동<br>✔️ 건설 현장 등 강도 높은 육체노동</div>", unsafe_allow_html=True)
        exc_options = ["고강도 웨이트/파워리프팅", "철인 3종/마라톤 훈련", "엘리트 체육/프로 선수 훈련"]
        
    try: exc_idx = exc_options.index(p.get('exercise_type', exc_options[0]))
    except: exc_idx = 0
    
    exc_val = st.selectbox("해당 단계 주요 훈련 종목", exc_options, index=exc_idx)
    
    cs1, cs2 = st.columns(2)
    with cs1: bed_hr = st.text_input("평균 취침 시간 (예: 23:30)", value=p.get('sleep_bed_hr', '23:30'))
    with cs2: wake_hr = st.text_input("평균 기상 시간 (예: 07:00)", value=p.get('sleep_wake_hr', '07:00'))
    
    cm1, cm2, cm3 = st.columns(3)
    with cm1: meal_cnt = st.selectbox("식사 횟수", ["1끼", "2끼", "3끼", "4끼 이상"], index=2)
    with cm2: f_hr = st.text_input("첫 식사 시간", value=p.get('first_meal_hr', '08:00'))
    with cm3: l_hr = st.text_input("마지막 식사 시간", value=p.get('last_meal_hr', '19:00'))
    
    carb_v = st.selectbox("메인 식단 베이스", ["채소 위주 샐러드", "곡물 샐러드볼", "육류 샐러드", "목초사육 소고기/연어", "비건 식단", "다이어트 정식", "일반 한식 백반", "면류/배달음식"], index=5)
    
    st.markdown("##### 🍩 간식 및 수분 섭취")
    snack_v = st.selectbox("주요 간식", ["안 먹음", "로스팅 캐슈넛/참크래커", "단백질바/에너지바", "초콜릿/과자/아이스크림 등"], index=0)
    
    cw1, cw2, cw3 = st.columns(3)
    with cw1: snack_freq = st.selectbox("간식 빈도", ["안 먹음", "주 1~2회", "주 3~4회", "매일 1회", "수시로"], index=0)
    with cw2: snack_time = st.selectbox("간식 시간대", ["없음", "오전", "오후", "야간"], index=0)
    with cw3: snack_amt = st.selectbox("간식 섭취량", ["없음", "소량", "다량"], index=0)
    
    cw4, cw5 = st.columns([3,7])
    with cw4: w_unit = st.selectbox("생수 단위 선택", ["잔", "컵", "리터(L)"], index=0)
    with cw5: w_cnt_str = st.text_input("하루 평균 생수 섭취량", value=str(p.get('water_cnt', 8.0)))
    
    cb1, cb2 = st.columns([3,7])
    with cb1: b_unit = st.selectbox("타 음료 단위 선택", ["작은 캔", "큰 캔", "잔"], index=0)
    with cb2: b_cnt_str = st.text_input("타 액상 섭취량", value=str(p.get('bev_cnt', 1.0)))
    b_type = st.selectbox("주로 마시는 음료 종류", ["안 마심", "제로 슈거 음료", "디카페인 커피 등", "일반 액상과당 (주스/탄산)"], index=0)
    
    if st.button("🚀 분석 후 기준 데이터 클라우드 저장", type="primary", use_container_width=True):
        try:
            a_val = int(a_val_str)
            h_val, w_val, t_w_val = float(h_val_str), float(w_val_str), float(t_w_val_str)
            w_cnt, b_cnt = float(w_cnt_str), float(b_cnt_str)
            
            p_data = {
                'gender': g_val, 'age': a_val, 'height': h_val, 'weight': w_val, 'target_weight': t_w_val, 
                'activity_level': act_val, 'exercise_type': exc_val, 
                'sleep_bed_hr': bed_hr, 'sleep_wake_hr': wake_hr, 
                'meal_count': meal_cnt, 'first_meal_hr': f_hr, 'last_meal_hr': l_hr, 
                'carb_type': carb_v, 'snack_type': snack_v, 'snack_freq': snack_freq, 
                'snack_time': snack_time, 'snack_amt': snack_amt, 
                'water_unit': w_unit, 'water_cnt': w_cnt, 
                'bev_type': b_type, 'bev_unit': b_unit, 'bev_cnt': b_cnt
            }
            
            t_cal, t_c, t_p, t_f, _ = generate_master_feedback(p_data)
            
            c.execute("DELETE FROM user_profile")
            c.execute("""INSERT INTO user_profile 
                         (gender, age, height, weight, target_weight, activity_level, exercise_type, 
                          target_calories, target_carb, target_protein, target_fat, sleep_bed_hr, sleep_wake_hr,
                          meal_count, first_meal_hr, last_meal_hr, carb_type, snack_type, snack_freq, snack_time, snack_amt, 
                          water_unit, water_cnt, bev_type, bev_unit, bev_cnt) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                      (g_val, a_val, h_val, w_val, t_w_val, act_val, exc_val, t_cal, t_c, t_p, t_f, bed_hr, wake_hr, meal_cnt, f_hr, l_hr, carb_v, snack_v, snack_freq, snack_time, snack_amt, w_unit, w_cnt, b_type, b_unit, b_cnt))
            
            commit_and_sync(conn, ['user_profile'])
            st.success("✅ 정밀 대사 진단 데이터가 구글 클라우드에 완벽하게 저장되었습니다! 달력 조회 및 리포트 탭에 정상 연동되었습니다.")
            st.balloons()
            
        except ValueError:
            st.error("나이, 신장, 체중 등의 수치 항목은 반드시 숫자만 입력해주세요.")
