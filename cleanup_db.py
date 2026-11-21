import sqlite3

def cleanup_database():
    """Deep clean the jobs database"""
    conn = sqlite3.connect("jobs.db")
    cursor = conn.cursor()
    
    print("=" * 50)
    print("🧹 STARTING DATABASE CLEANUP")
    print("=" * 50)
    
    # 1. Remove jobs with no skills
    cursor.execute("""
        DELETE FROM jobs 
        WHERE id NOT IN (SELECT DISTINCT job_id FROM job_skills)
    """)
    no_skills = cursor.rowcount
    print(f"✅ Removed {no_skills} jobs with no skills")
    
    # 2. Remove jobs with no salary
    cursor.execute("""
        DELETE FROM jobs 
        WHERE salary = 'Not listed' 
        OR salary IS NULL 
        OR salary = ''
    """)
    no_salary = cursor.rowcount
    print(f"✅ Removed {no_salary} jobs with no salary listed")
    
    # 3. Remove jobs with very short descriptions
    cursor.execute("""
        DELETE FROM jobs 
        WHERE LENGTH(description) < 200
    """)
    short_desc = cursor.rowcount
    print(f"✅ Removed {short_desc} jobs with short descriptions")
    
    # 4. Remove duplicate jobs (same title + company)
    cursor.execute("""
        DELETE FROM jobs 
        WHERE id NOT IN (
            SELECT MIN(id) 
            FROM jobs 
            GROUP BY title, company
        )
    """)
    duplicates = cursor.rowcount
    print(f"✅ Removed {duplicates} duplicate jobs")
    
    # 5. Remove senior roles
    senior_terms = ['senior', 'sr.', 'lead', 'manager', 'director', 'principal']
    for term in senior_terms:
        cursor.execute("""
            DELETE FROM jobs 
            WHERE LOWER(title) LIKE ?
        """, (f"%{term}%",))
    senior_roles = cursor.rowcount
    print(f"✅ Removed {senior_roles} senior-level jobs")
    
    # 6. Remove suspicious domains
    bad_domains = ['torre.ai', 'grabjobs', 'jooble', 'talent.com', 'jobsinusa']
    for domain in bad_domains:
        cursor.execute("DELETE FROM jobs WHERE link LIKE ?", (f"%{domain}%",))
    bad_sources = cursor.rowcount
    print(f"✅ Removed {bad_sources} jobs from low-quality sources")
    
    # 7. Remove orphaned skills
    cursor.execute("""
        DELETE FROM job_skills 
        WHERE job_id NOT IN (SELECT id FROM jobs)
    """)
    orphaned_skills = cursor.rowcount
    print(f"✅ Removed {orphaned_skills} orphaned skill references")
    
    # 8. Remove unused skills from skills table
    cursor.execute("""
        DELETE FROM skills 
        WHERE id NOT IN (SELECT DISTINCT skill_id FROM job_skills)
    """)
    unused_skills = cursor.rowcount
    print(f"✅ Removed {unused_skills} unused skills")
    
    conn.commit()
    
    # Show final stats
    cursor.execute("SELECT COUNT(*) FROM jobs")
    final_count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(DISTINCT job_id) FROM job_skills
    """)
    jobs_with_skills = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(LENGTH(description)) FROM jobs")
    avg_desc_length = cursor.fetchone()[0] or 0
    
    print("\n" + "=" * 50)
    print("📊 FINAL DATABASE STATS")
    print("=" * 50)
    print(f"📁 Total quality jobs: {final_count}")
    print(f"🎯 Jobs with skills: {jobs_with_skills} ({jobs_with_skills/final_count*100:.1f}%)" if final_count > 0 else "N/A")
    print(f"📝 Avg description length: {int(avg_desc_length)} characters")
    print("=" * 50)
    
    conn.close()

if __name__ == "__main__":
    cleanup_database()