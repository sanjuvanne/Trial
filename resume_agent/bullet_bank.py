"""Bullet bank manager — load, score, update, and persist resume bullets."""

import csv
import io
import os
import re
from dataclasses import dataclass, field

from resume_agent.config import BULLET_BANK_PATH, BULLET_FIELDS, RELEVANCE_SCALE


@dataclass
class Bullet:
    company: str = ""
    experience: str = ""
    resume_line: str = ""
    duration: str = ""
    themes: str = ""
    metrics_present: str = "N"
    metrics_notes: str = ""
    relevance_score: int = 0

    def to_row(self) -> list:
        return [
            self.company,
            self.experience,
            self.resume_line,
            self.duration,
            self.themes,
            self.metrics_present,
            self.metrics_notes,
        ]

    def score_label(self) -> str:
        return RELEVANCE_SCALE.get(self.relevance_score, "Unknown")

    def has_metrics(self) -> bool:
        return self.metrics_present.upper().startswith("Y")


def load_bullets(path: str = BULLET_BANK_PATH) -> list:
    """Load bullets from the markdown bullet bank file."""
    if not os.path.exists(path):
        return []

    with open(path, "r") as f:
        content = f.read()

    table_rows = re.findall(r"^\|(.+)\|$", content, re.MULTILINE)
    bullets = []
    data_started = False
    for row in table_rows:
        cells = [c.strip() for c in row.split("|")]
        if all(c == "" or set(c) <= {"-", " "} for c in cells):
            data_started = True
            continue
        if not data_started:
            continue
        if len(cells) < 3 or not any(cells):
            continue

        b = Bullet(
            company=cells[0] if len(cells) > 0 else "",
            experience=cells[1] if len(cells) > 1 else "",
            resume_line=cells[2] if len(cells) > 2 else "",
            duration=cells[3] if len(cells) > 3 else "",
            themes=cells[4] if len(cells) > 4 else "",
            metrics_present=cells[5] if len(cells) > 5 else "N",
            metrics_notes=cells[6] if len(cells) > 6 else "",
        )
        if b.resume_line:
            bullets.append(b)

    return bullets


def save_bullets(bullets: list, path: str = BULLET_BANK_PATH):
    """Persist bullets back to the markdown bullet bank file."""
    lines = [
        "# Master Bullet Bank\n",
        "This is the canonical source of truth for all resume bullets.\n",
        "## Bullets\n",
        "| Company | Experience | Resume Line | Duration | Themes | Metrics Present | Metrics Notes |",
        "|---------|-----------|-------------|----------|--------|-----------------|---------------|",
    ]
    for b in bullets:
        row = "| " + " | ".join(b.to_row()) + " |"
        lines.append(row)

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def add_bullet(bullets: list, bullet: Bullet) -> list:
    """Add a new bullet to the bank (never deletes existing ones)."""
    bullets.append(bullet)
    return bullets


def score_bullet(bullet: Bullet, icp_traits: list, jd_vocabulary: list) -> int:
    """Score a bullet against ICP traits on a 0-3 scale.

    Heuristic scoring based on keyword overlap. The LLM agent layer
    will refine scores with semantic understanding.
    """
    text = (bullet.resume_line + " " + bullet.themes).lower()
    trait_hits = sum(1 for t in icp_traits if t.lower() in text)
    vocab_hits = sum(1 for v in jd_vocabulary if v.lower() in text)

    total = trait_hits * 2 + vocab_hits
    if total >= 5:
        return 3
    elif total >= 3:
        return 2
    elif total >= 1:
        return 1
    return 0


def score_all_bullets(
    bullets: list, icp_traits: list, jd_vocabulary: list
) -> list:
    """Score and sort all bullets by relevance, descending."""
    for b in bullets:
        b.relevance_score = score_bullet(b, icp_traits, jd_vocabulary)
    return sorted(bullets, key=lambda b: b.relevance_score, reverse=True)


def bullets_to_markdown_table(bullets: list) -> str:
    """Render bullets as a markdown table string."""
    lines = [
        "| Company | Experience | Resume Line | Duration | Themes | Metrics | Score |",
        "|---------|-----------|-------------|----------|--------|---------|-------|",
    ]
    for b in bullets:
        score_display = f"{b.relevance_score} ({b.score_label()})"
        row = (
            f"| {b.company} | {b.experience} | {b.resume_line} "
            f"| {b.duration} | {b.themes} | {b.metrics_present} | {score_display} |"
        )
        lines.append(row)
    return "\n".join(lines)


def export_csv(bullets: list) -> str:
    """Export bullets as CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(BULLET_FIELDS)
    for b in bullets:
        writer.writerow(b.to_row())
    return output.getvalue()
