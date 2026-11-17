
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("resume_data.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            target_role TEXT DEFAULT 'Software Developer',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS skill_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            skill TEXT NOT NULL,
            semester INTEGER NOT NULL CHECK(semester BETWEEN 1 AND 8),
            rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
            evidence TEXT NOT NULL,
            evidence_type TEXT NOT NULL,
            verified INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, skill, semester),
            FOREIGN KEY(student_id) REFERENCES students(student_id)
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            skills TEXT NOT NULL,
            evidence_url TEXT DEFAULT '',
            semester INTEGER NOT NULL CHECK(semester BETWEEN 1 AND 8),
            FOREIGN KEY(student_id) REFERENCES students(student_id)
        );

        CREATE TABLE IF NOT EXISTS faculty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT DEFAULT '',
            expertise TEXT NOT NULL,
            profile_url TEXT DEFAULT '',
            verified INTEGER NOT NULL DEFAULT 0,
            UNIQUE(name, department, expertise)
        );
        """)


def save_student(student_id, name, target_role):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO students (student_id, name, target_role)
            VALUES (?, ?, ?)
            ON CONFLICT(student_id) DO UPDATE SET
                name = excluded.name,
                target_role = excluded.target_role
        """, (student_id, name, target_role))


def save_skill(student_id, skill, semester, rating, evidence, evidence_type):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO skill_records
                (student_id, skill, semester, rating, evidence, evidence_type)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(student_id, skill, semester) DO UPDATE SET
                rating = excluded.rating,
                evidence = excluded.evidence,
                evidence_type = excluded.evidence_type
        """, (student_id, skill, semester, rating, evidence, evidence_type))


def get_skills(student_id):
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM skill_records
            WHERE student_id = ?
            ORDER BY semester, skill
        """, (student_id,)).fetchall()


def save_project(student_id, title, description, skills, evidence_url, semester):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO projects
                (student_id, title, description, skills, evidence_url, semester)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (student_id, title, description, skills, evidence_url, semester))


def get_projects(student_id):
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM projects
            WHERE student_id = ?
            ORDER BY semester, title
        """, (student_id,)).fetchall()


def get_faculty():
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM faculty
            WHERE verified = 1
            ORDER BY name
        """).fetchall()


def sync_faculty(csv_path):
    import csv

    csv_path = Path(csv_path)
    if not csv_path.exists():
        return

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        with get_connection() as conn:
            for row in reader:
                name = row.get("name", "").strip()
                expertise = row.get("expertise", "").strip()

                if not name or not expertise:
                    continue

                conn.execute("""
                    INSERT OR IGNORE INTO faculty
                        (name, department, expertise, profile_url, verified)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    name,
                    row.get("department", "").strip(),
                    expertise,
                    row.get("profile_url", "").strip(),
                    int(row.get("verified", "0").strip() in ("1", "true", "True", "yes", "Yes"))
                ))
