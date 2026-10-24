# const-fn

> Make functions `const fn` when they can run at compile time

## Why It Matters

A `const fn` can be called in const contexts — array lengths, `const`/`static` initializers, const-generic arguments — as well as at runtime, so marking a pure, simple function `const` widens where it can be used at zero cost. The compiler evaluates calls in const contexts during compilation, eliminating the work entirely from the binary. Current stable Rust supports most arithmetic, bitwise ops, conditionals, and slice operations in `const fn`; the main restrictions are heap allocation and most trait method calls.

## Bad

```rust
// not const — cannot use result as an array length or const initializer
fn header_len() -> usize {
    4
}

fn magic_mask() -> u32 {
    0xFF00_FF00
}

fn make_buf() -> [u8; 4] {
    // runtime call — compiler cannot inline the length into the type
    [0u8; header_len()]  // error: `header_len` is not a `const fn`
}
```

## Good

```rust
const fn header_len() -> usize {
    4
}

const fn magic_mask() -> u32 {
    0xFF00_FF00
}

// usable as an array length — evaluated at compile time
let buf = [0u8; header_len()];

// usable in a const initializer
const MASK: u32 = magic_mask();

// usable in a static
static HEADER: [u8; header_len()] = [0u8; header_len()];

// const fn with logic — still fine on stable
const fn align_up(n: usize, align: usize) -> usize {
    (n + align - 1) & !(align - 1)
}

const ALIGNED: usize = align_up(13, 8); // 16, computed at compile time
```

## Notes

Adding `const` to a function permits existing runtime uses and enables new const-context uses. Public const-callability is then an API commitment: removing `const` breaks callers that use the function in constant expressions and requires a breaking release. Choose `const fn` when compile-time use is useful and you can maintain it. All operations in the body must be const-stable on the library's MSRV; needing a runtime-only operation later is not a reason to remove public `const` support in a compatible release.

## See Also

- [const-block](const-block.md) - force compile-time evaluation and assertions inline
- [const-generics](const-generics.md) - parameterize types and functions over const values
- [opt-inline-small](opt-inline-small.md) - inline small hot functions
