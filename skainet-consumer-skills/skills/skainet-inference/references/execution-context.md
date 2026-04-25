# ExecutionContext

Authoritative source: `SKaiNET/skainet-backends/skainet-backend-cpu/src/commonMain/kotlin/sk/ainet/context/DirectCpuExecutionContext.kt` and `SKaiNET/skainet-lang/skainet-lang-core/src/commonMain/kotlin/sk/ainet/context/Phase.kt`.

## What it is

`ExecutionContext` is the runtime backend SKaiNET operations dispatch through. It owns:

- The tensor data factory (`tensorDataFactory`) — produces backing storage for new tensors.
- The execution phase (`phase: Phase.EVAL` or `Phase.TRAIN`).
- Optional forward hooks (`_hooks: ForwardHooks?`) — observe layer outputs.
- Execution stats (`executionStats: ExecutionStats`) — profiling counters.

Every operation (tensor construction, matmul, conv2d, …) takes the context (or reads it from a tensor's `ops` field). Different contexts → different backends.

## Factories

### CPU (the default)

```kotlin
public class DirectCpuExecutionContext(
    override val executionStats: ExecutionStats = ExecutionStats(),
    override val phase: Phase = Phase.EVAL,
    private val _hooks: ForwardHooks? = null,
    override val tensorDataFactory: TensorDataFactory = DenseTensorDataFactory()
) : ExecutionContext {
    public companion object {
        @JvmStatic
        @JvmOverloads
        public fun create(phase: Phase = Phase.EVAL): DirectCpuExecutionContext
    }
}
```

`DirectCpuExecutionContext.create()` is the standard consumer entry point. `@JvmStatic` + `@JvmOverloads` make it idiomatic from Java too: `SKaiNET.context()` ultimately resolves here.

The CPU backend auto-selects NEON / SSE / scalar paths based on platform — consumers don't pick.

### Phase-aware (NN-flavoured)

```kotlin
public class DefaultNeuralNetworkExecutionContext(
    override val phase: Phase = Phase.EVAL
) : NeuralNetworkExecutionContext
```

A simpler context used in some examples and tests. It defers to `DirectCpuExecutionContext` underneath for CPU ops but exposes the `NeuralNetworkExecutionContext` interface that the `sequential { }` builder uses.

For most consumer code, prefer `DirectCpuExecutionContext.create()` directly.

## `Phase`

```kotlin
public enum class Phase {
    TRAIN,
    EVAL
}

public val ExecutionContext.inTraining: Boolean get() = phase == Phase.TRAIN
```

Layer behaviour that depends on phase:

- **Dropout** — disabled in `EVAL`, active in `TRAIN`.
- **BatchNormalization** — uses running stats in `EVAL`, updates them in `TRAIN`.
- **Custom activations** with `if (ctx.inTraining)` branches.

Default to `EVAL` everywhere except inside a training loop.

## Lifetime

- One context per inference session is typical.
- Contexts are heavyweight (factory + stats + caches) — don't construct one per `forward(...)` call.
- Contexts are NOT explicitly disposed; let GC reclaim them when the session ends.
- A `DirectCpuExecutionContext` is thread-safe to share across multiple coroutines doing forward passes (CPU ops are stateless apart from stats).

## Hooks

```kotlin
public interface ForwardHooks {
    public fun onLayerOutput(layerId: String, output: Tensor<*, *>)
}
```

Pass an implementation to the constructor (`_hooks` parameter) to observe layer outputs by id. Useful for:

- Logging activations for debugging.
- Capturing intermediate tensors for visualisation.
- Building telemetry pipelines.

Setting hooks doesn't change `forward` semantics — it just emits observations.

## ExecutionStats

`ExecutionStats` accumulates counters (op count, byte counts, …) across a context's lifetime. Read fields directly to surface them in benchmarks. Default: `ExecutionStats()` collects nothing (safe to leave alone).
