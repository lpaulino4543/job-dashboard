"""
Skill matching engine for Job Intelligence Dashboard.
Extracts skills from job descriptions and calculates match scores
against user profiles using exact, partial, and synonym matching.
"""
import re
from config import SKILL_SYNONYMS, MATCH_WEIGHTS, CORE_SKILLS


class SkillMatcher:
    """
    Extracts and matches skills between job descriptions and user profiles.
    
    Supports three match types:
    - Exact match: Same skill in both lists
    - Partial match: Substring relationship (e.g., 'data' in 'data analysis')
    - Synonym match: Recognized alternative name for a skill
    """

    def __init__(self):
        self.synonyms = SKILL_SYNONYMS
        self.weights = MATCH_WEIGHTS

    def normalize_skill(self, skill):
        """
        Convert a skill name to its standard form using the synonym map.
        Example: 'react.js' -> 'react'
        """
        skill = skill.lower().strip()
        for standard_skill, synonyms in self.synonyms.items():
            if skill in synonyms or skill == standard_skill:
                return standard_skill
        return skill

    def extract_skills_from_text(self, text):
        """
        Scan text for known skills and their synonyms.
        
        Returns:
            tuple: (list of found skills, dict of skill->confidence scores)
        """
        if not text:
            return [], {}

        text = text.lower()
        found_skills = set()
        skill_scores = {}

        for skill in CORE_SKILLS:
            # Check for the standard skill name
            if " " in skill:
                if skill in text:
                    found_skills.add(skill)
                    skill_scores[skill] = 1.0
            else:
                if re.search(rf'\b{re.escape(skill)}\b', text):
                    found_skills.add(skill)
                    skill_scores[skill] = 1.0

            # Check for known synonyms
            if skill in self.synonyms:
                for synonym in self.synonyms[skill]:
                    if " " in synonym:
                        if synonym in text:
                            found_skills.add(skill)
                            skill_scores[skill] = max(
                                skill_scores.get(skill, 0),
                                self.weights["synonym_match"]
                            )
                    else:
                        if re.search(rf'\b{re.escape(synonym)}\b', text):
                            found_skills.add(skill)
                            skill_scores[skill] = max(
                                skill_scores.get(skill, 0),
                                self.weights["synonym_match"]
                            )

        return list(found_skills), skill_scores

    def calculate_match_score(self, job_skills_str, user_skills, job_description=""):
        """
        Calculate a percentage match score between job requirements and user skills.
        
        Args:
            job_skills_str: Comma-separated string of job skills
            user_skills: List of user's skills
            job_description: (Optional) job description text
            
        Returns:
            dict with score, match breakdowns, and missing skills
        """
        if not job_skills_str or job_skills_str.strip() == "":
            return self._empty_match_result()

        # Parse job skills from comma-separated string
        job_skills = [
            s.strip().lower()
            for s in job_skills_str.split(",")
            if s.strip()
        ]
        user_skills_lower = [s.lower() for s in user_skills]

        exact_matches = []
        partial_matches = []
        synonym_matches = []
        missing_skills = []

        for job_skill in job_skills:
            normalized_skill = self.normalize_skill(job_skill)

            # Check exact match
            if normalized_skill in user_skills_lower:
                exact_matches.append(normalized_skill)
                continue

            # Check partial and synonym matches
            found_related = False
            for user_skill in user_skills_lower:
                # Partial: substring relationship
                if (user_skill in normalized_skill or
                        normalized_skill in user_skill):
                    partial_matches.append(normalized_skill)
                    found_related = True
                    break

                # Synonym: user has a known synonym of the job skill
                if normalized_skill in self.synonyms:
                    if user_skill in self.synonyms[normalized_skill]:
                        synonym_matches.append(normalized_skill)
                        found_related = True
                        break

            if not found_related:
                missing_skills.append(normalized_skill)

        # Calculate weighted score
        exact_score = len(exact_matches) * self.weights["exact_match"]
        partial_score = len(partial_matches) * self.weights["partial_match"]
        synonym_score = len(synonym_matches) * self.weights["synonym_match"]

        total_possible = len(job_skills)
        total_achieved = exact_score + partial_score + synonym_score

        match_percentage = (
            round((total_achieved / total_possible * 100))
            if total_possible > 0 else 0
        )
        match_percentage = min(match_percentage, 100)

        return {
            "score": match_percentage,
            "exact_matches": exact_matches,
            "partial_matches": partial_matches,
            "synonym_matches": synonym_matches,
            "missing_skills": missing_skills,
            "total_required": total_possible,
            "total_matched": (
                len(exact_matches) +
                len(partial_matches) +
                len(synonym_matches)
            )
        }

    def _empty_match_result(self):
        """Return a default empty match result structure."""
        return {
            "score": 0,
            "exact_matches": [],
            "partial_matches": [],
            "synonym_matches": [],
            "missing_skills": [],
            "total_required": 0,
            "total_matched": 0
        }

    def get_improvement_suggestions(self, missing_skills):
        """
        Generate learning resource suggestions for missing skills.
        
        Args:
            missing_skills: List of skill names the user doesn't have
            
        Returns:
            List of dicts with skill, resource, URL, difficulty, and demand
        """
        learning_resources = {
            "python": {
                "resource": "Python.org",
                "url": "https://python.org",
                "difficulty": "Beginner"
            },
            "sql": {
                "resource": "Mode Analytics SQL Tutorial",
                "url": "https://mode.com/sql-tutorial",
                "difficulty": "Beginner"
            },
            "excel": {
                "resource": "Excel Easy",
                "url": "https://excel-easy.com",
                "difficulty": "Beginner"
            },
            "tableau": {
                "resource": "Tableau Public",
                "url": "https://public.tableau.com",
                "difficulty": "Intermediate"
            },
            "power bi": {
                "resource": "Microsoft Learn",
                "url": "https://learn.microsoft.com/power-bi",
                "difficulty": "Intermediate"
            },
            "aws": {
                "resource": "AWS Free Tier",
                "url": "https://aws.amazon.com/free",
                "difficulty": "Advanced"
            },
            "docker": {
                "resource": "Docker Playground",
                "url": "https://labs.play-with-docker.com",
                "difficulty": "Intermediate"
            },
            "machine learning": {
                "resource": "Kaggle Learn",
                "url": "https://kaggle.com/learn",
                "difficulty": "Advanced"
            }
        }

        suggestions = []
        for skill in missing_skills:
            resource = learning_resources.get(skill, {
                "resource": "YouTube",
                "url": f"https://youtube.com/results?search_query=learn+{skill}",
                "difficulty": "Varies"
            })
            suggestions.append({
                "skill": skill,
                "learning_resource": resource["resource"],
                "resource_url": resource["url"],
                "difficulty": resource["difficulty"],
                "market_demand": (
                    "High" if skill in ["python", "sql", "aws"] else "Medium"
                )
            })

        return suggestions