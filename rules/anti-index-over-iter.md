# anti-index-over-iter

> Prefer iterators when they make traversal clearer; measure performance differences

## Why It Matters

Iterators express traversal directly and can make off-by-one mistakes less likely. Indexing also supports bounds-check elimination and SIMD when the optimizer can prove the range: a loop over 0..data.len() is a common case. Neither syntax alone guarantees vectorization or faster code; measure representative optimized builds.

## Index-Based Version

```rust
// The range can let the optimizer prove each index is in bounds
fn sum_squares(data: &[i32]) -> i64 {
    let mut result = 0i64;
    for i in 0..data.len() {
        result += (data[i] as i64) * (data[i] as i64);
    }
    result
}

// Index-based with multiple arrays
fn dot_product(a: &[f64], b: &[f64]) -> f64 {
    let mut sum = 0.0;
    for i in 0..a.len().min(b.len()) {
        sum += a[i] * b[i];
    }
    sum
}

// Mutation with indices
fn normalize(data: &mut [f64]) {
    let max = data.iter().cloned().fold(0.0, f64::max);
    for i in 0..data.len() {
        data[i] /= max;
    }
}
```

## Iterator Version

```rust
// Iterator - no bounds checks, SIMD-friendly
fn sum_squares(data: &[i32]) -> i64 {
    data.iter()
        .map(|&x| (x as i64) * (x as i64))
        .sum()
}

// Zip - handles length mismatch automatically
fn dot_product(a: &[f64], b: &[f64]) -> f64 {
    a.iter()
        .zip(b.iter())
        .map(|(&x, &y)| x * y)
        .sum()
}

// Mutable iteration
fn normalize(data: &mut [f64]) {
    let max = data.iter().cloned().fold(0.0, f64::max);
    for x in data.iter_mut() {
        *x /= max;
    }
}
```

## When Indices Are Needed

Sometimes you genuinely need indices:

```rust
// Need index in output
for (i, item) in items.iter().enumerate() {
    println!("{}: {}", i, item);
}

// Non-sequential access
for pair in data.chunks_exact_mut(2) {
    pair.swap(0, 1); // Leaves an odd trailing element unchanged
}

// Multi-dimensional iteration
for i in 0..rows {
    for j in 0..cols {
        matrix[i][j] = i * cols + j;
    }
}
```

## Comparison

| Pattern | Bounds Checks | SIMD | Safety |
|---------|---------------|------|--------|
| `for i in 0..data.len() { data[i] }` | Can be eliminated | Can vectorize | Safe indexing panics if an invalid index is reached |
| `for x in &data` | None | Good | Safe |
| `for x in data.iter()` | None | Good | Safe |
| `data.iter().enumerate()` | None | Good | Safe |

## Common Conversions

| Index Pattern | Iterator Pattern |
|---------------|------------------|
| `for i in 0..v.len()` | `for x in &v` |
| `v[0]` | `v.first()` |
| `v[v.len()-1]` | `v.last()` |
| `for i in 0..a.len() { a[i] + b[i] }` | `a.iter().zip(&b)` |
| `for i in 0..v.len() { v[i] *= 2 }` | `for x in &mut v { *x *= 2 }` |

## Performance Note

```rust
// Iterator version can auto-vectorize
let sum: i32 = data.iter().sum();

// This indexed loop can also auto-vectorize and eliminate bounds checks
let mut sum = 0;
for i in 0..data.len() {
    sum += data[i];
}
```

## See Also

- [perf-iter-over-index](./perf-iter-over-index.md) - Performance details
- [opt-bounds-check](./opt-bounds-check.md) - Bounds check elimination
- [perf-iter-lazy](./perf-iter-lazy.md) - Lazy iterators
