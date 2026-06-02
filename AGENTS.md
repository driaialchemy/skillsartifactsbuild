# AGENTS.md

## Project goal
This project is a hands-on learning sandbox for building a demand-planning prototype using synthetic M5-Walmart-style forecast data. The work is meant to help a novice understand how Claude Skills and Claude Artifacts operate by first recreating skill-like behavior in small Python scripts, then packaging one real Skill folder, and finally preparing a React artifact specification that can be pasted into Claude.ai.

## Tech stack
Python 3.10+ with the standard library, numpy, and streamlit. No other dependencies should be introduced unless the user explicitly approves them first.

## Folder layout
- `data/`: synthetic datasets, sample inputs, and generated intermediate files
- `scripts/`: standalone Python scripts that mimic skill behavior
- `skills/`: one real Claude Skill folder with `SKILL.md` and a bundled script later in the project
- `artifact/`: React artifact specification and related notes for Claude.ai
- `app/`: Streamlit human-in-the-loop review tool
- `README.md`: project overview and phased roadmap
- `.gitignore`: local and generated file exclusions for this project
- `AGENTS.md`: project memory file for future Codex work

## Coding rules
- Keep scripts under 150 lines whenever practical.
- Put explicit threshold constants at the top of any rule-based script.
- Use the Python standard library plus numpy only; do not add extra packages without asking first.
- Every script must be runnable standalone with `python scripts/<name>.py`.

## Workflow rules
- Read existing files in the directory before making changes.
- Verify work by running the relevant script and showing its output.
- Commit after each phase with a descriptive message.