# SKaiNET contributor skills — Index

Skills that fire ONLY when the agent is editing files **inside the SKaiNET repository** (`/home/miso/projects/SKills/SKaiNET/` or wherever the repo is cloned). Each skill enforces in-repo conventions: package layout, version-catalog discipline, KMP source-set placement, the Java-facade convention, and the in-repo test policy.

If the user is writing application code that *consumes* SKaiNET as a library, none of these should fire — the sibling **skainet-consumer-skills** plugin covers that audience. The two plugins are designed to be installed together; the descriptions disambiguate via path heuristics so only one fires per prompt.

## Layering

```
gradle-multimodule  →  kmp  →  kotlin
                                ↓
                  skainet-java-interop
                                ↓
                       skainet-testing
```

## Skills

| Skill | Trigger sentence (matches when the user…) |
|---|---|
| [kotlin](kotlin/SKILL.md) | edits `.kt` files inside the SKaiNET repo — explicit-API mode, package layout, sealed hierarchies, `value class`. |
| [gradle-multimodule](gradle-multimodule/SKILL.md) | edits `SKaiNET/build.gradle.kts`, `SKaiNET/settings.gradle.kts`, `SKaiNET/gradle/libs.versions.toml`, `SKaiNET/build-logic/`, or adds a new `skainet-*` module within SKaiNET. |
| [kmp](kmp/SKILL.md) | configures KMP targets or moves code between source-sets in a `SKaiNET/skainet-*/` module. |
| [skainet-java-interop](skainet-java-interop/SKILL.md) | designs the Java-facing facade INSIDE SKaiNET — files under `SKaiNET/*/jvmMain/kotlin/sk/ainet/java/`. |
| [skainet-testing](skainet-testing/SKILL.md) | writes or edits tests INSIDE SKaiNET — Kotest specs in `jvmTest/`, `kotlin.test` in `commonTest/`, `TensorAssertions` + `ToleranceConfig`, JUnit 5 mirrors in `skainet-test-java`. |

## Public DSL skills (consumer plugin)

The two skills that teach how to *use* the public DSL — `skainet-data-dsl` and `skainet-nn-dsl` — live in the **skainet-consumer-skills** plugin because they describe the public API surface that BOTH consumers and contributors invoke. Contributors editing the DSL implementation use the `kotlin` skill above for idiom rules.

## Conventions

- Every code example in a SKILL.md ends with `// from: <path>:<line-range>`.
- Each SKILL.md states "When NOT to use" up front and explicitly defers consumer-style use cases to the consumer plugin.
- Hard rules are numbered MUST statements; the cheatsheet style (DSL skills) is reserved for the consumer plugin.
