# perf-iter-over-index

> Prefer iterators over manual indexing

## Why It Matters

Iterators are the idiomatic way to traverse collections in Rust. They enable bounds check elimination, SIMD auto-vectorization, and cleaner code. Manual indexing can also receive these optimizations when its range is provably valid, such as 0..data.len(). Prefer the clearest traversal; verify material performance differences in optimized code instead of inferring them from syntax.

## Index-Based Version

```rust
// The range can let the optimizer prove each index is in bounds
fn sum_squares(data: &[i32]) -> i64 {
    let mut sum = 0i64;
    for i in 0..data.len() {
        sum += (data[i] as i64) * (data[i] as i64);
    }
    sum
}

// Index-based iteration with multiple collections
fn dot_product(a: &[f64], b: &[f64]) -> f64 {
    let mut sum = 0.0;
    for i in 0..a.len().min(b.len()) {
        sum += a[i] * b[i];
    }
    sum
}

// Mutating with indices
fn double_values(data: &mut [i32]) {
    for i in 0..data.len() {
        data[i] *= 2;
    }
}
```

## Iterator Version

```rust
// Iterator - bounds checks eliminated, SIMD-friendly
fn sum_squares(data: &[i32]) -> i64 {
    data.iter()
        .map(|&x| (x as i64) * (x as i64))
        .sum()
}

// Zip iterators - no manual length handling
fn dot_product(a: &[f64], b: &[f64]) -> f64 {
    a.iter()
        .zip(b.iter())
        .map(|(&x, &y)| x * y)
        .sum()
}

// Mutable iteration
fn double_values(data: &mut [i32]) {
    for x in data.iter_mut() {
        *x *= 2;
    }
}
```

## When Indexing Is Needed

Sometimes you genuinely need indices:

```rust
// Need the index for output or processing
for (i, value) in data.iter().enumerate() {
    println!("Index {}: {}", i, value);
}

// Non-sequential access patterns
fn interleave(data: &mut [i32]) {
    let mid = data.len() / 2;
    for i in 0..mid {
        data.swap(i * 2, mid + i);
    }
}
```

## Performance Comparison

| Pattern | Bounds Checks | SIMD Potential | Clarity |
|---------|---------------|----------------|---------|
| `for i in 0..data.len()` | Can be eliminated | Can vectorize | Depends on the operation |
| `for &x in slice` | None | High | High |
| `.iter().enumerate()` | None | Medium | High |
| `get_unchecked` | None (unsafe) | High | Low |

## Iterator Advantages

```rust
// Chaining operations - single pass
let result: Vec<_> = data.iter()
    .filter(|x| **x > 0)
    .map(|x| x * 2)
    .collect();

// Early termination optimized
let found = data.iter().any(|&x| x == target);

// Parallel iteration (with rayon)
use rayon::prelude::*;
let sum: i64 = data.par_iter().map(|&x| x as i64).sum();
```

## See Also

- [perf-iter-lazy](./perf-iter-lazy.md) - Keep iterators lazy
- [opt-bounds-check](./opt-bounds-check.md) - Bounds check elimination
- [anti-index-over-iter](./anti-index-over-iter.md) - Anti-pattern
- [conc-rayon-par-iter](./conc-rayon-par-iter.md) - Parallelize data-parallel loops
