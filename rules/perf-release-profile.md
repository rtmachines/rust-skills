# perf-release-profile

> Optimize release profile settings

## Why It Matters

The default release profile already optimizes runtime code. Tuning LTO and codegen units may improve a particular binary at the cost of build time or memory; compare representative workloads before choosing a profile.

## Default Profile

```toml
[profile.release]
opt-level = 3
debug = false
lto = false
codegen-units = 16
```

## Optimized Profile

```toml
[profile.release]
opt-level = 3          # Maximum optimization
lto = "fat"            # Full link-time optimization
codegen-units = 1      # Better optimization, slower compile
panic = "abort"        # Smaller binary, no unwinding
strip = true           # Remove symbols

[profile.release.package."*"]
# Keep dependencies optimized even if main crate changes
opt-level = 3
```

## Profile Options

| Option | Values | Effect |
|--------|--------|--------|
| `opt-level` | 0-3, "s", "z" | Optimization level |
| `lto` | false, "off", "thin", "fat" | LTO scope and strategy |
| `codegen-units` | 1-256 | Parallel compilation units |
| `panic` | "unwind", "abort" | Panic behavior |
| `strip` | true, false, "symbols", "debuginfo" | Binary stripping |
| `debug` | true, false, 0-2 | Debug info level |

## Optimization Levels

| Level | Description | Use Case |
|-------|-------------|----------|
| `0` | No optimization | Debug builds |
| `1` | Basic optimization | Fast compile |
| `2` | Most optimizations | Balanced |
| `3` | All optimizations | Maximum performance |
| `"s"` | Optimize for size | Embedded |
| `"z"` | Minimize size | Smallest binary |

## LTO Options

| Option | Behavior | Trade-off |
|--------|----------|-----------|
| `false` | Local thin LTO across codegen units, except when codegen-units = 1 or opt-level = 0 | Cargo default; no cross-crate LTO |
| `"off"` | Disable LTO | Useful baseline when measuring |
| `"thin"` | Cross-crate thin LTO | Often cheaper to build than fat LTO; measure the binary |
| `"fat"` | Cross-crate fat LTO | More build work; no universal speed or size ranking |

## Custom Profiles

```toml
# Fast release builds for development
[profile.release-dev]
inherits = "release"
lto = false
codegen-units = 16

# Maximum performance for production
[profile.release-prod]
inherits = "release"
lto = "fat"
codegen-units = 1
strip = true

# Profiling with symbols
[profile.profiling]
inherits = "release"
debug = true
strip = false
```

Use with: `cargo build --profile release-prod`

## Dev Dependencies Optimization

Speed up tests and dev builds:

```toml
[profile.dev]
opt-level = 0

# Optimize dependencies even in dev
[profile.dev.package."*"]
opt-level = 3
```

## Benchmarking Profile

```toml
[profile.bench]
inherits = "release"
debug = true      # For profiling
strip = false     # Keep symbols for flamegraphs
lto = "fat"       # Consistent with release-prod
```

## Size vs Speed Trade-offs

```toml
# Smallest binary
[profile.min-size]
inherits = "release"
opt-level = "z"
lto = "fat"
codegen-units = 1
panic = "abort"
strip = true

# Balance size and speed
[profile.balanced]
inherits = "release"
opt-level = "s"
lto = "thin"
```

## Workspace Configuration

```toml
# In workspace Cargo.toml
[profile.release]
lto = "fat"
codegen-units = 1

# Override for specific package
[profile.release.package.fast-compile-lib]
codegen-units = 16
# lto is not allowed in package overrides; choose it in the top-level profile.
```

## See Also

- [opt-lto-release](./opt-lto-release.md) - LTO details
- [opt-codegen-units](./opt-codegen-units.md) - Codegen units
- [opt-pgo-profile](./opt-pgo-profile.md) - Profile-guided optimization
