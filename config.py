"""
Configuration file for Job Intelligence Dashboard.
Contains skill definitions, job filters, matching weights, and user profile.
No API keys required - all job APIs used are free.
"""

# ---------------------------------------------------------------------------
# CORE SKILLS - Skills the system can detect in job descriptions
# ---------------------------------------------------------------------------
CORE_SKILLS = [
    "python", "sql", "excel", "tableau", "power bi",
    "java", "javascript", "react", "pandas", "numpy",
    "data analysis", "data visualization", "dashboard",
    "reporting", "etl", "database", "aws", "azure", "gcp",
    "statistics", "machine learning", "git", "docker"
]

# ---------------------------------------------------------------------------
# SKILL SYNONYMS - Maps alternative names to standard skill names
# Improves matching by recognizing different ways to describe the same skill
# ---------------------------------------------------------------------------
SKILL_SYNONYMS = {
    "python": ["python3", "python 3", "py", "python programming"],
    "react": ["react.js", "reactjs", "react js", "react native"],
    "javascript": ["js", "ecmascript", "es6"],
    "power bi": ["powerbi", "power-bi", "power bi desktop"],
    "aws": ["amazon web services", "aws cloud", "amazon aws"],
    "gcp": ["google cloud", "google cloud platform", "gcp cloud"],
    "excel": ["microsoft excel", "ms excel", "spreadsheet"],
    "sql": ["postgresql", "mysql", "sql server", "t-sql", "pl/sql"],
    "tableau": ["tableau desktop", "tableau server", "tableau online"],
    "machine learning": ["ml", "deep learning", "ai", "artificial intelligence"]
}

# ---------------------------------------------------------------------------
# TRUSTED JOB SOURCES - Domains considered legitimate
# ---------------------------------------------------------------------------
TRUSTED_SOURCES = [
    "linkedin.com", "indeed.com", "greenhouse.io", "lever.co",
    "workday.com", "ziprecruiter.com", "glassdoor.com",
    "remotive.com", "weworkremotely.com", "remote.co"
]

# ---------------------------------------------------------------------------
# EXCLUDED DOMAINS - Low-quality or aggregator sites to skip
# ---------------------------------------------------------------------------
EXCLUDED_DOMAINS = [
    "torre.ai", "grabjobs", "talent.com", "jobsinusa", "usajobs.gov"
]

# ---------------------------------------------------------------------------
# SUSPICIOUS KEYWORDS - Terms that may indicate scam postings
# ---------------------------------------------------------------------------
SUSPICIOUS_KEYWORDS = [
    "quick money", "whatsapp", "telegram", "investment", "training fee"
]

# ---------------------------------------------------------------------------
# MATCHING WEIGHTS - Controls how different match types are scored
# exact_match: Skill appears exactly in both job and user profile
# partial_match: Skill is a substring (e.g., "data" matches "data analysis")
# synonym_match: Skill matched via synonym mapping
# ---------------------------------------------------------------------------
MATCH_WEIGHTS = {
    "exact_match": 1.0,
    "partial_match": 0.6,
    "synonym_match": 0.8,
    "related_skill": 0.3
}

# ---------------------------------------------------------------------------
# USER PROFILE - Default skills and preferences
# Edit these or update skills through the dashboard sidebar
# ---------------------------------------------------------------------------
USER_PROFILE = {
    "skills": [
        "python", "sql", "excel", "tableau",
        "power bi", "java", "javascript", "react"
    ],
    "experience_level": "entry",
    "preferred_locations": ["Remote", "New York", "Brooklyn"],
    "salary_min": 50000,
    "salary_max": 80000
}