"""Job description parser — extracts structured signals from a raw JD."""

import re
from dataclasses import dataclass, field


@dataclass
class ParsedJD:
    raw_text: str
    company: str = ""
    product_surface: str = ""
    seniority_scope: str = ""
    success_criteria: list = field(default_factory=list)
    required_competencies: list = field(default_factory=list)
    evaluation_signals: list = field(default_factory=list)
    vocabulary: list = field(default_factory=list)
    nice_to_haves: list = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Company: {self.company}",
            f"Product Surface: {self.product_surface}",
            f"Seniority Scope: {self.seniority_scope}",
            "",
            "Success Criteria:",
        ]
        for c in self.success_criteria:
            lines.append(f"  - {c}")
        lines.append("")
        lines.append("Required Competencies:")
        for c in self.required_competencies:
            lines.append(f"  - {c}")
        lines.append("")
        lines.append("Evaluation Signals:")
        for s in self.evaluation_signals:
            lines.append(f"  - {s}")
        lines.append("")
        lines.append("Key Vocabulary:")
        for v in self.vocabulary:
            lines.append(f"  - {v}")
        if self.nice_to_haves:
            lines.append("")
            lines.append("Nice-to-Haves:")
            for n in self.nice_to_haves:
                lines.append(f"  - {n}")
        return "\n".join(lines)


def extract_sections(text: str) -> dict:
    """Split a JD into named sections based on common heading patterns."""
    heading_re = re.compile(
        r"^(#{1,3}\s+.+|[A-Z][A-Za-z\s/&]{2,}:?\s*)$", re.MULTILINE
    )
    sections = {}
    matches = list(heading_re.finditer(text))
    for i, match in enumerate(matches):
        key = match.group(1).strip().lstrip("#").strip(":").strip().lower()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections[key] = body
    return sections


def extract_bullet_items(text: str) -> list:
    """Pull bullet-pointed or numbered list items from a block of text."""
    items = re.findall(r"(?:^|\n)\s*[-•*]\s+(.+)", text)
    items += re.findall(r"(?:^|\n)\s*\d+[.)]\s+(.+)", text)
    return [item.strip() for item in items if item.strip()]


def parse_jd(text: str) -> ParsedJD:
    """Parse a raw job description into structured fields.

    This performs heuristic extraction. For higher-quality parsing,
    the agent's LLM step will refine these fields interactively.
    """
    parsed = ParsedJD(raw_text=text)
    sections = extract_sections(text)

    all_bullets = extract_bullet_items(text)

    for key, body in sections.items():
        bullets = extract_bullet_items(body)
        if any(w in key for w in ["about", "company", "who we are"]):
            parsed.company = body.split("\n")[0].strip() if body else ""
            parsed.product_surface = body[:200]
        elif any(w in key for w in ["responsibilit", "what you", "role"]):
            parsed.success_criteria.extend(bullets or [body[:200]])
        elif any(w in key for w in ["requirement", "qualification", "must"]):
            parsed.required_competencies.extend(bullets or [body[:200]])
        elif any(w in key for w in ["nice", "preferred", "bonus"]):
            parsed.nice_to_haves.extend(bullets or [body[:200]])

    tech_terms = re.findall(
        r"\b(?:[A-Z][a-z]+(?:\s[A-Z][a-z]+)*|[A-Z]{2,}(?:/[A-Z]{2,})*)\b", text
    )
    common_words = {
        "The", "This", "You", "We", "Our", "Your", "What", "How", "Who",
        "Are", "Will", "And", "For", "With", "About", "Have", "Been",
        "From", "That", "They", "Their", "Some", "More", "Any", "All",
        "Not", "But", "Can", "May", "Must", "Should", "Would", "Could",
    }
    vocab = sorted(set(t for t in tech_terms if t not in common_words))
    parsed.vocabulary = vocab[:30]

    return parsed
