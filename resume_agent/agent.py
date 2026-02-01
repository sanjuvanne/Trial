"""Resume Tailoring Agent — orchestrates the recursive operating loop.

This module ties together JD parsing, ICP construction, bullet scoring,
gap analysis, and resume building into a single interactive workflow.
"""

import json
import os
import sys

from resume_agent.bullet_bank import (
    Bullet,
    add_bullet,
    bullets_to_markdown_table,
    export_csv,
    load_bullets,
    save_bullets,
    score_all_bullets,
)
from resume_agent.config import BULLET_BANK_PATH, RESUME_PATH
from resume_agent.icp import ICP, build_gap_map, render_gap_map
from resume_agent.jd_parser import ParsedJD, parse_jd
from resume_agent.resume_builder import (
    build_metrics_to_fill,
    build_resume_markdown,
    render_diff_summary,
    render_metrics_to_fill,
    save_version,
)


class ResumeTailoringAgent:
    """Interactive agent that drives the resume tailoring loop."""

    def __init__(self):
        self.bullets = load_bullets()
        self.parsed_jd = None
        self.icp = None
        self.gap_map = None
        self.scored_bullets = []
        self.constraints = {}
        self.header_info = {}
        self.iteration = 0

    def step1_parse_jd(self, jd_text: str) -> ParsedJD:
        """Step 1: Parse the job description into structured fields."""
        self.parsed_jd = parse_jd(jd_text)
        return self.parsed_jd

    def step2_build_icp(self, traits: list = None) -> ICP:
        """Step 2: Build the Ideal Candidate Profile.

        Args:
            traits: List of dicts with keys: name, why, evidence, priority.
                    If None, uses heuristics from the parsed JD.
        """
        self.icp = ICP()

        if traits:
            for t in traits:
                self.icp.add_trait(
                    name=t["name"],
                    why=t["why"],
                    evidence=t["evidence"],
                    priority=t.get("priority", "must-have"),
                )
        elif self.parsed_jd:
            for comp in self.parsed_jd.required_competencies:
                self.icp.add_trait(
                    name=comp[:50],
                    why="Listed as required in JD",
                    evidence="Concrete example with metrics",
                    priority="must-have",
                )
            for nt in self.parsed_jd.nice_to_haves:
                self.icp.add_trait(
                    name=nt[:50],
                    why="Listed as preferred in JD",
                    evidence="Supporting example",
                    priority="nice-to-have",
                )

        return self.icp

    def step3_score_bullets(self) -> list:
        """Step 3: Score all bullets against the ICP."""
        trait_names = [t.name for t in self.icp.traits] if self.icp else []
        vocab = self.parsed_jd.vocabulary if self.parsed_jd else []
        self.scored_bullets = score_all_bullets(self.bullets, trait_names, vocab)
        return self.scored_bullets

    def step4_gap_analysis(self) -> list:
        """Step 4: Run gap analysis and generate questions."""
        self.gap_map = build_gap_map(self.icp, self.scored_bullets)
        return self.gap_map

    def add_new_bullets(self, new_bullets: list):
        """Add user-provided bullets and re-run scoring.

        Args:
            new_bullets: List of dicts with Bullet fields.
        """
        for nb in new_bullets:
            bullet = Bullet(
                company=nb.get("company", ""),
                experience=nb.get("experience", ""),
                resume_line=nb.get("resume_line", ""),
                duration=nb.get("duration", ""),
                themes=nb.get("themes", ""),
                metrics_present=nb.get("metrics_present", "N"),
                metrics_notes=nb.get("metrics_notes", ""),
            )
            self.bullets = add_bullet(self.bullets, bullet)

        save_bullets(self.bullets)
        self.step3_score_bullets()
        self.gap_map = build_gap_map(self.icp, self.scored_bullets)

    def step5_build_resume(self) -> str:
        """Step 5: Construct the targeted resume."""
        resume_md = build_resume_markdown(
            self.scored_bullets,
            header_info=self.header_info,
            constraints=self.constraints,
        )
        with open(RESUME_PATH, "w") as f:
            f.write(resume_md)
        return resume_md

    def step6_output_package(self, label: str = "") -> dict:
        """Step 6: Assemble and return the complete output package."""
        resume_md = self.step5_build_resume()
        version_path = save_version(resume_md, label=label)

        metrics_to_fill = build_metrics_to_fill(self.scored_bullets)
        diff_summary = render_diff_summary(
            self.bullets, self.scored_bullets, self.icp.traits if self.icp else []
        )

        package = {
            "icp": self.icp.render() if self.icp else "",
            "evidence_map": bullets_to_markdown_table(self.scored_bullets),
            "gap_map": render_gap_map(self.gap_map) if self.gap_map else "",
            "bullet_bank_csv": export_csv(self.bullets),
            "resume": resume_md,
            "metrics_to_fill": render_metrics_to_fill(metrics_to_fill),
            "diff_summary": diff_summary,
            "version_path": version_path,
        }

        return package

    def run_full_loop(self, jd_text: str, label: str = "") -> dict:
        """Run the complete operating loop (Steps 1-6).

        For human-in-the-loop interaction, call individual steps instead.
        """
        self.step1_parse_jd(jd_text)
        self.step2_build_icp()
        self.step3_score_bullets()
        self.step4_gap_analysis()
        return self.step6_output_package(label=label)

    def render_full_output(self, package: dict) -> str:
        """Render the complete output package as a single markdown document."""
        sections = [
            package["icp"],
            "",
            "---",
            "",
            "## Evidence Map",
            "",
            package["evidence_map"],
            "",
            "---",
            "",
            package["gap_map"],
            "",
            "---",
            "",
            "## Updated Bullet Bank (CSV)",
            "",
            "```csv",
            package["bullet_bank_csv"],
            "```",
            "",
            "---",
            "",
            "## Targeted Resume Draft",
            "",
            package["resume"],
            "",
            "---",
            "",
            package["metrics_to_fill"],
            "",
            "---",
            "",
            package["diff_summary"],
            "",
            f"\n*Version saved to: {package['version_path']}*",
        ]
        return "\n".join(sections)


def interactive_cli():
    """Run the agent as an interactive CLI."""
    agent = ResumeTailoringAgent()

    print("=" * 60)
    print("  Resume Strategy & Tailoring Agent")
    print("=" * 60)
    print()
    print("Paste the full job description for the role you're targeting.")
    print("(Enter an empty line followed by 'END' to finish input)")
    print()

    jd_lines = []
    while True:
        line = input()
        if line.strip().upper() == "END":
            break
        jd_lines.append(line)
    jd_text = "\n".join(jd_lines)

    if not jd_text.strip():
        print("No job description provided. Exiting.")
        sys.exit(1)

    print("\nAny constraints? (e.g., '1-page, emphasize quality')")
    print("Press Enter to skip:")
    constraints_input = input().strip()
    if constraints_input:
        agent.constraints["notes"] = constraints_input

    # Run Steps 1-4
    print("\n--- Step 1: Parsing JD ---")
    parsed = agent.step1_parse_jd(jd_text)
    print(parsed.summary())

    print("\n--- Step 2: Building ICP ---")
    icp = agent.step2_build_icp()
    print(icp.render())

    print("\n--- Step 3: Scoring Bullets ---")
    scored = agent.step3_score_bullets()
    print(f"Scored {len(scored)} bullets.")
    for b in scored[:5]:
        print(f"  [{b.relevance_score}] {b.resume_line[:70]}...")

    print("\n--- Step 4: Gap Analysis ---")
    gap_map = agent.step4_gap_analysis()
    print(render_gap_map(gap_map))

    # Human-in-the-loop
    missing = [e for e in gap_map if e.status in ("partial", "missing")]
    if missing:
        print("\n--- Human-in-the-Loop ---")
        print("I have questions about gaps in your evidence.")
        print("Answer each or press Enter to skip.\n")

        new_bullets_data = []
        for entry in missing:
            print(f"\nTrait: {entry.trait.name}")
            for q in entry.questions:
                print(f"  Q: {q}")
                answer = input("  A: ").strip()
                if answer:
                    new_bullets_data.append({
                        "company": "",
                        "experience": "",
                        "resume_line": answer,
                        "themes": entry.trait.name,
                        "metrics_present": "Y" if any(
                            c.isdigit() for c in answer
                        ) else "N",
                    })

        if new_bullets_data:
            print("\nAdding new bullets and re-scoring...")
            agent.add_new_bullets(new_bullets_data)

    # Build and output
    print("\n--- Step 5 & 6: Building Resume & Output Package ---")
    package = agent.step6_output_package(label="cli")
    full_output = agent.render_full_output(package)
    print("\n" + full_output)

    print("\nDone. Resume saved to:", RESUME_PATH)
    print("Version saved to:", package["version_path"])


if __name__ == "__main__":
    interactive_cli()
