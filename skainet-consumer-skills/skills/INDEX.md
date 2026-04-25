# SKaiNET consumer skills — Index

Skills for application developers using **SKaiNET as a library**. Activate when the user is editing a project that depends on `sk.ainet:skainet-bom` / `sk.ainet.core:skainet-*` artifacts — not when editing files inside the SKaiNET repo itself.

If the user is contributing to SKaiNET, the sibling **skainet-contributor-skills** plugin covers that audience. The two plugins are designed to be installed together; the descriptions disambiguate via path heuristics so only one fires per prompt.

## Layering

```
skainet-consumer-setup  →  skainet-data-dsl  ↘
                       ↘  skainet-nn-dsl     →  skainet-inference
                          skainet-model-loading ↗
                                                ↓
                            skainet-android-integration  /  skainet-java-consumer
```

`skainet-consumer-setup` is the entry point — get the dependency right before anything else. The two DSL skills teach the public API surface. `skainet-model-loading` and `skainet-inference` form the inference pipeline. `skainet-android-integration` and `skainet-java-consumer` are platform-specific specialisations.

## Skills

| Skill | Trigger sentence (matches when the user…) |
|---|---|
| [skainet-consumer-setup](skainet-consumer-setup/SKILL.md) | adds SKaiNET to a Gradle project that does NOT live inside the SKaiNET repo — BOM, artifact picker, KMP vs. JVM-only consumer setup. |
| [skainet-data-dsl](skainet-data-dsl/SKILL.md) | constructs tensors or transform pipelines (`tensor { }`, `pipeline<>().rescale().normalize()`, `sliceView { }`). |
| [skainet-nn-dsl](skainet-nn-dsl/SKILL.md) | builds a network with `sequential<T, V> { }` or `dag { }`. |
| [skainet-model-loading](skainet-model-loading/SKILL.md) | loads pre-trained models — GGUF, ONNX, SafeTensors, JSON. |
| [skainet-inference](skainet-inference/SKILL.md) | sets up `ExecutionContext`, runs `model.forward(x, ctx)`, batches, threads, configures TurboQuant for KV-cache. |
| [skainet-android-integration](skainet-android-integration/SKILL.md) | wires SKaiNET into an Android app — assets, lifecycle, vendor-native backend, memory pressure. |
| [skainet-java-consumer](skainet-java-consumer/SKILL.md) | calls SKaiNET from a pure-Java app via the `sk.ainet.java` facade — Maven dependencies for a JVM-only consumer, idiomatic Java usage of `SKaiNET`, `TensorJavaOps`, `StableHloConverterFactory`, `TokenizerFactory`. |

## Conventions

- Every code example in a SKILL.md ends with `// from: <path>:<line-range>` so a citation check can verify it.
- Each SKILL.md states "When NOT to use" up front and explicitly defers contributor-side use cases to the contributor plugin.
- The two DSL skills lead with a Cheatsheet — they teach usage, not constraints.
- `skainet-consumer-setup` and `skainet-java-consumer` carry hard rules around Maven coordinates and BOM versions because misuse there is silent and costly.
