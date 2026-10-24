# mem-thinvec

> Consider `ThinVec<T>` when many collection values make metadata size important

## Why It Matters

On a 64-bit target, `Vec<T>` occupies 24 bytes even when empty. `ThinVec` from the `thin-vec` crate uses one non-null pointer (8 bytes), storing length and capacity with heap data. Empty values point to a shared singleton without allocating. Both `Vec` and `ThinVec` support the null-pointer optimization for `Option`; ThinVec's metadata reduction comes from moving its header, not an exclusive ability to optimize `Option`.

## Bad

```rust
struct TreeNode {
    value: i32,
    // Each node pays 24 bytes for children, even leaves
    children: Vec<TreeNode>,  // Most nodes are leaves with empty Vec
}

// Or using Option<Vec<T>>
struct SparseData {
    // Option<Vec> = 24 bytes on 64-bit: NPO avoids an extra discriminant
    tags: Option<Vec<String>>,
    metadata: Option<Vec<Metadata>>,
    // 48 bytes for usually-None fields
}
```

## Good

```rust
use thin_vec::ThinVec;

struct TreeNode {
    value: i32,
    // Empty ThinVec points to a shared singleton - 8 bytes on 64-bit
    children: ThinVec<TreeNode>,
}

struct SparseData {
    // Keep Option if absent and present-but-empty have different meanings.
    tags: Option<ThinVec<String>>,
    metadata: Option<ThinVec<Metadata>>,
    // 16 bytes vs 48 bytes
}
```

## Memory Layout

```rust
use std::mem::size_of;

// Layout on a 64-bit target, thin-vec 0.2.21
assert_eq!(size_of::<Vec<u8>>(), 24);
assert_eq!(size_of::<Option<Vec<u8>>>(), 24);  // NPO: no extra discriminant

// ThinVec: 8 bytes (one pointer)
use thin_vec::ThinVec;
assert_eq!(size_of::<ThinVec<u8>>(), 8);
assert_eq!(size_of::<Option<ThinVec<u8>>>(), 8);  // Option is free!
```

## ThinVec vs Vec

| Feature | `Vec<T>` | `ThinVec<T>` |
|---------|----------|--------------|
| Size (empty) | 24 bytes | 8 bytes |
| Size (non-empty) | 24 bytes | 8 bytes (header on heap) |
| Option<T> optimization | Yes | Yes |
| Header access | len/cap in the value | len/cap behind the pointer |
| Iteration speed | Measure for the workload | Measure for the workload |
| API compatibility | Full | Vec-like |

## When to Use ThinVec

```rust
// ✅ Good: Many instances, often empty
struct SparseGraph {
    nodes: Vec<Node>,
    // Most edges lists are empty or small
    edges: Vec<ThinVec<EdgeId>>,  // Saves 16 bytes per node
}

// ✅ Good: Often-empty collection field (use Option to represent absence)
struct Document {
    content: String,
    attachments: ThinVec<Attachment>,  // Often empty
}

// Benchmark before changing representation in a hot loop
fn process_hot_path(data: &ThinVec<Item>) {
    // The header is indirect, but a loop need not reload it every iteration.
    for item in data {
        process(item);
    }
}

// ❌ Avoid: Few instances
fn main() {
    let single_vec: ThinVec<i32> = ThinVec::new();
    // Saving 16 bytes once is meaningless
}
```

## API Compatibility

```rust
use thin_vec::{ThinVec, thin_vec};

// Constructor macro
let v: ThinVec<i32> = thin_vec![1, 2, 3];

// Familiar Vec-like API
let mut v = ThinVec::new();
v.push(1);
v.push(2);
v.extend([3, 4, 5]);
v.pop();

// Iteration
for item in &v {
    println!("{}", item);
}

// Slicing
let slice: &[i32] = &v[..];

// Conversion
let vec: Vec<i32> = v.into();
let thin: ThinVec<i32> = vec.into();
```

## Cargo.toml

```toml
[dependencies]
thin-vec = "0.2"
```

## See Also

- [mem-smallvec](./mem-smallvec.md) - Stack-allocated small vecs
- [mem-boxed-slice](./mem-boxed-slice.md) - Fixed-size heap slices
- [mem-with-capacity](./mem-with-capacity.md) - Pre-allocation strategies
