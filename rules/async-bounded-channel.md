# async-bounded-channel

> Use bounded channels to apply backpressure and prevent unbounded memory growth

## Why It Matters

Unbounded channels grow without limit when producers outpace consumers. In production, this leads to memory exhaustion. Bounded channels apply backpressure—producers wait when the channel is full, naturally throttling the system. This bounds queued message count. Also bound payload sizes, pending producers and active tasks before claiming a global memory or OOM bound.

## Bad

```rust
use tokio::sync::mpsc;

// Unbounded channel - can grow forever
let (tx, mut rx) = mpsc::unbounded_channel::<Message>();

// Fast producer, slow consumer = unbounded memory growth
tokio::spawn(async move {
    loop {
        let msg = generate_message();
        tx.send(msg).unwrap();  // No capacity backpressure; Err if the receiver is gone
    }
});

tokio::spawn(async move {
    while let Some(msg) = rx.recv().await {
        slow_process(msg).await;  // Can't keep up
    }
});
// Memory grows unboundedly until crash
```

## Good

```rust
use tokio::sync::mpsc;

// Bounded channel - backpressure when full
let (tx, mut rx) = mpsc::channel::<Message>(100);  // Max 100 items

// Producer waits when channel full
tokio::spawn(async move {
    loop {
        let msg = generate_message();
        // Suspends if the channel is full - natural backpressure
        tx.send(msg).await.unwrap();
    }
});

tokio::spawn(async move {
    while let Some(msg) = rx.recv().await {
        slow_process(msg).await;
    }
});
// Queue capacity is 100 messages; producers and active work need separate bounds.
```

## Choosing Buffer Size

```rust
// Too small: frequent blocking, reduced throughput
let (tx, rx) = mpsc::channel::<Item>(1);

// Too large: delayed backpressure, memory waste
let (tx, rx) = mpsc::channel::<Item>(1_000_000);

// Guidelines:
// - Start with expected burst size
// - Measure actual usage in production
// - Err on the smaller side initially

// Small items, high throughput
let (tx, rx) = mpsc::channel::<u64>(1000);

// Large items, moderate throughput  
let (tx, rx) = mpsc::channel::<LargeStruct>(100);

// Low latency requirement
let (tx, rx) = mpsc::channel::<Command>(10);
```

## Handling Full Channel

```rust
use tokio::sync::mpsc;
use tokio::time::{timeout, Duration};

let (tx, mut rx) = mpsc::channel::<Message>(100);

// Option 1: Wait indefinitely (default)
tx.send(msg).await?;

// Option 2: Try send, fail if full
match tx.try_send(msg) {
    Ok(()) => println!("Sent"),
    Err(TrySendError::Full(msg)) => {
        println!("Channel full, dropping message");
    }
    Err(TrySendError::Closed(msg)) => {
        println!("Receiver dropped");
    }
}

// Option 3: Timeout
match timeout(Duration::from_secs(1), tx.send(msg)).await {
    Ok(Ok(())) => println!("Sent"),
    Ok(Err(_)) => println!("Channel closed"),
    Err(_) => println!("Timeout - channel full for too long"),
}

// Option 4: send with permit reservation
let permit = tx.reserve().await?;
permit.send(msg);  // Guaranteed to succeed
```

## Channel Types

```rust
// mpsc: many producers, single consumer
let (tx, rx) = mpsc::channel::<Message>(100);
let tx2 = tx.clone();  // Can clone sender

// oneshot: single value, one producer, one consumer
let (tx, rx) = oneshot::channel::<Response>();
tx.send(response);  // Can only send once

// broadcast: multiple consumers, each gets all messages
let (tx, _) = broadcast::channel::<Event>(100);
let mut rx1 = tx.subscribe();
let mut rx2 = tx.subscribe();

// watch: single latest value, multiple consumers
let (tx, rx) = watch::channel::<State>(initial);
// Receivers see latest value, not all values
```

## Worker Pool Pattern

```rust
use std::sync::Arc;
use tokio::sync::{mpsc, Mutex};

// process(item) returns Output. The caller owns and joins every worker.
async fn process_with_workers(
    items: Vec<Item>,
) -> Result<Vec<Output>, tokio::task::JoinError> {
    let (tx, rx) = mpsc::channel(100);
    let rx = Arc::new(Mutex::new(rx));
    
    // Spawn worker pool
    let workers: Vec<_> = (0..4).map(|_| {
        let rx = rx.clone();
        tokio::spawn(async move {
            let mut outputs = Vec::new();
            loop {
                let item = {
                    // mpsc has one Receiver. The async mutex serializes receiving,
                    // including its await; it is released before processing.
                    let mut rx = rx.lock().await;
                    rx.recv().await
                };
                match item {
                    Some(item) => outputs.push(process(item).await),
                    None => break,
                }
            }
            outputs
        })
    }).collect();
    
    // The supervisor must not keep a spare Receiver owner alive if all workers fail.
    drop(rx);

    // Send items
    for item in items {
        if tx.send(item).await.is_err() {
            break; // Every worker ended; still join them below to observe failure
        }
    }
    drop(tx); // Signal workers to stop after consuming queued work

    // join_all waits for every handle before we propagate a worker failure.
    let joined = futures::future::join_all(workers).await;
    let mut outputs = Vec::new();
    let mut first_error = None;
    for result in joined {
        match result {
            Ok(worker_outputs) => outputs.extend(worker_outputs),
            Err(error) if first_error.is_none() => first_error = Some(error),
            Err(_) => {}
        }
    }
    match first_error {
        Some(error) => Err(error),
        None => Ok(outputs), // Grouped by worker, not original input order
    }
}
```

## See Also

- [async-mpsc-queue](./async-mpsc-queue.md) - Multi-producer patterns
- [async-oneshot-response](./async-oneshot-response.md) - Request-response pattern
- [async-watch-latest](./async-watch-latest.md) - Latest-value broadcasting
