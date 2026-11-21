"""
Database setup and management for Job Intelligence Dashboard.
Creates SQLite tables for jobs, skills, and application tracking.
"""
import sqlite3


def create_database():
    """
    Create all required database tables and indexes.
    Safe to run multiple times - uses IF NOT EXISTS.
    """
    conn = sqlite3.connect("jobs.db")
    cursor = conn.cursor()

    # Check if existing skills table needs migration (missing category column)
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='skills'"
    )
    if cursor.fetchone():
        cursor.execute("PRAGMA table_info(skills)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'category' not in columns:
            print("Migrating skills table: adding category column...")
            cursor.execute("DROP TABLE IF EXISTS job_skills")
            cursor.execute("DROP TABLE IF EXISTS skills")

    # --- Jobs Table ---
    # Stores scraped job postings with unique link constraint
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        location TEXT,
        salary TEXT,
        description TEXT,
        link TEXT UNIQUE,
        source TEXT,
        posted_date TIMESTAMP,
        scraped_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'Saved'
    )
    """)

    # --- Skills Table ---
    # Normalized skill names with categories
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        category TEXT
    )
    """)

    # --- Job-Skills Bridge Table ---
    # Many-to-many relationship between jobs and skills
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS job_skills (
        job_id INTEGER,
        skill_id INTEGER,
        relevance_score FLOAT DEFAULT 1.0,
        PRIMARY KEY (job_id, skill_id),
        FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
        FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
    )
    """)

    # --- Application Tracking Table ---
    # Tracks the status and history of job applications
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS application_tracking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER,
        applied_date TIMESTAMP,
        follow_up_date TIMESTAMP,
        interview_date TIMESTAMP,
        status TEXT,
        notes TEXT,
        FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
    )
    """)

    # --- Skill Progress Table ---
    # Tracks user's learning progress for skills
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS skill_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        skill_name TEXT UNIQUE,
        proficiency INTEGER DEFAULT 0,
        last_practiced TIMESTAMP,
        learning_resource TEXT,
        target_proficiency INTEGER,
        notes TEXT
    )
    """)

    # --- Indexes for Performance ---
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_job_skills_job ON job_skills(job_id)"
    )

    # --- Default Skills ---
    # Pre-populate common skills with categories
    default_skills = [
        ("python", "Programming"),
        ("sql", "Database"),
        ("excel", "Tools"),
        ("tableau", "Visualization"),
        ("power bi", "Visualization"),
        ("java", "Programming"),
        ("javascript", "Programming"),
        ("react", "Framework"),
        ("pandas", "Library"),
        ("numpy", "Library"),
        ("machine learning", "Advanced"),
        ("aws", "Cloud"),
        ("docker", "DevOps"),
        ("git", "DevOps")
    ]

    cursor.executemany(
        "INSERT OR IGNORE INTO skills (name, category) VALUES (?, ?)",
        default_skills
    )

    conn.commit()
    conn.close()
    print("Database created successfully")


def reset_database():
    """
    Completely reset the database by dropping all tables and recreating.
    Requires user confirmation before proceeding.
    """
    conn = sqlite3.connect("jobs.db")
    cursor = conn.cursor()

    print("WARNING: This will delete all job data!")
    response = input("Are you sure? (yes/no): ")

    if response.lower() == 'yes':
        cursor.execute("DROP TABLE IF EXISTS job_skills")
        cursor.execute("DROP TABLE IF EXISTS skills")
        cursor.execute("DROP TABLE IF EXISTS jobs")
        cursor.execute("DROP TABLE IF EXISTS application_tracking")
        cursor.execute("DROP TABLE IF EXISTS skill_progress")
        conn.commit()
        conn.close()
        print("Database reset complete")
        create_database()
    else:
        print("Reset cancelled")
        conn.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        reset_database()
    else:
        create_database()