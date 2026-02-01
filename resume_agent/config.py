"""Configuration and constants for the resume tailoring agent."""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_CONTENT_DIR = os.path.join(BASE_DIR, "master-content")
VERSIONS_DIR = os.path.join(BASE_DIR, "versions")
BULLET_BANK_PATH = os.path.join(MASTER_CONTENT_DIR, "bullets-superset.md")
RESUME_PATH = os.path.join(BASE_DIR, "resume.md")

RELEVANCE_SCALE = {
    0: "Not relevant",
    1: "Somewhat relevant",
    2: "Strong evidence",
    3: "Direct, high-signal evidence for a must-have trait",
}

BULLET_DENSITY = {
    "current": (6, 9),
    "previous_major": (4, 6),
    "older": (1, 3),
}

BULLET_FIELDS = [
    "Company",
    "Experience",
    "Resume Line",
    "Duration",
    "Themes",
    "Metrics Present",
    "Metrics Notes",
]
