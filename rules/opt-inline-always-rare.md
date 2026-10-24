# opt-inline-always-rare

> Use `#[inline(always)]` sparingly—only for critical hot paths proven by profiling

## Why It Matters

`#[inline(always)]` strongly suggests inlining; inline attributes are compiler hints, not language-level guarantees. Excessive inlining can increase binary size and hurt instruction-cache behavior. Reserve this hint for hot paths where measurements and generated code justify it.

## Bad

```rust
// Annotating everything - trusting intuition over data
#[inline(always)]
pub fn get_name(&self) -> &str {
    &self.name
}

#[inline(always)]
pub fn calculate_tax(amount: f64) -> f64 {
    amount * 0.1
}

#[inline(always)]
fn helper(x: i32) -> i32 {
    x + 1
}

// Result: bloated binary, poor cache utilization
```

## Good

```rust
// Let compiler decide for most functions
pub fn get_name(&self) -> &str {
    &self.name
}

pub fn calculate_tax(amount: f64) -> f64 {
    amount * 0.1
}

// Only force inline for proven hot paths
impl Hasher for MyHasher {
    // Hasher::write is called millions of times in tight loops
    // Keep the hint only if this workload's benchmark shows a benefit.
    #[inline(always)]
    fn write(&mut self, bytes: &[u8]) {
        // Very small, very hot
        self.state = self.state.wrapping_add(bytes.len() as u64);
    }
}
```

## When #[inline(always)] Helps

```rust
// ✅ Tiny functions in hot inner loops
#[inline(always)]
fn fast_hash(a: u64, b: u64) -> u64 {
    a.wrapping_mul(b).wrapping_add(a)
}

// ✅ Generic functions that benefit from monomorphization
#[inline(always)]
fn swap<T>(a: &mut T, b: &mut T) {
    std::mem::swap(a, b);
}

// ✅ Iterator adapters and closures
#[inline(always)]
fn apply<T, F: Fn(T) -> T>(f: F, x: T) -> T {
    f(x)
}

// ✅ SIMD/vectorization helpers
#[inline(always)]
fn add_simd(a: &[f32], b: &[f32], out: &mut [f32]) {
    // ...
}
```

## Inline Variants

```rust
// #[inline] - hint to inline, compiler may ignore
#[inline]
fn suggested_inline(x: i32) -> i32 { x + 1 }

// #[inline(always)] - strongly suggest inlining; verify generated code
#[inline(always)]
fn force_inline(x: i32) -> i32 { x + 1 }

// #[inline(never)] - suggest avoiding inlining (for profiling, code size)
#[inline(never)]
fn no_inline(x: i32) -> i32 { x + 1 }

// No annotation - compiler decides based on heuristics
fn compiler_decides(x: i32) -> i32 { x + 1 }
```

## Measuring Inline Impact

```rust
// Use criterion to benchmark
use criterion::{criterion_group, criterion_main, Criterion};

fn bench_with_inline(c: &mut Criterion) {
    c.bench_function("hot_path_inline", |b| {
        b.iter(|| hot_loop())
    });
}

// Compare binary sizes
// cargo bloat --release --crates

// Check if function was inlined
// cargo asm --rust my_crate::hot_function
```

## Generic Functions

```rust
// Generic bodies are available for downstream monomorphization even without
// #[inline]. The attribute can still influence optimization heuristics.

// In library crate:
use std::fmt::Display;
#[inline]  // Optional hint, not a prerequisite for this generic body
pub fn generic_function<T: Display>(x: T) {
    println!("{}", x);
}

// This generic function can be inlined across crates without the attribute
// or LTO. That possibility does not guarantee any particular optimization.
```

## See Also

- [opt-inline-small](./opt-inline-small.md) - Regular inline for small functions
- [opt-inline-never-cold](./opt-inline-never-cold.md) - Preventing inlining
- [perf-profile-first](./perf-profile-first.md) - Profile before optimizing
