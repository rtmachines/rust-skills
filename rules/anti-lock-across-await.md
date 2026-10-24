# anti-lock-across-await

> Avoid synchronous guards across await; keep async locks for the scope required by the invariant

## Why It Matters

Holding a `Mutex` or `RwLock` guard across an `.await` causes the lock to be held while the task is suspended. Other users cannot acquire the lock until it is released. A blocking `std::sync::Mutex` acquisition can deadlock executor progress when its owner is suspended. A Tokio mutex deliberately supports guards across await, for example to serialize access to an I/O connection; unnecessary long lock scopes still reduce concurrency.

## Bad

```rust
use std::sync::Mutex;
use tokio::sync::Mutex as AsyncMutex;

// DEADLOCK RISK: std::sync::Mutex held across await
async fn bad_std_mutex(data: &Mutex<Vec<i32>>) {
    let mut guard = data.lock().unwrap();
    do_async_work().await;  // Lock held during await!
    guard.push(42);
}

// Avoidable contention if this network call does not need the protected Vec
async fn bad_async_mutex(data: &AsyncMutex<Vec<i32>>) {
    let mut guard = data.lock().await;
    slow_network_call().await;  // Lock held for entire call!
    guard.push(42);
}
```

## Good

```rust
use std::sync::Mutex;
use tokio::sync::Mutex as AsyncMutex;

// This operation accepts a snapshot; intervening Vec changes are allowed.
// If it were a read-modify-write transaction, this split would not be equivalent.
async fn good_approach(data: &Mutex<Vec<i32>>) {
    let value = {
        let guard = data.lock().unwrap();
        guard.last().copied()  // Extract what you need
    };  // Lock released here
    
    let result = do_async_work(value).await;
    
    {
        let mut guard = data.lock().unwrap();
        guard.push(result);
    }
}

// Minimize lock scope with async mutex
async fn good_async_mutex(data: &AsyncMutex<Vec<i32>>, item: i32) {
    // Quick lock, quick release
    data.lock().await.push(item);
    
    // Async work without lock
    let result = slow_network_call().await;
    
    // Quick lock again
    data.lock().await.push(result);
}
```

## Pattern: Clone Before Await

```rust
async fn process(data: &AsyncMutex<Config>) -> Result<()> {
    // Clone inside lock scope
    let config = data.lock().await.clone();
    
    // Now use config freely across awaits
    let result = fetch_data(&config.url).await?;
    process_result(&config, result).await?;
    
    Ok(())
}
```

## Pattern: Restructure to Avoid Lock

```rust
// Instead of locking a shared map
struct Service {
    data: AsyncMutex<HashMap<String, Data>>,
}

// Use channels or owned data
struct BetterService {
    // Each task owns its data via channels
    sender: mpsc::Sender<Request>,
}

impl BetterService {
    async fn request(&self, key: String) -> anyhow::Result<Data> {
        let (tx, rx) = oneshot::channel();
        self.sender.send(Request { key, respond: tx }).await
            .map_err(|_| anyhow::anyhow!("service queue closed"))?;
        Ok(rx.await?)
    }
}
```

## What Can Cross Await

| Type | Safe Across Await? |
|------|--------------------|
| `std::sync::Mutex` guard | Avoid: can block executor progress; ordinary guards also prevent Send |
| `std::sync::RwLock` guard | Avoid: blocking acquisition can deadlock executor progress |
| `tokio::sync::Mutex` guard | Supported; retain when serialization across I/O is required |
| `tokio::sync::RwLock` guard | Supported; consider contention, ordering and deadlocks |
| Owned values | Lifetime is owned; Send depends on the value |
| `Arc<T>` | Send/Sync depend on T; cloning does not change them |
| References | Lifetime and Send/Sync constraints must hold |

## Detection

```toml
# Cargo.toml
[lints.clippy]
await_holding_lock = "deny"
await_holding_refcell_ref = "deny"
```

## See Also

- [async-no-lock-await](./async-no-lock-await.md) - Async lock patterns
- [async-clone-before-await](./async-clone-before-await.md) - Clone pattern
- [own-mutex-interior](./own-mutex-interior.md) - Mutex usage
