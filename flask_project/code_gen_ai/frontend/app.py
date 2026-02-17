import streamlit as st
import requests

st.set_page_config(page_title="CodeGen AI", page_icon="💻", layout="wide")

st.title("💻 Code Generation AI")
st.write("Enter a task description, and AI will generate the code for you.")

prompt = st.text_area("📝 Enter your prompt:", height=150)

if st.button("Generate Code"):
    if prompt.strip():
        with st.spinner("Generating code..."):
            response = requests.post(
                "http://127.0.0.1:8000/generate", 
                json={"prompt": prompt}
            )
            if response.status_code == 200:
                code = response.json()["code"]
                st.code(code, language="python")
            else:
                st.error("Error: Could not get response from API")
    else:
        st.warning("Please enter a prompt first!")
