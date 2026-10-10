"""A minimal Agent Skills loader that follows the agentskills.io specification.

discover()  scans a skills directory for <name>/SKILL.md and reads the frontmatter
catalog()   builds the small catalog the model sees at session start (tier 1)
activate()  returns the full SKILL.md body and lists bundled files (tier 2)
"""

import pathlib
import re

import yaml

NAME_RULE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")  # lowercase, digits, single hyphens


def parse(skill_md: pathlib.Path) -> tuple[dict, str]:
    text = skill_md.read_text()
    _, frontmatter, body = text.split("---", 2)
    return yaml.safe_load(frontmatter), body.strip()


def problems(meta: dict, folder: str) -> list[str]:
    name, description = meta.get("name", ""), meta.get("description", "")
    found = []
    if not (1 <= len(name) <= 64 and NAME_RULE.match(name)):
        found.append("name must be 1-64 lowercase letters, digits and single hyphens")
    if name != folder:
        found.append("name must match the folder name")
    if not 1 <= len(description) <= 1024:
        found.append("description must be 1-1024 characters")
    elif len(description) < 40:
        found.append("description is under 40 characters, our own rule so the model can match it")
    return found


def discover(root: pathlib.Path) -> dict[str, dict]:
    skills = {}
    for skill_md in sorted(root.glob("*/SKILL.md")):
        meta, _ = parse(skill_md)
        issues = problems(meta, skill_md.parent.name)
        if issues:
            print(f"skipped {skill_md.parent.name}: {'; '.join(issues)}")
            continue
        skills[meta["name"]] = {"description": meta["description"], "location": skill_md.resolve()}
    return skills


def catalog(skills: dict[str, dict]) -> str:
    entries = "\n".join(
        f"  <skill>\n    <name>{name}</name>\n    <description>{info['description']}</description>\n  </skill>"
        for name, info in skills.items())
    return f"<available_skills>\n{entries}\n</available_skills>"


def activate(skills: dict[str, dict], name: str) -> str:
    location = skills[name]["location"]
    _, body = parse(location)
    files = sorted(str(p.relative_to(location.parent)) for p in location.parent.rglob("*")
                   if p.is_file() and p.name != "SKILL.md")
    listed = "\n".join(f"  <file>{f}</file>" for f in files)
    return (f'<skill_content name="{name}">\n{body}\n\nSkill directory: {location.parent.name}\n'
            f"<skill_resources>\n{listed}\n</skill_resources>\n</skill_content>")
