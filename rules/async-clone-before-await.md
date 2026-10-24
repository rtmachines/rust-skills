# async-clone-before-await

> Clone shared handles for additional ownership; check lifetime and Send independently

## Why It Matters

Borrowing across `.await` is valid when the referent stays alive and the future meets its executor's bounds. Cloning is useful when another task needs an independent owner or when you explicitly need a snapshot. It does not inherently make a future Send: `Rc` stays non-Send after cloning, and `Arc<T>` is Send/Sync only when T meets the corresponding requirements.

## Bad

```rust
use std::rc::Rc;

// Cloning Rc does not make a suspended future transferable between threads.
async fn still_not_send(data: Rc<Vec<i32>>) {
    let data = data.clone();
    tokio::task::yield_now().await;
    println!("{data:?}");
}
// tokio::spawn(still_not_send(Rc::new(vec![1]))); // compile error: not Send
```

## Good

```rust
use std::sync::Arc;

struct Data {
    items: Vec<i32>,
}

// The owned Arc keeps Data alive. &[i32] is Send because i32 is Sync;
// borrowing it through await does not require cloning the Vec.
async fn process(data: Arc<Data>) -> i32 {
    let slice = &data.items[..];
    tokio::task::yield_now().await;
    slice.iter().sum()
}

async fn example() -> Result<(), tokio::task::JoinError> {
    let shared = Arc::new(Data { items: vec![1, 2, 3] });
    let task_data = Arc::clone(&shared); // Additional owner for the spawned task
    let handle = tokio::spawn(process(task_data));
    assert_eq!(shared.items.len(), 3); // Caller retains its own Arc
    assert_eq!(handle.await?, 6);
    Ok(())
}
```

## The Send Problem

`tokio::spawn` requires Send even on a current-thread runtime. Use a supported local task when thread transfer is unnecessary, or use Send-capable data when the work needs ordinary spawn.

```rust
use std::rc::Rc;

async fn local_example() {
    let local = tokio::task::LocalSet::new();
    local.run_until(async {
        let data = Rc::new(vec![1, 2, 3]);
        let handle = tokio::task::spawn_local(async move {
            tokio::task::yield_now().await;
            data.iter().sum::<i32>()
        });
        assert_eq!(handle.await.expect("local task should finish"), 6);
    }).await;
}
```

Changing Rc to Arc helps only if the contents also have the required Send/Sync properties. A reference held through await is not itself a reason to clone.

## Minimizing Clones

```rust
// Bad: clone everything eagerly
async fn wasteful(data: Arc<LargeData>) {
    let data = (*data).clone();  // Clones entire LargeData
    async_work().await;
    use_one_field(&data.small_field);
}

// Good: clone only what you need
async fn efficient(data: Arc<LargeData>) {
    let small = data.small_field.clone();  // Clone only needed field
    async_work().await;
    use_one_field(&small);
}

// Good: if you need the whole thing, keep the Arc
async fn arc_efficient(data: Arc<LargeData>) {
    // This function already owns data; no extra Arc clone is needed.
    async_work().await;
    use_data(&data);  // Access through Arc
}
```

## Spawn Pattern

```rust
let shared = Arc::new(SharedState::new());
let mut tasks = tokio::task::JoinSet::new();

for i in 0..10 {
    let shared = Arc::clone(&shared);
    tasks.spawn(async move {
        shared.do_something(i).await;
    });
}

let mut first_error = None;
while let Some(result) = tasks.join_next().await {
    if let Err(error) = result {
        first_error.get_or_insert(error);
    }
}
if let Some(error) = first_error {
    return Err(error); // Propagate only after all tasks have been joined
}
```

A caller whose supervisor may be cancelled also needs an explicit cancellation and join policy; dropping task handles only detaches their tasks.

## Scope-Based Approach

```rust
// Limit borrow scope to before await
async fn scoped(data: Arc<Data>) {
    // Scope 1: borrow, compute, drop borrow
    let computed = {
        let slice = &data.items[..];  // Borrow
        compute_something(slice)       // Use
    };  // Borrow ends here
    
    // Now safe to await
    expensive_async_operation().await;
    
    use_computed(computed);
}
```

## MutexGuard Across Await

An async mutex can protect a whole asynchronous operation when serialization is required. Releasing it early is appropriate only when interleaving does not change the contract.

```rust
use std::sync::Arc;
use tokio::sync::Mutex;

struct Counter { value: i32 }

// Atomic with respect to other users of this mutex.
async fn serialized(mutex: Arc<Mutex<Counter>>) {
    let mut guard = mutex.lock().await;
    guard.value += 1;
    slow_operation().await;
    guard.value += 1;
}

// Different contract: observers are allowed to see the intermediate state.
async fn interleaved(mutex: Arc<Mutex<Counter>>) {
    mutex.lock().await.value += 1;
    slow_operation().await;
    mutex.lock().await.value += 1;
}
```

These examples illustrate alternative contracts, not a mechanical good/bad rewrite. Neither form should await work that reacquires a lock it still owns.

## See Also

- [async-no-lock-await](./async-no-lock-await.md) - Lock guards across await
- [own-arc-shared](./own-arc-shared.md) - Arc usage patterns
- [async-spawn-blocking](./async-spawn-blocking.md) - Blocking in async
