import streamlit as st
import requests

# Адреса FastAPI бекенду
API_URL = "http://app:8000" # http://app:8000 # Якщо ви запускаєте Streamlit в Docker, використовуйте ім'я сервісу

st.title("Кон-Тики: путь к Земле")

# Створюємо дві вкладки: для завантаження PDF та для запитань до агента
tab1 = st.tabs(["Ask Agent"])

with tab1[0]:
    st.header("Ask your question")
    question = st.text_input("Enter your question:")

    if 'answers' not in st.session_state:
        st.session_state.answers = []

    if st.button("Get Answer") and question:
        # Надсилаємо питання до FastAPI і отримуємо відповідь
        response = requests.post(f"{API_URL}/query", json={"question": question})
        if response.status_code == 200:
            answer = response.json().get("answer")
            st.session_state.answers.append(f"Запит: {question}")
            st.session_state.answers.append(answer)

            st.markdown("### Agent's answer:")
            for ans in st.session_state.answers[::-1]:
                st.write(ans)
        else:
            st.error(f"Error: {response.text}")
