# ExecutionContext

Authoritative source: `SKaiNET/skainet-backends/skainet-backend-cpu/src/commonMain/kotlin/sk/ainet/context/DirectCpuExecutionContext.kt`, `SKaiNET/skainet-lang/skainet-lang-core/src/commonMain/kotlin/sk/ainet/context/ExecutionContext.kt`, `.../context/Phase.kt`, and `.../context/schedule/Schedule.kt`.

## What it is

`ExecutionContext` is the runtime backend SKaiNET operations dispatch through. It owns:

- The tensor data factory (`tensorDataFactory`) — produces backing storage for new tensors.
- The execution phase (`phase: Phase.EVAL` or `Phase.TRAIN`), with the convenience flag `inTraining`.
- The schedule (`schedule: Schedule`) — how an op's independent work maps onto cores (0.54.0+).
- Optional forward hooks (`hooks: ForwardHooks?`) — observe module forward calls.
- Execution stats (`executionStats: ExecutionStats`) and an observer registry (`observers`).

Every operation (tensor construction, matmul, conv2d, …) takes the context (or reads it from a tensor's `ops` field). Different contexts → different backends.

## Factories

### CPU (the default)

```kotlin
public class DirectCpuExecutionContext @JvmOverloads constructor(
    override val executionStats: ExecutionStats = ExecutionStats(),
    override val phase: Phase = Phase.EVAL,
    private val _hooks: ForwardHooks? = null,
    override val tensorDataFactory: TensorDataFactory = DenseTensorDataFactory(),
) : ExecutionContext {
    // Secondary constructor adds `schedule: Schedule` as a fifth parameter.
    public companion object {
        @JvmStatic
        @JvmOverloads
        public fun create(phase: Phase = Phase.EVAL): DirectCpuExecutionContext
    }
}
```

`DirectCpuExecutionContext.create()` is the standard consumer entry point. `@JvmStatic` + `@JvmOverloads` make it idiomatic from Java too: `SKaiNET.context()` ultimately resolves here.

The CPU backend auto-selects its kernel tier per platform (Panama/FFM vector kernels on the JVM, JNI NEON on Android when `skainet-backend-jni-cpu` is on the classpath, scalar reference as the floor) — consumers don't pick. Since 0.52.0 kernel providers self-install on first use (`KernelDispatch.ensureInstalled()` via `ServiceLoader` on JVM/Android); no bootstrap call needed.

### Shape-only (NN-flavoured)

```kotlin
public class DefaultNeuralNetworkExecutionContext(
    override val phase: Phase = Phase.EVAL
) : NeuralNetworkExecutionContext
```

Lives in `sk.ainet.lang.nn`. Its `ops` is `VoidTensorOps` — shape propagation without real arithmetic — so it is for building/describing models and shape-checking, not for producing real numbers. For actual inference, use `DirectCpuExecutionContext.create()`.

## `Phase`

```kotlin
public enum class Phase {
    TRAIN,
    EVAL
}

// On ExecutionContext itself:
public val inTraining: Boolean get() = phase == Phase.TRAIN
```

Layer behaviour that depends on phase:

- **Dropout** — disabled in `EVAL`, active in `TRAIN`.
- **BatchNormalization** — uses running stats in `EVAL`, updates them in `TRAIN`.
- **Custom activations** with `if (ctx.inTraining)` branches.

Default to `EVAL` everywhere except inside a training loop.

## `Schedule` — intra-op threading (0.54.0+)

`sk.ainet.context.schedule.Schedule` is the Halide-style split between *what* an op computes and *how many tasks* compute it. A schedule never changes a result: scheduled runs are bit-identical to sequential ones.

```kotlin
public interface Schedule {
    public val parallelism: Int           // 1 means sequential
    public val name: String               // "sequential", "coroutines(8)", …
    public fun forRange(n: Int, grain: Int = 1, body: (start: Int, end: Int) -> Unit)
    public object Sequential : Schedule   // the default everywhere: one task, caller's thread
}
```

- `ctx.schedule` — the context's current schedule.
- `ctx.withSchedule(schedule)` — a sibling context whose ops run under that schedule. There is also a block form: `ctx.withSchedule(s) { scheduled -> model.forward(x, scheduled) }` (extension in `sk.ainet.context`). Create inputs through the scheduled context so tensor-bound ops carry the schedule.
- Platform defaults: **JVM** → `CoroutineSchedule.hardware()` (one task per core on `Dispatchers.Default`); **Android, Kotlin/Native, JS/Wasm** → `Schedule.Sequential`.
- `sk.ainet.exec.schedule.CoroutineSchedule` (JVM-only, in `skainet-backend-cpu`): `CoroutineSchedule(parallelism = N)`, `CoroutineSchedule.hardware()`, and `CoroutineSchedule.dedicated(N)` for an owned daemon pool (`AutoCloseable`).
- A context that cannot honour a requested schedule emits `TraceEvent.ScheduleDowngraded` — unhonoured requests are visible in the trace, never silent.

When to touch it: force `Schedule.Sequential` when your server already runs many concurrent forward calls (avoid oversubscription), or when you need deterministic single-threaded profiling. Leave the default alone otherwise.

## Lifetime

- One context per inference session is typical.
- Contexts are heavyweight (factory + cached ops + stats) — don't construct one per `forward(...)` call. The `ops` instance is built lazily once and cached.
- Contexts are NOT explicitly disposed; let GC reclaim them when the session ends. (A `CoroutineSchedule.dedicated(...)` pool is the exception — close it.)
- Sharing one `DirectCpuExecutionContext` across coroutines doing forward passes is the normal pattern; the kernel registries are safe for concurrent reads (0.54.0).

## Hooks

```kotlin
public interface ForwardHooks {
    public fun onForwardBegin(module: ModuleNode, input: Any)
    public fun onForwardEnd(module: ModuleNode, input: Any, output: Any)
}
```

Lives in `sk.ainet.lang.nn.hooks`. Pass an implementation to the constructor (`_hooks` parameter); the context exposes it as `hooks`. `Module.forward` wraps every module call in `onForwardBegin`/`onForwardEnd`. Useful for:

- Logging activations for debugging.
- Capturing intermediate tensors for visualisation.
- Building telemetry pipelines (a `TapeRecorder` in the same package records a tape this way).

Setting hooks doesn't change `forward` semantics — it just emits observations.

## ExecutionStats

`ExecutionStats` accumulates counters across a context's lifetime. Read fields directly to surface them in benchmarks. Default: `ExecutionStats()` collects nothing (safe to leave alone). For richer tracing there is also `ctx.traceSink` (default `NoopTraceSink`) and the `observers` registry (`registerObserver` / `unregisterObserver`).
