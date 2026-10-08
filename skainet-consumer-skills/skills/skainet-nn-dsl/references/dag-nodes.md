# DAG node reference

Authoritative source: `SKaiNET/skainet-lang/skainet-lang-dag/src/commonMain/kotlin/sk/ainet/lang/dag/GraphDsl.kt`. Update when signatures drift.

## Entry point

```kotlin
public fun dag(block: DagBuilder.() -> Unit): GraphProgram
// from: GraphDsl.kt:63-67
```

The DAG builder is **definition-only**: no tensors are allocated. The returned `GraphProgram` is what `skainet-compile-dag` lowers into an executable `ComputeGraph`.

## `GraphValue<T>`

```kotlin
public data class GraphValue<out T : DType>(
    public val nodeId: String,
    public val outputIndex: Int,
    public val spec: TensorSpec
)
// from: GraphDsl.kt:17-21
```

Every value flowing through the graph is one of these. `spec` carries shape + dtype metadata used by shape inference and the compile/export passes.

## Inputs / parameters / constants

```kotlin
public fun <T : DType> input(
    name: String,
    spec: TensorSpec = TensorSpec(name = name, shape = null, dtype = "unknown")
): GraphValue<T>
// from: GraphDsl.kt:152

public fun <T : DType> parameter(name: String, spec: TensorSpec): GraphValue<T>
// from: GraphDsl.kt:166

public inline fun <reified T : DType, V> parameter(
    name: String,
    noinline builder: SymbolicTensorBuilder<T>.() -> TensorSpec
): GraphValue<T>
// from: GraphDsl.kt:372-379

public fun <T : DType> constant(name: String, spec: TensorSpec): GraphValue<T>
public inline fun <reified T : DType, V> constant(
    name: String,
    noinline builder: SymbolicTensorBuilder<T>.() -> TensorSpec
): GraphValue<T>
// from: GraphDsl.kt:180, 385-392
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
// from: GraphDsl.kt:398-404
```

Use this to wire any `Operation` instance — useful when the DSL doesn't yet have a sugar function for an op you need.

Two annotated `op(...)` overloads attach compile-lane hints to the node's attributes:

```kotlin
// Schedule hint (SKEEP-005 compile lane) — ScheduleDsl.kt
public fun DagBuilder.op(operation: Operation, inputs: List<GraphValue<*>>,
    schedule: ScheduleHint, id: String = "", extraAttributes: Map<String, Any?> = emptyMap()): List<GraphValue<*>>
public fun DagBuilder.schedule(hint: ScheduleHint, block: DagBuilder.() -> Unit)  // ambient hint for every op in block
public fun parallel(vararg dims: String, parallelism: Int? = null): ScheduleHint  // e.g. parallel("heads"), parallel("rows", parallelism = 8)

// Dtype policy (W6 of the hybrid adaptive DSL RFC) — DtypePolicyDsl.kt
public fun DagBuilder.op(operation: Operation, inputs: List<GraphValue<*>>,
    dtypePolicy: DTypePolicy, id: String = "", extraAttributes: Map<String, Any?> = emptyMap()): List<GraphValue<*>>
```

Hints never change what the graph computes. `ScheduleAnnotationPass` (skainet-compile-opt) validates schedule hints per op and the StableHLO export emits them as the `skainet.schedule` module attribute; dtype policies feed `DTypeConstraintResolutionPass`. `DagBuilder.withAttributes(attributes, block)` (`GraphDsl.kt:86-93`) is the generic ambient-attribute mechanism both are built on.

## Outputs

```kotlin
public fun output(vararg values: GraphValue<*>)
// from: GraphDsl.kt:409-411
```

If `output(...)` is never called, the last node's outputs are used as the program's outputs. Be explicit anyway — drift in node order will silently change which value is "the output."

## Reusable sub-graphs — `dagModule`

```kotlin
public abstract class DagModule {
    public abstract fun DagBuilder.apply(inputs: List<GraphValue<*>>): List<GraphValue<*>>
}

public fun DagBuilder.module(module: DagModule, inputs: List<GraphValue<*>>): List<GraphValue<*>>

public fun dagModule(block: DagBuilder.(List<GraphValue<*>>) -> List<GraphValue<*>>): DagModule
// from: GraphDsl.kt:419-454
```

`dagModule { inputs -> ... }` is the easy way to define a reusable block. It's instantiated with `module(myBlock, listOf(...))` inside any `dag { ... }`.

## Op-name sugar

Helpers like `matmul(a, b)`, `relu(x)`, `add(a, b)` are KSP-generated extensions on `DagBuilder`: `GraphDslOps.kt` declares `@GenerateGraphDsl public interface GraphDslOps : TensorOps`, and the processor in `skainet-lang-ksp-processor` (`GraphDslGenerator.kt`) emits one DSL extension per `TensorOps` operation. Real usage: `skainet-compile/skainet-compile-dag/src/commonTest/kotlin/sk/ainet/compile/graph/GraphProgramCompilerTest.kt:19-20` (`val mm = matmul(x, w); val y = relu(mm)` inside `dag { }`).

If a helper you want isn't present, fall back to `op(operation, inputs)` with the `Operation` instance (e.g. `op(MatmulOperation<FP32, Float>(), listOf(x, w))`).

## Shape inference

`recordNode` calls `ensureOutputSpecs`, which first consults the DSL-side `inferDagOutputSpecs(operation, inputs, nodeId)` hook, then `operation.inferOutputs(inputSpecs)` — implemented by each `Operation`. If inference fails (or returns empty), the DSL falls back to propagating dtype/shape from the first input (`GraphDsl.kt:98-122`). Treat fallback as a code smell — the operation should know its output shape.

## When to use op-only `op(...)` vs `dagModule`

- **One-off custom op call** → `op(MyOp, listOf(a, b))` inline.
- **Repeated structure** (residual block, attention head, U-Net stage) → `dagModule { ... }`.

## Compilation downstream

`GraphProgram` is consumed by:

- `skainet-compile:skainet-compile-dag` — lowers to `ComputeGraph`.
- `skainet-compile:skainet-compile-hlo` — emits StableHLO MLIR.
- `skainet-compile:skainet-compile-c` — generates C99/Arduino code.
- `skainet-compile:skainet-compile-json` — JSON serialisation for tooling.
- `skainet-compile:skainet-compile-opt` — graph optimization passes (incl. `ScheduleAnnotationPass`, `DTypeConstraintResolutionPass`).
- `skainet-compile:skainet-compile-minerva` — secure-MCU project-bundle export.

The DSL author rarely calls these directly; the test or app entry point does.
