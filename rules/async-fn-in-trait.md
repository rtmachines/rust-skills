# async-fn-in-trait

> Prefer native `async fn` in traits for static dispatch; use explicit boxing when dynamic dispatch is required

## Why It Matters

Since Rust 1.75, you can write `async fn` directly inside trait definitions (AFIT — async functions in traits). This eliminates the `#[async_trait]` proc-macro dependency and removes the hidden `Box<dyn Future>` allocation it inserts on every call. Fewer allocations, no macro expansion overhead, and no extra crate to audit. However, native async fn in traits carries two precise caveats you must understand before migrating.

## Boxed Approach for Dynamic Dispatch

```rust
// requires async_trait crate; boxes every future on the heap
use async_trait::async_trait;

#[async_trait]
trait Repo {
    async fn get(&self, id: u64) -> anyhow::Result<String>;
    async fn save(&self, value: String) -> anyhow::Result<()>;
}

struct PgRepo;

#[async_trait]
impl Repo for PgRepo {
    async fn get(&self, id: u64) -> anyhow::Result<String> {
        Ok(format!("row-{id}"))
    }

    async fn save(&self, value: String) -> anyhow::Result<()> {
        let _ = value;
        Ok(())
    }
}
```

## Native Approach for Static Dispatch

```rust
// native async fn in traits — no macro, no boxing
trait Repo {
    async fn get(&self, id: u64) -> anyhow::Result<String>;
    async fn save(&self, value: String) -> anyhow::Result<()>;
}

struct PgRepo;

impl Repo for PgRepo {
    async fn get(&self, id: u64) -> anyhow::Result<String> {
        Ok(format!("row-{id}"))
    }

    async fn save(&self, value: String) -> anyhow::Result<()> {
        let _ = value;
        Ok(())
    }
}
```

## Caveats

**Caveat 1 — not dyn-compatible.** A dispatchable native async method (or an opaque-return method) prevents this trait from being used as `dyn Repo`. Keep `#[async_trait]` when its boxing policy fits, or expose an explicit boxed-future interface:

```rust
use std::future::Future;
use std::pin::Pin;

trait DynRepo: Send + Sync {
    fn get(&self, id: u64)
        -> Pin<Box<dyn Future<Output = anyhow::Result<String>> + Send + '_>>;
}

struct MemoryRepo;

impl DynRepo for MemoryRepo {
    fn get(&self, id: u64)
        -> Pin<Box<dyn Future<Output = anyhow::Result<String>> + Send + '_>>
    {
        Box::pin(async move { Ok(format!("row-{id}")) })
    }
}

fn make_repo() -> Box<dyn DynRepo> {
    Box::new(MemoryRepo)
}
```

**Caveat 2 — returned futures need their own `Send` contract.** `tokio::spawn` requires `Send + 'static` futures, including on a current-thread runtime. Use `LocalSet`/`spawn_local` for supported non-Send tasks. A native async trait alone does not promise a Send future, even when an implementation happens to produce one.

`trait-variant` 0.1 generates a static-dispatch variant with additional bounds; it does **not** generate a boxed, dyn-compatible interface:

```rust
#[trait_variant::make(RepoSend: Send)]
trait LocalRepo {
    async fn get(&self, id: u64) -> anyhow::Result<String>;
}

// RepoSend is still used through generics, not Box<dyn RepoSend>.
async fn load<R: RepoSend>(repo: &R, id: u64) -> anyhow::Result<String> {
    repo.get(id).await
}
```

Alternatively, express the return-future bound directly:

```rust
use std::future::Future;

trait Repo {
    fn get(&self, id: u64) -> impl Future<Output = anyhow::Result<String>> + Send;
}
```

The callable/receiver's thread-safety bounds and the returned future's bounds are separate. For a future borrowing `&self`, the implementation must also make the captured borrow safe to send.

## When to Use Each Approach

| Scenario | Recommended approach |
|---|---|
| Static dispatch only (generics, `impl Trait`) | Native `async fn` in trait |
| Need `dyn Trait` | `#[async_trait]` or an explicit boxed-future interface |
| Multi-threaded Tokio, spawned tasks | `trait-variant` `Send` variant or explicit `+ Send` |
| Local task driven by `LocalSet`/`spawn_local` | Native `async fn` without a Send promise when appropriate |

## See Also

- [anti-type-erasure](anti-type-erasure.md) - prefer `impl Trait` over `Box<dyn Trait>` when possible
- [async-async-fn-bounds](async-async-fn-bounds.md) - use `AsyncFn` bounds for higher-order async functions
- [async-tokio-runtime](async-tokio-runtime.md) - use Tokio for production async runtime
