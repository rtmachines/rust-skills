# obs-tracing-over-log

> Use `tracing` for structured, span-aware diagnostics instead of `println!` or bare `log`

## Why It Matters

`println!` and `eprintln!` have no concept of log levels, targets, or structured data — they cannot be silenced, filtered, or parsed by observability pipelines. The `log` facade provides levels, targets, and structured fields when its `kv` feature is enabled, but it has no span model. `tracing` records both *events* (point-in-time observations) and *spans* (contextual scopes attached to execution with `#[instrument]` or `Instrument`; propagate them deliberately to spawned work), with structured key-value fields, level filtering, and target routing. It is also interoperable with the `log` ecosystem via `tracing`'s `log` feature flag.

## Bad

```rust
fn handle_login(id: u64) {
    println!("user {} logged in", id);
    // No level, no structure, no filtering, goes to stdout unconditionally
}

fn main() {
    handle_login(42);
}
```

## Good

```rust
use tracing::info;

fn handle_login(id: u64) {
    // Structured field: user.id is queryable in JSON/OpenTelemetry backends
    info!(user.id = %id, "user logged in");
}

fn main() {
    // One-time subscriber init belongs in the binary, not in libraries
    tracing_subscriber::fmt::init();
    handle_login(42);
}
```

## Key Points

| Approach | Levels | Structured | Async-aware spans | `log` compat |
|---|---|---|---|---|
| `println!` | No | No | No | No |
| `log` facade | Yes | Yes with `kv` | No | Yes |
| `tracing` | Yes | Yes | Yes | Yes (via feature) |

- Add to `Cargo.toml`: `tracing = "0.1"` for all crates; `tracing-subscriber = { version = "0.3", features = ["env-filter"] }` for binaries only.
- The `%expr` sigil uses `Display`; `?expr` uses `Debug`; bare `field = value` records typed primitives.
- `tracing` ships a `log` compatibility bridge: enable `tracing-subscriber`'s `tracing-log` feature (enabled by default); its subscriber initialization also installs `LogTracer`. For manual subscriber setup, install `tracing_log::LogTracer` once. Avoid initializing it twice.

## See Also

- [obs-structured-fields](obs-structured-fields.md) - record key-value fields, not interpolated strings
- [obs-instrument-spans](obs-instrument-spans.md) - attach context to async tasks with spans
- [async-tokio-runtime](async-tokio-runtime.md) - production async runtime setup
