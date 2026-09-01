import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import json
import google.generativeai as genai
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials
import io
import pypdfium2 as pdfium

# ==========================================
# 0. 🔑 API 키 및 클라우드 인증 금고
# ==========================================
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    GEMINI_API_KEY = None

def get_gsheet_client():
    try:
        if "GCP_CREDENTIALS" not in st.secrets: 
            st.error("🚨 에러: 시크릿 금고에서 'GCP_CREDENTIALS' 키를 찾을 수 없습니다.")
            return None
        creds_json = json.loads(st.secrets["GCP_CREDENTIALS"])
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"🚨 JSON 데이터 해독 실패: {e}")
        return None

# ==========================================
# AI 분석 로직
# ==========================================
def analyze_food_image(img_bytes, api_key):
    if not api_key: return "{}"
    
    img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
    img.thumbnail((800, 800))
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="JPEG", quality=85)
    img_buffer.seek(0)
    
    optimized_img = Image.open(img_buffer)
    genai.configure(api_key=api_key)
    
    model = genai.GenerativeModel(
        model_name='gemini-3.5-flash-lite', 
        generation_config={"response_mime_type": "application/json", "temperature": 0.0}
    )
    
    prompt = '''당신은 식품 영양 분석 전문가이자 광학 문자 인식(OCR) 시스템입니다.
    사진을 분석하여 아래의 [절대 행동 지침]을 엄격히 준수한 후 JSON으로만 결과를 출력하십시오.
    
    [절대 행동 지침]
    1. 텍스트 판독(OCR) 최우선: 사진 내에 제품명, 원재료명, 영양성분표 등의 글자가 있다면 시각적 형태나 색상보다 글자를 무조건 1순위 팩트로 신뢰하십시오.
    2. 시각적 착시 및 추측 금지: 글자 판독이 불가능한 경우에만 시각적 추론을 사용하되 가장 보편적인 식재료로 보수적으로 판단하십시오.
    3. 객관적 영양 수치 매핑: 판독된 정확한 제품명 또는 메뉴를 바탕으로, 시중의 표준 데이터베이스에 근접한 수치를 입력하십시오. 알 수 없는 수치는 0처리.
    4. 출력 형식: 마크다운 기호 없이 순수 JSON 포맷만 반환.
    
    출력 JSON 키 구조:
    {"name": "인식된 메뉴명", "calories": 0, "carb": 0, "protein": 0, "fat": 0, "sugar": 0, "sat_fat": 0, "trans_fat": 0, "sodium": 0, "fiber": 0, "quality": "좋은 음식/주의 음식/위험 음식 중 택 1"}'''
    
    response = model.generate_content([prompt, optimized_img])
    return response.text.strip()

def analyze_atflee_pdf(pdf_bytes, api_key):
    if not api_key: return "{}"
    
    pdf = pdfium.PdfDocument(pdf_bytes)
    page = pdf[0]
    img = page.render(scale=2.0).to_pil().convert('RGB')
    img.thumbnail((1200, 1200))
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="JPEG", quality=85)
    img_buffer.seek(0)
    
    optimized_img = Image.open(img_buffer)
    genai.configure(api_key=api_key)
    
    model = genai.GenerativeModel(
        model_name='gemini-3.5-flash-lite', 
        generation_config={"response_mime_type": "application/json", "temperature": 0.0}
    )
    
    prompt = '''당신은 전문 체성분 데이터 분석가이자 광학 문자 판독(OCR) 전문가입니다.
    제공된 체성분 분석표 이미지에서 정확한 수치를 찾아 JSON으로만 반환하십시오.
    
    [절대 행동 지침]
    1. 체중(weight), 골격근량(skeletal_muscle), 체지방률(body_fat_percent), 내장지방(visceral_fat), 기초대사량(bmr)을 정확히 추출하세요.
    2. 출력은 반드시 아래 JSON 형식으로만 반환하세요.
    {"weight": 76.2, "skeletal_muscle": 33.1, "body_fat_percent": 23.1, "visceral_fat": 7, "bmr": 1635}'''
    
    response = model.generate_content([prompt, optimized_img])
    return response.text.strip()

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
    
    [data-testid="baseButton-secondary"] {
        background-color: #2C3E50 !important; border: none !important; border-radius: 8px !important;
        color: white !important; font-weight: 800 !important; box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important; transition: all 0.2s ease !important;
    }
    [data-testid="baseButton-secondary"]:active { transform: scale(0.98) !important; }
    
    [data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #FF6B6B, #C0392B) !important; border: none !important; border-radius: 10px !important;
        color: white !important; font-size: 1.15rem !important; font-weight: 900 !important; height: 55px !important;
        box-shadow: 0 4px 10px rgba(192, 57, 43, 0.25) !important; transition: all 0.2s ease !important;
    }
    [data-testid="baseButton-primary"]:active { transform: scale(0.98) !important; }
    
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
    .diet-table th { background-color: #34495E; color: white; padding: 10px 4px; text-align: center; font-weight: 800; font-size: 0.9rem; word-break: keep-all;}
    .diet-table td { padding: 12px 4px; text-align: left; border-bottom: 1px solid #E5E7E9; vertical-align: middle; background-color: white; line-height: 1.5;}
    .diet-table td:first-child, .diet-table td:last-child { text-align: center; }
    .badge { padding: 4px 8px; border-radius: 6px; font-weight: 900; font-size: 0.85rem; white-space: nowrap; display: inline-block;}
    
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

c = conn.cursor()
c.execute("PRAGMA table_info(diet_logs)")
columns = [col[1] for col in c.fetchall()]
if "meal_end_time" not in columns:
    c.execute("ALTER TABLE diet_logs ADD COLUMN meal_end_time TEXT")
    conn.commit()

c.execute("PRAGMA table_info(daily_weight)")
dw_columns = [col[1] for col in c.fetchall()]
if "skeletal_muscle" not in dw_columns:
    c.execute("ALTER TABLE daily_weight ADD COLUMN skeletal_muscle REAL DEFAULT 0.0")
    c.execute("ALTER TABLE daily_weight ADD COLUMN body_fat_percent REAL DEFAULT 0.0")
    c.execute("ALTER TABLE daily_weight ADD COLUMN visceral_fat INTEGER DEFAULT 0")
    c.execute("ALTER TABLE daily_weight ADD COLUMN bmr INTEGER DEFAULT 0")
    conn.commit()

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
        st.error("GCP 인증 실패: st.secrets 설정 상태를 확인하세요.")
        return False
        
    try: 
        sheet = client.open("my_diet_db")
    except Exception as e: 
        st.error(f"구글 시트 접근 불가: {e}")
        return False
    
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
                
                try: ws.update('A1', data)
                except TypeError: ws.update(values=data, range_name='A1')
        except Exception as e: 
            st.error(f"[{t}] 시트 업로드 실패: {e}")
            return False
            
    return True

if 'db_synced' not in st.session_state:
    with st.spinner("☁️ 클라우드 데이터베이스와 안전하게 동기화 중입니다..."):
        sync_from_sheets(conn)
        st.session_state.db_synced = True

# UTC+9 통일 (앱 전체 기준 시간)
now = datetime.utcnow() + timedelta(hours=9)
today_str = now.strftime("%Y-%m-%d")
wd_map = {0:'월', 1:'화', 2:'수', 3:'목', 4:'금', 5:'토', 6:'일'}
date_display = f"{now.strftime('%y - %m - %d')} ( {wd_map[now.weekday()]} )"

def safe_get(val, default_val): return val if pd.notna(val) else default_val

# ==========================================
# 3. 진단 리포트 생성 함수 (앳플리 데이터 연동 완비)
# ==========================================
def generate_master_feedback(p):
    h = float(safe_get(p.get('height'), 160.0))
    w = float(safe_get(p.get('weight'), 60.0))
    t_w = float(safe_get(p.get('target_weight'), 55.0))
    a = int(safe_get(p.get('age'), 30))
    g = str(safe_get(p.get('gender'), '여성'))
    
    act = str(safe_get(p.get('activity_level'), '1단계 (주로 앉아서 생활)'))
    exc = str(safe_get(p.get('exercise_type'), '운동 안 함'))
    
    atflee_bmr = 0
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT bmr FROM daily_weight WHERE bmr > 0 ORDER BY date DESC LIMIT 1")
        res = cursor.fetchone()
        if res:
            atflee_bmr = int(res[0])
    except: pass
        
    if atflee_bmr > 0:
        bmr = atflee_bmr
        bmr_source = "앳플리 체성분 분석"
    else:
        bmr = (10 * w) + (6.25 * h) - (5 * a) + (5 if g == "남성" else -161)
        bmr_source = "통계 공식"
    
    base_multi = 1.2
    if "2단계" in act: base_multi = 1.375
    elif "3단계" in act: base_multi = 1.55
    elif "4단계" in act: base_multi = 1.725
    
    if exc in ["고강도 웨이트/파워리프팅", "철인 3종/마라톤 훈련", "엘리트 체육/프로 선수 훈련", "인터벌 러닝/크로스핏"]: base_multi += 0.1
    elif exc in ["웨이트 트레이닝 (머신/프리웨이트)", "격렬한 구기 종목 (축구, 농구 등)", "가벼운 조깅/러닝", "자전거/수영 (저강도)"]: base_multi += 0.05
    
    tdee = bmr * base_multi
    deficit = 500 if w > t_w else 0
    target_cal = max(int(tdee - deficit), int(bmr) + 100)
    
    p_ratio = 1.8
    if "웨이트" in exc or "고강도" in exc or "크로스핏" in exc or "마라톤" in exc: p_ratio = 2.0
        
    protein_g = int(t_w * p_ratio) 
    fat_g = int((target_cal * 0.25) / 9)
    carb_g = int((target_cal - (protein_g * 4) - (fat_g * 9)) / 4)

    adv = f"<div class='report-title'>📌 Section 1. [ 체성분 및 활동 대사량 산출 ]</div>"
    adv += f"<div class='report-p'>현재 고객님의 기초대사량은 <b>{int(bmr)} kcal</b>입니다. <span style='font-size:0.85rem; color:#7F8C8D;'>({bmr_source} 기준)</span><br><br><b>[{act}]</b> 활동량과 <b>[{exc}]</b> 훈련 종목을 반영한 일일 총 에너지 소모량(TDEE)은 <b>{int(tdee)} kcal</b>로 분석되었습니다.<br><br>목표 체중({t_w}kg) 도달을 위해 <b>1일 권장 섭취량을 {target_cal} kcal</b>로 설정합니다.</div>"
    return target_cal, carb_g, protein_g, fat_g, adv

# ==========================================
# 4. 앱 강제 라우팅 및 좌측 사이드바
# ==========================================
p_df = pd.read_sql("SELECT * FROM user_profile ORDER BY id DESC LIMIT 1", conn)
is_new_user = p_df.empty

if is_new_user:
    st.markdown("<h1>🥑 브쌤's Diet 일지</h1>", unsafe_allow_html=True)
    st.warning("⚠️ 최초 1회 [정밀 대사 진단]을 완료해야 앱 메뉴가 활성화됩니다.")
    menu = "⚙️ 정밀 대사 재진단"
    p = {}  
else:
    p = p_df.iloc[0]
    st.sidebar.markdown("### 📌 메뉴 이동")
    menu_options = ["📝 일일 기록 (메인)", "📅 달력 조회", "📋 대사 진단 리포트", "⚙️ 정밀 대사 재진단"]
    menu = st.sidebar.radio("", menu_options, label_visibility="collapsed")

# ==========================================
# 5. 페이지 렌더링
# ==========================================
if menu == "📝 일일 기록 (메인)":
    st.markdown("<h1>🥑 브쌤's Diet 일지</h1>", unsafe_allow_html=True)
    st.markdown(f"<div class='date-display'>{date_display}</div>", unsafe_allow_html=True)
    
    # 💡 오늘 식사 중인 "모든" 메뉴 일괄 조회
    c.execute("SELECT menu_name, meal_time FROM diet_logs WHERE date=? AND (meal_end_time IS NULL OR meal_end_time = '' OR LOWER(meal_end_time) IN ('nan', 'none', 'null'))", (today_str,))
    ongoing_meals = c.fetchall()
    
    if ongoing_meals:
        am_names = ", ".join([m[0] for m in ongoing_meals])
        lm_start = min([m[1] for m in ongoing_meals])
        st.markdown(f"""
        <div class='status-dashboard status-eating'>
            <div class='status-title'>🍽️ 현재 식사 중입니다: {am_names}</div>
            <div class='status-time'>최초 시작: {lm_start}</div>
            <div class='status-msg'>식사를 마치셨다면 [📅 달력 조회] 탭에서 '일괄 식사 종료' 버튼을 눌러주세요.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # 종료된 식사 중 가장 마지막 기록을 기준으로 공복 계산
        c.execute("SELECT date, meal_end_time FROM diet_logs WHERE meal_end_time IS NOT NULL AND meal_end_time != '' AND LOWER(meal_end_time) NOT IN ('nan', 'none', 'null') ORDER BY date DESC, meal_end_time DESC LIMIT 1")
        last_ended_meal = c.fetchone()
        
        if last_ended_meal:
            lm_date, lm_end = last_ended_meal
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
            st.markdown(f"<div class='status-dashboard status-wait'><div class='status-title'>타이머 대기 중</div><div class='status-msg'>완료된 식사 기록이 없습니다. 첫 식사를 기록해주세요.</div></div>", unsafe_allow_html=True)

    tab_list = ["🥗 식단 기록", "⏰ 습관", "🏋️ 운동", "📉 체중"]
    if p.get('gender') == '여성': tab_list.append("🩸 주기")
    tabs = st.tabs(tab_list)
    
    with tabs[0]: 
        st.markdown("##### 🍽️ 새로운 식사 시작 (입력)")
        user_start_time = st.text_input("식사 시작 시각 (예: 12:00)", value=now.strftime("%H:%M"))
        meal_type = ""
        
        if 'camera_on' not in st.session_state: st.session_state.camera_on = False
        if 'ai_menu' not in st.session_state:
            st.session_state.ai_menu = ""
            st.session_state.ai_calories = 0
            for k in ['carb', 'protein', 'fat', 'sugar', 'sat_fat', 'trans_fat', 'sodium', 'fiber']: st.session_state[f'ai_{k}'] = 0
            st.session_state.ai_quality = "좋은 음식"
            
        col_btn, _ = st.columns([1, 1])
        with col_btn:
            if not st.session_state.camera_on:
                if st.button("📷 스마트 카메라 켜기", use_container_width=True):
                    st.session_state.camera_on = True
                    st.rerun()
            else:
                if st.button("❌ 카메라 닫기", use_container_width=True):
                    st.session_state.camera_on = False
                    st.rerun()
                    
        if st.session_state.camera_on:
            uploaded_file = st.camera_input("알아서 인식합니다", label_visibility="collapsed")
            if uploaded_file is not None:
                if st.button("🔍 AI 심층 영양소 분석"):
                    if not GEMINI_API_KEY: st.error("API 금고가 비어있습니다.")
                    else:
                        with st.spinner("AI가 고화질 이미지를 즉시 전송하여 정밀 판독 중입니다..."):
                            try:
                                img_bytes = uploaded_file.getvalue()
                                result_text = analyze_food_image(img_bytes, GEMINI_API_KEY)
                                
                                start_idx, end_idx = result_text.find('{'), result_text.rfind('}')
                                if start_idx != -1 and end_idx != -1:
                                    ai_data = json.loads(result_text[start_idx:end_idx+1])
                                    st.session_state.ai_menu = ai_data.get("name", "")
                                    st.session_state.ai_calories = float(ai_data.get("calories", 0))
                                    for k in ['carb', 'protein', 'fat', 'sugar', 'sat_fat', 'trans_fat', 'sodium', 'fiber']:
                                        st.session_state[f'ai_{k}'] = float(ai_data.get(k, 0))
                                    st.session_state.ai_quality = ai_data.get("quality", "좋은 음식")
                                    st.success(f"✅ 정밀 분석 완료! (인식된 메뉴: {st.session_state.ai_menu})")
                                else: st.error("데이터 형식 반환에 실패했습니다.")
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
                            with st.spinner("클라우드에 안전하게 동기화 중입니다..."):
                                c.execute('INSERT INTO diet_logs (date, meal_type, menu_name, calories, carb, protein, fat, sugar, sat_fat, trans_fat, sodium, fiber, meal_time, meal_end_time, quality) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                                          (today_str, meal_type, m_name, cal, carb, protein, fat, sugar, sat_fat_v, trans_fat_v, sodium, fiber, user_start_time.strip(), "", q))
                                
                                conn.commit()
                                is_success = commit_and_sync(conn, ['diet_logs'])
                            
                            if is_success:
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
                with st.spinner("클라우드 연동 중..."):
                    if w_df.empty: c.execute("INSERT INTO daily_habits (date, water_unit, water_amt) VALUES (?, '잔', 1.0)", (today_str,))
                    else: c.execute("UPDATE daily_habits SET water_amt = coalesce(water_amt, 0) + 1.0 WHERE date=?", (today_str,))
                    conn.commit()
                    commit_and_sync(conn, ['daily_habits'])
                st.session_state.habit_msg = "💧 생수 1단위가 추가되었습니다."
                st.rerun()
        with col_w2:
            if st.button("💧 큰 컵 (+2)", use_container_width=True):
                with st.spinner("클라우드 연동 중..."):
                    if w_df.empty: c.execute("INSERT INTO daily_habits (date, water_unit, water_amt) VALUES (?, '잔', 2.0)", (today_str,))
                    else: c.execute("UPDATE daily_habits SET water_amt = coalesce(water_amt, 0) + 2.0 WHERE date=?", (today_str,))
                    conn.commit() 
                    commit_and_sync(conn, ['daily_habits'])
                st.session_state.habit_msg = "💧 생수 2단위가 추가되었습니다."
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
                with st.spinner("클라우드 연동 중..."):
                    if b_df.empty: c.execute("INSERT INTO beverage_logs (date, bev_name, amount, unit) VALUES (?, ?, 1.0, '작은 캔')", (today_str, selected_b_name))
                    else: c.execute("UPDATE beverage_logs SET amount = amount + 1.0 WHERE id=?", (int(b_df.iloc[0]['id']),))
                    conn.commit()
                    commit_and_sync(conn, ['beverage_logs'])
                st.session_state.habit_msg = f"☕ [{selected_b_name}] 1단위 추가 완료."
                st.rerun()
        with col_b2:
            if st.button("☕ 큰 캔 (+2)", use_container_width=True):
                with st.spinner("클라우드 연동 중..."):
                    if b_df.empty: c.execute("INSERT INTO beverage_logs (date, bev_name, amount, unit) VALUES (?, ?, 2.0, '큰 캔')", (today_str, selected_b_name))
                    else: c.execute("UPDATE beverage_logs SET amount = amount + 2.0 WHERE id=?", (int(b_df.iloc[0]['id']),))
                    conn.commit()
                    commit_and_sync(conn, ['beverage_logs'])
                st.session_state.habit_msg = f"☕ [{selected_b_name}] 2단위 추가 완료."
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
                    
                    with st.spinner("클라우드 연동 중..."):
                        c.execute("SELECT date FROM daily_habits WHERE date=?", (today_str,))
                        if c.fetchone():
                            c.execute("UPDATE daily_habits SET bed_time=?, wake_time=?, water_unit=?, water_amt=? WHERE date=?", (bed_t_str, wake_t_str, w_unit, w_man_amt, today_str))
                        else:
                            c.execute("INSERT INTO daily_habits (date, bed_time, wake_time, water_unit, water_amt) VALUES (?, ?, ?, ?, ?)", (today_str, bed_t_str, wake_t_str, w_unit, w_man_amt))
                        
                        if b_man_amt > 0:
                            if b_df.empty: c.execute("INSERT INTO beverage_logs (date, bev_name, amount, unit) VALUES (?, ?, ?, ?)", (today_str, selected_b_name, b_man_amt, b_unit))
                            else: c.execute("UPDATE beverage_logs SET amount=?, unit=? WHERE id=?", (b_man_amt, b_unit, int(b_df.iloc[0]['id'])))
                        elif b_man_amt == 0 and not b_df.empty:
                            c.execute("DELETE FROM beverage_logs WHERE id=?", (int(b_df.iloc[0]['id']),))
                            
                        conn.commit() 
                        is_success = commit_and_sync(conn, ['daily_habits', 'beverage_logs'])
                    if is_success:
                        st.success("데이터베이스에 완벽히 업데이트되었습니다!")
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
                st.session_state.ex_start = datetime.utcnow() + timedelta(hours=9)
                st.rerun()
        with t_col2:
            if st.button("⏹️ 타이머 종료", use_container_width=True):
                if st.session_state.ex_start:
                    kst_now = datetime.utcnow() + timedelta(hours=9)
                    diff = kst_now - st.session_state.ex_start
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
                    
                    with st.spinner("클라우드 연동 중..."):
                        c.execute("INSERT INTO exercise_logs (date, ex_name, duration, calories_burned) VALUES (?, ?, ?, ?)", (today_str, st.session_state.active_ex_name.split(' (')[0], ex_min, burned_cal))
                        conn.commit() 
                        commit_and_sync(conn, ['exercise_logs'])
                    st.session_state.ex_mins = 0
                    st.success(f"🔥 총 {burned_cal}kcal 소모 기록 완료!")
                except ValueError: st.error("숫자만 입력해주세요.")

    with tabs[3]:
        st.markdown("##### 📉 오늘의 체성분 입력 (PDF 연동)")
        
        if st.session_state.get("weight_save_success"):
            st.success("✅ ☁️ 체성분 데이터가 클라우드 및 로컬에 완벽하게 저장되었습니다!")
            st.session_state.weight_save_success = False

        st.info("💡 **앳플리(Atflee) 체성분 PDF 결과지**를 업로드하면 상세 데이터를 자동 기록합니다.")
        
        pdf_file = st.file_uploader("PDF 파일 업로드 (iOS 파일 앱 연동)", type=['pdf'], label_visibility="collapsed")
        
        if pdf_file is not None:
            if st.button("🔍 AI 체성분 데이터 자동 추출"):
                if not GEMINI_API_KEY: 
                    st.error("API 금고가 비어있습니다.")
                else:
                    with st.spinner("AI가 고해상도 이미지를 고속 전송하여 정밀 판독 중입니다..."):
                        try:
                            pdf_bytes = pdf_file.getvalue()
                            result_text = analyze_atflee_pdf(pdf_bytes, GEMINI_API_KEY)
                            
                            s_idx, e_idx = result_text.find('{'), result_text.rfind('}')
                            if s_idx != -1 and e_idx != -1:
                                w_data = json.loads(result_text[s_idx:e_idx+1])
                                st.session_state.ai_weight = float(w_data.get("weight", 0.0))
                                st.session_state.ai_muscle = float(w_data.get("skeletal_muscle", 0.0))
                                st.session_state.ai_fat_pct = float(w_data.get("body_fat_percent", 0.0))
                                st.session_state.ai_visceral_fat = int(w_data.get("visceral_fat", 0))
                                st.session_state.ai_bmr = int(w_data.get("bmr", 0))
                                st.success(f"✅ 추출 완료! (체중: {st.session_state.ai_weight}kg | 골격근량: {st.session_state.ai_muscle}kg | 체지방률: {st.session_state.ai_fat_pct}%)")
                            else:
                                st.error("데이터를 명확히 찾지 못했습니다.")
                        except Exception as e:
                            st.error(f"통신 또는 파싱 에러: {e}")

        curr_w_df = pd.read_sql(f"SELECT * FROM daily_weight WHERE date='{today_str}'", conn)
        
        default_w = str(st.session_state.ai_weight) if 'ai_weight' in st.session_state else (str(curr_w_df.iloc[0]['weight']) if not curr_w_df.empty else str(p.get('weight', 60.0)))
        default_m = str(st.session_state.ai_muscle) if 'ai_muscle' in st.session_state else (str(curr_w_df.iloc[0]['skeletal_muscle']) if not curr_w_df.empty and 'skeletal_muscle' in curr_w_df.columns else "0.0")
        default_f = str(st.session_state.ai_fat_pct) if 'ai_fat_pct' in st.session_state else (str(curr_w_df.iloc[0]['body_fat_percent']) if not curr_w_df.empty and 'body_fat_percent' in curr_w_df.columns else "0.0")
        default_v = str(st.session_state.ai_visceral_fat) if 'ai_visceral_fat' in st.session_state else (str(curr_w_df.iloc[0]['visceral_fat']) if not curr_w_df.empty and 'visceral_fat' in curr_w_df.columns else "0")
        default_bmr = str(st.session_state.ai_bmr) if 'ai_bmr' in st.session_state else (str(curr_w_df.iloc[0]['bmr']) if not curr_w_df.empty and 'bmr' in curr_w_df.columns else "0")
        
        with st.form("weight_form_main"):
            c1, c2, c3 = st.columns(3)
            with c1: today_w_str = text_input_w = st.text_input("체중 (kg)", value=default_w)
            with c2: muscle_str = st.text_input("골격근량 (kg)", value=default_m)
            with c3: fat_pct_str = st.text_input("체지방률 (%)", value=default_f)
            
            c4, c5 = st.columns(2)
            with c4: vf_str = st.text_input("내장지방지수", value=default_v)
            with c5: bmr_str = st.text_input("기초대사량 (kcal)", value=default_bmr)
            
            if st.form_submit_button("로컬 데이터베이스 업데이트", type="primary"):
                try:
                    t_w, t_m, t_f = float(today_w_str), float(muscle_str), float(fat_pct_str)
                    t_v, t_bmr = int(vf_str), int(bmr_str)
                    
                    with st.spinner("클라우드 연동 중..."):
                        c.execute("SELECT id FROM daily_weight WHERE date=?", (today_str,))
                        if c.fetchone():
                            c.execute("UPDATE daily_weight SET weight=?, skeletal_muscle=?, body_fat_percent=?, visceral_fat=?, bmr=? WHERE date=?", (t_w, t_m, t_f, t_v, t_bmr, today_str))
                        else:
                            c.execute("INSERT INTO daily_weight (date, weight, skeletal_muscle, body_fat_percent, visceral_fat, bmr) VALUES (?, ?, ?, ?, ?, ?)", (today_str, t_w, t_m, t_f, t_v, t_bmr))
                            
                        if not is_new_user:
                            c.execute("UPDATE user_profile SET weight = ? WHERE id = ?", (t_w, int(p['id'])))
                            
                        is_success = commit_and_sync(conn, ['daily_weight', 'user_profile'])
                    
                    if is_success:
                        for k in ['ai_weight', 'ai_muscle', 'ai_fat_pct', 'ai_visceral_fat', 'ai_bmr']:
                            if k in st.session_state: del st.session_state[k]
                        st.session_state.weight_save_success = True
                        st.rerun()
                except ValueError: 
                    st.error("숫자만 입력해주세요.")

    if len(tabs) == 5: 
        with tabs[4]:
            st.markdown("##### 🩸 주기 업데이트")
            with st.form("period_tracker"):
                last_p_date = st.text_input("최근 생리 시작일 (예: 2026-08-01)", value=str(safe_get(p.get('last_period_date'), "")))
                if st.form_submit_button("로컬 저장"):
                    try:
                        with st.spinner("클라우드 연동 중..."):
                            valid_date = datetime.strptime(last_p_date.strip(), "%Y-%m-%d")
                            c.execute("UPDATE user_profile SET last_period_date = ? WHERE id = ?", (last_p_date, int(p['id'])))
                            conn.commit()
                            commit_and_sync(conn, ['user_profile'])
                        st.success("저장 완료.")
                    except ValueError: st.error("날짜 형식을 맞춰주세요.")

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
        avg_cal, avg_p = 0, 0
    
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
        
    bev_df = pd.read_sql(f"SELECT * FROM beverage_logs WHERE date='{view_date_str}'", conn)
    
    for idx, b_row in bev_df.iterrows():
        calc_b_name, calc_b_amt, calc_b_un = b_row['bev_name'], b_row['amount'], b_row['unit']
        
        if calc_b_un == "작은 캔": vol_multi = 2.5
        elif calc_b_un == "큰 캔": vol_multi = 3.55
        else: vol_multi = 2.0
        
        if calc_b_name in ["일반 탄산음료 (콜라, 사이다)", "과일 주스 / 스무디", "기타 당류 포함 액상"]: k_per_100, c_per_100 = 45, 11
        elif calc_b_name == "달콤한 커피류 (믹스커피, 바닐라라떼 등)": k_per_100, c_per_100 = 60, 10
        elif calc_b_name == "가향 우유 (초코우유, 바나나우유 등)": k_per_100, c_per_100 = 80, 10
        elif calc_b_name in ["단백질 보충 액상", "일반 우유 / 무가당 두유"]: k_per_100, c_per_100 = 50, 5 
        else: k_per_100, c_per_100 = 0, 0
            
        e_cal += (k_per_100 * vol_multi * calc_b_amt)
        e_c += (c_per_100 * vol_multi * calc_b_amt)
    
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

    # 💡 조회일자 기준, 종료되지 않은 '모든' 식사를 식별
    c.execute(f"SELECT id, menu_name, meal_time FROM diet_logs WHERE date='{view_date_str}' AND (meal_end_time IS NULL OR meal_end_time = '' OR LOWER(meal_end_time) IN ('nan', 'none', 'null'))")
    active_meals = c.fetchall()
    
    st.markdown("##### 🍽 식단 기록 목록")
    if active_meals:
        am_names = ", ".join([am[1] for am in active_meals])
        st.markdown(f"<div style='background:#FFF3CD; padding:8px 12px; border-radius:6px; border-left:4px solid #F1C40F; margin-bottom:12px;'><span style='font-size:0.9rem; font-weight:bold; color:#7D6608;'>⏳ 현재 진행 중: {am_names}</span></div>", unsafe_allow_html=True)

    table_html = "<table class='diet-table'><tr><th style='width:25%;'>시간</th><th style='width:50%;'>메뉴 (상세영양소)</th><th style='width:25%;'>평가</th></tr>"
    if logs.empty: table_html += "<tr><td colspan='3' style='color:#7F8C8D; padding:20px 0;'>기록된 식단이 없습니다.</td></tr>"
    else:
        for idx, row in logs.iterrows():
            q = str(row.get('quality', ''))
            if "좋은" in q: badge = "<span class='badge' style='background:#D5F5E3; color:#1E8449;'>🟢 좋은 음식</span>"
            elif "주의" in q: badge = "<span class='badge' style='background:#FCF3CF; color:#D4AC0D;'>🟡 주의 음식</span>"
            else: badge = "<span class='badge' style='background:#FADBD8; color:#C0392B;'>🚨 위험 음식</span>"
            
            if pd.notna(row['meal_end_time']) and str(row['meal_end_time']).strip() != "" and str(row['meal_end_time']).strip().lower() not in ["nan", "none", "null"]:
                end_t = f"~ {row['meal_end_time']}"
            else:
                end_t = "<span style='color:#E74C3C;'>(식사 중)</span>"
                
            # 💡 하드코딩되었던 UI를 확장하여 상세 칼로리 및 탄단지 표출 로직 적용
            macro_info = f"<br><span style='font-size:0.8rem; color:#7F8C8D;'>{int(row.get('calories', 0))}kcal | 탄 {int(row.get('carb', 0))}g 단 {int(row.get('protein', 0))}g 지 {int(row.get('fat', 0))}g</span>"
            table_html += f"<tr><td><b>{row['meal_time']}</b><br><span style='font-size:0.75rem; color:#7F8C8D;'>{end_t}</span></td><td><b style='color:#2C3E50;'>{row['menu_name']}</b>{macro_info}</td><td>{badge}</td></tr>"
    table_html += "</table>"
    st.markdown(table_html, unsafe_allow_html=True)
    
    if active_meals:
        col_blank, col_end_btn = st.columns([7, 3])
        with col_end_btn:
            if st.button("🏁 일괄 식사 종료", key="end_meal_btn_bottom", type="primary", use_container_width=True):
                with st.spinner("클라우드와 동기화 중입니다..."):
                    now_str = now.strftime("%H:%M")
                    # 💡 단일 ID 지정(LIMIT 1) 업데이트가 아닌, 현재 진행 중인 '모든' 식사를 일괄 종료
                    c.execute("UPDATE diet_logs SET meal_end_time=? WHERE date=? AND (meal_end_time IS NULL OR meal_end_time='' OR LOWER(meal_end_time) IN ('nan', 'none', 'null'))", (now_str, view_date_str))
                    conn.commit()
                    commit_and_sync(conn, ['diet_logs', 'daily_habits', 'beverage_logs', 'exercise_logs', 'daily_weight'])
                st.session_state.meal_end_success = True
                st.rerun()

    if st.session_state.get("meal_end_success"):
        st.success("✅ 진행 중인 모든 식사가 종료되었습니다. 공복 타이머가 가동됩니다.")
        st.session_state.meal_end_success = False
    
    if not logs.empty:
        with st.expander("🛠️ 식단 삭제하기"):
            with st.form("delete_diet_form"):
                del_options = {f"[{row['meal_time']}] {row['menu_name']} (고유번호: {row['db_rowid']})": row['db_rowid'] for idx, row in logs.iterrows()}
                selected_del_key = st.selectbox("삭제할 식단 선택", options=list(del_options.keys()))
                if st.form_submit_button("영구 삭제"):
                    with st.spinner("삭제 및 클라우드 연동 중..."):
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
                    with st.spinner("삭제 및 클라우드 연동 중..."):
                        c.execute("DELETE FROM exercise_logs WHERE id = ?", (ex_del_opts[selected_ex_key],))
                        commit_and_sync(conn, ['exercise_logs'])
                    st.rerun()

    st.markdown("##### 📋 습관 및 체중 피드백")
    habit_df = pd.read_sql(f"SELECT * FROM daily_habits WHERE date='{view_date_str}'", conn)
    
    habit_table = "<table class='diet-table'><tr><th style='width:20%;'>항목</th><th style='width:25%;'>상태</th><th style='width:55%;'>전문가 피드백</th></tr>"
    
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
        b_name, b_amt, b_un = b_row['bev_name'], b_row['amount'], b_row['unit']
        
        if b_name == "아메리카노 / 에스프레소": b_badge, b_msg = "<span class='badge' style='background:#D5F5E3; color:#1E8449;'>🟢 적정</span>", f"{b_amt}{b_un} 섭취. 당류가 없어 대사에 좋지만, 이뇨 작용으로 수분이 손실되니 마신 양의 2배만큼 생수를 보충하세요. (늦은 오후 섭취 시 수면 방해 주의)"
        elif b_name == "차류 (녹차, 홍차, 콤부차 등)": b_badge, b_msg = "<span class='badge' style='background:#D5F5E3; color:#1E8449;'>🟢 적정</span>", f"{b_amt}{b_un} 섭취. 수분 보충과 항산화에 좋으나, 카페인이 든 차는 늦은 시간 섭취를 피하는 것이 좋습니다."
        elif b_name == "제로 칼로리 음료 (제로콜라 등)": b_badge, b_msg = "<span class='badge' style='background:#D5F5E3; color:#1E8449;'>🟢 적정</span>", f"{b_amt}{b_un} 섭취. 혈당을 올리진 않으나 인공감미료가 뇌의 보상 회로를 자극해 가짜 배고픔을 유발할 수 있습니다. 단독 섭취보다는 식사 중에만 드세요."
        elif b_name in ["단백질 보충 액상", "일반 우유 / 무가당 두유"]: b_badge, b_msg = "<span class='badge' style='background:#FCF3CF; color:#D4AC0D;'>🟡 주의</span>", f"{b_amt}{b_un} 섭취. 영양가는 높으나 '칼로리'가 있어 단식(공복) 시간을 깨뜨립니다. 식사 대용이나 운동 직후에 섭취하세요."
        elif b_name == "달콤한 커피류 (믹스커피, 바닐라라떼 등)": b_badge, b_msg = "<span class='badge' style='background:#FADBD8; color:#C0392B;'>🚨 위험</span>", f"{b_amt}{b_un} 섭취. 정제당과 포화지방(크림)의 결합은 혈당 스파이크와 복부 체지방 축적을 가장 빠르고 강하게 유발합니다."
        elif b_name == "과일 주스 / 스무디": b_badge, b_msg = "<span class='badge' style='background:#FADBD8; color:#C0392B;'>🚨 위험</span>", f"{b_amt}{b_un} 섭취. 과일을 갈아 마시면 식이섬유 구조가 파괴되어, 액상과당과 똑같이 간에 지방으로 직접 축적됩니다."
        else: b_badge, b_msg = "<span class='badge' style='background:#FADBD8; color:#C0392B;'>🚨 위험</span>", f"{b_amt}{b_un} 섭취. 액상과당은 인슐린을 급격히 분비시켜 체지방 연소 모드를 즉시 중단시킵니다."

        habit_table += f"<tr><td><b>음료</b><br><span style='font-size:0.7rem; color:#7F8C8D;'>{b_name}</span></td><td>{b_badge}</td><td style='text-align:left; font-size:0.85rem;'>{b_msg}</td></tr>"
    
    w_hist_df = pd.read_sql(f"SELECT * FROM daily_weight WHERE date='{view_date_str}'", conn)
    if not w_hist_df.empty:
        day_w = w_hist_df.iloc[0]['weight']
        day_m = w_hist_df.iloc[0]['skeletal_muscle'] if 'skeletal_muscle' in w_hist_df.columns else 0
        day_f = w_hist_df.iloc[0]['body_fat_percent'] if 'body_fat_percent' in w_hist_df.columns else 0
        
        prev_w_df = pd.read_sql(f"SELECT weight FROM daily_weight WHERE date < '{view_date_str}' ORDER BY date DESC LIMIT 1", conn)
        
        if not prev_w_df.empty:
            prev_w = prev_w_df.iloc[0]['weight']
            diff = round(day_w - prev_w, 1)
            
            if diff <= -0.1:
                w_badge, w_msg, w_disp = "<span class='badge' style='background:#D5F5E3; color:#1E8449;'>🟢 감량</span>", f"전일 대비 <b>{abs(diff)}kg 감량</b>되었습니다. 체지방 연소가 원활한 긍정적 지표입니다. 현재 대사 상태를 유지하세요.", f"{day_w}kg <span style='color:#1E8449; font-weight:bold;'>(⬇ {abs(diff)}kg)</span>"
            elif diff >= 0.1:
                w_badge, w_msg, w_disp = "<span class='badge' style='background:#FADBD8; color:#C0392B;'>🚨 증가</span>", f"전일 대비 <b>{diff}kg 증가</b>했습니다. 단순 수분 정체 및 글리코겐 로딩일 확률이 높으니 스트레스 받지 마시고, 전날 나트륨 섭취량을 점검하세요.", f"{day_w}kg <span style='color:#C0392B; font-weight:bold;'>(⬆ {diff}kg)</span>"
            else:
                w_badge, w_msg, w_disp = "<span class='badge' style='background:#FCF3CF; color:#D4AC0D;'>🟡 유지/정체</span>", "전일과 체중이 동일합니다. 대사 적응기이거나 수분 정체기일 수 있습니다. 충분한 수분 섭취와 활동량 유지가 필요합니다.", f"{day_w}kg <span style='color:#D4AC0D; font-weight:bold;'>( - )</span>"
        else:
            w_badge, w_msg, w_disp = "<span class='badge' style='background:#F2F3F4; color:#2C3E50;'>기록 시작</span>", "비교할 전일 데이터가 없습니다. 내일부터 일일 변화량 및 전문 피드백이 제공됩니다.", f"{day_w}kg"
            
        if day_m > 0 and day_f > 0:
            w_msg += f"<br><div style='margin-top:6px; padding-top:6px; border-top:1px dashed #E5E7E9;'><span style='color:#34495E; font-weight:600;'>골격근량: {day_m}kg<br>체지방률: {day_f}%</span></div>"

        habit_table += f"<tr><td><b>체중</b></td><td>{w_badge}</td><td style='text-align:left; font-size:0.85rem;'><b>{w_disp}</b><br><span style='color:#7F8C8D;'>{w_msg}</span></td></tr>"
    
    habit_table += "</table>"
    if habit_df.empty and w_hist_df.empty and bev_df.empty:
        st.info("해당 일자의 습관 및 체중 기록이 없습니다.")
    else:
        st.markdown(habit_table, unsafe_allow_html=True)

elif menu == "📋 대사 진단 리포트":
    st.markdown("<h1>🥑 브쌤's Diet 일지</h1>", unsafe_allow_html=True)
    st.markdown("### 📋 정밀 대사 진단 리포트")
    _, _, _, _, f_text = generate_master_feedback(p)
    st.markdown(f"<div class='report-box'>{f_text}</div>", unsafe_allow_html=True)

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
    act_options = ["1단계 (주로 앉아서 생활)", "2단계 (가벼운 활동/운동)", "3단계 (보통 수준의 활동/운동)", "4단계 (육체노동 또는 강도 높은 운동)"]
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
            
            with st.spinner("클라우드와 동기화 중입니다..."):
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
