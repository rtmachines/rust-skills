# unsafe-miri-ci

> Run `cargo miri test` in CI for every crate that contains `unsafe` code.

## Why It Matters

Miri interprets Rust tests and detects many classes of undefined behavior in the executions it explores: invalid memory accesses, uninitialized reads, data races, and violations of the selected pointer/aliasing model. It complements code review and tools such as sanitizers, which also dynamically detect classes of memory and concurrency bugs.

Passing Miri is not a proof of soundness. Results depend on executed paths, inputs, schedules, the selected model and supported operations. A test using only safe code can still expose unsoundness in a dependency's safe API.

## Bad

```yaml
# Ordinary tests alone do not check the unsafe implementation under Miri.
- name: Test
  run: cargo test --all-features
```

## Good

```yaml
# .github/workflows/miri.yml
name: Miri

on: [push, pull_request]

jobs:
  miri:
    name: Miri (nightly)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install nightly toolchain with Miri
        run: |
          rustup toolchain install nightly --component miri
          rustup override set nightly
          cargo miri setup

      - name: Run Miri
        env:
          MIRIFLAGS: "-Zmiri-strict-provenance"
        run: cargo miri test --all-features
```

## Key Points

- **Nightly only**: Miri requires a nightly toolchain. Pin a specific nightly date in `rust-toolchain.toml` if you need reproducible CI.
- **Cost**: interpretation can be much slower than native tests. Measure the suite's cost and select targeted tests when needed; no universal slowdown factor applies.
- **`MIRIFLAGS` and models**: check supported flags and the default aliasing model for the pinned nightly. Strict provenance can reject unsupported pointer constructions; Stacked Borrows and Tree Borrows model different aliasing rules. A result is evidence under the model used, not a complete language-level proof.
- **Setup command**: `cargo miri setup` pre-builds the Miri sysroot so the first test run is not cold. Run it once per CI cache key.
- Test unsafe abstractions through their safe APIs as well. A crate without its own unsafe blocks may exercise unsafe standard-library, dependency or generated code.

## When It's Acceptable to Skip

- Tests whose relevant operations are unsupported by the selected Miri version; isolate and test supported parts, and record what remains unchecked.
- Generated code still merits testing when it participates in the safety boundary; auditing the generator is complementary.
- Very large integration tests that make Miri impractical — run a targeted unit-test subset instead.

Choose supported feature combinations; `--all-features` is appropriate only when those features work together. Record the nightly, flags, test subset and remaining gaps. See the [Miri documentation](https://github.com/rust-lang/miri) for current support and limitations.

## See Also

- [unsafe-maybeuninit](unsafe-maybeuninit.md) - use `MaybeUninit<T>` for uninitialized memory
- [unsafe-safety-comment](unsafe-safety-comment.md) - document every unsafe block
- [test-criterion-bench](test-criterion-bench.md) - use criterion for benchmarking (separate from Miri)
