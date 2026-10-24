# opt-lto-release

> Measure LTO for release builds and choose its scope deliberately

## Why It Matters

Link-Time Optimization (LTO) enables additional optimization across code-generation units and crate boundaries, including inlining, dead-code elimination and devirtualization. Some cross-crate optimization, notably generic monomorphization, is already possible without LTO. Measure build time, binary size and representative workloads; no fixed speedup or ranking of modes is guaranteed.

## Bad

```toml
# Cargo.toml - default release profile
[profile.release]
opt-level = 3
# No LTO = missed optimization opportunities
```

## Good

```toml
# Cargo.toml - candidate profile to benchmark
[profile.release]
opt-level = 3
lto = "fat"          # Whole-graph LTO; compare with thin and off
codegen-units = 1    # Less parallel code generation; benchmark the trade-off
# panic = "abort"    # Optional behavior change: no unwinding/cleanup on panic
strip = true         # Remove symbols for smaller binary
```

## LTO Options Explained

These are alternative values, not entries to combine in one TOML table:

```toml
# Default: local ThinLTO across this crate's codegen units when applicable.
# Not performed with codegen-units = 1 or opt-level = 0.
lto = false

# Thin LTO across crates - typically less build cost than fat LTO
lto = "thin"

# Fat LTO across crates - broader analysis, often greater build cost
lto = "fat"
# Equivalent to:
lto = true

# Disable LTO entirely, including local ThinLTO
lto = "off"
```

## Trade-offs

| Setting | Compile Time | Binary Size | Performance |
|---------|--------------|-------------|-------------|
| `lto = "off"` | No LTO work | Measure | Comparison without LTO |
| `lto = false` | Local ThinLTO when applicable | Measure | Cargo default |
| `lto = "thin"` | Cross-crate ThinLTO work | Measure | Workload-dependent |
| `lto = "fat"` | Whole-graph analysis, often more build work | Measure | Workload-dependent |

## Evidence from Production

Some production crates offer fat LTO and `codegen-units = 1` as build choices.
For example, ripgrep ships a `release-lto`
profile (see the Cargo Book for profile documentation:
<https://doc.rust-lang.org/cargo/reference/profiles.html>):

```toml
# A common pattern in performance-critical crates
[profile.release]
overflow-checks = true
lto = "fat"
codegen-units = 1

# Named profile for explicit LTO builds (e.g. ripgrep's release-lto)
[profile.release-lto]
inherits = "release"
opt-level = 3
lto = "fat"
codegen-units = 1
# panic = "abort" # opt in only if abort-on-panic matches the application
strip = "symbols"
```

## Complete Optimized Profile

```toml
[profile.release]
opt-level = 3        # Optimize for speed; measure against other settings
lto = "fat"          # Link-time optimization
codegen-units = 1    # Single codegen unit for better optimization
# panic = "abort"    # Optional abort-on-panic behavior
strip = true         # Strip symbols
debug = false        # No debug info

# For benchmarking (need some debug info for profiling)
[profile.bench]
inherits = "release"
debug = true
strip = false

# Fast dev builds with optimized dependencies
[profile.dev]
opt-level = 0
debug = true

[profile.dev.package."*"]
opt-level = 3        # Optimize dependencies even in dev
```

## When to Use Each

| Situation | LTO Setting |
|-----------|-------------|
| Development | `false` (fast compiles) |
| CI builds | `"thin"` (balance) |
| Release binaries | Benchmark `"thin"`, `"fat"`, `false` and `"off"` |
| Libraries (crates.io) | `false` (users choose) |

## Measuring Impact

```bash
# Set lto = "off" in Cargo.toml for the no-LTO comparison
cargo build --release
hyperfine ./target/release/myapp

# Build with LTO
# (after adding lto = "fat" to Cargo.toml)
cargo build --release
hyperfine ./target/release/myapp

# Compare binary sizes
ls -la target/release/myapp
```

## See Also

- [opt-codegen-units](opt-codegen-units.md) - Use codegen-units = 1
- [opt-pgo-profile](opt-pgo-profile.md) - Profile-guided optimization
- [perf-release-profile](perf-release-profile.md) - Full release profile settings
