import json
import os
import streamlit as st
from PIL import Image
import base64
from io import BytesIO
import google.generativeai as genai

# Page configuration for mobile view optimized layout
st.set_page_config(
    page_title="토익 오답 & 단어 노트",
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for mobile-friendly UI
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        justify-content: center;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #ffffff;
        border-radius: 10px;
        font-weight: bold;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stTabs [aria-selected="true"] {
        background-color: #007bff !important;
        color: white !important;
    }
    div.stButton > button {
        width: 100%;
        border-radius: 10px;
        font-weight: bold;
        height: 45px;
    }
    .card-container {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

DATA_FILE = "toeic_notes.json"
IMAGE_DIR = "uploaded_images"

# Ensure image directory exists
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_gemini_api_key():
    api_key = None
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
    
    with st.sidebar:
        st.subheader("⚙️ 설정")
        user_key = st.text_input("Gemini API 키", value=api_key or "", type="password", help="Google AI Studio에서 발급받은 API 키를 입력하세요.")
        if user_key:
            api_key = user_key
            
    return api_key

def analyze_image_with_gemini(image, api_key):
    if not api_key:
        st.warning("Gemini API 키가 설정되지 않아 AI 자동 분석을 건너뜁니다. 사이드바에서 API 키를 입력해 주세요.")
        return None, None
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = """
        이 이미지는 토익(TOEIC) 문제 또는 단어장 사진입니다. 이미지 내용을 분석하여 다음 JSON 형식으로만 정확히 답변해주세요. 다른 설명이나 마크다운 백틱(```json 등)은 붙이지 말고 순수 JSON 문자열만 출력하세요.
        {
            "title": "문제 번호 또는 핵심 단어 요약 (예: Part 5 101번 또는 Acquired)",
            "content": "문제 내용, 보기, 정답 및 상세한 해설을 정리해서 작성"
        }
        """
        
        response = model.generate_content([prompt, image])
        result_text = response.text.strip()
        
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
            
        parsed = json.loads(result_text.strip())
        return parsed.get("title", ""), parsed.get("content", "")
    except Exception as e:
        st.error(f"AI 분석 중 오류가 발생했습니다: {e}")
        return None, None

def main():
    api_key = get_gemini_api_key()
    
    st.markdown("<h2 style='text-align: center; color: #007bff;'>🎯 토익 오답 & 단어 노트</h2>", unsafe_allow_html=True)
    st.write("")

    notes = load_data()

    tab1, tab2 = st.tabs(["📝 문제/단어 등록", "🔄 오답 노트/복습"])

    with tab1:
        st.markdown("### 새로운 오답/단어 추가")
        
        if "ai_title" not in st.session_state:
            st.session_state.ai_title = ""
        if "ai_content" not in st.session_state:
            st.session_state.ai_content = ""
            
        uploaded_file = st.file_uploader("사진 업로드 (카메라 촬영 또는 갤러리 선택)", type=["jpg", "jpeg", "png"])
        
        if uploaded_file is not None:
            img = Image.open(uploaded_file)
            st.image(img, caption="업로드된 사진 미리보기", use_container_width=True)
            
            if st.button("🤖 Gemini AI로 사진 자동 분석하기"):
                with st.spinner("AI가 사진 속 문제와 해설을 분석 중입니다..."):
                    t, c = analyze_image_with_gemini(img, api_key)
                    if t is not None:
                        st.session_state.ai_title = t
                        st.session_state.ai_content = c
                        st.success("AI 분석 완료! 아래 입력란에 내용이 자동으로 채워졌습니다.")

        with st.form("note_form", clear_on_submit=False):
            note_type = st.radio("유형 선택", ["단어", "오답 문제"], horizontal=True)
            title = st.text_input("제목", value=st.session_state.ai_title, placeholder="핵심 제목을 입력하세요")
            content = st.text_area("내용 및 해설", value=st.session_state.ai_content, placeholder="문제 내용, 단어 뜻, 오답 이유 및 해설을 입력하세요")
            
            submitted = st.form_submit_button("저장하기")
            
            if submitted:
                if not title.strip() or not content.strip():
                    st.error("제목과 내용은 필수 입력 항목입니다.")
                else:
                    image_path = None
                    if uploaded_file is not None:
                        image_filename = f"{os.urandom(8).hex()}_{uploaded_file.name}"
                        image_path = os.path.join(IMAGE_DIR, image_filename)
                        img.save(image_path)
                    
                    new_item = {
                        "id": os.urandom(4).hex(),
                        "type": note_type,
                        "title": title,
                        "content": content,
                        "image_path": image_path
                    }
                    
                    notes.append(new_item)
                    save_data(notes)
                    st.session_state.ai_title = ""
                    st.session_state.ai_content = ""
                    st.success("성공적으로 저장되었습니다!")
                    st.rerun()

    with tab2:
        st.markdown("### 플래시카드 복습 및 리스트")
        
        if not notes:
            st.info("저장된 노트가 없습니다. '문제/단어 등록' 탭에서 첫 번째 노트를 추가해 보세요!")
        else:
            filter_type = st.selectbox("필터", ["전체", "단어", "오답 문제"])
            
            filtered_notes = notes if filter_type == "전체" else [n for n in notes if n["type"] == filter_type]
            
            if not filtered_notes:
                st.warning(f"'{filter_type}' 유형의 저장된 데이터가 없습니다.")
            else:
                review_mode = st.radio("보기 방식", ["플래시카드 (카드형)", "리스트 전체보기"], horizontal=True)
                
                if review_mode == "플래시카드 (카드형)":
                    if "card_index" not in st.session_state:
                        st.session_state.card_index = 0
                    
                    if st.session_state.card_index >= len(filtered_notes):
                        st.session_state.card_index = 0
                        
                    current_note = filtered_notes[st.session_state.card_index]
                    
                    st.markdown(f"카드 **{st.session_state.card_index + 1}** / {len(filtered_notes)}")
                    
                    with st.container():
                        st.markdown(f"""
                        <div class="card-container">
                            <span style="background-color: #007bff; color: white; padding: 3px 8px; border-radius: 5px; font-size: 0.8rem;">{current_note['type']}</span>
                            <h3 style="margin-top: 10px; color: #333;">{current_note['title']}</h3>
                            <hr style="margin: 10px 0;">
                            <p style="white-space: pre-wrap; color: #555; font-size: 1.1rem;">{current_note['content']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if current_note.get("image_path") and os.path.exists(current_note["image_path"]):
                            st.image(current_note["image_path"], use_container_width=True)
                    
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col1:
                        if st.button("⬅️ 이전"):
                            st.session_state.card_index = (st.session_state.card_index - 1) % len(filtered_notes)
                            st.rerun()
                    with col2:
                        if st.button("🗑️ 현재 카드 삭제"):
                            notes = [n for n in notes if n["id"] != current_note["id"]]
                            if current_note.get("image_path") and os.path.exists(current_note["image_path"]):
                                try:
                                    os.remove(current_note["image_path"])
                                except:
                                    pass
                            save_data(notes)
                            st.session_state.card_index = 0
                            st.success("삭제되었습니다!")
                            st.rerun()
                    with col3:
                        if st.button("다음 ➡️"):
                            st.session_state.card_index = (st.session_state.card_index + 1) % len(filtered_notes)
                            st.rerun()
                            
                else:
                    for i, note in enumerate(filtered_notes):
                        with st.expander(f"[{note['type']}] {note['title']}"):
                            st.write(f"**내용 및 해설:**")
                            st.markdown(f"<div style='background-color: #fff; padding: 10px; border-radius: 5px;'>{note['content']}</div>", unsafe_allow_html=True)
                            
                            if note.get("image_path") and os.path.exists(note["image_path"]):
                                st.image(note["image_path"], use_container_width=True)
                                
                            if st.button(f"삭제하기", key=f"del_{note['id']}"):
                                notes = [n for n in notes if n["id"] != note["id"]]
                                if note.get("image_path") and os.path.exists(note["image_path"]):
                                    try:
                                        os.remove(note["image_path"])
                                    except:
                                        pass
                                save_data(notes)
                                st.success("삭제되었습니다!")
                                st.rerun()

if __name__ == "__main__":
    main()
