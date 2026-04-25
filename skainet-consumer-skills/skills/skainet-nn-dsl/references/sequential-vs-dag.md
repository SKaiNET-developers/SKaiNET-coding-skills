# Sequential vs DAG — choosing the right builder

## TL;DR

| You need… | Use… |
|---|---|
| Linear stack of layers, no branching | `sequential<T, V> { }` |
| Skip connections, residual blocks | `dag { }` |
| Multiple inputs (image + metadata) | `dag { }` |
| Multiple outputs (multi-task heads) | `dag { }` |
| To call `.forward(x, ctx)` directly | `sequential` |
| To compile to C / HLO / ONNX | `dag` (compiler operates on `GraphProgram`) |
| To reuse a sub-graph | `dag` + `dagModule { }` |

## Why these two builders, not one

`sequential` produces a `Module<T, V>` — a runnable network with `.forward(x, ctx)` and parameter access. It's the high-level, "model-as-API" form.

`dag` produces a `GraphProgram` — a definition-only AST. It's the low-level, "model-as-data" form, suitable for graph optimisation and compilation to other targets.

You can wrap a `Module<T, V>` to expose its forward as a graph (the team uses KSP-generated tracing wrappers for this), but it's a one-way trip — you can't run a `GraphProgram` as a model without going through the compiler.

## When to start with sequential and migrate to DAG

A common pattern: prototype with `sequential`, switch to `dag` when the architecture grows beyond a stack.

Triggers to migrate:
- You start hacking around the linear-stack constraint (e.g. computing branch outputs outside the builder and zipping them back in).
- You need shape information per node for compilation / quantisation / export.
- You want to share a sub-graph between two models.

How to migrate:
1. Identify the input(s) and turn each into a `dag { val x = input<...>("x", spec) ... }`.
2. Replace each `sequential` layer with the equivalent op call (`dense` → `matmul + add(bias) + relu`; `conv2d` → `conv2d` op with explicit weight tensors via `parameter`).
3. Mark outputs explicitly with `output(...)` — sequential's "last layer is the output" convention does not exist in DAG.

## When NOT to use DAG

- You're prototyping. The friction is real — you write more code per layer.
- You're writing a tutorial / README example. Sequential reads more naturally.
- You don't need the symbolic representation. A `Module<T, V>` is enough for inference / training inside the JVM.

## Mixed: sequential as a sub-graph in DAG

`sequential` can stand alone or be invoked from inside DAG-built code, but `dagModule` is the official reusable-block mechanism inside a `dag { }`. Don't reach for sequential inside a DAG — the type and execution semantics don't align.
