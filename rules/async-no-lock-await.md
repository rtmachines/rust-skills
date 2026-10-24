# async-no-lock-await

> Avoid blocking guards across await; choose async lock scope to preserve the protected operation

## Why It Matters

Holding a lock across an `.await` point can cause deadlocks and severely hurt performance. The owner may suspend while others wait. Blocking lock acquisition can stop executor progress; Tokio mutex/RwLock acquisition suspends the waiter instead. Async guards are intended to span await when a resource needs serialized ownership. Keep such a scope deliberate and avoid awaiting code that reacquires the same lock.

## Bad

```rust
use tokio::sync::Mutex;

async fn bad_update(state: &Mutex<State>) {
    let mut guard = state.lock().await;
    
    // Unnecessary contention if this fetch is independent of protected state
    let data = fetch_from_network().await;
    
    guard.value = data;
}  // Lock finally released

// Holding a Tokio guard is supported; this scope may be needlessly long.
```

## Good

```rust
use tokio::sync::Mutex;

async fn good_update(state: &Mutex<State>) {
    // Fetch data BEFORE taking the lock
    let data = fetch_from_network().await;
    
    // Lock only for the quick update
    let mut guard = state.lock().await;
    guard.value = data;
}  // Lock released immediately

// Alternative: snapshot an immutable ID, process, then update.
// Contract here: State.id does not change while State is in use.
async fn good_update_v2(state: &Mutex<State>) {
    // Extract what we need
    let id = {
        let guard = state.lock().await;
        guard.id.clone()
    };  // Lock released!
    
    // Do async work without lock
    let data = fetch_by_id(id).await;
    
    // Quick update
    state.lock().await.value = data;
}
```

Extraction examples below assume snapshot results may be applied after concurrent activity. If that is not the contract, retain an async lock for the operation, validate a version before applying the result, or use one task to own the transaction. Splitting a lock scope must not silently change atomicity.

## The Problem Visualized

```rust
// Task A:
let guard = mutex.lock().await;    // Acquires lock
expensive_io().await;              // Suspended, still holding lock!
// ... many milliseconds pass ...
drop(guard);                       // Finally releases

// Task B, C, D:
let guard = mutex.lock().await;    // Other tasks suspend until A releases the async mutex.
```

## Patterns for Extraction

```rust
use tokio::sync::Mutex;

// Pattern 1: Clone out, process, update
async fn pattern_clone(state: &Mutex<State>) {
    let config = state.lock().await.config.clone();
    let result = process_with_io(&config).await;
    state.lock().await.result = result;
}

// Pattern 2: Compute closure, apply
async fn pattern_closure(state: &Mutex<State>) {
    let update = compute_update().await;
    
    state.lock().await.apply(update);
}

// Pattern 3: Message passing
async fn pattern_message(
    state: &Mutex<State>,
    tx: mpsc::Sender<Update>,
) {
    let update = compute_update().await;
    tx.send(update).await.unwrap();
}

// Separate task handles updates
async fn state_manager(
    state: Arc<Mutex<State>>,
    mut rx: mpsc::Receiver<Update>,
) {
    while let Some(update) = rx.recv().await {
        state.lock().await.apply(update);
    }
}
```

## Using RwLock

```rust
use tokio::sync::RwLock;

async fn read_heavy(state: &RwLock<State>) {
    // Clone a snapshot when the processing does not require a stable locked view
    let value = {
        let guard = state.read().await;
        guard.value.clone()
    };
    
    // Process without lock
    let result = process(value).await;
    
    // Write lock for update
    state.write().await.result = result;
}
```

## std::sync::Mutex vs tokio::sync::Mutex

```rust
// Prefer std::sync::Mutex for work that does NOT span an .await —
// it is simpler, faster, and avoids the async overhead.
// Only reach for tokio::sync::Mutex when you genuinely must hold
// the lock across an .await point, such as serializing a shared I/O resource.

// std::sync::Mutex in async (quick, non-awaiting operation — preferred):
async fn quick_update(state: &std::sync::Mutex<State>) {
    state.lock().unwrap().counter += 1;  // No await inside lock scope, OK
}

// tokio::sync::Mutex (only when the lock scope must span an .await):
async fn must_await_inside(state: &tokio::sync::Mutex<State>) {
    let mut guard = state.lock().await;
    // Required when State owns one connection and this exchange must be serialized.
    // Do not call back into code that tries to lock the same State.
    guard.connection.exchange().await;
}
```

## See Also

- [async-spawn-blocking](async-spawn-blocking.md) - Use spawn_blocking for CPU work
- [async-clone-before-await](async-clone-before-await.md) - Clone data before await
- [anti-lock-across-await](anti-lock-across-await.md) - Anti-pattern reference
