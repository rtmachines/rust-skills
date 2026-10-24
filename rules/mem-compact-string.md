# mem-compact-string

> Use compact string types for memory-constrained string storage

## Why It Matters

On a 64-bit target, standard `String` has 24 bytes of metadata (pointer, length and capacity). For many short strings, metadata and separate allocations can dominate memory use. Libraries such as `compact_str`, `smartstring`, and `ecow` store short strings inline. Capacity limits count UTF-8 bytes, not characters; the numbers below describe the listed library versions on 64-bit targets.

## Bad

```rust
struct User {
    id: u64,
    // Short nonempty usernames still need String metadata and a heap buffer
    username: String,
    email: String,
}

// 1 million users = 24 bytes * 2 * 1M = 48MB just for String metadata
// Plus all the heap allocations for actual content
```

## Good

```rust
use compact_str::CompactString;

struct User {
    id: u64,
    // CompactString 0.9: 24 bytes; up to 24 UTF-8 bytes can be stored inline
    username: CompactString,
    email: CompactString,
}

// Most usernames fit inline = zero heap allocations
// Same memory footprint as String but way fewer allocations
```

## Compact String Libraries

### compact_str

```rust
use compact_str::CompactString;

// Inline storage for strings ≤ 24 bytes on 64-bit (≤ 12 on 32-bit)
let small: CompactString = "hello".into();  // No heap allocation

// Automatic heap fallback for larger strings
let large: CompactString = "x".repeat(100).into();

// String-like API
let mut s = CompactString::new("hello");
s.push_str(" world");
assert_eq!(s.as_str(), "hello world");

// Format macro
use compact_str::format_compact;
let s = format_compact!("value: {}", 42);
```

### smartstring

```rust
use smartstring::{SmartString, LazyCompact};

// Explicit mode: 23 bytes inline capacity on 64-bit (11 on 32-bit).
// smartstring::alias::String is the convenient LazyCompact alias.
let s: SmartString<LazyCompact> = "short string".into();

// Compact mode: 23 bytes inline on 64-bit
use smartstring::Compact;
let s: SmartString<Compact> = "hello".into();
```

### ecow (copy-on-write)

```rust
use ecow::EcoString;

// Clone is cheap: inline content is copied; heap-backed content is shared.
let s1: EcoString = "shared data".into();
let s2 = s1.clone();  // This short inline string does not need an allocation

// Mutation may allocate when growing beyond inline capacity or unsharing data
let mut s3 = s1.clone();
s3.push_str(" modified");  // Now allocates
```

## Memory Comparison

```rust
use std::mem::size_of;

// Sizes on a 64-bit target; inline capacities and ownership strategies differ
assert_eq!(size_of::<String>(), 24);
assert_eq!(size_of::<compact_str::CompactString>(), 24);
assert_eq!(size_of::<smartstring::SmartString<smartstring::LazyCompact>>(), 24);
assert_eq!(size_of::<ecow::EcoString>(), 16);  // Even smaller!
```

## Inline Capacity

| Type | Size | Inline Capacity |
|------|------|-----------------|
| `String` | 24 | 0 (empty strings need no heap allocation) |
| `CompactString` | 24 | 24 bytes [^1] |
| `SmartString<LazyCompact>` | 24 | 23 bytes |
| `EcoString` | 16 | 15 bytes |

[^1]: compact_str 0.9 uses the final byte to distinguish representations; a valid UTF-8 byte at full inline length also encodes the 24-byte case. It does not always reserve a separate tag byte. The corresponding compact_str / smartstring inline capacities on 32-bit targets are 12 / 11 bytes.

## When to Use

```rust
// ✅ Good: Many short strings in memory
struct Dictionary {
    words: Vec<CompactString>,  // Millions of short words
}

// ✅ Good: Frequently cloned strings
struct Template {
    parts: Vec<EcoString>,  // O(1) clone
}

// ❌ Don't: Hot path string manipulation
fn transform(s: &str) -> String {
    // Standard String is optimized for manipulation
    s.to_uppercase()
}

// ❌ Don't: API boundaries (prefer &str or String for interop)
pub fn public_api(input: CompactString) { }  // Forces dependency
pub fn public_api(input: impl Into<String>) { }  // Better
```

## Cargo.toml

```toml
[dependencies]
compact_str = "0.9"
# or
smartstring = "1.0"
# or
ecow = "0.2"
```

## See Also

- [mem-boxed-slice](./mem-boxed-slice.md) - Box<str> for immutable strings
- [own-cow-conditional](./own-cow-conditional.md) - Cow<str> for borrow-or-own
- [mem-smallvec](./mem-smallvec.md) - Similar concept for Vec
