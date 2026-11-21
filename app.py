"""
Job Intelligence Dashboard - Multi-User Edition
Streamlit web application with Supabase authentication.
Each user has their own profile, skills, and job tracking data.
"""
import time
_t0 = time.time()
import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from skill_matcher import SkillMatcher
from resume_parser import parse_resume
from supabase_client import (
    sign_up_user,
    sign_in_user,
    sign_out_user,
    get_user_profile,
    update_user_profile,
    get_user_skills,
    add_user_skill,
    delete_user_skill,
    clear_user_skills,
    clear_user_experiences,
    clear_user_projects,
    clear_user_education,
    get_user_experiences,
    add_user_experience,
    get_user_projects,
    add_user_project,
    get_user_education,
    add_user_education,
    get_user_jobs,
    update_user_job_status,
)

print(f"[TIMING] imports: {time.time() - _t0:.2f}s")

matcher = SkillMatcher()

# ---------------------------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Job Intelligence Dashboard",
    page_icon="Jobs",
    layout="wide",
    initial_sidebar_state="expanded",
)



# ---------------------------------------------------------------------------
# AUTH STATE
# ---------------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

# ===========================================================================
# LOGIN / SIGNUP SCREEN
# ===========================================================================
if st.session_state.user is None:
    st.title("Job Intelligence Dashboard")
    st.caption("Sign in or create an account to get started")

    auth_tab1, auth_tab2 = st.tabs(["Sign In", "Sign Up"])

    with auth_tab1:
        with st.form("sign_in_form"):
            st.subheader("Welcome back")
            sign_in_email = st.text_input("Email", key="signin_email")
            sign_in_password = st.text_input(
                "Password", type="password", key="signin_password"
            )
            sign_in_submit = st.form_submit_button(
                "Sign In", type="primary", use_container_width=True
            )

            if sign_in_submit:
                if not sign_in_email or not sign_in_password:
                    st.error("Please enter both email and password.")
                else:
                    try:
                        response = sign_in_user(sign_in_email, sign_in_password)
                        st.session_state.user = response.user
                        st.success("Signed in successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Sign in failed: {str(e)}")

    with auth_tab2:
        with st.form("sign_up_form"):
            st.subheader("Create your account")
            sign_up_email = st.text_input("Email", key="signup_email")
            sign_up_password = st.text_input(
                "Password (min 6 characters)",
                type="password",
                key="signup_password",
            )
            sign_up_confirm = st.text_input(
                "Confirm Password",
                type="password",
                key="signup_confirm",
            )
            sign_up_submit = st.form_submit_button(
                "Create Account", type="primary", use_container_width=True
            )

            if sign_up_submit:
                if not sign_up_email or not sign_up_password:
                    st.error("Please fill in all fields.")
                elif sign_up_password != sign_up_confirm:
                    st.error("Passwords do not match.")
                elif len(sign_up_password) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    try:
                        sign_up_user(sign_up_email, sign_up_password)
                        st.success(
                            "Account created! You can now sign in with your credentials."
                        )
                    except Exception as e:
                        st.error(f"Sign up failed: {str(e)}")

    st.stop()

# ===========================================================================
# USER IS LOGGED IN
# ===========================================================================
user = st.session_state.user
user_id = user.id

# Load profile
profile = get_user_profile(user_id)
if profile is None:
    st.error("Profile not found. Please sign out and try again.")
    if st.button("Sign Out"):
        sign_out_user()
    st.stop()

# Load user's current data
user_skills_data = get_user_skills(user_id)
user_skill_names = [s["skill_name"].lower() for s in user_skills_data]

# Determine if user needs onboarding
needs_onboarding = (
    not profile.get("full_name")
    and len(user_skills_data) == 0
)

# ===========================================================================
# HELPER: Save parsed resume data to Supabase
# ===========================================================================
def save_parsed_data(parsed, replace_existing: bool = False):
    """
    Save parsed resume data to Supabase for the logged-in user.
    If replace_existing is True, clears all existing data first.
    """
    contact = parsed.get("contact", {})

    # Update the profile row with contact info
    update_user_profile(user_id, {
        "full_name": contact.get("full_name", "") or profile.get("full_name", ""),
        "email": contact.get("email", "") or profile.get("email", ""),
        "phone": contact.get("phone", "") or profile.get("phone", ""),
        "location": contact.get("location", "") or profile.get("location", ""),
        "linkedin": contact.get("linkedin", "") or profile.get("linkedin", ""),
        "github": contact.get("github", "") or profile.get("github", ""),
    })

    # Clear existing data if replacing
    if replace_existing:
        clear_user_skills(user_id)
        clear_user_experiences(user_id)
        clear_user_projects(user_id)
        clear_user_education(user_id)

    # Save skills
    for skill in parsed.get("skills", []):
        try:
            add_user_skill(user_id, {
                "skill_name": skill,
                "category": "General",
                "proficiency": 2,
                "keywords": [skill.lower()],
            })
        except Exception:
            pass  # Skip duplicates

    # Save experiences
    for i, exp in enumerate(parsed.get("experiences", [])):
        try:
            add_user_experience(user_id, {
                "title": exp.get("title", ""),
                "company": exp.get("company", ""),
                "location": exp.get("location", ""),
                "start_date": exp.get("start_date", ""),
                "end_date": exp.get("end_date", ""),
                "bullets": exp.get("bullets", []),
                "skills_used": [],
                "display_order": i,
            })
        except Exception as e:
            st.warning(f"Could not save experience: {e}")

    # Save projects
    for proj in parsed.get("projects", []):
        try:
            add_user_project(user_id, {
                "name": proj.get("name", ""),
                "description": proj.get("description", ""),
                "technologies": proj.get("technologies", []),
                "bullets": proj.get("bullets", []),
                "date": proj.get("date", ""),
            })
        except Exception as e:
            st.warning(f"Could not save project: {e}")

    # Save education
    for edu in parsed.get("education", []):
        try:
            add_user_education(user_id, {
                "degree": edu.get("degree", ""),
                "school": edu.get("school", ""),
                "location": edu.get("location", ""),
                "graduation": edu.get("graduation", ""),
                "gpa": edu.get("gpa", ""),
                "coursework": edu.get("coursework", []),
            })
        except Exception as e:
            st.warning(f"Could not save education: {e}")


# ===========================================================================
# SIDEBAR
# ===========================================================================
with st.sidebar:
    st.title("Job Intelligence")
    st.caption(f"Signed in as {user.email}")

    if st.button("Sign Out", use_container_width=True):
        sign_out_user()

    # ---- Upload Resume Button (always available) ----
    if st.button("Upload New Resume", type="primary", use_container_width=True):
        st.session_state.onboarding_step = "upload"
        st.session_state.upload_mode = "update"
        st.rerun()

    st.divider()

    # ---- Profile Editor ----
    st.subheader("Your Profile")
    with st.expander("Edit Profile", expanded=False):
        new_name = st.text_input(
            "Full Name", value=profile.get("full_name") or ""
        )
        new_field = st.text_input(
            "Your Field (e.g., Data, Marketing, Nursing)",
            value=profile.get("field") or "",
        )
        new_level = st.selectbox(
            "Experience Level",
            ["entry", "mid", "senior"],
            index=["entry", "mid", "senior"].index(
                profile.get("experience_level") or "entry"
            ),
        )

        if st.button("Save Profile", type="primary", key="save_profile"):
            update_user_profile(
                user_id,
                {
                    "full_name": new_name,
                    "field": new_field,
                    "experience_level": new_level,
                },
            )
            st.success("Profile saved!")
            st.rerun()

    st.divider()

    # ---- Skills Manager ----
    st.subheader("Your Skills")

    with st.expander("Add a Skill", expanded=False):
        skill_name = st.text_input("Skill Name", key="new_skill_name")
        skill_category = st.text_input(
            "Category", key="new_skill_category"
        )
        skill_proficiency = st.slider(
            "Proficiency (1=Basic, 4=Expert)", 1, 4, 2, key="new_skill_prof"
        )
        skill_keywords = st.text_input(
            "Keywords (comma-separated synonyms)", key="new_skill_keywords"
        )

        if st.button("Add Skill", type="primary", key="add_skill_btn"):
            if not skill_name.strip():
                st.error("Please enter a skill name.")
            else:
                try:
                    add_user_skill(
                        user_id,
                        {
                            "skill_name": skill_name.strip(),
                            "category": skill_category.strip() or "General",
                            "proficiency": skill_proficiency,
                            "keywords": [
                                k.strip().lower()
                                for k in skill_keywords.split(",")
                                if k.strip()
                            ],
                        },
                    )
                    st.success(f"Added {skill_name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not add skill: {e}")

    if user_skills_data:
        level_labels = {1: "Basic", 2: "Intermediate", 3: "Advanced", 4: "Expert"}
        categories = {}
        for skill in user_skills_data:
            cat = skill.get("category") or "General"
            categories.setdefault(cat, []).append(skill)

        for category, skills in categories.items():
            st.markdown(f"**{category}**")
            for skill in skills:
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    st.write(
                        f"{skill['skill_name']} "
                        f"({level_labels.get(skill['proficiency'], '')})"
                    )
                with col_b:
                    if st.button(
                        "X",
                        key=f"del_skill_{skill['id']}",
                        help="Remove this skill",
                    ):
                        delete_user_skill(user_id, skill["id"])
                        st.rerun()
    else:
        st.info("No skills yet. Add a skill above or upload a resume.")

    st.divider()

    # ---- Filters ----
    st.subheader("Filters")
    min_score = st.slider("Minimum Match Score", 0, 100, 20)
    status_filter = st.selectbox(
        "Application Status",
        ["All", "Saved", "Applied", "Interview", "Rejected", "Offer"],
    )


# ===========================================================================
# UPLOAD / REVIEW FLOW (shared between onboarding and update)
# ===========================================================================
def render_upload_screen(is_update: bool):
    """Render the file upload screen."""
    if is_update:
        st.title("Upload a New Resume")
        st.caption(
            "Upload your resume to update your profile. You can review "
            "and edit the extracted data before saving."
        )
    else:
        st.title("Welcome! Let's Set Up Your Profile")
        st.caption("Upload your resume to get started, or fill in the details manually.")

    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help="We'll extract your information. You'll review it before saving.",
        key="resume_uploader",
    )

    if uploaded_file is not None:
        if st.button("Parse My Resume", type="primary"):
            with st.spinner("Reading your resume..."):
                parsed = parse_resume(uploaded_file)
                st.session_state.parsed_resume = parsed
                st.session_state.onboarding_step = "review"
                st.rerun()

    if not is_update:
        st.divider()
        st.write("Don't have a resume ready?")
        if st.button("Fill in Manually Instead"):
            st.session_state.parsed_resume = {
                "contact": {
                    "full_name": "",
                    "email": "",
                    "phone": "",
                    "location": "",
                    "linkedin": "",
                    "github": "",
                },
                "skills": [],
                "experiences": [],
                "education": [],
                "projects": [],
            }
            st.session_state.onboarding_step = "review"
            st.rerun()


def render_review_screen(is_update: bool):
    """Render the review-and-edit screen for parsed data."""
    parsed = st.session_state.parsed_resume

    st.title("Review Your Information")
    st.caption(
        "We've extracted what we could from your resume. "
        "Please fix anything that looks wrong before saving."
    )

    # ---- Contact Info ----
    with st.expander("Contact Information", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input(
                "Full Name",
                value=parsed["contact"].get("full_name", ""),
                key="rv_name",
            )
            email = st.text_input(
                "Email",
                value=parsed["contact"].get("email", ""),
                key="rv_email",
            )
            phone = st.text_input(
                "Phone",
                value=parsed["contact"].get("phone", ""),
                key="rv_phone",
            )
        with col2:
            location = st.text_input(
                "Location",
                value=parsed["contact"].get("location", ""),
                key="rv_location",
            )
            linkedin = st.text_input(
                "LinkedIn",
                value=parsed["contact"].get("linkedin", ""),
                key="rv_linkedin",
            )
            github = st.text_input(
                "GitHub",
                value=parsed["contact"].get("github", ""),
                key="rv_github",
            )

    # ---- Skills ----
    with st.expander("Skills", expanded=True):
        st.write(f"Found **{len(parsed.get('skills', []))}** skills.")
        st.caption("These will become your skills for job matching.")

        if "review_skills" not in st.session_state:
            st.session_state.review_skills = list(parsed.get("skills", []))

        # Show skills as tags with remove buttons
        skills_to_remove = []
        for i, skill in enumerate(st.session_state.review_skills):
            col_a, col_b = st.columns([5, 1])
            with col_a:
                st.write(f"- {skill}")
            with col_b:
                if st.button("X", key=f"rv_rm_skill_{i}"):
                    skills_to_remove.append(i)

        for i in sorted(skills_to_remove, reverse=True):
            st.session_state.review_skills.pop(i)
            st.rerun()

        # Add skill input
        col_a, col_b = st.columns([4, 1])
        with col_a:
            new_skill = st.text_input(
                "Add a skill", key="rv_new_skill", label_visibility="collapsed",
                placeholder="Add a skill..."
            )
        with col_b:
            if st.button("Add", key="rv_add_skill") and new_skill.strip():
                st.session_state.review_skills.append(new_skill.strip())
                st.rerun()

    # ---- Experience ----
    with st.expander("Work Experience", expanded=True):
        if "review_experiences" not in st.session_state:
            st.session_state.review_experiences = list(parsed.get("experiences", []))

        if st.session_state.review_experiences:
            for i, exp in enumerate(st.session_state.review_experiences):
                st.markdown(
                    f"**{exp.get('title', '(No title)')}** at "
                    f"{exp.get('company', '(No company)')}"
                )
                st.caption(
                    f"{exp.get('start_date', '')} - {exp.get('end_date', '')}"
                )
                if exp.get("bullets"):
                    for b in exp["bullets"][:3]:
                        st.write(f"  - {b}")
                    if len(exp["bullets"]) > 3:
                        st.caption(f"  ... and {len(exp['bullets']) - 3} more")
                if st.button("Remove", key=f"rv_rm_exp_{i}"):
                    st.session_state.review_experiences.pop(i)
                    st.rerun()
                st.divider()
        else:
            st.info("No experience entries found.")

        # Add new experience
        with st.form("rv_add_exp_form", clear_on_submit=True):
            st.write("**Add an Experience**")
            col1, col2 = st.columns(2)
            with col1:
                new_title = st.text_input("Job Title")
                new_start = st.text_input("Start Date (e.g., Jan 2022)")
            with col2:
                new_company = st.text_input("Company")
                new_end = st.text_input("End Date (or 'Present')")
            new_bullets = st.text_area("Accomplishments (one per line)")

            if st.form_submit_button("Add Experience"):
                if new_title and new_company:
                    st.session_state.review_experiences.append({
                        "title": new_title,
                        "company": new_company,
                        "location": "",
                        "start_date": new_start,
                        "end_date": new_end,
                        "bullets": [
                            b.strip() for b in new_bullets.split("\n") if b.strip()
                        ],
                    })
                    st.rerun()

    # ---- Education ----
    with st.expander("Education", expanded=False):
        if "review_education" not in st.session_state:
            st.session_state.review_education = list(parsed.get("education", []))

        if st.session_state.review_education:
            for i, edu in enumerate(st.session_state.review_education):
                st.markdown(f"**{edu.get('degree', '(No degree)')}**")
                st.caption(edu.get("school", ""))
                if st.button("Remove", key=f"rv_rm_edu_{i}"):
                    st.session_state.review_education.pop(i)
                    st.rerun()
                st.divider()
        else:
            st.info("No education entries found.")

        with st.form("rv_add_edu_form", clear_on_submit=True):
            new_degree = st.text_input("Degree")
            new_school = st.text_input("School")
            new_grad = st.text_input("Graduation (e.g., May 2025)")
            if st.form_submit_button("Add Education"):
                if new_degree and new_school:
                    st.session_state.review_education.append({
                        "degree": new_degree,
                        "school": new_school,
                        "location": "",
                        "graduation": new_grad,
                        "gpa": "",
                        "coursework": [],
                    })
                    st.rerun()

    # ---- Save ----
    st.divider()

    if is_update:
        replace_existing = st.checkbox(
            "Replace all existing data (recommended when uploading a new resume)",
            value=True,
        )
    else:
        replace_existing = True  # Onboarding always replaces (nothing to replace)

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button(
            "Save My Profile",
            type="primary",
            use_container_width=True,
            key="rv_save",
        ):
            with st.spinner("Saving..."):
                # Build the parsed dict from current session state
                final_data = {
                    "contact": {
                        "full_name": name,
                        "email": email,
                        "phone": phone,
                        "location": location,
                        "linkedin": linkedin,
                        "github": github,
                    },
                    "skills": st.session_state.review_skills,
                    "experiences": st.session_state.review_experiences,
                    "education": st.session_state.review_education,
                    "projects": parsed.get("projects", []),
                }

                save_parsed_data(final_data, replace_existing=replace_existing)

                # Clear session state
                for key in [
                    "parsed_resume", "onboarding_step", "upload_mode",
                    "review_skills", "review_experiences", "review_education",
                ]:
                    st.session_state.pop(key, None)

                st.success("Profile saved! Loading your dashboard...")
                st.rerun()

    with col2:
        if st.button("Cancel", use_container_width=True, key="rv_cancel"):
            for key in [
                "parsed_resume", "onboarding_step", "upload_mode",
                "review_skills", "review_experiences", "review_education",
            ]:
                st.session_state.pop(key, None)
            st.rerun()


# ---- Route to the right screen ----
current_step = st.session_state.get("onboarding_step")
is_update = st.session_state.get("upload_mode") == "update"

if current_step == "upload":
    render_upload_screen(is_update=is_update)
    st.stop()

if current_step == "review":
    render_review_screen(is_update=is_update)
    st.stop()

if needs_onboarding:
    # First-time users land on the upload screen in onboarding mode
    st.session_state.onboarding_step = "upload"
    st.session_state.upload_mode = "onboarding"
    st.rerun()


# ===========================================================================
# DASHBOARD
# ===========================================================================
@st.cache_data(ttl=300)
def load_jobs():
    """Load the shared job pool from local SQLite."""
    try:
        conn = sqlite3.connect("jobs.db", check_same_thread=False)
        query = """
        SELECT
            j.id, j.title, j.company, j.location, j.salary,
            j.description, j.link, j.source, j.posted_date,
            COALESCE(GROUP_CONCAT(DISTINCT s.name), '') as skills,
            COUNT(DISTINCT js.skill_id) as skill_count
        FROM jobs j
        LEFT JOIN job_skills js ON j.id = js.job_id
        LEFT JOIN skills s ON js.skill_id = s.id
        WHERE j.description IS NOT NULL AND j.description != ''
        GROUP BY j.id
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Could not load jobs.db: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_skill_stats():
    """Load top in-demand skills from the shared pool."""
    try:
        conn = sqlite3.connect("jobs.db", check_same_thread=False)
        query = """
        SELECT s.name, s.category, COUNT(*) as job_count
        FROM skills s
        JOIN job_skills js ON s.id = js.skill_id
        GROUP BY s.name, s.category
        ORDER BY job_count DESC
        LIMIT 20
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


df = load_jobs()
skill_stats = load_skill_stats()

# Merge user job statuses
user_jobs_data = get_user_jobs(user_id)
user_job_status = {j["job_id"]: j["status"] for j in user_jobs_data}

# Calculate match scores
if not df.empty and user_skill_names:
    def get_match_score(row):
        result = matcher.calculate_match_score(row["skills"], user_skill_names)
        return result["score"]

    df["match_score"] = df.apply(get_match_score, axis=1)
    df["status"] = df["id"].apply(lambda jid: user_job_status.get(jid, "Saved"))
else:
    df["match_score"] = 0
    df["status"] = "Saved"

# Apply filters
filtered_df = df.copy()
if status_filter != "All":
    filtered_df = filtered_df[filtered_df["status"] == status_filter]
filtered_df = filtered_df[filtered_df["match_score"] >= min_score]
filtered_df = filtered_df.sort_values(by="match_score", ascending=False)

# ===========================================================================
# MAIN CONTENT
# ===========================================================================
st.title("Job Intelligence Dashboard")
display_name = profile.get("full_name") or user.email
st.caption(f"Welcome back, {display_name}")

if not user_skill_names:
    st.warning(
        "You haven't added any skills yet. Use the Upload New Resume button "
        "in the sidebar, or add skills manually."
    )

# ---- Metrics ----
if not filtered_df.empty:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Matching Jobs", len(filtered_df))
    with col2:
        avg = int(filtered_df["match_score"].mean())
        st.metric("Avg Match Score", f"{avg}%")
    with col3:
        applied = len(filtered_df[filtered_df["status"] == "Applied"])
        st.metric("Applied", applied)
    with col4:
        if "posted_date" in filtered_df.columns:
            today_count = len(
                filtered_df[
                    pd.to_datetime(filtered_df["posted_date"]).dt.date
                    == datetime.now().date()
                ]
            )
            st.metric("New Today", today_count)
else:
    st.warning("No jobs found. Run the scraper first: python scraper.py")

# ---- Tabs ----
if not filtered_df.empty:
    tab1, tab2, tab3 = st.tabs(["Analytics", "Top Matches", "Skill Insights"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            if not skill_stats.empty:
                fig = px.bar(
                    skill_stats.head(10),
                    x="name", y="job_count", color="category",
                    title="Most In-Demand Skills",
                    labels={"name": "Skill", "job_count": "Number of Jobs"},
                )
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.histogram(
                filtered_df, x="match_score", nbins=20,
                title="Match Score Distribution",
                labels={"match_score": "Match Score (%)", "count": "Number of Jobs"},
            )
            fig.add_vline(x=70, line_dash="dash", line_color="red",
                          annotation_text="Good Match Threshold")
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        for _, row in filtered_df.head(10).iterrows():
            job_id = row["id"]
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 2])

                with col1:
                    st.subheader(row["title"])
                    st.write(f"{row['company']} -- {row['location']}")
                    st.caption(f"Source: {row.get('source', 'Unknown')}")

                with col2:
                    score = row["match_score"]
                    if score >= 80:
                        st.success(f"{score}% Match")
                    elif score >= 60:
                        st.warning(f"{score}% Match")
                    else:
                        st.error(f"{score}% Match")
                    if row["salary"] and row["salary"] != "Not listed":
                        st.write(f"Salary: {row['salary']}")

                with col3:
                    if row["link"]:
                        st.link_button("APPLY TO JOB", row["link"], type="primary")

                    status_options = ["Saved", "Applied", "Interview", "Rejected", "Offer"]
                    current_status = row["status"] if row["status"] in status_options else "Saved"
                    new_status = st.selectbox(
                        "Status", status_options,
                        index=status_options.index(current_status),
                        key=f"status_top_{job_id}",
                    )
                    if new_status != current_status:
                        update_user_job_status(user_id, job_id, new_status)
                        st.rerun()

                if row["skills"]:
                    skills_list = row["skills"].split(",")
                    st.markdown(" ".join([f"`{s.strip()}`" for s in skills_list[:5]]))

                st.divider()

    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            skill_demand = []
            for skill in user_skill_names:
                demand = len(filtered_df[
                    filtered_df["skills"].str.contains(skill, case=False, na=False, regex=False)
                ])
                skill_demand.append({"skill": skill, "jobs": demand})
            if skill_demand:
                demand_df = pd.DataFrame(skill_demand)
                fig = px.bar(demand_df, x="skill", y="jobs",
                             title="Your Skills - Market Demand",
                             labels={"skill": "Your Skill", "jobs": "Available Jobs"})
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            if not skill_stats.empty and user_skill_names:
                top_missing = skill_stats[
                    ~skill_stats["name"].str.lower().isin(user_skill_names)
                ].head(5)
                if not top_missing.empty:
                    fig = px.pie(top_missing, values="job_count", names="name",
                                 title="Top Skills You're Missing")
                    st.plotly_chart(fig, use_container_width=True)
                    st.subheader("Learning Resources")
                    for s in matcher.get_improvement_suggestions(
                        top_missing["name"].tolist()
                    ):
                        with st.expander(f"Learn {s['skill'].title()} - {s['difficulty']}"):
                            st.write(f"**Resource:** {s['learning_resource']}")
                            st.write(f"**Link:** {s['resource_url']}")
                            st.write(f"**Market Demand:** {s['market_demand']}")

# ---- All Jobs List ----
if not filtered_df.empty:
    st.divider()
    st.subheader(f"All Matching Jobs ({len(filtered_df)})")

    jobs_per_page = 10
    total_pages = max(1, (len(filtered_df) // jobs_per_page) + 1)
    page = st.number_input("Page", 1, total_pages, 1, label_visibility="collapsed")

    start_idx = (page - 1) * jobs_per_page
    end_idx = min(start_idx + jobs_per_page, len(filtered_df))

    for _, row in filtered_df.iloc[start_idx:end_idx].iterrows():
        job_id = row["id"]
        with st.container():
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.write(f"**{row['title']}**")
                st.write(f"{row['company']} -- {row['location']}")
            with col2:
                score = row["match_score"]
                st.progress(score / 100, text=f"{score}% Match")
            with col3:
                status_options = ["Saved", "Applied", "Interview", "Rejected", "Offer"]
                current_status = row["status"] if row["status"] in status_options else "Saved"
                new_status = st.selectbox(
                    "Status", status_options,
                    index=status_options.index(current_status),
                    key=f"status_all_{job_id}",
                )
                if new_status != current_status:
                    update_user_job_status(user_id, job_id, new_status)
                    st.rerun()
            st.divider()

# ---- Footer ----
st.divider()
st.caption(
    f"Signed in as {user.email} | "
    f"Total jobs: {len(df)} | Matching: {len(filtered_df)}"
)