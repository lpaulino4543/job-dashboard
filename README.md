# Job Intelligence Dashboard

A LinkedIn-like job tracking dashboard with skill-based matching, built with Streamlit.

## Features
- Scrapes job postings from free APIs (Remotive, Arbeitnow)
- Extracts skills from job descriptions using synonym matching
- Calculates match scores between your skills and job requirements
- Tracks application status (Saved, Applied, Interview, Offer, Rejected)
- Visualizes skill demand and match score distribution
- Suggests learning resources for missing skills

## Quick Start

```bash
# 1. Setup (first time only)
python3 run.py --setup

# 2. Scrape jobs
python3 run.py --scrape

# 3. Launch dashboard
python3 run.py --dashboard