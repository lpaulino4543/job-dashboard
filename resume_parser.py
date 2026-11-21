"""
Resume parsing module.
Extracts structured data from uploaded PDF resumes using pdfplumber and regex.
Parsing is best-effort; results should always be reviewed by the user.
"""
import re
from io import BytesIO
import pdfplumber


# ---------------------------------------------------------------------------
# TEXT EXTRACTION
# ---------------------------------------------------------------------------
def extract_text_from_pdf(uploaded_file) -> str:
    """
    Extract text from an uploaded PDF using pdfplumber with layout preserved.

    layout=True uses the X/Y coordinates of each character to reconstruct
    horizontal spacing, which dramatically improves quality over plain
    character-by-character extraction.

    Args:
        uploaded_file: Streamlit UploadedFile object

    Returns:
        Concatenated text from all pages, or empty string on failure
    """
    try:
        # Reset the read pointer in case the file was read before
        uploaded_file.seek(0)
        pdf_bytes = uploaded_file.read()

        text_parts = []

        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                try:
                    page_text = page.extract_text(
                        layout=True,
                        x_tolerance=3,
                        y_tolerance=3,
                    )
                    if page_text:
                        text_parts.append(page_text)
                except Exception as page_err:
                    # If layout mode fails for a page, try without it
                    try:
                        fallback = page.extract_text()
                        if fallback:
                            text_parts.append(fallback)
                    except Exception:
                        print(f"Page extraction failed: {page_err}")
                        continue

        return "\n".join(text_parts)
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return ""


# ---------------------------------------------------------------------------
# TEXT CLEANING
# ---------------------------------------------------------------------------
# Common ligatures and smart characters that PDFs love to insert
LIGATURE_FIXES = {
    "\ufb00": "ff",   # ﬀ
    "\ufb01": "fi",   # ﬁ
    "\ufb02": "fl",   # ﬂ
    "\ufb03": "ffi",  # ﬃ
    "\ufb04": "ffl",  # ﬄ
    "\u2018": "'",    # left single quote
    "\u2019": "'",    # right single quote
    "\u201c": '"',    # left double quote
    "\u201d": '"',    # right double quote
    "\u2013": "-",    # en dash
    "\u2014": "-",    # em dash
    "\u2022": "-",    # bullet
    "\u25cf": "-",    # black circle
    "\u25cb": "-",    # white circle
    "\u25aa": "-",    # small square
    "\u25ab": "-",    # small white square
    "\u2023": "-",    # triangular bullet
    "\u2043": "-",    # hyphen bullet
    "\u00a0": " ",    # non-breaking space
    "\u200b": "",     # zero-width space
    "\ufeff": "",     # BOM
}


def clean_text(text: str) -> str:
    """
    Normalize resume text for consistent parsing.

    Handles:
    - Ligatures and smart quotes from PDF extraction
    - Hyphenated line breaks (words split across lines)
    - Excess whitespace and newlines
    - Bullet character normalization
    """
    if not text:
        return ""

    # Normalize line endings first
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Fix ligatures and special characters
    for bad, good in LIGATURE_FIXES.items():
        text = text.replace(bad, good)

    # Join hyphenated line breaks: "data-\nanalyst" -> "dataanalyst"
    # Only when the character after the newline is lowercase (continuation)
    text = re.sub(r"-\n(?=[a-z])", "", text)

    # Join lines that clearly continue a sentence.
    # A line ending in a comma followed by a lowercase-starting line
    # is almost certainly a wrapped sentence.
    text = re.sub(r",\n(?=[a-z])", ", ", text)

    # Collapse tabs and multiple spaces into single space
    text = re.sub(r"[ \t]+", " ", text)

    # Fix over-separated characters (e.g., "P y t h o n" -> "Python")
    # This happens when PDFs render each char separately
    # Only apply if we see 4+ single-char tokens in a row
    text = re.sub(
        r"\b(\w(?:\s\w){3,})\b",
        lambda m: m.group(1).replace(" ", "") if len(m.group(1).split()) >= 4 else m.group(1),
        text,
    )

    # Collapse 3+ newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ---------------------------------------------------------------------------
# SECTION DETECTION
# ---------------------------------------------------------------------------
# Headers we look for when splitting the resume into sections
SECTION_HEADERS = {
    "experience": [
        "EXPERIENCE", "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE",
        "EMPLOYMENT", "EMPLOYMENT HISTORY", "WORK HISTORY", "CAREER HISTORY",
    ],
    "education": [
        "EDUCATION", "ACADEMIC BACKGROUND", "ACADEMIC HISTORY",
        "EDUCATION & TRAINING",
    ],
    "skills": [
        "SKILLS", "TECHNICAL SKILLS", "CORE COMPETENCIES",
        "CORE SKILLS", "EXPERTISE", "AREAS OF EXPERTISE",
        "TECHNICAL PROFICIENCIES", "COMPETENCIES",
    ],
    "projects": [
        "PROJECTS", "PERSONAL PROJECTS", "SELECTED PROJECTS",
        "RELEVANT PROJECTS", "SIDE PROJECTS",
    ],
    "certifications": [
        "CERTIFICATIONS", "CERTIFICATES", "LICENSES",
        "CERTIFICATIONS & LICENSES",
    ],
}


def find_section(text: str, section_name: str) -> str:
    """
    Extract the text belonging to a specific section.

    Finds the section header, then returns everything up to the next
    recognized section header (or end of text).

    Args:
        text: Full resume text
        section_name: Key into SECTION_HEADERS (e.g., "experience")

    Returns:
        Section body text, or empty string if section not found
    """
    headers = SECTION_HEADERS.get(section_name, [])
    if not headers:
        return ""

    # Build a regex matching any of this section's headers on its own line
    header_pattern = (
        r"^\s*(?:" + "|".join(re.escape(h) for h in headers) + r")\s*:?\s*$"
    )
    header_match = re.search(header_pattern, text, re.IGNORECASE | re.MULTILINE)
    if not header_match:
        # Fallback: header might appear inline, not on its own line
        header_pattern_inline = (
            r"(?:" + "|".join(re.escape(h) for h in headers) + r")\s*:?\s*"
        )
        header_match = re.search(header_pattern_inline, text, re.IGNORECASE)
        if not header_match:
            return ""
        section_start = header_match.end()
    else:
        section_start = header_match.end()

    # Build a regex matching ANY section header (to know where to stop)
    all_headers = []
    for h_list in SECTION_HEADERS.values():
        all_headers.extend(h_list)
    stop_pattern = (
        r"^\s*(?:" + "|".join(re.escape(h) for h in all_headers) + r")\s*:?\s*$"
    )
    stop_match = re.search(
        stop_pattern, text[section_start:], re.IGNORECASE | re.MULTILINE
    )

    if stop_match:
        return text[section_start:section_start + stop_match.start()].strip()
    return text[section_start:].strip()


# ---------------------------------------------------------------------------
# CONTACT INFO PARSING
# ---------------------------------------------------------------------------
def parse_contact_info(text: str) -> dict:
    """
    Extract name, email, phone, location, LinkedIn, and GitHub from resume text.
    """
    result = {
        "full_name": "",
        "email": "",
        "phone": "",
        "location": "",
        "linkedin": "",
        "github": "",
    }

    # Email
    email_match = re.search(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text
    )
    if email_match:
        result["email"] = email_match.group(0)

    # Phone (US formats)
    phone_match = re.search(
        r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", text
    )
    if phone_match:
        result["phone"] = phone_match.group(0).strip()

    # LinkedIn
    linkedin_match = re.search(
        r"(?:linkedin\.com/in/|linkedin[:\s]+)([A-Za-z0-9_-]+)",
        text,
        re.IGNORECASE,
    )
    if linkedin_match:
        result["linkedin"] = f"linkedin.com/in/{linkedin_match.group(1)}"

    # GitHub
    github_match = re.search(
        r"(?:github\.com/|github[:\s]+)([A-Za-z0-9_-]+)",
        text,
        re.IGNORECASE,
    )
    if github_match:
        result["github"] = f"github.com/{github_match.group(1)}"

    # Name: usually the first non-empty line that isn't contact info
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    for line in lines[:5]:
        # Skip lines with contact info
        if any(marker in line.lower() for marker in [
            "@", "http", "www.", "linkedin", "github", "phone", "email"
        ]):
            continue
        if re.search(r"\d{3}[-.\s]?\d{3}[-.\s]?\d{4}", line):
            continue

        # Names: 2-4 words, all starting with capital letters
        words = line.split()
        if 1 < len(words) <= 4:
            if all(w[0].isupper() for w in words if w and w[0].isalpha()):
                # Exclude lines that look like section headers
                if line.upper() != line:  # all-caps lines are usually headers
                    result["full_name"] = line
                    break
                elif len(words) <= 3:
                    # All-caps names are common too
                    result["full_name"] = line
                    break

    # Location: "City, ST" pattern
    location_match = re.search(
        r"\b([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?,\s*[A-Z]{2})\b", text
    )
    if location_match:
        result["location"] = location_match.group(1)

    return result


# ---------------------------------------------------------------------------
# SKILLS PARSING
# ---------------------------------------------------------------------------
# Common skill separators
SKILL_SEPARATORS = re.compile(r"[,|•·;]|\s{2,}|\t")


def parse_skills(text: str, known_keywords: list = None) -> list:
    """
    Extract skills from resume text.

    If known_keywords is provided, matches against that list.
    Otherwise, looks for a SKILLS section and splits on separators.
    """
    if known_keywords:
        text_lower = text.lower()
        found = []
        for keyword in known_keywords:
            if re.search(rf"\b{re.escape(keyword.lower())}\b", text_lower):
                found.append(keyword)
        return sorted(set(found))

    skills_section = find_section(text, "skills")
    if not skills_section:
        return []

    skills = set()

    # Split section into lines, then each line into items
    for line in skills_section.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Skip category labels like "Programming:"
        line = re.sub(r"^[A-Za-z\s&/]+:\s*", "", line)

        # Split on common separators
        for item in SKILL_SEPARATORS.split(line):
            item = item.strip(" -–")
            # Reasonable skill length
            if 1 < len(item) < 40:
                # Skip obvious non-skills
                if re.match(r"^[\d\s.]+$", item):
                    continue
                skills.add(item)

    return sorted(skills)


# ---------------------------------------------------------------------------
# EXPERIENCE PARSING
# ---------------------------------------------------------------------------
# Matches "Jan 2022 - Present", "2020-2023", "06/2021 - 08/2022", etc.
DATE_RANGE_PATTERN = re.compile(
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}"
    r"|\d{1,2}/\d{4}"
    r"|\d{4})"
    r"\s*(?:-|–|—|to)\s*"
    r"((?:Present|Current|Now"
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}"
    r"|\d{1,2}/\d{4}"
    r"|\d{4}))",
    re.IGNORECASE,
)


def parse_experience(text: str) -> list:
    """
    Extract work experience entries from resume text.

    Strategy: find the experience section, locate each date range,
    then look at the lines immediately above for title and company.
    """
    section = find_section(text, "experience")
    if not section:
        return []

    experiences = []

    for match in DATE_RANGE_PATTERN.finditer(section):
        start_date = match.group(1)
        end_date = match.group(2)

        # Grab the text just before this date range
        before = section[:match.start()].strip()
        before_lines = [l.strip() for l in before.split("\n") if l.strip()]

        # Grab the text just after this date range (until the next date range)
        after_start = match.end()
        next_match = DATE_RANGE_PATTERN.search(section, after_start)
        after_end = next_match.start() if next_match else len(section)
        after = section[after_start:after_end].strip()

        title = ""
        company = ""
        location = ""

        # Look at the last 1-2 lines before the date for title/company
        if before_lines:
            last = before_lines[-1]
            # Common format: "Title at Company" or "Title | Company" or "Title - Company"
            for sep in [" at ", " | ", " - ", " — ", " · "]:
                if sep in last:
                    parts = last.split(sep, 1)
                    title = parts[0].strip()
                    company = parts[1].strip()
                    break
            else:
                # No separator: likely just company on this line
                company = last
                if len(before_lines) >= 2:
                    title = before_lines[-2]

        # Extract bullets from the after text
        bullets = []
        for line in after.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Bullet indicators: leading dash, or the line is fairly long
            if line.startswith("-") or len(line) > 40:
                bullet = line.lstrip("-•· ").strip()
                if bullet:
                    bullets.append(bullet)

        if title or company:
            experiences.append({
                "title": title,
                "company": company,
                "location": location,
                "start_date": start_date,
                "end_date": end_date,
                "bullets": bullets[:6],  # Cap at 6 bullets
            })

    return experiences


# ---------------------------------------------------------------------------
# EDUCATION PARSING
# ---------------------------------------------------------------------------
DEGREE_PATTERN = re.compile(
    r"\b(Bachelor(?:'s)?|Master(?:'s)?|Associate(?:'s)?|Doctorate|PhD|"
    r"B\.?\s?S\.?|M\.?\s?S\.?|B\.?\s?A\.?|M\.?\s?A\.?|MBA|"
    r"Certificate|Diploma)\b",
    re.IGNORECASE,
)

UNIVERSITY_PATTERN = re.compile(
    r"\b(University|College|Institute|School|Academy|Polytechnic)\b",
    re.IGNORECASE,
)


def parse_education(text: str) -> list:
    """
    Extract education entries from the resume.

    Looks for degree keywords and, when found, grabs nearby lines for
    school, location, and graduation date.
    """
    section = find_section(text, "education")
    if not section:
        return []

    lines = [l.strip() for l in section.split("\n") if l.strip()]
    education = []

    i = 0
    while i < len(lines):
        line = lines[i]

        if DEGREE_PATTERN.search(line) or UNIVERSITY_PATTERN.search(line):
            entry = {
                "degree": "",
                "school": "",
                "location": "",
                "graduation": "",
                "gpa": "",
                "coursework": [],
            }

            # Determine which line is degree vs school
            if DEGREE_PATTERN.search(line):
                entry["degree"] = line
                # Look at next line for school
                if i + 1 < len(lines) and UNIVERSITY_PATTERN.search(lines[i + 1]):
                    entry["school"] = lines[i + 1]
                    i += 1
            else:
                entry["school"] = line
                # Look at next line for degree
                if i + 1 < len(lines) and DEGREE_PATTERN.search(lines[i + 1]):
                    entry["degree"] = lines[i + 1]
                    i += 1

            # Look ahead a few more lines for graduation date and GPA
            for j in range(i + 1, min(i + 4, len(lines))):
                lookahead = lines[j]
                grad_match = re.search(
                    r"(?:Graduated|Expected|Class of)\s*:?\s*"
                    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
                    r"[a-z]*\.?\s*\d{4}|\d{4})",
                    lookahead,
                    re.IGNORECASE,
                )
                if grad_match:
                    entry["graduation"] = grad_match.group(1)

                gpa_match = re.search(r"GPA\s*:?\s*([\d.]+)", lookahead, re.IGNORECASE)
                if gpa_match:
                    entry["gpa"] = gpa_match.group(1)

            if entry["degree"] or entry["school"]:
                education.append(entry)

        i += 1

    return education


# ---------------------------------------------------------------------------
# PROJECTS PARSING
# ---------------------------------------------------------------------------
def parse_projects(text: str) -> list:
    """
    Extract project entries. Looks for a projects section and splits
    on lines that appear to be project titles.
    """
    section = find_section(text, "projects")
    if not section:
        return []

    projects = []
    lines = [l.strip() for l in section.split("\n") if l.strip()]

    current = None
    for line in lines:
        # A new project header is usually short and either bold-looking
        # (all caps or title case) with no leading bullet
        is_new_project = (
            len(line) < 60
            and not line.startswith("-")
            and (
                line.isupper()
                or (line[0].isupper() and line.count(" ") <= 6)
            )
        )

        if is_new_project and not current:
            current = {"name": line, "description": "", "technologies": [], "bullets": []}
        elif is_new_project and current and len(current["bullets"]) > 0:
            projects.append(current)
            current = {"name": line, "description": "", "technologies": [], "bullets": []}
        elif current and line.startswith("-"):
            current["bullets"].append(line.lstrip("-•· ").strip())
        elif current:
            # Free-form line — treat as description or tech list
            if any(kw in line.lower() for kw in ["tech", "stack", "tools", "built with"]):
                # Strip the label and split
                tech_part = re.sub(
                    r"^.*?(?:tech|stack|tools|built with)[^:]*:\s*",
                    "",
                    line,
                    flags=re.IGNORECASE,
                )
                current["technologies"] = [
                    t.strip() for t in re.split(r"[,|·]", tech_part) if t.strip()
                ]
            else:
                current["bullets"].append(line)

    if current:
        projects.append(current)

    return projects


# ---------------------------------------------------------------------------
# MASTER PARSE FUNCTION
# ---------------------------------------------------------------------------
def parse_resume(uploaded_file, known_skills: list = None) -> dict:
    """
    Master parsing function. Returns structured resume data.

    Args:
        uploaded_file: Streamlit UploadedFile
        known_skills: Optional list of skill keywords to match against

    Returns:
        Dictionary with keys: contact, skills, experiences, education,
        projects, raw_text
    """
    raw_text = extract_text_from_pdf(uploaded_file)
    if not raw_text:
        return {
            "contact": {},
            "skills": [],
            "experiences": [],
            "education": [],
            "projects": [],
            "raw_text": "",
        }

    cleaned = clean_text(raw_text)

    return {
        "contact": parse_contact_info(cleaned),
        "skills": parse_skills(cleaned, known_skills),
        "experiences": parse_experience(cleaned),
        "education": parse_education(cleaned),
        "projects": parse_projects(cleaned),
        "raw_text": cleaned,
    }