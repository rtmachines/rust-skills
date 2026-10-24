# lint-unsafe-doc

> Require documentation for unsafe blocks

## Why It Matters

The `undocumented_unsafe_blocks` lint ensures every unsafe block has a `// SAFETY:` comment explaining why the operation is sound. Unsafe code is the source of most memory safety bugs—documenting invariants catches mistakes and helps reviewers.

## Configuration

```rust
#![warn(clippy::undocumented_unsafe_blocks)]
```

Or in `Cargo.toml`:

```toml
[lints.clippy]
undocumented_unsafe_blocks = "warn"
```

For strict enforcement:

```toml
[lints.clippy]
undocumented_unsafe_blocks = "deny"
```

## Bad

```rust
/// # Safety
/// `ptr` and `len` must satisfy `slice::from_raw_parts` for lifetime `'a`.
pub unsafe fn read_data<'a>(ptr: *const u8, len: usize) -> &'a [u8] {
    unsafe {
        std::slice::from_raw_parts(ptr, len)  // WARN: undocumented
    }
}

impl Buffer {
    /// # Safety
    /// `index` must be less than `self.data.len()`.
    pub unsafe fn get_unchecked(&self, index: usize) -> &u8 {
        unsafe { self.data.get_unchecked(index) }  // WARN
    }
}
```

## Good

```rust
/// Borrows bytes from an external allocation.
///
/// # Safety
///
/// `ptr` must be non-null and aligned, even when `len == 0`. The range must
/// lie in one allocation, contain `len` initialized bytes, and have a size
/// no greater than `isize::MAX`. For all of `'a`, that allocation must remain
/// alive and these bytes must not be mutated. The caller chooses a lifetime
/// that satisfies these obligations; a comment cannot enforce them in safe code.
pub unsafe fn read_data<'a>(ptr: *const u8, len: usize) -> &'a [u8] {
    // SAFETY: The caller upholds all from_raw_parts requirements for 'a.
    unsafe {
        std::slice::from_raw_parts(ptr, len)
    }
}

pub struct Buffer {
    data: Vec<u8>,
}

impl Buffer {
    /// Returns a byte, panicking if the index is out of bounds.
    pub fn get(&self, index: usize) -> &u8 {
        assert!(index < self.data.len(), "index out of bounds");
        // SAFETY: The unconditional assertion proves index < data.len()
        // in every build profile; the Vec remains borrowed for the result.
        unsafe { self.data.get_unchecked(index) }
    }
}
```

Prefer a slice parameter when external raw pointers are unnecessary. Likewise,
`self.data.get(index)` or checked indexing is usually clearer than the manually
checked unsafe access above. A `debug_assert!` alone cannot justify a safe wrapper:
its check can disappear in release builds. Documentation does not impose unsafe
caller obligations on a safe function.

## SAFETY Comment Format

```rust
// SAFETY: <explanation of why this is sound>
unsafe {
    // ...
}
```

The comment should explain:
1. **What invariants are upheld** - preconditions that make this safe
2. **Why the invariants hold** - how you know they're satisfied
3. **What could go wrong** - if invariants are violated

## Examples by Category

### Pointer Operations

```rust
// SAFETY: ptr was obtained from Box::into_raw, so it's valid
// and properly aligned. We're taking back ownership.
let boxed = unsafe { Box::from_raw(ptr) };
```

### Unchecked Operations

```rust
assert!(i < self.data.len(), "index out of bounds");
// SAFETY: The unconditional check above proves the index is in bounds.
unsafe { self.data.get_unchecked(i) }
```

### FFI Calls

```rust
// SAFETY: libc::getenv is safe to call with a null-terminated
// string. We ensure null termination with CString::new.
// The returned pointer is valid for the lifetime of the environment.
let value = unsafe { libc::getenv(key.as_ptr()) };
```

### Trait Implementations

```rust
// SAFETY: MyType contains no pointers or interior mutability,
// and all bit patterns are valid MyType values.
unsafe impl Send for MyType {}
unsafe impl Sync for MyType {}
```

## Related Lints

```toml
[lints.clippy]
undocumented_unsafe_blocks = "warn"
# Also consider:
multiple_unsafe_ops_per_block = "warn"  # One operation per block
```

## See Also

- [doc-safety-section](./doc-safety-section.md) - `# Safety` in docs
- [lint-deny-correctness](./lint-deny-correctness.md) - Correctness lints
- [type-repr-transparent](./type-repr-transparent.md) - FFI safety
