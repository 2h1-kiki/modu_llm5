"""
여행 계획 어시스턴트
- 탭 기반 레이아웃
- 고급 설정 (Accordion)
- 실시간 통계 대시보드
- 조건부 UI
- 이벤트 체이닝
"""

import gradio as gr
import json
import requests
import os
from datetime import datetime, timedelta
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT
import re

# 환경변수 로드
load_dotenv()

# OpenWeatherMap API 키
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")


def create_chain(model_name, temperature, max_tokens):
    prompt = ChatPromptTemplate.from_messages([
        ("system", """당신은 전문 여행 플래너 AI 어시스턴트입니다. 
        
        답변 시 다음 정보를 포함해주세요:
        - 구체적인 장소와 추천 이유
        - 시간대별 일정
        - 예상 비용 (숙박, 식비, 교통, 입장료 등)
        - 교통 수단 및 이동 시간
        - 추천 맛집 및 특산물
        - 여행 팁
        
        답변은 친절하고 구체적으로, 마크다운 형식으로 작성해주세요."""),
        MessagesPlaceholder("chat_history"),
        ("human", "{user_input}")
    ])
    
    model = ChatOpenAI(
        model=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        presence_penalty=0.3,
        frequency_penalty=0.3,
    )
    
    return prompt | model | StrOutputParser()




def get_forecast_weather(city_name, target_datetime):
    """5일 예보 날씨 정보 조회"""
    if not WEATHER_API_KEY:
        return "⚠️ 날씨 API 키가 설정되지 않았습니다."
    
    # 한국 도시명 매핑
    city_mapping = {
        '서울': 'Seoul', '제주도': 'Jeju', '제주': 'Jeju', '부산': 'Busan',
        '인천': 'Incheon', '대구': 'Daegu', '대전': 'Daejeon', '광주': 'Gwangju',
        '울산': 'Ulsan', '강릉': 'Gangneung', '경주': 'Gyeongju', '전주': 'Jeonju',
        '여수': 'Yeosu', '도쿄': 'Tokyo', '오사카': 'Osaka', '대만': 'Taipei',
        'LA': 'Los Angeles', '뉴욕': 'New York', '런던': 'London',
        '파리': 'Paris', '벤쿠버': 'Vancouver',
    }
    
    english_city = city_mapping.get(city_name, city_name)
    
    try:
        # 5일 예보 API 호출
        url = f"http://api.openweathermap.org/data/2.5/forecast?q={english_city}&appid={WEATHER_API_KEY}&units=metric&lang=kr"
        response = requests.get(url, timeout=5)
        
        if response.status_code != 200:
            return f"⚠️ 날씨 정보를 가져올 수 없습니다. (도시: {city_name})"
        
        data = response.json()
        
        # 목표 날짜/시간에 가장 가까운 예보 찾기
        target_timestamp = target_datetime.timestamp()
        closest_forecast = None
        min_diff = float('inf')
        
        for forecast in data['list']:
            forecast_time = forecast['dt']
            diff = abs(forecast_time - target_timestamp)
            
            if diff < min_diff:
                min_diff = diff
                closest_forecast = forecast
        
        if not closest_forecast:
            return "⚠️ 해당 날짜의 예보를 찾을 수 없습니다."
        
        # 예보 시간
        forecast_dt = datetime.fromtimestamp(closest_forecast['dt'])
        
        # 날짜 형식을 영문으로 변경 (인코딩 오류 방지)
        date_str = forecast_dt.strftime('%Y-%m-%d %H:%M')
        
        weather_info = f"""
### 🌤️ {city_name} 날씨 예보

📅 **예보 날짜**: {date_str}

- **예상 기온**: {closest_forecast['main']['temp']:.1f}°C (체감 {closest_forecast['main']['feels_like']:.1f}°C)
- **날씨**: {closest_forecast['weather'][0]['description']}
- **습도**: {closest_forecast['main']['humidity']}%
- **풍속**: {closest_forecast['wind']['speed']:.1f} m/s
- **최저/최고**: {closest_forecast['main']['temp_min']:.1f}°C / {closest_forecast['main']['temp_max']:.1f}°C
- **강수 확률**: {closest_forecast.get('pop', 0) * 100:.0f}%

💡 **여행 팁**: """
        
        # 날씨에 따른 팁
        temp = closest_forecast['main']['temp']
        if temp < 5:
            weather_info += "추운 날씨가 예상됩니다. 따뜻한 옷을 챙기세요! 🧥"
        elif temp < 15:
            weather_info += "쌀쌀한 날씨가 예상됩니다. 가벼운 외투를 준비하세요. 🧥"
        elif temp < 25:
            weather_info += "여행하기 좋은 날씨가 예상됩니다! 😊"
        else:
            weather_info += "더운 날씨가 예상됩니다. 선크림과 물을 챙기세요! ☀️"
        
        # 비 예보
        if closest_forecast.get('pop', 0) > 0.3:
            weather_info += f"\n☔ 강수 확률이 {closest_forecast.get('pop', 0) * 100:.0f}%입니다. 우산을 챙기세요!"
        
        return weather_info
        
    except Exception as e:
        return f"⚠️ 날씨 조회 중 오류 발생: {str(e)}"


def add_budget_calculator(message, response):
    """예산 계산기 추가"""
    if any(word in message for word in ['예산', '비용', '경비', '돈', '얼마']):
        response += "\n\n---\n### 💰 예산 계산 가이드\n\n"
        response += "**국내 여행 기준 (1인당)**\n"
        response += "- 🏨 숙박: 5만원~15만원/박\n"
        response += "- 🍽️ 식비: 3만원~5만원/일\n"
        response += "- 🚗 교통: 지역별 상이\n"
        response += "- 🎫 관광지: 1만원~3만원/일\n"
        response += "- 🛍️ 기타: 2만원~5만원/일\n"
    return response


def add_checklist(message, response):
    """여행 준비 체크리스트 추가"""
    if any(word in message for word in ['준비', '챙겨', '필요', '체크리스트', '준비물']):
        response += "\n\n---\n### ✅ 여행 준비 체크리스트\n\n"
        response += "**필수 준비물**\n"
        response += "- [ ] 신분증/여권\n"
        response += "- [ ] 숙박 예약 확인서\n"
        response += "- [ ] 교통편 예약\n"
        response += "- [ ] 현금/카드\n"
        response += "- [ ] 충전기/보조배터리\n\n"
        response += "**선택 준비물**\n"
        response += "- [ ] 여행자 보험\n"
        response += "- [ ] 상비약\n"
        response += "- [ ] 우산/선크림\n"
        response += "- [ ] 카메라\n"
    return response


def add_map_links(response):
    """지도 링크 추가"""
    locations = {
        '서울': 'Seoul', '부산': 'Busan', '제주': 'Jeju',
        '경주': 'Gyeongju', '강릉': 'Gangneung', '전주': 'Jeonju', '여수': 'Yeosu',
    }
    
    for korean, english in locations.items():
        if korean in response:
            response += f"\n\n🗺️ [{korean} Google Maps에서 보기](https://maps.google.com/?q={english}+Korea)"
            break
    
    return response


def export_conversation(history):
    """대화 내용을 PDF 파일로 저장 (한글 지원)"""
    if not history:
        return None
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"여행계획_{timestamp}.pdf"
    
    try:
        # PDF 문서 생성
        doc = SimpleDocTemplate(filename, pagesize=A4)
        story = []
        
        # 한글 폰트 등록 (Windows 기본 폰트 사용)
        try:
            # Windows 맑은 고딕 폰트 사용
            pdfmetrics.registerFont(TTFont('Malgun', 'malgun.ttf'))
            font_name = 'Malgun'
        except:
            try:
                # 맑은 고딕이 없으면 굴림 사용
                pdfmetrics.registerFont(TTFont('Gulim', 'gulim.ttc'))
                font_name = 'Gulim'
            except:
                # 폰트 등록 실패 시 기본 폰트 사용 (한글 깨짐)
                font_name = 'Helvetica'
        
        # 스타일 설정
        styles = getSampleStyleSheet()
        
        # 제목 스타일
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=font_name,
            fontSize=20,
            spaceAfter=30,
            alignment=TA_LEFT
        )
        
        # 본문 스타일
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['BodyText'],
            fontName=font_name,
            fontSize=10,
            spaceAfter=12,
            leading=14
        )
        
        # 제목 추가
        story.append(Paragraph("여행 계획 대화 내용", title_style))
        story.append(Paragraph(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", body_style))
        story.append(Spacer(1, 0.3*inch))
        
        # 대화 내용 추가
        for i, msg in enumerate(history):
            role = "사용자" if msg['role'] == "user" else "AI 어시스턴트"
            
            # 역할 표시
            role_text = f"<b>{role}:</b>"
            story.append(Paragraph(role_text, body_style))
            
            # 메시지 내용 (마크다운 제거 및 HTML 이스케이프)
            content = msg['content']
            # 마크다운 기호 제거
            content = re.sub(r'[#*`]', '', content)
            # HTML 특수문자 이스케이프
            content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            # 줄바꿈 처리
            content = content.replace('\n', '<br/>')
            
            # 내용이 너무 길면 잘라내기
            if len(content) > 5000:
                content = content[:5000] + "... (내용이 너무 길어 생략됨)"
            
            story.append(Paragraph(content, body_style))
            story.append(Spacer(1, 0.2*inch))
            
            # 구분선
            if i < len(history) - 1:
                story.append(Paragraph("_" * 80, body_style))
                story.append(Spacer(1, 0.1*inch))
        
        # PDF 생성
        doc.build(story)
        return filename
        
    except Exception as e:
        print(f"PDF 생성 오류: {e}")
        # PDF 생성 실패 시 텍스트 파일로 대체
        txt_filename = f"여행계획_{timestamp}.txt"
        content = "=" * 50 + "\n"
        content += "여행 계획 대화 내용\n"
        content += f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += "=" * 50 + "\n\n"
        
        for msg in history:
            role = "사용자" if msg['role'] == "user" else "AI 어시스턴트"
            content += f"{role}:\n{msg['content']}\n\n"
            content += "-" * 50 + "\n\n"
        
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return txt_filename


def answer_invoke_stream(message, history, model_name, temperature, max_tokens):
    """메시지 처리 및 응답 생성 (스트리밍)"""
    chain = create_chain(model_name, temperature, max_tokens)
    
    history_messages = []
    for msg in history:
        if msg['role'] == "user":
            history_messages.append(HumanMessage(content=msg['content']))
        elif msg['role'] == "assistant":
            history_messages.append(AIMessage(content=msg['content']))
    
    history_messages.append(HumanMessage(content=message))
    
    # AI 응답 스트리밍 생성
    full_response = ""
    for chunk in chain.stream({
        "chat_history": history_messages,
        "user_input": message
    }):
        full_response += chunk
        yield full_response
    
    # 추가 기능 적용
    full_response = add_budget_calculator(message, full_response)
    full_response = add_checklist(message, full_response)
    full_response = add_map_links(full_response)
    
    yield full_response


def update_stats(history):
    """대화 통계 업데이트"""
    total = len(history)
    user = sum(1 for msg in history if msg['role'] == 'user')
    ai = sum(1 for msg in history if msg['role'] == 'assistant')
    
    # 키워드 분석
    all_text = " ".join([msg['content'] for msg in history if msg['role'] == 'user'])
    keywords = {
        '제주': all_text.count('제주'),
        '부산': all_text.count('부산'),
        '서울': all_text.count('서울'),
        '예산': all_text.count('예산') + all_text.count('비용'),
    }
    
    return f"💬 {total}", f"👤 {user}", f"🤖 {ai}", keywords


def create_stats_chart(keywords):
    """통계 차트 생성"""
    if not any(keywords.values()):
        return "아직 대화 데이터가 없습니다."
    
    chart = "### 📊 언급된 키워드\n\n"
    for key, count in keywords.items():
        if count > 0:
            bar = "█" * count
            chart += f"**{key}**: {bar} ({count}회)\n"
    
    return chart


# CSS 스타일
custom_css = """
.gradio-container {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.header-text {
    text-align: center;
    padding: 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 10px;
    margin-bottom: 20px;
}

.stat-box {
    text-align: center;
    padding: 15px;
    background: #f8f9fa;
    border-radius: 8px;
    border: 1px solid #dee2e6;
}

.feature-card {
    padding: 15px;
    background: white;
    border-radius: 8px;
    border-left: 4px solid #667eea;
    margin: 10px 0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
"""

# Gradio 인터페이스 구성
with gr.Blocks(title="🌍 LLM5기_6조 여행 계획 어시스턴트") as demo:
    
    # 헤더
    gr.HTML("""
        <div class="header-text">
            <h1>🌍 LLM5기_6조 여행 계획 어시스턴트</h1>
            <p>여행 계획 어시스턴트가 당신만의 완벽한 여행 일정을 만들어드립니다.</p>
        </div>
    """)
    
    # 상태 관리
    chat_history = gr.State([])
    
    # 탭 기반 레이아웃
    with gr.Tabs() as tabs:
        
        # 탭 1: 채팅
        with gr.Tab("💬 채팅", id=0):
            with gr.Row():
                # 왼쪽: 채팅 영역
                with gr.Column(scale=7):
                    chatbot = gr.Chatbot(
                        label="대화",
                        height=800,
                    )
                    
                    with gr.Row():
                        msg = gr.Textbox(
                            label="메시지 입력",
                            placeholder="예: 제주도 2박 3일 여행 계획 짜줘",
                            scale=9,
                            container=False,
                        )
                        submit = gr.Button("전송 📤", variant="primary", scale=1)
                
                # 오른쪽: 빠른 정보
                with gr.Column(scale=3):
                    gr.Markdown("### 📊 실시간 통계")
                    with gr.Row():
                        total_stat = gr.Textbox(label="전체", value="💬 0", interactive=False, container=False)
                        user_stat = gr.Textbox(label="사용자", value="👤 0", interactive=False, container=False)
                        ai_stat = gr.Textbox(label="AI", value="🤖 0", interactive=False, container=False)
                    
                    gr.Markdown("---")
                    
                    # 인기 여행지 & 빠른 질문
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### 🔥 인기 여행지")
                            popular = gr.Dropdown(
                                choices=["서울", "제주도", "도쿄", "대만", "LA", "뉴욕", "런던", "파리", "벤쿠버", "오사카"],
                                label="여행지 선택",
                                value=None,
                                container=False,
                            )
                        
                        with gr.Column(scale=1):
                            gr.Markdown("### 💡 빠른 질문")
                            quick_question_dropdown = gr.Dropdown(
                                choices=["🍽️ 근처 맛집 리스트 찾기", "💰 여행지 예상 비용", "🚗 여행지 가는 방법"],
                                label="질문 선택",
                                value=None,
                                container=False,
                            )
                            apply_quick_btn = gr.Button("✅ 적용", size="sm", variant="primary")
                    
                    gr.Markdown("---")
                    
                    # 기능 안내
                    gr.Markdown("### ✨ 주요 기능")
                    gr.HTML("""
                        <div class="feature-card">
                            <strong>🌤️ 날씨 검색</strong><br>
                            <small>별도 탭에서 날씨 조회</small>
                        </div>
                        <div class="feature-card">
                            <strong>💰 자동 예산 계산</strong><br>
                            <small>'예산', '비용' 키워드</small>
                        </div>
                        <div class="feature-card">
                            <strong>✅ 준비물 체크리스트</strong><br>
                            <small>'준비물', '챙겨' 키워드</small>
                        </div>
                        <div class="feature-card">
                            <strong>🗺️ 지도 링크</strong><br>
                            <small>주요 도시 자동 인식</small>
                        </div>
                    """)
        
        # 탭 2: 날씨 검색
        with gr.Tab("🌤️ 날씨 검색", id=1):
            gr.Markdown("## 🌍 여행지 날씨 정보")
            
            gr.Markdown("""
            여행 계획을 세우기 전에 목적지의 날씨를 확인하세요!
            **5일 이내 날씨 예보**를 제공합니다.
            """)
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📍 여행지 정보 입력")
                    
                    weather_city_input = gr.Textbox(
                        label="도시명",
                        placeholder="예: 서울, Tokyo, Paris, New York",
                        info="한글 또는 영문으로 입력하세요"
                    )
                    
                    gr.Markdown("**인기 여행지 빠른 선택**")
                    with gr.Row():
                        city_btn1 = gr.Button("서울", size="sm")
                        city_btn2 = gr.Button("제주도", size="sm")
                        city_btn3 = gr.Button("도쿄", size="sm")
                    with gr.Row():
                        city_btn4 = gr.Button("파리", size="sm")
                        city_btn5 = gr.Button("뉴욕", size="sm")
                        city_btn6 = gr.Button("런던", size="sm")
                    
                    gr.Markdown("### 📅 날짜 및 시간 선택")
                    
                    # 5일 이내 날짜만 선택 가능하도록 설정
                    from datetime import datetime, timedelta
                    today = datetime.now()
                    max_date = today + timedelta(days=5)
                    
                    weather_date_input = gr.DateTime(
                        label="날짜",
                        value=today,
                        info="오늘부터 5일 이내만 선택 가능",
                        include_time=False,
                        type="datetime"
                    )
                    
                    with gr.Row():
                        weather_hour_input = gr.Dropdown(
                            choices=[f"{i}시" for i in range(1, 13)],
                            label="시간",
                            value="12시",
                            scale=1
                        )
                        weather_ampm_input = gr.Radio(
                            choices=["오전", "오후"],
                            label="AM/PM",
                            value="오후",
                            scale=1
                        )
                    
                    gr.Markdown(f"**선택 가능 기간**: {today.strftime('%Y-%m-%d')} ~ {max_date.strftime('%Y-%m-%d')}")
                    
                    gr.Markdown("**빠른 날짜 선택**")
                    with gr.Row():
                        today_btn = gr.Button("오늘 오후 12시", size="sm")
                        tomorrow_btn = gr.Button("내일 오후 12시", size="sm")
                        day3_btn = gr.Button("모레 오후 12시", size="sm")
                    
                    weather_search_btn = gr.Button("🔍 날씨 조회", variant="primary", size="lg")
                
                with gr.Column(scale=2):
                    gr.Markdown("### 🌤️ 날씨 정보")
                    weather_result = gr.Markdown("""
                    왼쪽에서 도시와 날짜/시간을 선택한 후 '날씨 조회' 버튼을 클릭하세요.
                    
                    **제공 정보:**
                    - 🌡️ 예상 기온 및 체감 온도
                    - ☁️ 날씨 상태 (맑음, 흐림, 비 등)
                    - 💧 습도
                    - 💨 풍속
                    - 📊 최저/최고 기온
                    - ☔ 강수 확률
                    - 💡 날씨에 따른 여행 팁
                    """)
            
            gr.Markdown("---")
            
            gr.Markdown("### 💡 사용 팁")
            gr.Markdown("""
            - **도시명 입력**: 한글(서울, 제주도) 또는 영문(Seoul, Tokyo) 모두 가능
            - **날짜 선택**: 오늘부터 5일 이내 날짜 입력 (YYYY-MM-DD 형식)
            - **시간 선택**: 드롭다운에서 시간 선택 (3시간 단위 예보)
            - **빠른 선택**: 인기 여행지/날짜 버튼으로 빠르게 입력
            - **5일 예보**: 무료 API로 5일 이내 날씨 예보 제공
            """)
        
        # 탭 3: 통계
        with gr.Tab("📊 통계 대시보드", id=2):
            gr.Markdown("## 📈 대화 분석")
            
            with gr.Row():
                with gr.Column():
                    stats_total = gr.Textbox(label="총 메시지", value="0", interactive=False)
                with gr.Column():
                    stats_user = gr.Textbox(label="사용자 메시지", value="0", interactive=False)
                with gr.Column():
                    stats_ai = gr.Textbox(label="AI 메시지", value="0", interactive=False)
            
            gr.Markdown("---")
            
            keyword_chart = gr.Markdown("### 📊 키워드 분석\n\n아직 대화 데이터가 없습니다.")
            
            refresh_stats = gr.Button("🔄 통계 새로고침", variant="secondary")
        
        # 탭 4: 설정
        with gr.Tab("⚙️ 설정", id=3):
            gr.Markdown("## 🎛️ AI 모델 설정")
            
            with gr.Accordion("🤖 모델 선택", open=True):
                model_choice = gr.Dropdown(
                    choices=["gpt-4.1-nano", "gpt-4.1-mini", "gpt-4o-mini"],
                    value="gpt-4.1-nano",
                    label="모델",
                    info="더 큰 모델일수록 더 상세한 답변을 제공합니다"
                )
            
            with gr.Accordion("🎨 응답 스타일", open=True):
                temperature = gr.Slider(
                    minimum=0,
                    maximum=1,
                    value=0.7,
                    step=0.1,
                    label="창의성 (Temperature)",
                    info="높을수록 더 창의적이고 다양한 답변"
                )
                
                max_tokens = gr.Slider(
                    minimum=500,
                    maximum=3000,
                    value=2000,
                    step=100,
                    label="최대 응답 길이",
                    info="더 긴 답변을 원하면 값을 높이세요"
                )
            
            gr.Markdown("---")
            
            gr.Markdown("### 💡 설정 가이드")
            gr.Markdown("""
            - **gpt-4.1-nano**: 빠르고 경제적 (추천)
            - **gpt-4.1-mini**: 균형잡힌 성능
            - **gpt-4o-mini**: 가장 상세한 답변
            
            - **창의성 0.3**: 정확하고 일관된 답변
            - **창의성 0.7**: 균형잡힌 답변 (추천)
            - **창의성 1.0**: 창의적이고 다양한 답변
            """)
            
            reset_settings = gr.Button("🔄 기본값으로 초기화", variant="secondary")
        
        # 탭 5: 세션 관리
        with gr.Tab("📂 세션 관리", id=4):
            gr.Markdown("## 💾 대화 세션 관리")
            
            gr.Markdown("""
            대화 기록을 관리하고 저장할 수 있습니다.
            """)
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 🗑️ 대화 초기화")
                    gr.Markdown("""
                    현재 대화 내용을 모두 삭제합니다.
                    - 채팅 기록 삭제
                    - 통계 초기화
                    - 되돌릴 수 없으니 주의하세요!
                    """)
                    clear_session = gr.Button("🗑️ 대화 초기화", variant="stop", size="lg")
                    clear_status = gr.Markdown("")
                
                with gr.Column():
                    gr.Markdown("### 📥 대화 내보내기")
                    gr.Markdown("""
                    현재 대화 내용을 텍스트 파일로 저장합니다.
                    - 사용자 질문과 AI 답변 포함
                    - 타임스탬프 자동 추가
                    - 여행 계획 보관용으로 활용
                    """)
                    export_session = gr.Button("📥 대화 내보내기", variant="primary", size="lg")
                    download_file = gr.File(label="다운로드 파일", visible=False)
            
            gr.Markdown("---")
            
            gr.Markdown("### 📊 현재 세션 정보")
            with gr.Row():
                with gr.Column():
                    session_total = gr.Textbox(label="총 메시지 수", value="0", interactive=False)
                with gr.Column():
                    session_user = gr.Textbox(label="사용자 메시지", value="0", interactive=False)
                with gr.Column():
                    session_ai = gr.Textbox(label="AI 메시지", value="0", interactive=False)
            
            refresh_session = gr.Button("🔄 세션 정보 새로고침", variant="secondary")
    
    # 함수 정의
    def user_message(message, history):
        """사용자 메시지 추가"""
        return "", history + [{"role": "user", "content": message}]
    
    def bot_response(history, model_name, temp, max_tok):
        """봇 응답 생성 (스트리밍)"""
        user_msg = history[-1]["content"]
        
        for response_chunk in answer_invoke_stream(user_msg, history[:-1], model_name, temp, max_tok):
            if len(history) > 0 and history[-1]["role"] == "assistant":
                history[-1] = {"role": "assistant", "content": response_chunk}
            else:
                history.append({"role": "assistant", "content": response_chunk})
            
            stats = update_stats(history)
            yield history, history, *stats[:3]
    
    def clear_chat():
        """대화 초기화"""
        gr.Info("대화가 초기화되었습니다!")
        return [], [], "💬 0", "👤 0", "🤖 0", "✅ 대화가 초기화되었습니다.", "0", "0", "0"
    
    def export_chat(history):
        """대화 내보내기 (PDF)"""
        if not history:
            gr.Warning("저장할 대화가 없습니다.")
            return None
        filename = export_conversation(history)
        gr.Info("대화가 PDF 파일로 저장되었습니다!")
        return gr.File(value=filename, visible=True)
    
    def quick_question(destination):
        """인기 여행지 빠른 질문"""
        if destination:
            return f"{destination} 2박 3일 여행 계획 짜줘"
        return ""
    
    def create_quick_prompt(destination, question_type):
        """인기 여행지 + 빠른 질문 조합"""
        if not destination:
            # 여행지가 선택되지 않은 경우 기본 질문
            if question_type == "맛집":
                return "근처 맛집 리스트 알려줘"
            elif question_type == "비용":
                return "여행 예상 비용 알려줘"
            elif question_type == "방법":
                return "가는 방법 알려줘"
        else:
            # 여행지가 선택된 경우 조합
            if question_type == "맛집":
                return f"{destination} 근처 맛집 리스트 알려줘"
            elif question_type == "비용":
                return f"{destination} 여행 예상 비용 알려줘"
            elif question_type == "방법":
                if destination in ["서울", "제주도"]:
                    return f"서울에서 {destination} 가는 방법 알려줘"
                else:
                    return f"{destination} 가는 방법 알려줘"
        return ""
    
    def apply_quick_question(destination, question_dropdown):
        """드롭다운에서 선택한 질문 적용"""
        if not question_dropdown:
            gr.Warning("빠른 질문을 선택해주세요!")
            return ""
        
        # 드롭다운 텍스트에서 질문 타입 추출
        if "맛집" in question_dropdown:
            question_type = "맛집"
        elif "비용" in question_dropdown:
            question_type = "비용"
        elif "방법" in question_dropdown:
            question_type = "방법"
        else:
            return ""
        
        return create_quick_prompt(destination, question_type)
    
    def check_weather_new(city, target_date, hour_str, ampm):
        """날씨 확인 (새 탭용 - 5일 예보)"""
        if not city or city.strip() == "":
            return "⚠️ 도시명을 입력해주세요."
        
        try:
            # 현재 시간
            now = datetime.now()
            
            # datetime 객체가 아닌 경우 처리
            if not isinstance(target_date, datetime):
                return "⚠️ 날짜를 선택해주세요."
            
            # 시간 파싱 (예: "12시" -> 12)
            hour = int(hour_str.replace("시", ""))
            
            # AM/PM 처리
            if ampm == "오후" and hour != 12:
                hour += 12
            elif ampm == "오전" and hour == 12:
                hour = 0
            
            # 날짜와 시간 결합
            target_datetime = target_date.replace(hour=hour, minute=0, second=0, microsecond=0)
            
            # 5일 이내 체크
            days_diff = (target_datetime - now).days
            hours_diff = (target_datetime - now).total_seconds() / 3600
            
            if hours_diff < 0:
                return "⚠️ 과거 날짜/시간은 조회할 수 없습니다. 현재 이후를 선택해주세요."
            elif days_diff > 5:
                return "⚠️ 5일 이내 날짜만 조회 가능합니다. 더 가까운 날짜를 선택해주세요."
            
            # 5일 예보 조회
            return get_forecast_weather(city.strip(), target_datetime)
            
        except Exception as e:
            return f"⚠️ 오류 발생: {str(e)}"
    
    def set_date_quick(days_offset):
        """빠른 날짜 선택 - 날짜만 반환"""
        target_date = datetime.now() + timedelta(days=days_offset)
        return target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def set_time_quick():
        """빠른 시간 선택 - 오후 12시"""
        return "12시", "오후"
    
    def set_city(city_name):
        """빠른 선택 버튼으로 도시 설정"""
        return city_name
    
    def refresh_statistics(history):
        """통계 새로고침"""
        if not history:
            return "0", "0", "0", "### 📊 키워드 분석\n\n아직 대화 데이터가 없습니다."
        
        total, user, ai, keywords = update_stats(history)
        chart = create_stats_chart(keywords)
        
        return total.split()[1], user.split()[1], ai.split()[1], chart
    
    def refresh_session_info(history):
        """세션 정보 새로고침"""
        if not history:
            return "0", "0", "0"
        
        total = len(history)
        user = sum(1 for msg in history if msg['role'] == 'user')
        ai = sum(1 for msg in history if msg['role'] == 'assistant')
        
        return str(total), str(user), str(ai)
    
    def reset_to_default():
        """설정 초기화"""
        gr.Info("설정이 기본값으로 초기화되었습니다!")
        return "gpt-4.1-nano", 0.7, 2000
    
    # 빠른 질문 적용 버튼
    apply_quick_btn.click(
        apply_quick_question,
        [popular, quick_question_dropdown],
        msg
    )
    
    # 날씨 검색 탭 이벤트
    weather_search_btn.click(
        check_weather_new,
        [weather_city_input, weather_date_input, weather_hour_input, weather_ampm_input],
        weather_result
    )
    
    # 도시 빠른 선택 버튼
    city_btn1.click(lambda: "서울", None, weather_city_input)
    city_btn2.click(lambda: "제주도", None, weather_city_input)
    city_btn3.click(lambda: "도쿄", None, weather_city_input)
    city_btn4.click(lambda: "파리", None, weather_city_input)
    city_btn5.click(lambda: "뉴욕", None, weather_city_input)
    city_btn6.click(lambda: "런던", None, weather_city_input)
    
    # 날짜 빠른 선택 버튼 (날짜, 시간, AM/PM 모두 설정)
    today_btn.click(
        lambda: (set_date_quick(0), "12시", "오후"),
        None,
        [weather_date_input, weather_hour_input, weather_ampm_input]
    )
    tomorrow_btn.click(
        lambda: (set_date_quick(1), "12시", "오후"),
        None,
        [weather_date_input, weather_hour_input, weather_ampm_input]
    )
    day3_btn.click(
        lambda: (set_date_quick(2), "12시", "오후"),
        None,
        [weather_date_input, weather_hour_input, weather_ampm_input]
    )
    
    # 메시지 전송 이벤트
    msg.submit(
        user_message,
        [msg, chat_history],
        [msg, chat_history]
    ).then(
        bot_response,
        [chat_history, model_choice, temperature, max_tokens],
        [chat_history, chatbot, total_stat, user_stat, ai_stat]
    )
    
    submit.click(
        user_message,
        [msg, chat_history],
        [msg, chat_history]
    ).then(
        bot_response,
        [chat_history, model_choice, temperature, max_tokens],
        [chat_history, chatbot, total_stat, user_stat, ai_stat]
    )
    
    # 통계 새로고침
    refresh_stats.click(
        refresh_statistics,
        chat_history,
        [stats_total, stats_user, stats_ai, keyword_chart]
    )
    
    # 설정 초기화
    reset_settings.click(
        reset_to_default,
        None,
        [model_choice, temperature, max_tokens]
    )
    
    # 세션 관리 이벤트
    clear_session.click(
        clear_chat,
        None,
        [chat_history, chatbot, total_stat, user_stat, ai_stat, clear_status, session_total, session_user, session_ai]
    )
    
    export_session.click(export_chat, chat_history, download_file)
    
    refresh_session.click(
        refresh_session_info,
        chat_history,
        [session_total, session_user, session_ai]
    )


if __name__ == "__main__":
    demo.launch(
        share=False,
        server_name="127.0.0.1",
        server_port=7863,
        css=custom_css,
    )
