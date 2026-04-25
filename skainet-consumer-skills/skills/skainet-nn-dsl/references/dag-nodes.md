# DAG node reference

Authoritative source: `SKaiNET/skainet-lang/skainet-lang-dag/src/commonMain/kotlin/sk/ainet/lang/dag/GraphDsl.kt`. Update when signatures drift.

## Entry point

```kotlin
public fun dag(block: DagBuilder.() -> Unit): GraphProgram
// from: GraphDsl.kt:61-65
```

The DAG builder is **definition-only**: no tensors are allocated. The returned `GraphProgram` is what `skainet-compile-dag` lowers into an executable `ComputeGraph`.

## `GraphValue<T>`

```kotlin
public data class GraphValue<out T : DType>(
    public val nodeId: String,
    public val outputIndex: Int,
    public val spec: TensorSpec
)
// from: GraphDsl.kt:14-19
```

Every value flowing through the graph is one of these. `spec` carries shape + dtype metadata (for shape inference and ONNX export).

## Inputs / parameters / constants

```kotlin
public fun <T : DType> input(
    name: String,
    spec: TensorSpec = TensorSpec(name = name, shape = null, dtype = "unknown")
): GraphValue<T>
// from: GraphDsl.kt:127-136

public fun <T : DType> parameter(name: String, spec: TensorSpec): GraphValue<T>
// from: GraphDsl.kt:141-150

public inline fun <reified T : DType, V> parameter(
    name: String,
    noinline builder: SymbolicTensorBuilder<T>.() -> TensorSpec
): GraphValue<T>
// from: GraphDsl.kt:174-182

public fun <T : DType> constant(name: String, spec: TensorSpec): GraphValue<T>
public inline fun <reified T : DType, V> constant(
    name: String,
    noinline builder: SymbolicTensorBuilder<T>.() -> TensorSpec
): GraphValue<T>
// from: GraphDsl.kt:155-195
```

The `<reified T, V> { shape(...) { ... } }` form is the same shape-DSL family as the data DSL — see `skainet-data-dsl/references/tensor-builders.md`.

## Generic op hook

```kotlin
public fun op(
    operation: Operation,
    inputs: List<GraphValue<*>>,
    id: String = "",
    attributes: Map<String, Any?> = emptyMap()
): List<GraphValue<*>>
// from: GraphDsl.kt:200-206
```

Use this to wire any `Operation` instance — useful when the DSL doesn't yet have a sugar function for an op you need.

## Outputs

```kotlin
public fun output(vararg values: GraphValue<*>)
// from: GraphDsl.kt:211-214
```

If `output(...)` is never called, the last node's outputs are used as the program's outputs. Be explicit anyway — drift in node order will silently change which value is "the output."

## Reusable sub-graphs — `dagModule`

```kotlin
public abstract class DagModule {
    public abstract fun DagBuilder.apply(inputs: List<GraphValue<*>>): List<GraphValue<*>>
}

public fun DagBuilder.module(module: DagModule, inputs: List<GraphValue<*>>): List<GraphValue<*>>

public fun dagModule(block: DagBuilder.(List<GraphValue<*>>) -> List<GraphValue<*>>): DagModule
// from: GraphDsl.kt:222-257
```

`dagModule { inputs -> ... }` is the easy way to define a reusable block. It's instantiated with `module(myBlock, listOf(...))` inside any `dag { ... }`.

## Op-name sugar

The DSL has helpers like `matmul(a, b)`, `relu(x)`, `add(a, b)` declared as DSL extensions on `DagBuilder` (in the same file family). Each calls `recordNode(...)` with the appropriate `Operation` and propagates inferred output specs.

If a helper you want isn't yet present, fall back to `op(operation, inputs)`. Don't add helpers without also adding shape inference for the matching `Operation`.

## Shape inference

`recordNode` calls `operation.inferOutputs(inputSpecs)` — implemented by each `Operation`. If inference fails (or returns empty), the DSL falls back to propagating dtype/shape from the first input. Treat fallback as a code smell — the operation should know its output shape.

## When to use op-only `op(...)` vs `dagModule`

- **One-off custom op call** → `op(MyOp, listOf(a, b))` inline.
- **Repeated structure** (residual block, attention head, U-Net stage) → `dagModule { ... }`.

## Compilation downstream

`GraphProgram` is consumed by:

- `skainet-compile:skainet-compile-dag` — lowers to `ComputeGraph`.
- `skainet-compile:skainet-compile-hlo` — emits StableHLO MLIR.
- `skainet-compile:skainet-compile-c` — generates C99/Arduino code.
- `skainet-compile:skainet-compile-json` — JSON serialisation for tooling.
- `skainet-compile:skainet-compile-opt` — graph optimization passes.

The DSL author rarely calls these directly; the test or app entry point does.
