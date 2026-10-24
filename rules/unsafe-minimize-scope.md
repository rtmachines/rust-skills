# unsafe-minimize-scope

> Keep `unsafe` blocks as small as possible — mark only the operation that requires unsafety, not the surrounding safe code.

## Why It Matters

An `unsafe fn` declares obligations for its caller; an `unsafe` block identifies operations whose preconditions the implementation must establish. Keep those blocks small enough to review the relevant proof. In edition 2024, `unsafe_op_in_unsafe_fn` warns by default when such an operation lacks an explicit block. Use `#![deny(unsafe_op_in_unsafe_fn)]` if the project wants to make that diagnostic an error.

## Bad

```rust
// Entire function body marked unsafe — safe arithmetic, bounds checks,
// and the single unsafe dereference are all equally "dangerous" to a reader.
unsafe fn sum_at(ptr: *const i32, len: usize, index: usize) -> i32 {
    let adjusted_len = len.saturating_sub(1); // safe — but looks unsafe
    assert!(index <= adjusted_len);           // safe — but looks unsafe
    let value = *ptr.add(index);              // the only actually unsafe op
    value + 1                                 // safe — but looks unsafe
}
```

```rust
// Huge unsafe block wrapping safe logic inside an unsafe fn (2024 edition
// warns about missing explicit unsafe blocks, but large blocks obscure proofs).
pub unsafe fn process(ptr: *const u8, len: usize) -> Vec<u8> {
    unsafe {
        let mut result = Vec::with_capacity(len); // safe
        for i in 0..len {                         // safe
            result.push(*ptr.add(i));             // unsafe — buried in noise
        }
        result
    }
}
```

## Good

```rust
// A slice establishes validity and lifetime; an integer length beside an
// arbitrary raw pointer would not. Ordinary values[index] is preferable unless
// profiling justifies unchecked access; this demonstrates a local proof.
fn sum_at(values: &[i32], index: usize) -> i32 {
    assert!(index < values.len(), "index out of bounds");
    // SAFETY: values is a live slice and the assertion proves index is in it.
    let value = unsafe { *values.get_unchecked(index) };
    value + 1
}
```

```rust
// Explicit blocks also make a genuinely unsafe function easier to audit.
/// # Safety
///
/// For nonzero `len`, `ptr` must point to at least `len` initialized bytes in
/// one live allocation, readable without concurrent mutation for this call.
/// Pointer arithmetic over that range must remain within the allocation.
pub unsafe fn process(ptr: *const u8, len: usize) -> Vec<u8> {
    let mut result = Vec::with_capacity(len); // safe — outside any unsafe block
    for i in 0..len {
        // SAFETY: caller guarantees ptr is valid for len bytes; i < len.
        let byte = unsafe { *ptr.add(i) };
        result.push(byte);
    }
    result
}
```

## Key Points

- **2024 edition `unsafe_op_in_unsafe_fn`**: missing explicit unsafe blocks produce a warning by default, or an error when the lint is set to `deny`/`forbid`.
- A safe wrapper must establish the unsafe preconditions for every legal safe call. If validity depends on caller-supplied raw pointers, expose an `unsafe fn` with a complete contract or change the interface to references/slices.
- Each small unsafe block needs its own `// SAFETY:` comment (see `unsafe-safety-comment`).
- If multiple consecutive lines are all unsafe for the *same* invariant reason, a single block covering only those lines is acceptable.

## When a Larger Block Is Acceptable

If two unsafe operations share the *exact same precondition* and separating them would require re-stating the identical justification, a single block covering both is fine — but it should still be the minimum necessary scope.

## See Also

- [unsafe-safety-comment](unsafe-safety-comment.md) - write `// SAFETY:` above every unsafe block
- [unsafe-send-sync-manual](unsafe-send-sync-manual.md) - document invariants when manually implementing Send/Sync
