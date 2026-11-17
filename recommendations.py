
import re

ROLE_SKILLS = {
    "AI/ML Engineer": [
        "python", "machine learning", "statistics",
        "scikit-learn", "pandas", "numpy", "sql"
    ],
    "Data Scientist": [
        "python", "statistics", "pandas", "numpy",
        "sql", "machine learning", "data analysis"
    ],
    "Software Developer": [
        "python", "java", "dsa", "git",
        "sql", "problem solving"
    ],
    "Frontend Developer": [
        "html", "css", "javascript", "react", "git"
    ],
    "Data Analyst": [
        "sql", "excel", "python", "pandas",
        "data analysis", "data visualization"
    ],
}


def normalize(value):
    return re.sub(r"\s+", " ", str(value).lower()).strip()


def skill_gaps(target_role, recorded_skills):
    required = ROLE_SKILLS.get(target_role, [])
    existing = {normalize(s) for s in recorded_skills}

    return {
        "matched": [s for s in required if normalize(s) in existing],
        "missing": [s for s in required if normalize(s) not in existing],
    }


def calculate_growth(records):
    """Compare consecutive recorded ratings for each skill."""
    history = {}

    for row in records:
        skill = row["skill"]
        history.setdefault(skill, []).append(row)

    results = []

    for skill, entries in history.items():
        entries.sort(key=lambda r: r["semester"])

        if len(entries) < 2:
            continue

        first = entries[0]
        latest = entries[-1]

        results.append({
            "Skill": skill,
            "First semester": first["semester"],
            "Latest semester": latest["semester"],
            "Previous rating": first["rating"],
            "Latest rating": latest["rating"],
            "Rating change": latest["rating"] - first["rating"],
            "Evidence recorded": all(
                bool(str(r["evidence"]).strip()) for r in entries
            ),
            "Evidence verified": all(
                bool(r["verified"]) for r in entries
            ),
        })

    return results


def match_faculty(missing_skills, faculty_rows):
    """Rank verified faculty by overlap with missing skills."""
    matches = []

    for faculty in faculty_rows:
        if not faculty["verified"]:
            continue

        expertise = {
            normalize(s)
            for s in str(faculty["expertise"]).split(";")
            if s.strip()
        }

        overlap = [
            skill for skill in missing_skills
            if normalize(skill) in expertise
        ]

        if overlap:
            matches.append({
                "name": faculty["name"],
                "department": faculty["department"],
                "expertise_match": overlap,
                "profile_url": faculty["profile_url"],
                "match_count": len(overlap),
            })

    return sorted(
        matches,
        key=lambda item: item["match_count"],
        reverse=True
    )
