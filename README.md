# skainet-coding-skills

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Official [Claude Code](https://docs.claude.com/en/docs/claude-code) plugin marketplace for working with [SKaiNET](https://github.com/SKaiNET-developers/SKaiNET) — the Kotlin Multiplatform on-device ML/AI framework. Maintained under the [SKaiNET-developers](https://github.com/SKaiNET-developers) organization.

The marketplace hosts two side-by-side skill bundles. They're designed to be installed together; per-skill descriptions disambiguate via path heuristics so exactly one fires per prompt.

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

In any Claude Code session:

```text
/plugin marketplace add SKaiNET-developers/skainet-coding-skills
/plugin install skainet-contributor-skills
/plugin install skainet-consumer-skills
```

Or clone locally and point at the working tree:

```sh
git clone https://github.com/SKaiNET-developers/skainet-coding-skills.git
# then in Claude Code:
/plugin marketplace add /path/to/skainet-coding-skills
```

## Repository layout

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

- Every code example in a SKILL.md ends with `// from: <path>:<line-range>` so the citation check (CI on every PR) verifies it stays in sync with SKaiNET source as the framework evolves.
- Descriptions explicitly say when each skill should NOT fire, to prevent trigger collisions across the two plugins.
- Constraint skills carry numbered hard rules; the two pure-DSL skills (`skainet-data-dsl`, `skainet-nn-dsl`) lead with a cheatsheet instead.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for skill authoring, citation rules, and the eval scenario format.

## Related

- [SKaiNET](https://github.com/SKaiNET-developers/SKaiNET) — the framework this marketplace serves.
- [SKaiNET website](https://skainet.sk/)
- [DeepWiki for SKaiNET](https://deepwiki.com/sk-ai-net/SKaiNET)
- [Claude Code plugins](https://docs.claude.com/en/docs/claude-code/plugins) — how the marketplace and skills format work.

## License

MIT — see [LICENSE](LICENSE). Matches the upstream [SKaiNET](https://github.com/SKaiNET-developers/SKaiNET) license.
