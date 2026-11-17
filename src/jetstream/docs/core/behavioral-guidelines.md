# Behavioral guidelines

How Claude (and anyone else) should work in a Cloudfeaster repo. They lean towards caution over speed; for a trivial task, use judgment.

## 1. Think before coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions. If you're unsure, ask.
- If a request can be read more than one way, say so; don't pick one silently.
- If there's a simpler approach, say so, and push back when it's warranted.
- If something is unclear, stop, name what's confusing, and ask.

## 2. Simplicity first

**The least code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for code used once.
- No "flexibility" or "configurability" that wasn't asked for.
- No error handling for things that can't happen.
- If you wrote 200 lines and it could be 50, rewrite it.

Ask: would a senior engineer say this is overcomplicated? If so, simplify.

## 3. Surgical changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" nearby code, comments or formatting.
- Don't refactor what isn't broken.
- Match the existing style, even if you'd write it differently.
- If you notice unrelated dead code, mention it; don't delete it.

When your change leaves something unused:

- Remove the imports, variables and functions that your change made unused.
- Leave dead code that was already there, unless asked.

The test: every changed line traces directly to the request.

## 4. Goal-driven execution

**Define what success looks like, and loop until it's verified.**

Turn tasks into goals you can check:

- "Add validation" → "write tests for invalid inputs, then make them pass".
- "Fix the bug" → "write a test that reproduces it, then make it pass".
- "Refactor X" → "make sure the tests pass before and after".

For a task with several steps, state a short plan:

```text
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Clear success criteria let you work on your own; vague ones ("make it work") need constant clarification.

## 5. Capture repeated tasks as skills

**When someone describes a routine, multi-step task they do repeatedly, propose capturing it as a Claude Code skill.**

- A skill specific to the repo goes in its `.claude/skills/<name>/SKILL.md`, checked in.
- Propose a skill rather than repeating the same manual steps each time the task comes up.
- Don't propose one for a one-off task, or one simple enough that a skill would only add indirection.

---

**These guidelines are working if** diffs have fewer unnecessary changes, fewer rewrites are needed because of overcomplication, and clarifying questions come before implementation rather than after mistakes.
