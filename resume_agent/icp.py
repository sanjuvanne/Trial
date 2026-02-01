"""Ideal Candidate Profile (ICP) builder and gap analysis."""

from dataclasses import dataclass, field


@dataclass
class ICPTrait:
    name: str
    why_it_matters: str
    evidence_needed: str
    priority: str = "must-have"  # "must-have" or "nice-to-have"
    covered: bool = False
    supporting_bullets: list = field(default_factory=list)
    coverage_strength: str = "missing"  # "strong", "partial", "missing"


@dataclass
class ICP:
    traits: list = field(default_factory=list)

    def add_trait(
        self,
        name: str,
        why: str,
        evidence: str,
        priority: str = "must-have",
    ) -> "ICP":
        self.traits.append(
            ICPTrait(
                name=name,
                why_it_matters=why,
                evidence_needed=evidence,
                priority=priority,
            )
        )
        return self

    def ranked_traits(self) -> list:
        priority_order = {"must-have": 0, "nice-to-have": 1}
        return sorted(
            self.traits,
            key=lambda t: (priority_order.get(t.priority, 2), t.name),
        )

    def must_haves(self) -> list:
        return [t for t in self.traits if t.priority == "must-have"]

    def nice_to_haves(self) -> list:
        return [t for t in self.traits if t.priority == "nice-to-have"]

    def render(self) -> str:
        lines = ["## Ideal Candidate Profile\n"]
        lines.append("### Must-Have Traits")
        for i, t in enumerate(self.must_haves(), 1):
            lines.append(f"\n**{i}. {t.name}**")
            lines.append(f"  - Why: {t.why_it_matters}")
            lines.append(f"  - Evidence needed: {t.evidence_needed}")

        nths = self.nice_to_haves()
        if nths:
            lines.append("\n### Nice-to-Have Traits")
            for i, t in enumerate(nths, 1):
                lines.append(f"\n**{i}. {t.name}**")
                lines.append(f"  - Why: {t.why_it_matters}")
                lines.append(f"  - Evidence needed: {t.evidence_needed}")

        return "\n".join(lines)


@dataclass
class GapMapEntry:
    trait: ICPTrait
    status: str  # "covered", "partial", "missing"
    bullets: list = field(default_factory=list)
    questions: list = field(default_factory=list)


def build_gap_map(icp: ICP, scored_bullets: list) -> list:
    """Compare ICP traits to scored bullets and produce a gap map.

    For each trait, classify as covered / partial / missing based on
    whether high-scoring bullets exist that address it.
    """
    gap_map = []
    for trait in icp.ranked_traits():
        matching = [
            b
            for b in scored_bullets
            if trait.name.lower() in (b.resume_line + " " + b.themes).lower()
            and b.relevance_score >= 2
        ]
        partial = [
            b
            for b in scored_bullets
            if trait.name.lower() in (b.resume_line + " " + b.themes).lower()
            and b.relevance_score == 1
        ]

        if matching:
            status = "covered"
            trait.covered = True
            trait.coverage_strength = "strong"
        elif partial:
            status = "partial"
            trait.coverage_strength = "partial"
        else:
            status = "missing"
            trait.coverage_strength = "missing"

        entry = GapMapEntry(
            trait=trait,
            status=status,
            bullets=matching or partial,
        )

        if status == "partial":
            entry.questions = [
                f"Can you share a specific example where you demonstrated {trait.name}?",
                f"What metrics or outcomes can you cite for {trait.name}?",
            ]
        elif status == "missing":
            entry.questions = [
                f"Do you have experience with {trait.name}? Describe a concrete example.",
                f"What was the scope (team size, users, revenue impact) of your work in {trait.name}?",
                f"Who were the stakeholders and what was your decision authority for {trait.name}?",
            ]

        gap_map.append(entry)

    return gap_map


def render_gap_map(gap_map: list) -> str:
    """Render the gap map as readable markdown."""
    lines = ["## Gap Map\n"]

    covered = [e for e in gap_map if e.status == "covered"]
    partial = [e for e in gap_map if e.status == "partial"]
    missing = [e for e in gap_map if e.status == "missing"]

    lines.append(f"### Covered ({len(covered)} traits)")
    for e in covered:
        bullet_summary = "; ".join(
            b.resume_line[:60] + "..." for b in e.bullets[:3]
        )
        lines.append(f"- **{e.trait.name}**: {bullet_summary}")

    lines.append(f"\n### Partial ({len(partial)} traits)")
    for e in partial:
        lines.append(f"- **{e.trait.name}** (needs strengthening)")
        for q in e.questions:
            lines.append(f"  - Q: {q}")

    lines.append(f"\n### Missing ({len(missing)} traits)")
    for e in missing:
        lines.append(f"- **{e.trait.name}** (no evidence found)")
        for q in e.questions:
            lines.append(f"  - Q: {q}")

    return "\n".join(lines)
