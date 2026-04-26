# planner-memo skill

This packaged skill wraps the same core memo-generation logic as `scripts/generate_memos.py`, but it adds the pieces Claude needs to use it as a skill: a trigger-focused `SKILL.md`, a portable bundled script that accepts input and output paths, and a clear input/output contract. The loose script in `scripts/` stays project-specific and uses hardcoded paths so you can compare the two approaches directly.

You can use this skill in two main ways. In Claude.ai, upload the `skills/planner-memo/` folder as a skill so Claude can decide when to invoke it based on the frontmatter description and then use the bundled script. In the Claude API, reference the same skill folder through your skill-loading workflow so the model gets the same metadata, instructions, and bundled script.

To understand skill triggering, focus on the YAML frontmatter at the top of `SKILL.md`, especially the `description`. That description is the trigger surface Claude pattern-matches before it ever reads the body. The body sections help after the skill triggers, but the `name` and `description` are what determine whether Claude considers the skill relevant in the first place.
