"""
Resume tailoring engine.
Generates customized resumes based on job requirements and user's actual skills.
Never fabricates experience - only reorders and emphasizes existing qualifications.
"""
import os
from datetime import datetime
from fpdf import FPDF
from config import RESUME_PROFILE
from skill_matcher import SkillMatcher

# Initialize skill matcher for analyzing job requirements
matcher = SkillMatcher()


class ResumePDF(FPDF):
    """Custom PDF class with header and footer for professional resumes."""

    def header(self):
        """Add name and contact info header to each page."""
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, RESUME_PROFILE["name"], align="C")
        self.ln(6)
        self.set_font("Helvetica", "", 9)
        contact = (
            f"{RESUME_PROFILE['email']} | "
            f"{RESUME_PROFILE['phone']} | "
            f"{RESUME_PROFILE['location']}"
        )
        self.cell(0, 5, contact, align="C")
        self.ln(3)
        links = f"{RESUME_PROFILE['linkedin']} | {RESUME_PROFILE['github']}"
        self.cell(0, 5, links, align="C")
        self.ln(8)

    def footer(self):
        """Add page number to footer."""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title):
        """Add a formatted section title with underline."""
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 8, title.upper())
        self.ln(2)
        self.set_draw_color(0, 0, 0)
        self.set_line_width(0.3)
        self.line(self.get_x(), self.get_y(), self.get_x() + 190, self.get_y())
        self.ln(5)

    def bullet_point(self, text):
        """Add a bullet point with word wrapping."""
        self.set_font("Helvetica", "", 10)
        self.set_x(15)
        self.cell(5, 5, chr(8226))  # Bullet character
        self.multi_cell(175, 5, text)
        self.ln(1)


def analyze_job_fit(job_skills, job_description=""):
    """
    Analyze which of the user's skills are most relevant to a job.
    Returns a skill ranking to guide resume tailoring.
    """
    profile_skills = RESUME_PROFILE["skills"]
    relevant_skills = {}

    # Check each of the user's skills against job requirements
    for category, skills in profile_skills.items():
        for skill, level in skills.items():
            relevance = 0

            # Check if skill appears in job skills list
            if any(skill.lower() in js.lower() for js in job_skills):
                relevance += 3

            # Check if skill appears in job description
            if job_description and skill.lower() in job_description.lower():
                relevance += 2

            # Bonus for higher proficiency
            relevance += level * 0.5

            if relevance > 0:
                relevant_skills[skill] = {
                    "level": level,
                    "relevance": relevance,
                    "category": category
                }

    # Sort by relevance (highest first)
    return dict(
        sorted(
            relevant_skills.items(),
            key=lambda x: x[1]["relevance"],
            reverse=True
        )
    )


def tailor_summary(job_skills, job_description=""):
    """
    Create a tailored professional summary emphasizing relevant skills.
    Uses the template from config and fills in the user's top matching skills.
    """
    skill_ranking = analyze_job_fit(job_skills, job_description)

    # Get top 3-4 most relevant skills
    top_skills = list(skill_ranking.keys())[:4]
    skills_text = ", ".join(top_skills)

    summary = RESUME_PROFILE["summary_template"].format(
        top_skills=skills_text
    )

    return summary


def tailor_skills_section(job_skills, job_description=""):
    """
    Organize skills section, prioritizing those most relevant to the job.
    Returns skills grouped by category, with relevant skills highlighted first.
    """
    skill_ranking = analyze_job_fit(job_skills, job_description)
    profile_skills = RESUME_PROFILE["skills"]

    # Build tailored skills display
    tailored = {}

    for category, skills in profile_skills.items():
        category_skills = []
        for skill, level in skills.items():
            is_relevant = skill in skill_ranking
            relevance_score = (
                skill_ranking[skill]["relevance"] if is_relevant else 0
            )
            category_skills.append({
                "name": skill,
                "level": level,
                "relevant": is_relevant,
                "relevance": relevance_score
            })

        # Sort: relevant skills first, then by proficiency
        category_skills.sort(
            key=lambda x: (not x["relevant"], -x["relevance"], -x["level"])
        )

        if category_skills:
            tailored[category] = category_skills

    return tailored


def tailor_experience_bullets(job_skills, job_description=""):
    """
    Reorder experience bullets to emphasize accomplishments
    most relevant to the target job. Does not modify bullet content.
    """
    skill_ranking = analyze_job_fit(job_skills, job_description)
    top_skills = [s.lower() for s in list(skill_ranking.keys())[:6]]

    tailored_experiences = []

    for exp in RESUME_PROFILE["experiences"]:
        bullets = exp["bullets"].copy()

        # Score each bullet by how many top skills it mentions
        def bullet_relevance(bullet):
            bullet_lower = bullet.lower()
            return sum(
                1 for skill in top_skills if skill in bullet_lower
            )

        # Sort bullets: most relevant first
        bullets.sort(key=bullet_relevance, reverse=True)

        tailored_experiences.append({
            **exp,
            "bullets": bullets
        })

    return tailored_experiences


def tailor_projects(job_skills, job_description=""):
    """
    Prioritize projects that use skills relevant to the job.
    If the user has no projects matching job skills, keeps original order.
    """
    skill_ranking = analyze_job_fit(job_skills, job_description)
    top_skills = [s.lower() for s in list(skill_ranking.keys())[:6]]

    projects = RESUME_PROFILE["projects"].copy()

    # Score each project by technology overlap with job requirements
    def project_relevance(project):
        techs = [t.lower() for t in project.get("technologies", [])]
        return sum(1 for skill in top_skills if any(
            skill in tech for tech in techs
        ))

    projects.sort(key=project_relevance, reverse=True)
    return projects


def generate_resume(job_skills, job_title="", job_company="",
                    job_description=""):
    """
    Generate a tailored resume dictionary based on job requirements.
    Returns all sections ready for PDF generation or preview.
    """
    skill_ranking = analyze_job_fit(job_skills, job_description)

    resume_data = {
        "job_title": job_title,
        "job_company": job_company,
        "summary": tailor_summary(job_skills, job_description),
        "skills": tailor_skills_section(job_skills, job_description),
        "experiences": tailor_experience_bullets(job_skills, job_description),
        "projects": tailor_projects(job_skills, job_description),
        "education": RESUME_PROFILE["education"],
        "certifications": RESUME_PROFILE["certifications"],
        "match_skills": list(skill_ranking.keys())[:8],
        "match_percentage": len([
            s for s in skill_ranking if skill_ranking[s]["relevance"] >= 3
        ])
    }

    return resume_data


def generate_pdf(resume_data, filename=None):
    """
    Generate a professionally formatted PDF resume.
    
    Args:
        resume_data: Dictionary from generate_resume()
        filename: Output filename (auto-generated if None)
        
    Returns:
        Path to the generated PDF file
    """
    if filename is None:
        job_title = resume_data.get("job_title", "job")
        # Sanitize filename
        safe_title = "".join(
            c for c in job_title if c.isalnum() or c in " _-"
        ).rstrip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"resume_{safe_title[:30]}_{timestamp}.pdf"

    pdf = ResumePDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # --- Professional Summary ---
    pdf.section_title("Professional Summary")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, resume_data.get("summary", ""))
    pdf.ln(3)

    # --- Skills ---
    pdf.section_title("Skills")
    skills_data = resume_data.get("skills", {})

    for category, skills in skills_data.items():
        # Build skill string with proficiency indicators
        skill_strings = []
        for skill in skills:
            name = skill["name"]
            level = skill["level"]
            # Only show proficiency for higher levels
            if level >= 3:
                proficiency = "Expert" if level == 4 else "Proficient"
                skill_strings.append(f"{name} ({proficiency})")
            else:
                skill_strings.append(name)

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, f"{category}: ", ln=False)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, ", ".join(skill_strings))
        pdf.ln(2)

    pdf.ln(2)

    # --- Experience ---
    pdf.section_title("Professional Experience")

    for exp in resume_data.get("experiences", []):
        # Job title and company
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 6, exp["title"], ln=False)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, f"  |  {exp['company']}", ln=True)

        # Location and dates
        pdf.set_font("Helvetica", "I", 9)
        date_range = f"{exp['start_date']} - {exp['end_date']}"
        pdf.cell(0, 5, f"{exp['location']}  |  {date_range}", ln=True)
        pdf.ln(2)

        # Bullet points
        for bullet in exp.get("bullets", []):
            pdf.bullet_point(bullet)

        pdf.ln(3)

    # --- Projects ---
    pdf.section_title("Projects")

    for proj in resume_data.get("projects", []):
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 6, proj["name"], ln=True)
        pdf.set_font("Helvetica", "I", 9)
        tech_text = ", ".join(proj.get("technologies", []))
        pdf.cell(0, 5, f"Technologies: {tech_text}", ln=True)
        pdf.ln(2)

        for bullet in proj.get("bullets", []):
            pdf.bullet_point(bullet)

        pdf.ln(3)

    # --- Education ---
    pdf.section_title("Education")

    for edu in resume_data.get("education", []):
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 6, edu["degree"], ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 5, f"{edu['school']} - {edu['location']}", ln=True)
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 5, f"Graduation: {edu['graduation']}", ln=True)

        if edu.get("gpa"):
            pdf.cell(0, 5, f"GPA: {edu['gpa']}", ln=True)

        if edu.get("relevant_courses"):
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(0, 5, "Relevant Coursework:", ln=True)
            pdf.multi_cell(0, 5, ", ".join(edu["relevant_courses"]))
        pdf.ln(3)

    # --- Certifications ---
    certs = resume_data.get("certifications", [])
    if certs:
        pdf.section_title("Certifications")
        for cert in certs:
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(
                0, 5,
                f"{cert['name']} - {cert['issuer']} ({cert['date']})",
                ln=True
            )
        pdf.ln(3)

    # Save PDF
    pdf.output(filename)
    return filename