"""
Job scraper module.
Fetches job postings from free APIs (Remotive, Arbeitnow) and stores them
in the SQLite database with extracted skills.
"""
import requests
import sqlite3
import time
from datetime import datetime
from config import EXCLUDED_DOMAINS, SUSPICIOUS_KEYWORDS
from skill_matcher import SkillMatcher

# Initialize the skill matching engine for extracting skills from descriptions
matcher = SkillMatcher()


def is_quality_job(title, description, skills_found):
    """
    Filter out low-quality or irrelevant job postings.
    
    Returns False if:
    - Description is too short or missing
    - No skills were extracted
    - Title or description contains scam keywords
    - Title indicates a very senior executive role
    """
    if not description or len(description) < 30:
        return False

    if len(skills_found) < 1:
        return False

    desc_lower = description.lower()
    title_lower = title.lower()

    # Check for scam indicators
    for keyword in SUSPICIOUS_KEYWORDS:
        if keyword in desc_lower or keyword in title_lower:
            return False

    # Filter only C-level / VP roles
    very_senior = ["vp of", "vice president", "chief ", "head of engineering"]
    for term in very_senior:
        if term in title_lower:
            return False

    return True


def safe_str(value):
    """
    Safely convert any value to a string.
    Handles None, lists, dicts, and other types that APIs may return.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return " ".join([str(item) for item in value if item])
    return str(value)


def fetch_remotive_jobs(conn):
    """
    Fetch remote job postings from the Remotive API.
    
    Searches for multiple data-related terms and filters results
    by title keywords, then extracts skills and stores in database.
    """
    cursor = conn.cursor()
    print("\n--- Remotive API ---")

    url = "https://remotive.com/api/remote-jobs"
    added = 0
    skipped_quality = 0
    skipped_duplicate = 0
    skipped_no_data = 0

    # Search terms for finding relevant data jobs
    search_terms = [
        "data analyst", "data engineer", "business intelligence",
        "data science", "python developer", "sql"
    ]

    for term in search_terms:
        try:
            response = requests.get(url, params={"search": term, "limit": 25})
            if response.status_code != 200:
                continue

            data = response.json()
            jobs = data.get('jobs', [])

            for job in jobs:
                try:
                    # Extract and clean job fields
                    title = safe_str(job.get('title', '')).strip()
                    company = safe_str(job.get('company_name', '')).strip()
                    link = safe_str(job.get('url', '')).strip()
                    description = safe_str(job.get('description', ''))
                    location = safe_str(
                        job.get('candidate_required_location', 'Remote')
                    )
                    salary = job.get('salary', 'Not listed')

                    # Normalize salary field (can be dict or string)
                    if isinstance(salary, dict):
                        parts = []
                        if salary.get('min'):
                            parts.append(str(salary['min']))
                        if salary.get('max'):
                            parts.append(str(salary['max']))
                        salary = " - ".join(parts) if parts else "Not listed"
                    elif not salary or str(salary).strip() == "":
                        salary = "Not listed"
                    else:
                        salary = safe_str(salary)

                    # Validate required fields
                    if not title or not company or not link:
                        skipped_no_data += 1
                        continue
                    if not link.startswith('http'):
                        skipped_no_data += 1
                        continue

                    # Skip duplicates
                    cursor.execute(
                        "SELECT id FROM jobs WHERE link = ?", (link,)
                    )
                    if cursor.fetchone():
                        skipped_duplicate += 1
                        continue

                    # Extract skills from description
                    skills_found, skill_scores = \
                        matcher.extract_skills_from_text(description)

                    # Apply quality filter
                    if not is_quality_job(title, description, skills_found):
                        skipped_quality += 1
                        continue

                    # Insert job into database
                    cursor.execute("""
                    INSERT INTO jobs
                    (title, company, location, salary, description, link,
                     source, posted_date, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        title, company, location, salary,
                        description[:5000], link,
                        "Remotive", datetime.now().isoformat(), "Saved"
                    ))

                    job_id = cursor.lastrowid

                    # Insert extracted skills
                    for skill in skills_found:
                        if not skill or not isinstance(skill, str):
                            continue
                        cursor.execute(
                            "INSERT OR IGNORE INTO skills (name) VALUES (?)",
                            (skill,)
                        )
                        cursor.execute(
                            "SELECT id FROM skills WHERE name = ?", (skill,)
                        )
                        result = cursor.fetchone()
                        if result:
                            skill_id = result[0]
                            relevance = 1.0
                            if skill_scores and isinstance(skill_scores, dict):
                                relevance = skill_scores.get(skill, 1.0)
                            cursor.execute("""
                            INSERT OR IGNORE INTO job_skills
                            (job_id, skill_id, relevance_score)
                            VALUES (?, ?, ?)
                            """, (job_id, skill_id, relevance))

                    conn.commit()
                    added += 1

                    # Print first 5 additions as progress indicator
                    if added <= 5:
                        print(f"  + {title} [{len(skills_found)} skills]")

                except Exception:
                    continue

            time.sleep(1)  # Rate limiting between searches

        except Exception as e:
            print(f"  Error: {e}")

    print(
        f"  Added: {added} | Duplicate: {skipped_duplicate} | "
        f"No skills: {skipped_quality} | No data: {skipped_no_data}"
    )
    return added


def fetch_arbeitnow_jobs(conn):
    """
    Fetch job postings from the Arbeitnow API.
    
    Arbeitnow focuses on European companies but includes remote positions.
    Filters by data-related title keywords.
    """
    cursor = conn.cursor()
    print("\n--- Arbeitnow API ---")

    url = "https://www.arbeitnow.com/api/job-board-api"
    added = 0
    skipped_quality = 0
    skipped_duplicate = 0

    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"  Error: HTTP {response.status_code}")
            return 0

        data = response.json()
        jobs = data.get('data', [])

        # Only process jobs with data-related titles
        keywords = [
            'data analyst', 'data engineer', 'data scientist',
            'python', 'sql', 'analytics', 'business intelligence'
        ]

        for job in jobs:
            try:
                title = safe_str(job.get('title', '')).strip()
                company = safe_str(job.get('company_name', '')).strip()
                link = safe_str(job.get('url', '')).strip()
                description = safe_str(job.get('description', ''))
                location = safe_str(job.get('location', 'Remote'))

                # Filter by title keywords
                title_lower = title.lower()
                if not any(kw in title_lower for kw in keywords):
                    continue

                if not title or not company or not link:
                    continue

                # Skip duplicates
                cursor.execute(
                    "SELECT id FROM jobs WHERE link = ?", (link,)
                )
                if cursor.fetchone():
                    skipped_duplicate += 1
                    continue

                # Extract skills and check quality
                skills_found, skill_scores = \
                    matcher.extract_skills_from_text(description)

                if not is_quality_job(title, description, skills_found):
                    skipped_quality += 1
                    continue

                # Insert job
                cursor.execute("""
                INSERT INTO jobs
                (title, company, location, salary, description, link,
                 source, posted_date, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    title, company, location, "Not listed",
                    description[:5000], link,
                    "Arbeitnow", datetime.now().isoformat(), "Saved"
                ))

                job_id = cursor.lastrowid

                # Insert skills
                for skill in skills_found:
                    if not skill or not isinstance(skill, str):
                        continue
                    cursor.execute(
                        "INSERT OR IGNORE INTO skills (name) VALUES (?)",
                        (skill,)
                    )
                    cursor.execute(
                        "SELECT id FROM skills WHERE name = ?", (skill,)
                    )
                    result = cursor.fetchone()
                    if result:
                        skill_id = result[0]
                        relevance = 1.0
                        if skill_scores and isinstance(skill_scores, dict):
                            relevance = skill_scores.get(skill, 1.0)
                        cursor.execute("""
                        INSERT OR IGNORE INTO job_skills
                        (job_id, skill_id, relevance_score)
                        VALUES (?, ?, ?)
                        """, (job_id, skill_id, relevance))

                conn.commit()
                added += 1

                if added <= 5:
                    print(f"  + {title} [{len(skills_found)} skills]")

            except Exception:
                continue

        time.sleep(1)

    except Exception as e:
        print(f"  Error: {e}")

    print(
        f"  Added: {added} | Duplicate: {skipped_duplicate} | "
        f"No skills: {skipped_quality}"
    )
    return added


def fetch_jobs():
    """
    Main entry point for job scraping.
    Fetches from all available free APIs and prints summary statistics.
    """
    conn = sqlite3.connect("jobs.db")

    print("=" * 60)
    print(f"JOB SCRAPE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Clear previous data for a fresh start each run
    conn.execute("DELETE FROM job_skills")
    conn.execute("DELETE FROM jobs")
    conn.commit()
    print("Cleaned database for fresh start")

    # Fetch from all sources
    total_added = 0
    total_added += fetch_remotive_jobs(conn)
    total_added += fetch_arbeitnow_jobs(conn)

    # Print final statistics
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT job_id) FROM job_skills")
    jobs_with_skills = cursor.fetchone()[0]

    print("\n" + "=" * 60)
    print("SCRAPE COMPLETE")
    print(f"  New jobs: {total_added}")
    print(f"  Total: {total_jobs}")
    print(f"  With skills: {jobs_with_skills}")

    # Show recent additions
    cursor.execute("""
        SELECT title, company, source
        FROM jobs ORDER BY id DESC LIMIT 5
    """)
    recent = cursor.fetchall()
    if recent:
        print("\n  Recent jobs:")
        for title, company, source in recent:
            print(f"    - {title} at {company} [{source}]")

    print("=" * 60)
    conn.close()
    return total_added


if __name__ == "__main__":
    fetch_jobs()