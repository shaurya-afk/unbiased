import asyncio
import os
from collections import defaultdict

from google import genai

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


async def generate_context_files(raw) -> dict[str, str]:
    stack, projects, experience = await asyncio.gather(
        _call_gemini(_stack_prompt(raw)),
        _call_gemini(_projects_prompt(raw)),
        _call_gemini(_experience_prompt(raw)),
    )
    return {"stack.md": stack, "projects.md": projects, "experience.md": experience}


async def _call_gemini(prompt: str) -> str:
    response = await _get_client().aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text


def _stack_prompt(raw) -> str:
    lang_totals: dict[str, int] = defaultdict(int)
    for langs in raw.languages_json.values():
        for lang, count in langs.items():
            lang_totals[lang] += count
    sorted_langs = sorted(lang_totals.items(), key=lambda x: x[1], reverse=True)
    lang_summary = "\n".join(f"- {lang}: {count:,} bytes" for lang, count in sorted_langs[:15])

    dep_lines = []
    all_topics: set[str] = set()
    for repo in raw.repos_json:
        all_topics.update(repo.get("topics", []))
        for fname, content in repo.get("dep_files", {}).items():
            dep_lines.append(f"### {repo['name']} / {fname}\n{content[:500]}")

    deps_text = "\n\n".join(dep_lines[:20]) if dep_lines else "(none found)"
    topics_text = ", ".join(sorted(all_topics)) if all_topics else "(none)"

    return f"""You are a technical writer analyzing a developer's GitHub profile.

## Language Usage (by bytes)
{lang_summary}

## Repository Topics
{topics_text}

## Dependency Files Found
{deps_text}

Write a concise stack.md markdown document with exactly these sections:
# Tech Stack

## Languages
Bullet list of primary languages with rough usage proportion.

## Frameworks & Libraries
Bullet list inferred from the dependency files above.

## Tools & Platforms
Bullet list inferred from topics and repo patterns.

Be factual and concise. Only include what the data supports."""


def _projects_prompt(raw) -> str:
    repo_blocks = []
    for repo in raw.repos_json:
        name = repo["name"]
        desc = repo.get("description") or "(no description)"
        topics = ", ".join(repo.get("topics", [])) or "(none)"
        stars = repo.get("stars", 0)
        readme = raw.readmes_json.get(name, "")[:400]
        repo_blocks.append(
            f"**{name}** ({stars} stars)\n"
            f"Description: {desc}\n"
            f"Topics: {topics}\n"
            f"README excerpt:\n{readme}"
        )
    repos_text = "\n\n---\n\n".join(repo_blocks)

    return f"""You are summarizing a developer's GitHub projects.

## Repository Data
{repos_text}

Write a projects.md markdown document.
For each notable project (skip trivial/test/hello-world repos), use this format:

## project-name
One to two sentence description of what the project does.
**Tech:** comma-separated key technologies used

Order by importance/interest, most notable first. Aim for 3-8 projects."""


def _experience_prompt(raw) -> str:
    lang_totals: dict[str, int] = defaultdict(int)
    for langs in raw.languages_json.values():
        for lang, count in langs.items():
            lang_totals[lang] += count
    top_langs = [lang for lang, _ in sorted(lang_totals.items(), key=lambda x: x[1], reverse=True)[:8]]

    all_topics: set[str] = set()
    oldest = None
    for repo in raw.repos_json:
        all_topics.update(repo.get("topics", []))
        pushed = repo.get("pushed_at", "")
        if pushed and (oldest is None or pushed < oldest):
            oldest = pushed

    top_star_repo = max(raw.repos_json, key=lambda r: r.get("stars", 0), default=None)
    top_star_info = (
        f"{top_star_repo['name']} ({top_star_repo.get('stars', 0)} stars)"
        if top_star_repo else "unknown"
    )

    return f"""You are inferring a developer's background from their GitHub data.

## GitHub Summary
- Repos analyzed: {len(raw.repos_json)}
- Top languages: {", ".join(top_langs)}
- Repository topics: {", ".join(sorted(all_topics)[:30]) or "(none)"}
- Oldest active repo pushed_at: {oldest or "unknown"}
- Most starred repo: {top_star_info}

Write an experience.md markdown document with exactly this structure:
# Experience

2-3 paragraphs describing:
1. Estimated experience level and how long they've been actively coding on GitHub
2. Primary domain and areas of expertise
3. Notable strengths or patterns observed in their work

Be conservative and data-driven. Don't invent details not in the data."""
