# test_single_job.py
import requests
import sqlite3
from skill_matcher import SkillMatcher
from scraper import insert_job, safe_str, is_quality_job

matcher = SkillMatcher()

# Test with one Remotive job
print("=" * 60)
print("TESTING SINGLE JOB INSERTION")
print("=" * 60)

url = "https://remotive.com/api/remote-jobs"
response = requests.get(url, params={"search": "data analyst", "limit": 5})
data = response.json()
jobs = data.get('jobs', [])

if jobs:
    job = jobs[0]  # Take first job
    
    print(f"\nJob details:")
    print(f"  Title: {job.get('title')}")
    print(f"  Company: {job.get('company_name')}")
    print(f"  Location: {job.get('candidate_required_location')}")
    print(f"  Link: {job.get('url')}")
    print(f"  Salary type: {type(job.get('salary'))}")
    print(f"  Salary value: {job.get('salary')}")
    print(f"  Description length: {len(str(job.get('description', '')))}")
    
    # Extract skills
    description = str(job.get('description', ''))
    skills_found, skill_scores = matcher.extract_skills_from_text(description)
    print(f"  Skills found: {skills_found}")
    print(f"  Quality check: {is_quality_job(job['title'], description, skills_found)}")
    
    # Try to insert manually
    conn = sqlite3.connect("jobs.db")
    cursor = conn.cursor()
    
    result = insert_job(
        cursor,
        job.get('title'),
        job.get('company_name'),
        job.get('candidate_required_location', 'Remote'),
        job.get('salary'),
        job.get('description'),
        job.get('url'),
        skills_found,
        skill_scores,
        "Remotive"
    )
    
    if result:
        print("  INSERT SUCCESS!")
        conn.commit()
    else:
        print("  INSERT FAILED!")
        # Check why
        title = safe_str(job.get('title')).strip()
        company = safe_str(job.get('company_name')).strip()
        link = safe_str(job.get('url')).strip()
        print(f"  Title check: '{title}' - valid: {bool(title)}")
        print(f"  Company check: '{company}' - valid: {bool(company)}")
        print(f"  Link check: '{link}' - valid: {bool(link)}")
        print(f"  Link starts with http: {link.startswith('http')}")
    
    conn.close()

# Also test with Arbeitnow
print("\n" + "=" * 60)
print("TESTING ARBEITNOW JOB")
print("=" * 60)

url2 = "https://www.arbeitnow.com/api/job-board-api"
response2 = requests.get(url2)
data2 = response2.json()
jobs2 = data2.get('data', [])

# Find a data job
data_job = None
for job in jobs2:
    title = str(job.get('title', '')).lower()
    if 'data' in title or 'analyst' in title or 'python' in title:
        data_job = job
        break

if data_job:
    print(f"\nJob details:")
    print(f"  Title: {data_job.get('title')}")
    print(f"  Company: {data_job.get('company_name')}")
    print(f"  Location: {data_job.get('location')}")
    print(f"  Link: {data_job.get('url')}")
    print(f"  Link type: {type(data_job.get('url'))}")
    print(f"  Description length: {len(str(data_job.get('description', '')))}")
    
    # Extract skills
    description = str(data_job.get('description', ''))
    skills_found, skill_scores = matcher.extract_skills_from_text(description)
    print(f"  Skills found: {skills_found}")
    print(f"  Quality check: {is_quality_job(data_job['title'], description, skills_found)}")
    
    # Try to insert
    conn = sqlite3.connect("jobs.db")
    cursor = conn.cursor()
    
    result = insert_job(
        cursor,
        data_job.get('title'),
        data_job.get('company_name'),
        data_job.get('location', 'Remote'),
        "Not listed",
        data_job.get('description'),
        data_job.get('url'),
        skills_found,
        skill_scores,
        "Arbeitnow"
    )
    
    if result:
        print("  INSERT SUCCESS!")
        conn.commit()
    else:
        print("  INSERT FAILED!")
        link = safe_str(data_job.get('url')).strip()
        print(f"  Link: '{link}'")
        print(f"  Link starts with http: {link.startswith('http')}")
    
    conn.close()
else:
    print("No data jobs found in Arbeitnow")

# Show what's in the database
conn = sqlite3.connect("jobs.db")
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM jobs")
count = cursor.fetchone()[0]
print(f"\nTotal jobs in database: {count}")
conn.close()