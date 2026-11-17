
import csv
from pathlib import Path

import pdfplumber
import streamlit as st

from database import (
    init_db, save_student, save_skill, get_skills,
    save_project, get_projects, get_faculty, sync_faculty
)
from recommendations import (
    ROLE_SKILLS, skill_gaps, calculate_growth, match_faculty
)

BASE_DIR = Path(__file__).resolve().parent
SKILLS_FILE = BASE_DIR / "skills.txt"
FACULTY_FILE = BASE_DIR / "faculty.csv"

st.set_page_config(
    page_title="AI Resume Improver",
    page_icon="📄",
    layout="wide"
)


init_db()

if FACULTY_FILE.exists():
    sync_faculty(FACULTY_FILE)

if SKILLS_FILE.exists():
    with SKILLS_FILE.open(encoding="utf-8") as file:
        skills_db = [
            line.strip().lower()
            for line in file
            if line.strip()
        ]
else:
    skills_db = []

st.title("📄 AI Resume Improver & Career Growth Tracker")
st.caption(
    "Analyze your resume, track semester-wise skills, "
    "identify career gaps and discover verified faculty matches."
)

# Student profile shared by all modules
st.sidebar.header("Student Profile")
student_id = st.sidebar.text_input("Student ID", value="student_demo")
student_name = st.sidebar.text_input("Student name")
target_role = st.sidebar.selectbox(
    "Target career",
    list(ROLE_SKILLS.keys())
)

if student_id.strip():
    save_student(
        student_id.strip(),
        student_name.strip() or "Student",
        target_role
    )

if not student_id.strip():
    st.warning("Enter a Student ID to use the tracker.")
    st.stop()

tabs = st.tabs([
    "Resume Analyzer",
    "Skill Tracker",
    "Career Roadmap",
    "Resume Improver",
    "Faculty Matching"
])

# --------------------------------------------------
# 1. EXISTING RESUME ANALYZER
# --------------------------------------------------
with tabs[0]:
    st.header("Resume Analyzer")
    st.write("Upload your PDF and optionally paste a job description.")

    uploaded_file = st.file_uploader(
        "Upload Resume PDF",
        type=["pdf"],
        key="resume_pdf"
    )
    job_desc = st.text_area(
        "Paste Job Description Here",
        key="job_description"
    )

    if uploaded_file:
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                resume_text = "\n".join(
                    page.extract_text() or ""
                    for page in pdf.pages
                )

            st.session_state["resume_text"] = resume_text
            text_lower = resume_text.lower()

            matched_skills = [
                skill for skill in skills_db
                if skill in text_lower
            ]
            missing_skills = [
                skill for skill in skills_db
                if skill not in matched_skills
            ]

            # Retain the original score calculation.
            score = (
                int(len(matched_skills) / len(skills_db) * 100)
                if skills_db else 0
            )

            st.subheader("📊 ATS-style Resume Score")
            st.progress(score)
            st.success(f"Skills coverage score: {score}%")

            st.caption(
                "This is a skills coverage estimate, not a "
                "validated commercial ATS score."
            )

            if job_desc.strip():
                jd_words = set(job_desc.lower().split())
                resume_words = set(text_lower.split())
                jd_score = int(
                    len(jd_words & resume_words) / len(jd_words) * 100
                ) if jd_words else 0

                st.subheader("🎯 Job Description Match")
                st.progress(jd_score)
                st.info(f"Keyword overlap: {jd_score}%")

            st.subheader("✅ Detected Skills")
            st.write(", ".join(matched_skills) or "No skills detected.")

            st.subheader("⚠ Skills to Review")
            st.write(", ".join(missing_skills[:10]) or "None identified.")

        except Exception as error:
            st.error(f"Could not read this PDF: {error}")

    else:
        st.info("Upload a PDF to analyze your resume.")

# --------------------------------------------------
# 2. SEMESTER-WISE SKILL TRACKER
# --------------------------------------------------
with tabs[1]:
    st.header("Semester-wise Skill Tracker")

    with st.form("skill_form"):
        skill = st.text_input("Skill name")
        semester = st.selectbox("Semester", range(1, 9))
        rating = st.slider("Self-assessed level", 1, 5, 3)
        evidence_type = st.selectbox(
            "Evidence type",
            ["Project", "Certificate", "Coursework", "Assessment", "Other"]
        )
        evidence = st.text_area(
            "Evidence or project link",
            placeholder="Describe the work demonstrating this skill."
        )
        submitted = st.form_submit_button("Save Skill Record")

        if submitted:
            if not skill.strip() or not evidence.strip():
                st.error("Enter both a skill and its evidence.")
            else:
                save_skill(
                    student_id, skill, semester, rating,
                    evidence, evidence_type
                )
                st.success("Skill record saved.")
                st.rerun()

    records = get_skills(student_id)
    if records:
        st.subheader("Your skill history")
        st.dataframe(
            [dict(row) for row in records],
            use_container_width=True
        )

        growth = calculate_growth(records)
        if growth:
            st.subheader("Skill Growth")
            st.dataframe(growth, use_container_width=True)
        else:
            st.info(
                "Record the same skill in another semester "
                "to see its rating change."
            )
    else:
        st.info("No skill records yet. Add your first skill above.")

    st.subheader("Add a Project")
    with st.form("project_form"):
        project_title = st.text_input("Project title")
        project_description = st.text_area("Project description")
        project_skills = st.text_input(
            "Skills used (comma-separated)"
        )
        project_url = st.text_input("GitHub or project URL (optional)")
        project_semester = st.selectbox(
            "Project semester", range(1, 9), key="project_semester"
        )
        project_submitted = st.form_submit_button("Save Project")

        if project_submitted:
            if not project_title.strip() or not project_description.strip():
                st.error("Project title and description are required.")
            else:
                save_project(
                    student_id, project_title, project_description,
                    project_skills, project_url, project_semester
                )
                st.success("Project saved.")
                st.rerun()

    projects = get_projects(student_id)
    if projects:
        st.subheader("Recorded Projects")
        st.dataframe(
            [dict(row) for row in projects],
            use_container_width=True
        )

# --------------------------------------------------
# 3. CAREER ROADMAP AND SKILL GAPS
# --------------------------------------------------
with tabs[2]:
    st.header("Career Skill Gap Analysis")
    st.write(f"Selected career: **{target_role}**")

    records = get_skills(student_id)
    recorded_skills = list({
        row["skill"] for row in records
    })

    # Include skills detected in the current resume too.
    resume_text = st.session_state.get("resume_text", "").lower()
    resume_skills = [
        skill for skill in skills_db if skill in resume_text
    ]
    all_skills = list(set(recorded_skills + resume_skills))

    gaps = skill_gaps(target_role, all_skills)

    left, right = st.columns(2)
    left.metric("Required skills matched", len(gaps["matched"]))
    right.metric("Skills to develop", len(gaps["missing"]))

    st.subheader("Skills already identified")
    st.write(", ".join(gaps["matched"]) or "None identified yet.")

    st.subheader("Suggested skills to learn")
    st.write(", ".join(gaps["missing"]) or "All mapped skills identified.")

    if gaps["missing"]:
        st.caption(
            "Suggested next steps: choose one missing skill, "
            "complete a course or project, and record evidence "
            "in the Skill Tracker."
        )

    st.subheader("Career skill requirements")
    st.write(", ".join(ROLE_SKILLS[target_role]))

# --------------------------------------------------
# 4. RESUME IMPROVER
# --------------------------------------------------
with tabs[3]:
    st.header("Resume Improver")
    resume_text = st.session_state.get("resume_text", "")

    if not resume_text.strip():
        st.info("Upload a resume in the Resume Analyzer tab first.")
    else:
        st.subheader("Resume section checklist")

        checks = {
            "Contact information": ["email", "phone", "linkedin"],
            "Education": ["education", "university", "degree"],
            "Projects": ["project", "developed", "built"],
            "Experience": ["experience", "internship", "worked"],
            "Skills": ["skills", "technical skills"],
        }

        lower_text = resume_text.lower()
        for section, keywords in checks.items():
            present = any(word in lower_text for word in keywords)
            st.write(
                f"{'✅' if present else '⚠️'} {section}: "
                f"{'Possible match found' if present else 'Review this section'}"
            )

        st.subheader("Improvement suggestions")
        st.write(
            "- Start bullet points with clear action verbs.\n"
            "- Describe your contribution, tools used and measurable result.\n"
            "- Include relevant projects for your selected career.\n"
            "- Use consistent headings, dates and formatting.\n"
            "- Add metrics only when you can substantiate them."
        )

        st.subheader("Improve one bullet point")
        original_bullet = st.text_area(
            "Paste a bullet point from your resume"
        )
        action = st.text_input("Action verb", value="Developed")
        tools_used = st.text_input("Tools or technologies used")
        outcome = st.text_input(
            "Verified result or impact (optional)"
        )

        if st.button("Generate improved bullet"):
            if not original_bullet.strip() or not tools_used.strip():
                st.warning("Enter the original bullet and tools used.")
            else:
                improved = (
                    f"{action.strip()} {original_bullet.strip().rstrip('.')}"
                    f" using {tools_used.strip()}"
                )
                if outcome.strip():
                    improved += f", resulting in {outcome.strip()}"
                st.write("**Suggested version**")
                st.write(improved)
                st.caption(
                    "Review the wording and keep only claims you can verify."
                )

        st.info(
            "This initial version uses transparent rules and templates. "
            "It does not yet use a generative AI model."
        )

# --------------------------------------------------
# 5. VERIFIED FACULTY MATCHING
# --------------------------------------------------
with tabs[4]:
    st.header("Verified Faculty Matching")
    st.write(
        "Find faculty whose recorded expertise overlaps "
        "with your career skill gaps."
    )

    records = get_skills(student_id)
    recorded_skills = list({row["skill"] for row in records})
    resume_text = st.session_state.get("resume_text", "").lower()
    resume_skills = [
        skill for skill in skills_db if skill in resume_text
    ]

    gaps = skill_gaps(
        target_role,
        list(set(recorded_skills + resume_skills))
    )
    faculty = get_faculty()
    matches = match_faculty(gaps["missing"], faculty)

    if not faculty:
        st.warning(
            "No verified faculty records are available yet. "
            "Collect and verify official faculty profiles, then "
            "add them to faculty.csv."
        )
    elif not matches:
        st.info(
            "No verified faculty matches found for the current skill gaps."
        )
    else:
        for item in matches:
            st.subheader(item["name"])
            st.write(f"Department: {item['department'] or 'Not specified'}")
            st.write(
                "Matching expertise: "
                + ", ".join(item["expertise_match"])
            )
            if item["profile_url"].startswith("https://"):
                st.markdown(
                    f"[Official profile]({item['profile_url']})"
                )
            st.divider()

st.caption(
    "Privacy note: This prototype stores student records in a local "
    "SQLite database. Use a secure, persistent database and appropriate "
    "access controls before deploying it for multiple real students."
)
