# unsafe-send-sync-manual

> Document the invariants when manually implementing `Send` or `Sync`; prefer letting the compiler derive them automatically.

## Why It Matters

`Send` and `Sync` are `unsafe` auto-traits. The compiler derives them automatically and correctly for most types — manual implementations signal that the borrow checker cannot verify the invariant on its own. Get it wrong and you introduce data races that are impossible to catch with safe code. A manual `unsafe impl Send` without a clear justification is a liability: the next person to modify the type's fields may silently break the invariant without realizing the impl is load-bearing.

## Bad

```rust
use std::cell::Cell;
use std::sync::Arc;

// Cell<T> is !Sync because it allows non-atomic interior mutation.
// This manual impl removes that protection with no explanation.
struct SharedCounter {
    value: Cell<u32>,
}

unsafe impl Sync for SharedCounter {} // data race waiting to happen — no SAFETY comment
unsafe impl Send for SharedCounter {} // redundant: Cell<u32> already is Send
```

```rust
// Wrapping a raw pointer but forgetting to opt out of auto-Send/Sync.
struct MyBuffer {
    ptr: *mut u8,
    len: usize,
}
// *mut u8 is already !Send + !Sync, so the compiler correctly withholds
// auto-impls — but if you blindly add unsafe impls without justification,
// you may send the pointer to another thread while something else mutates it.
unsafe impl Send for MyBuffer {}  // no SAFETY: comment — why is this sound?
```

## Good

```rust
use std::marker::PhantomData;

// ---- 1. Opt OUT of Send/Sync using PhantomData ----
// If your type logically owns a *const T (e.g. an intrusive pointer),
// use PhantomData to prevent the compiler from auto-deriving Send/Sync.
struct IntrinsiveRef<T> {
    ptr: *const T,
    // PhantomData<*const T> makes this type !Send + !Sync automatically,
    // matching the semantics of a raw non-owning pointer.
    _marker: PhantomData<*const T>,
}
// No unsafe impl needed — the compiler correctly withholds Send/Sync.

// ---- 2. Opt IN with a documented unsafe impl ----
use std::sync::Mutex;

/// A buffer owned exclusively by one thread at a time.
/// The raw pointer always points to a heap allocation this struct owns;
/// no other reference to that allocation exists outside this struct.
struct OwnedBuffer {
    ptr: *mut u8,
    len: usize,
}

// SAFETY: this abstraction must enforce exclusive allocation ownership in
// every constructor and method, with no thread-affine access or destruction.
// Moving it transfers that ownership; no caller-provided Mutex is assumed.
unsafe impl Send for OwnedBuffer {}

// SAFETY: OwnedBuffer exposes no shared mutation — all methods require &mut self.
// Concurrent & references cannot mutate the buffer.
unsafe impl Sync for OwnedBuffer {}

// ---- 3. Prefer newtype wrappers around Arc for sharing ----
// Instead of manual Sync, wrap in Arc<Mutex<T>> so the compiler handles it.
use std::sync::Arc;

struct SafeCounter {
    value: Mutex<u32>,
}

// Arc<Mutex<u32>> is Send + Sync automatically — no manual impl required.
fn make_shared() -> Arc<SafeCounter> {
    Arc::new(SafeCounter { value: Mutex::new(0) })
}
```

## Key Points

- **Auto-derive first**: if the fields satisfy the required auto traits, let the compiler implement them. Raw pointers may require a manual proof; `Cell<T>` already implements `Send` when `T: Send`, but never `Sync`.
- **`PhantomData<*const T>`** is the canonical way to make a type `!Send + !Sync` — `*const T` is already `!Send + !Sync`, so the marker propagates without any `unsafe impl`.
- **`PhantomData<*mut T>`** makes a type `!Send + !Sync` and invariant over `T`; it does not represent a lifetime-bounded exclusive borrow. Use `PhantomData<&'a mut T>` when that is the relationship to encode.
- Every `unsafe impl Send`/`unsafe impl Sync` must carry a `// SAFETY:` comment explaining which invariant the programmer is upholding and why it holds.
- `Rc<T>` is neither `Send` nor `Sync`. Moving exclusively owned `Cell<T>` between threads is allowed when `T: Send`; sharing its non-atomic mutation through `Sync` is not. Choose `Arc` and synchronization when shared access is actually needed, and prove all fields and methods before overriding an auto-trait decision.

## See Also

- [unsafe-safety-comment](unsafe-safety-comment.md) - write `// SAFETY:` above every unsafe impl
- [type-phantom-marker](type-phantom-marker.md) - use `PhantomData<T>` for type-level markers
- [own-arc-shared](own-arc-shared.md) - use `Arc<T>` for thread-safe shared ownership
