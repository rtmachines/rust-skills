# doc-panics-section

> Include `# Panics` section for functions that can panic

## Why It Matters

Panics are exceptional conditions that crash the program (or unwind the stack). Users need to know when a function might panic so they can ensure preconditions are met or avoid the function in contexts where panics are unacceptable (e.g., `no_std`, embedded, FFI).

If a function can panic, document exactly when.

## Bad

```rust
/// Returns the element at the given index.
pub fn get(index: usize) -> &T {
    &self.data[index]  // Panics if out of bounds - not documented!
}

/// Divides two numbers.
pub fn divide(a: i32, b: i32) -> i32 {
    a / b  // Panics on division by zero - not documented!
}
```

## Good

```rust
/// Returns the element at the given index.
///
/// # Panics
///
/// Panics if `index` is out of bounds (i.e., `index >= self.len()`).
///
/// # Examples
///
/// ```
/// // Vec::get is a non-panicking standard-library alternative.
/// let v = vec![1, 2, 3];
/// assert_eq!(v.get(1), Some(&2));
/// ```
pub fn get(&self, index: usize) -> &T {
    &self.data[index]
}

/// Divides two numbers.
///
/// # Panics
///
/// Panics if `divisor` is zero, or if `dividend == i32::MIN`
/// and `divisor == -1` (division overflow, including release builds).
///
/// For a non-panicking version, use [`checked_divide`].
pub fn divide(dividend: i32, divisor: i32) -> i32 {
    dividend / divisor
}

/// Divides two numbers, returning `None` on zero divisor or division overflow.
pub fn checked_divide(dividend: i32, divisor: i32) -> Option<i32> {
    dividend.checked_div(divisor)
}
```

## Common Panic Conditions

| Operation | Panic Condition |
|-----------|-----------------|
| Index access `[i]` | Index out of bounds |
| Integer division `/`, `%` | Zero divisor; signed `MIN / -1` or `MIN % -1`, even in release |
| `.unwrap()` | `None` or `Err` value |
| `.expect()` | `None` or `Err` value |
| `slice::split_at(mid)` | `mid > len` |
| `Vec::remove(i)` | `i >= len` |
| Overflow (debug) | Integer overflow |

## Pattern: Panic vs Return Error

Document why you chose to panic vs return `Result`:

```rust
/// Creates a new buffer with the given capacity.
///
/// # Panics
///
/// Panics if `capacity` is zero. A buffer must have at least
/// one byte of capacity.
///
/// This panics rather than returning an error because a zero-capacity
/// buffer represents a programming error, not a runtime condition.
pub fn new(capacity: usize) -> Self {
    assert!(capacity > 0, "capacity must be non-zero");
    // ...
}
```

## Pattern: Debug-Only Panics

```rust
/// Adds an item to the collection.
///
/// # Panics
///
/// In debug builds, panics if the collection is at capacity.
/// In release builds, this is a no-op when at capacity.
pub fn push(&mut self, item: T) {
    debug_assert!(self.len < self.capacity, "collection at capacity");
    // ...
}
```

## Provide Non-Panicking Alternatives

When documenting a panicking function, point to safe alternatives:

```rust
/// # Panics
///
/// Panics if the index is out of bounds.
///
/// For a non-panicking version, use [`get`] which returns `Option<&T>`.
```

## See Also

- [doc-errors-section](./doc-errors-section.md) - Documenting errors
- [doc-safety-section](./doc-safety-section.md) - Documenting unsafe
- [err-result-over-panic](./err-result-over-panic.md) - Preferring Result
