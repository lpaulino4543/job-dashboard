# debug_scraper.py
import requests
import sqlite3
from skill_matcher import SkillMatcher

matcher = SkillMatcher()

# Test Remotive API
print("=" * 50)
print("TESTING REMOTIVE API")
print("=" * 50)

url = "https://remotive.com/api/remote-jobs"
response = requests.get(url, params={"search": "data analyst", "limit": 5})
data = response.json()
jobs = data.get('jobs', [])

print(f"Status: {response.status_code}")
print(f"Total jobs returned: {len(jobs)}")

for i, job in enumerate(jobs[:3]):
    print(f"\n--- Job {i+1} ---")
    print(f"Title: {job.get('title')}")
    print(f"Company: {job.get('company_name')}")
    print(f"Description length: {len(str(job.get('description', '')))}")
    print(f"Description type: {type(job.get('description'))}")
    
    # Test skill extraction
    desc = str(job.get('description', ''))
    skills_found, scores = matcher.extract_skills_from_text(desc)
    print(f"Skills found: {skills_found}")
    print(f"Number of skills: {len(skills_found)}")
    
    # Test quality check
    from scraper import is_quality_job
    quality = is_quality_job(
        job.get('title', ''),
        str(job.get('description', '')),
        skills_found
    )
    print(f"Passes quality check: {quality}")

# Test Arbeitnow
print("\n" + "=" * 50)
print("TESTING ARBEITNOW API")
print("=" * 50)

url2 = "https://www.arbeitnow.com/api/job-board-api"
response2 = requests.get(url2)
data2 = response2.json()
jobs2 = data2.get('data', [])

print(f"Status: {response2.status_code}")
print(f"Total jobs: {len(jobs2)}")

# Find data-related jobs
data_jobs = []
for job in jobs2:
    title = str(job.get('title', '')).lower()
    if any(kw in title for kw in ['data', 'analyst', 'analytics']):
        data_jobs.append(job)

print(f"Data-related jobs: {len(data_jobs)}")

for job in data_jobs[:3]:
    print(f"\n--- Data Job ---")
    print(f"Title: {job.get('title')}")
    print(f"Company: {job.get('company_name')}")
    desc = str(job.get('description', ''))
    print(f"Description length: {len(desc)}")
    
    skills_found, scores = matcher.extract_skills_from_text(desc)
    print(f"Skills found: {skills_found}")
    
    quality = is_quality_job(
        job.get('title', ''),
        desc,
        skills_found
    )
    print(f"Passes quality check: {quality}")