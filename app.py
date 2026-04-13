import streamlit as st
import pdfplumber

st.set_page_config(page_title="AI Resume Analyzer", layout="centered")

# Load skills database
with open("skills.txt", "r") as f:
    skills_db = [skill.strip().lower() for skill in f.readlines()]

st.title("📄 AI Resume Analyzer")
st.write("Upload your resume and get ATS-style feedback instantly.")

uploaded_file = st.file_uploader("Upload Resume PDF", type=["pdf"])
job_desc = st.text_area("Paste Job Description Here")

if uploaded_file:
    text = ""

    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted

    text_lower = text.lower()

    matched_skills = [skill for skill in skills_db if skill in text_lower]
    missing_skills = [skill for skill in skills_db if skill not in matched_skills]

    score = int((len(matched_skills) / len(skills_db)) * 100)

    st.subheader("📊 ATS Resume Score")
    st.progress(score)
    st.success(f"Your Resume Score: {score}%")

    if job_desc:
        jd_words = job_desc.lower().split()

        matched_jd_keywords = [word for word in jd_words if word in text_lower]

        jd_score = int((len(set(matched_jd_keywords)) / len(set(jd_words))) * 100)

        st.subheader("🎯 Job Match Score")
        st.progress(jd_score)
        st.info(f"Resume matches {jd_score}% of Job Description")


    st.subheader("✅ Detected Skills")
    st.write(", ".join(matched_skills) if matched_skills else "No skills detected.")

    st.subheader("⚠ Suggested Skills to Add")
    st.write(", ".join(missing_skills[:10]))