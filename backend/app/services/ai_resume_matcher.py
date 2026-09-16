"""
AI Resume Matching Engine.
Calculates candidate-to-job match scores using skill extraction, experience evaluation,
and keyword affinity scoring.
"""

def match_candidate_to_job(resume_text: str, required_skills: list[str], min_experience_years: int = 0, candidate_experience_years: int = 0) -> dict:
    if not required_skills:
        return {
            "score": 100.0,
            "matched_skills": [],
            "missing_skills": [],
            "experience_match": True,
            "reasons": ["No specific skills required for this job opening."]
        }

    resume_text_lower = resume_text.lower()
    matched_skills = [skill for skill in required_skills if skill.lower() in resume_text_lower]
    missing_skills = [skill for skill in required_skills if skill.lower() not in resume_text_lower]

    skill_score = (len(matched_skills) / len(required_skills)) * 80.0  # Skills count for 80%

    exp_match = candidate_experience_years >= min_experience_years
    exp_score = 20.0 if exp_match else max(0.0, (candidate_experience_years / max(1, min_experience_years)) * 20.0)

    total_score = round(min(100.0, skill_score + exp_score), 2)

    reasons = []
    if matched_skills:
        reasons.append(f"Matched {len(matched_skills)} of {len(required_skills)} required skills: {', '.join(matched_skills)}")
    if missing_skills:
        reasons.append(f"Missing skills: {', '.join(missing_skills)}")
    if exp_match:
        reasons.append(f"Meets experience requirement ({candidate_experience_years} yrs >= {min_experience_years} yrs)")
    else:
        reasons.append(f"Below required experience ({candidate_experience_years} yrs < {min_experience_years} yrs)")

    return {
        "score": total_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "experience_match": exp_match,
        "reasons": reasons
    }
