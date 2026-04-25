# Contributing to skainet-coding-skills

Thanks for helping make the SKaiNET skill set better. This guide covers how skills are structured, the citation rules, the eval format, and the local checks before opening a PR.

## What goes in which plugin

- **`skainet-contributor-skills/`** — fires only when editing files inside the SKaiNET repo itself (build scripts, source code under `SKaiNET/skainet-*/`, tests). Each skill enforces an in-repo convention.
- **`skainet-consumer-skills/`** — fires when the user is using SKaiNET as a library in their own app. Includes the public DSL skills and the integration skills (Android, Java, model loading, inference).

If you're unsure where a new skill belongs: ask "would this be useful to a developer who doesn't have the SKaiNET source tree on disk?". If yes → consumer plugin. If no → contributor plugin.

## Skill anatomy

Every skill lives at `<plugin>/skills/<skill-name>/` and contains:

```
SKILL.md            — frontmatter + workflow + canonical examples
references/         — one or more lookup-table .md files
evals/evals.json    — first-pass scenario tests
```

### `SKILL.md` template

```markdown
---
name: <skill-name>
description: <ONE sentence noun-phrase. Trigger tokens. WHEN NOT to use.>
version: 0.1.0
---

# <skill-name>

<One-paragraph purpose.>

## When to use
- bullets

## When NOT to use
- bullets — explicitly defer to sibling skills here

## Hard rules               (numbered MUST list — for constraint skills only)
1. ...

## Cheatsheet               (for the two pure-DSL skills only — replaces "Hard rules")

## Workflow
1. ...

## Canonical examples
<code blocks ending with: // from: <abs-path-or-relative-to-repo-root>:<line-range>>

## Related skills
- relative links to sibling SKILL.md files

## Anti-patterns
WRONG / RIGHT pairs.

## References
- [`references/<file>.md`](references/<file>.md) — one-line summary.
```

### `description` field

This is the **trigger sentence** Claude reads to decide whether to invoke the skill. Three rules:

1. **Lead with concrete tokens** the user might type (`tensor {`, `sequential<`, `@JvmStatic`, `viewModelScope`).
2. **Always include "Do NOT fire on …"** at least once, deferring to a sibling skill.
3. **Path-heuristic the audience**. Contributor skills say "INSIDE the SKaiNET repo"; consumer skills say "in your own Gradle project". Without this, the two plugins fire on the same prompts.

### Hard rules vs. cheatsheet

- Use **Hard rules** for skills that enforce a convention (`kotlin`, `gradle-multimodule`, `kmp`, `skainet-java-interop`, `skainet-testing`, `skainet-consumer-setup`, `skainet-android-integration`, `skainet-java-consumer`, `skainet-model-loading`, `skainet-inference`).
- Use **Cheatsheet** for skills that teach the public DSL (`skainet-data-dsl`, `skainet-nn-dsl`).

Don't mix the two in one skill — pick the audience and stick with it.

## Citation rules

Every code example in a SKILL.md or reference file MUST end with:

```kotlin
// from: SKaiNET/<absolute-path-from-SKaiNET-root>:<start>-<end>
```

Examples:

```
// from: SKaiNET/skainet-lang/skainet-lang-core/src/commonMain/kotlin/sk/ainet/lang/tensor/dsl/TensorDSL.kt:17-25
// from: SKaiNET/gradle/libs.versions.toml:1-95
// from: SKaiNET/skainet-test/skainet-test-java/src/test/java/sk/ainet/java/TensorJavaOpsTest.java:25-38
```

CI runs `tools/verify-citations.py` against a fresh SKaiNET clone on every PR. Citations that point at non-existent paths or out-of-range lines fail the build.

If you're citing the same file at multiple ranges, repeat the `// from:` comment per excerpt.

## Eval scenarios

Every skill ships an `evals/evals.json`:

```json
{
  "$schema": "https://json.schemastore.org/skainet-skill-evals-v1.json",
  "skill": "<skill-name>",
  "scenarios": [
    {
      "id": "<short-kebab-id>",
      "prompt": "<user-style ask that should activate this skill>",
      "must_contain": ["snippet 1", "snippet 2"],
      "must_not_contain": ["anti-pattern 1"],
      "must_not_contain_reason": "<one-line WHY these are forbidden — null if no anti-patterns>"
    }
  ]
}
```

Aim for 3–5 scenarios per skill — enough to catch regressions, not so many that maintenance churns. Each scenario should:

- Match a real user prompt the skill should fire on.
- Assert at least one positive token (`must_contain`) that exercises the canonical pattern.
- Assert at least one anti-pattern in `must_not_contain` (with `must_not_contain_reason`), unless the skill has none.

## Local development

```sh
# Clone the marketplace and SKaiNET as siblings
git clone https://github.com/SKaiNET-developers/skainet-coding-skills.git
git clone https://github.com/SKaiNET-developers/SKaiNET.git

cd skainet-coding-skills

# Run the citation check
python3 tools/verify-citations.py
```

Install the plugins locally to dogfood your changes:

```text
/plugin marketplace add /path/to/skainet-coding-skills
/plugin install skainet-contributor-skills
/plugin install skainet-consumer-skills
```

## Adding a new skill — checklist

- [ ] Decided which plugin it belongs in (contributor vs consumer).
- [ ] Created `<plugin>/skills/<name>/{SKILL.md, references/, evals/evals.json}`.
- [ ] `SKILL.md` description names concrete trigger tokens AND a "Do NOT fire on" deferral.
- [ ] `SKILL.md` description includes a path-heuristic for the audience.
- [ ] Every code example ends with `// from: <path>:<lines>`.
- [ ] At least 3 evals scenarios with `must_contain` + (where applicable) `must_not_contain` + reason.
- [ ] Added a row to the plugin's `skills/INDEX.md` table.
- [ ] Cross-references to related skills use relative `[`text`](../sibling/SKILL.md)` links within the same plugin; cross-plugin references use plain prose ("see the X skill in the sibling plugin").
- [ ] `python3 tools/verify-citations.py` passes locally.

## Bumping skill versions

When a skill's behaviour changes meaningfully, bump its version in the SKILL.md frontmatter (semver-style: `0.1.0` → `0.2.0` for new features, `0.1.0` → `0.1.1` for fixes). The plugin-level version in `<plugin>/.claude-plugin/plugin.json` bumps when ANY of its skills bump.

## Code of conduct

This project follows the SKaiNET-developers organization-wide [code of conduct](https://github.com/SKaiNET-developers). Be kind; assume good faith; review each other's work concretely.

## License

By contributing, you agree your contributions will be licensed under [MIT](LICENSE).
