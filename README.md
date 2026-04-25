# SKaiNET skills marketplace

A [Claude Code](https://docs.claude.com/en/docs/claude-code) plugin marketplace hosting two skill bundles for working with [SKaiNET](https://github.com/SKaiNET-developers/SKaiNET) — the Kotlin Multiplatform on-device ML/AI framework.

The two plugins are designed to be installed together; descriptions disambiguate via path heuristics so the right one fires for a given prompt.

## Plugins

### `skainet-contributor-skills`

For developers **contributing to SKaiNET itself** (editing files inside the SKaiNET repo).

| Skill | What it covers |
|---|---|
| `kotlin` | Explicit-API mode, package layout, sealed hierarchies, `value class`. |
| `gradle-multimodule` | Version-catalog discipline, convention plugins, BOM membership, `binary-compatibility-validator`. |
| `kmp` | Full target matrix (JVM/Android/iOS/macOS/Linux/androidNative/JS/WASM), source-set hierarchy, KSP wiring. |
| `skainet-java-interop` | The `@file:JvmName` / `object` + `@JvmStatic` facade convention under `*/jvmMain/kotlin/sk/ainet/java/`. |
| `skainet-testing` | Kotest in `jvmTest`, `kotlin.test` in `commonTest`, `TensorAssertions` + `ToleranceConfig`, JUnit 5 mirror in `skainet-test-java`. |

### `skainet-consumer-skills`

For developers **using SKaiNET as a library** in their own Kotlin / Java / Android / KMP app.

| Skill | What it covers |
|---|---|
| `skainet-consumer-setup` | BOM (`sk.ainet:skainet-bom`), library coordinates (`sk.ainet.core:skainet-*`), artifact picker. |
| `skainet-data-dsl` | `tensor { shape(…) { … } }`, transform pipelines, slice views. |
| `skainet-nn-dsl` | `sequential<T, V> { }` and `dag { }` neural-network builders. |
| `skainet-model-loading` | GGUF, ONNX, SafeTensors, JSON loaders. |
| `skainet-inference` | `ExecutionContext`, `model.forward(x, ctx)`, batching, threading, TurboQuant KV-cache. |
| `skainet-android-integration` | `assets/` → `cacheDir`, `viewModelScope` + `Dispatchers.Default`, ABI filters, `onTrimMemory`. |
| `skainet-java-consumer` | Maven dependencies, `SKaiNET.context()`, `TensorJavaOps.*`, `StableHloConverterFactory`, `TokenizerFactory`. |

## Installation

Clone this repository and point Claude Code at the marketplace:

```sh
git clone https://github.com/<your-fork>/skainet-skills.git ~/projects/SKills
```

Then in any Claude Code session run `/plugin marketplace add ~/projects/SKills`, followed by `/plugin install skainet-contributor-skills` and/or `/plugin install skainet-consumer-skills`.

## Layout

```
.
├── .claude-plugin/
│   └── marketplace.json                 # lists both plugins
├── skainet-contributor-skills/
│   ├── .claude-plugin/plugin.json
│   └── skills/
│       ├── INDEX.md
│       ├── kotlin/
│       ├── gradle-multimodule/
│       ├── kmp/
│       ├── skainet-java-interop/
│       └── skainet-testing/
└── skainet-consumer-skills/
    ├── .claude-plugin/plugin.json
    └── skills/
        ├── INDEX.md
        ├── skainet-consumer-setup/
        ├── skainet-data-dsl/
        ├── skainet-nn-dsl/
        ├── skainet-model-loading/
        ├── skainet-inference/
        ├── skainet-android-integration/
        └── skainet-java-consumer/
```

Each skill directory contains a `SKILL.md` (frontmatter + workflow + canonical examples), a `references/` folder with lookup tables, and an `evals/evals.json` with first-pass scenario tests.

## Conventions

- Every code example in a SKILL.md ends with `// from: <path>:<line-range>` so a citation check can verify it stays in sync with SKaiNET source as the framework evolves.
- Descriptions explicitly say when each skill should NOT fire, to prevent trigger collisions across the two plugins.
- Constraint skills (`kotlin`, `gradle-multimodule`, `kmp`, `skainet-java-interop`, `skainet-testing`, `skainet-consumer-setup`, `skainet-android-integration`, `skainet-java-consumer`, `skainet-model-loading`, `skainet-inference`) carry numbered hard rules; the two pure-DSL skills (`skainet-data-dsl`, `skainet-nn-dsl`) lead with a cheatsheet instead.

## SKaiNET

SKaiNET itself lives at <https://github.com/SKaiNET-developers/SKaiNET>. Clone it as a sibling directory if you want the citations in skill examples to resolve locally:

```sh
git clone https://github.com/SKaiNET-developers/SKaiNET.git
```

The clone is intentionally NOT tracked in this repository (see `.gitignore`).

## License

Apache-2.0 — see individual `plugin.json` files.
