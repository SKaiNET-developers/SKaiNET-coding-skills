<!-- Thanks for contributing! Please fill out the relevant sections below. -->

## Summary

<!-- One or two sentences on what this PR changes. -->

## Type of change

- [ ] New skill
- [ ] Update to an existing skill (clarification, anti-pattern, new example)
- [ ] New eval scenario
- [ ] SKaiNET API drifted — citations / signatures need refresh
- [ ] Tooling / CI / docs

## Checklist

- [ ] Skill `description` includes concrete trigger tokens AND a "Do NOT fire on" deferral.
- [ ] Skill `description` includes a path-heuristic for the audience (contributor vs. consumer).
- [ ] Every code example ends with `// from: <path>:<lines>`.
- [ ] `python3 tools/verify-citations.py` passes locally.
- [ ] `evals/evals.json` updated if the canonical pattern changed.
- [ ] Plugin `version` bumped if a skill's behaviour changed meaningfully.
- [ ] Plugin's `skills/INDEX.md` table updated if a skill was added/removed/renamed.

## Notes for reviewers

<!-- Anything reviewers should pay particular attention to: trigger collisions, eval scenarios that nearly fail, etc. -->
