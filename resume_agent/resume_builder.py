"""Resume builder — assembles a targeted resume from scored bullets."""

import os
from datetime import datetime

from resume_agent.config import BULLET_DENSITY, VERSIONS_DIR


def select_bullets(scored_bullets: list, role_tier: str = "current") -> list:
    """Select top bullets for a given role tier based on density rules."""
    min_count, max_count = BULLET_DENSITY.get(role_tier, (1, 3))
    relevant = [b for b in scored_bullets if b.relevance_score >= 1]
    return relevant[:max_count] if len(relevant) > max_count else relevant


def format_bullet(bullet) -> str:
    """Format a single bullet in the preferred structure:
    Impact/Outcome (metric) -> What I did -> How (mechanism) -> Scope
    """
    line = bullet.resume_line.strip()
    if not line.startswith("- "):
        line = f"- {line}"
    return line


def group_bullets_by_role(bullets: list) -> dict:
    """Group bullets by their experience/role field."""
    groups = {}
    for b in bullets:
        key = (b.company, b.experience)
        if key not in groups:
            groups[key] = {
                "company": b.company,
                "experience": b.experience,
                "duration": b.duration,
                "bullets": [],
            }
        groups[key]["bullets"].append(b)
    return groups


def build_resume_markdown(
    scored_bullets: list,
    header_info: dict = None,
    constraints: dict = None,
) -> str:
    """Build a complete resume in markdown from scored bullets.

    Args:
        scored_bullets: Bullets sorted by relevance score descending.
        header_info: Dict with name, email, phone, linkedin, location.
        constraints: Dict with page_count, emphasis preferences.

    Returns:
        Markdown string of the tailored resume.
    """
    header_info = header_info or {}
    constraints = constraints or {}

    name = header_info.get("name", "[Your Name]")
    email = header_info.get("email", "[Email]")
    phone = header_info.get("phone", "[Phone]")
    linkedin = header_info.get("linkedin", "[LinkedIn]")
    location = header_info.get("location", "[Location]")
    education = header_info.get("education", "[Degree] — [University], [Year]")
    skills = header_info.get("skills", "[Skills]")

    lines = [
        f"# {name}",
        f"{email} | {phone} | {linkedin} | {location}",
        "",
        "---",
        "",
        "## Experience",
        "",
    ]

    groups = group_bullets_by_role(scored_bullets)
    role_entries = list(groups.values())

    for i, role in enumerate(role_entries):
        tier = "current" if i == 0 else ("previous_major" if i == 1 else "older")
        min_b, max_b = BULLET_DENSITY.get(tier, (1, 3))

        lines.append(f"### {role['experience']} — {role['company']}")
        if role["duration"]:
            lines.append(f"*{role['duration']}*")
        lines.append("")

        selected = role["bullets"][:max_b]
        for b in selected:
            lines.append(format_bullet(b))
        lines.append("")

    lines.extend([
        "---",
        "",
        "## Education",
        "",
        education,
        "",
        "---",
        "",
        "## Skills",
        "",
        skills,
    ])

    return "\n".join(lines)


def save_version(resume_md: str, label: str = "") -> str:
    """Save a timestamped version of the resume to versions/."""
    os.makedirs(VERSIONS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"_{label}" if label else ""
    filename = f"resume_{timestamp}{suffix}.md"
    path = os.path.join(VERSIONS_DIR, filename)
    with open(path, "w") as f:
        f.write(resume_md)
    return path


def build_metrics_to_fill(scored_bullets: list) -> list:
    """Identify bullets with placeholder metrics that need real data."""
    placeholders = []
    for b in scored_bullets:
        if "[X]" in b.resume_line or "[x]" in b.resume_line:
            placeholders.append({
                "company": b.company,
                "experience": b.experience,
                "bullet": b.resume_line,
                "what_to_look_up": b.metrics_notes or "Specific metric value needed",
            })
    return placeholders


def render_metrics_to_fill(items: list) -> str:
    """Render the metrics-to-fill list as markdown."""
    if not items:
        return "## Metrics to Fill\n\nAll bullets have concrete metrics. No placeholders found."
    lines = ["## Metrics to Fill\n"]
    for item in items:
        lines.append(f"- **{item['experience']}** @ {item['company']}")
        lines.append(f"  Bullet: {item['bullet']}")
        lines.append(f"  Look up: {item['what_to_look_up']}")
    return "\n".join(lines)


def render_diff_summary(
    original_bullets: list, selected_bullets: list, icp_traits: list
) -> str:
    """Generate a 2-6 bullet diff summary of what was emphasized/de-emphasized."""
    selected_set = set(id(b) for b in selected_bullets)
    emphasized = [b for b in selected_bullets if b.relevance_score >= 2]
    deemphasized = [
        b for b in original_bullets
        if id(b) not in selected_set and b.relevance_score <= 1
    ]

    lines = ["## Diff Summary\n"]
    lines.append("**Emphasized:**")
    for b in emphasized[:3]:
        lines.append(f"- {b.resume_line[:80]}... (score: {b.relevance_score})")

    lines.append("\n**De-emphasized:**")
    for b in deemphasized[:3]:
        lines.append(f"- {b.resume_line[:80]}... (score: {b.relevance_score})")

    return "\n".join(lines)
