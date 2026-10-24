# async-async-fn-bounds

> Use `AsyncFn*` for lending async callbacks; keep explicit future bounds when that contract fits

## Why It Matters

The `AsyncFn`, `AsyncFnMut`, and `AsyncFnOnce` traits stabilized in Rust 1.85 (February 2025). They let you express higher-order async function bounds in a single, readable constraint — and, critically, they handle lifetime capture correctly. The old two-generic pattern `F: Fn() -> Fut, Fut: Future<Output = T>` cannot accept `async ||` closures that borrow from their environment, because the future's lifetime is not linked to the closure's call. `AsyncFn` solves this structurally.

## Separate Future Type

```rust
use std::future::Future;

// Useful for non-lending callbacks, including an explicit Fut: Send bound.
// It cannot express every async closure that borrows its captures across a call.
async fn retry<F, Fut, T, E>(times: usize, f: F) -> Result<T, E>
where
    F: Fn() -> Fut,
    Fut: Future<Output = Result<T, E>>,
{
    let mut last_err;
    let mut i = 0;
    loop {
        match f().await {
            Ok(v) => return Ok(v),
            Err(e) => {
                last_err = e;
                i += 1;
                if i >= times {
                    return Err(last_err);
                }
            }
        }
    }
}
```

## Good

```rust
// AsyncFn bound: concise, correct lifetime semantics, accepts async closures
async fn retry<F, T, E>(times: usize, f: F) -> Result<T, E>
where
    F: AsyncFn() -> Result<T, E>,
{
    let mut last_err;
    let mut i = 0;
    loop {
        match f().await {
            Ok(v) => return Ok(v),
            Err(e) => {
                last_err = e;
                i += 1;
                if i >= times {
                    return Err(last_err);
                }
            }
        }
    }
}

// callers can pass plain async functions or async closures
async fn fetch_data() -> Result<String, std::io::Error> {
    Ok("data".to_owned())
}

async fn example() {
    // async function reference
    let _ = retry(3, fetch_data).await;

    // async closure (impossible with the old F: Fn() -> Fut pattern
    // when the closure borrows a local across calls)
    let prefix = "prefix".to_owned();
    let _ = retry(3, async || {
        Ok::<_, std::io::Error>(format!("{prefix}-data"))
    })
    .await;
}
```

## The Three Variants

| Bound | Receiver | Use when |
|---|---|---|
| `AsyncFn()` | `&self` | callable through shared access; interior mutation is still possible |
| `AsyncFnMut()` | `&mut self` | callable multiple times, may mutate captured state |
| `AsyncFnOnce()` | `self` | invoked at most once by this owner; may consume captures |

These mirror `Fn` / `FnMut` / `FnOnce` semantics, so the same rules apply: prefer `AsyncFn` first; fall back to `AsyncFnMut` or `AsyncFnOnce` when needed.

## Key Points

- `AsyncFn()` desugars the bound `F: AsyncFn<(), Output = T>` — the call syntax mirrors `Fn()`.
- Plain `async fn` items (not closures) automatically implement `AsyncFn` when their signature matches.
- `AsyncFn` is in `std::ops` but the traits are brought in scope automatically in the 2024 edition; in older editions you may need `use std::ops::AsyncFn;`.
- `F: AsyncFn() -> T + Send` only makes the callable Send. It does **not** promise that each returned future is Send. Inspect or express that promise separately; wrapping a non-Send future in a struct or box does not make it Send.

For a non-lending callback, this stable helper states the future's bound explicitly:

```rust
use std::future::Future;

fn spawn_call<F, Fut, T>(callback: F) -> tokio::task::JoinHandle<T>
where
    F: FnOnce() -> Fut + Send + 'static,
    Fut: Future<Output = T> + Send,
    T: Send + 'static,
{
    tokio::spawn(async move { callback().await })
}
```

Keep and await the returned handle. For lending callbacks, use a local execution contract when sufficient, or an interface whose returned future separately guarantees Send; do not claim that adding Send only to AsyncFn establishes this.

## See Also

- [async-fn-in-trait](async-fn-in-trait.md) - native async fn in trait definitions
- [async-tokio-runtime](async-tokio-runtime.md) - use Tokio for production async runtime
