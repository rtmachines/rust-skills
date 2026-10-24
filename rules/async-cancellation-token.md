# async-cancellation-token

> Use `CancellationToken` for graceful shutdown and task cancellation

## Why It Matters

Dropping a `JoinHandle` doesn't cancel the task—it just detaches it. For graceful shutdown, you need explicit cancellation. `tokio_util::sync::CancellationToken` provides a cooperative cancellation mechanism that tasks can check and respond to, enabling clean resource cleanup.

## Bad

```rust
// Dropping handle doesn't stop the task
let handle = tokio::spawn(async {
    loop {
        do_work().await;
    }
});

drop(handle);  // Task continues running in background!

// Using bool flag - not async-aware
let running = Arc::new(AtomicBool::new(true));

tokio::spawn({
    let running = running.clone();
    async move {
        while running.load(Ordering::Relaxed) {
            do_work().await;  // Can't wake up if blocked here
        }
    }
});

running.store(false, Ordering::Relaxed);
// Task won't stop until current do_work() completes
```

## Good

```rust
use tokio_util::sync::CancellationToken;

let token = CancellationToken::new();

let handle = tokio::spawn({
    let token = token.clone();
    async move {
        loop {
            tokio::select! {
                _ = token.cancelled() => {
                    println!("Shutting down gracefully");
                    cleanup().await;
                    break;
                }
                _ = do_work() => {
                    // Work completed
                }
            }
        }
    }
});

// Later: trigger cancellation
token.cancel();
handle.await?;  // Task completes cleanly
```

## CancellationToken API

```rust
use tokio_util::sync::CancellationToken;

// Create token
let token = CancellationToken::new();

// Clone for sharing (cheap Arc-based clone)
let token2 = token.clone();

// Check if cancelled (non-blocking)
if token.is_cancelled() {
    return;
}

// Wait for cancellation (async)
token.cancelled().await;

// Trigger cancellation
token.cancel();

// Child tokens - cancelled when parent is cancelled
let child = token.child_token();
```

## Hierarchical Cancellation

```rust
use std::io;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::{TcpListener, TcpStream};
use tokio::task::JoinSet;
use tokio_util::sync::CancellationToken;

async fn run_server(shutdown: CancellationToken) -> io::Result<()> {
    let listener = TcpListener::bind("127.0.0.1:8080").await?;
    let server_token = shutdown.child_token();
    // A supervisor dropped before the explicit shutdown path still signals children.
    let _cancel_on_drop = server_token.clone().drop_guard();
    let mut connections = JoinSet::new();

    let mut outcome = loop {
        tokio::select! {
            _ = shutdown.cancelled() => break Ok(()),
            result = listener.accept() => {
                match result {
                    Ok((socket, _)) => {
                        connections.spawn(handle_connection(
                            socket,
                            server_token.child_token(),
                        ));
                    }
                    Err(error) => break Err(error),
                }
            }
            joined = connections.join_next(), if !connections.is_empty() => {
                match joined {
                    Some(Ok(Ok(()))) => {}
                    Some(Ok(Err(error))) => break Err(error),
                    Some(Err(error)) => break Err(io::Error::other(error)),
                    None => {}
                }
            }
        }
    };

    // Every explicit exit stops admission, requests cancellation, then joins.
    server_token.cancel();
    while let Some(joined) = connections.join_next().await {
        let result = match joined {
            Ok(result) => result,
            Err(error) => Err(io::Error::other(error)),
        };
        if outcome.is_ok() {
            outcome = result;
        }
    }
    outcome
}

async fn handle_connection(
    mut socket: TcpStream,
    token: CancellationToken,
) -> io::Result<()> {
    let mut buffer = [0u8; 1024];
    let outcome = loop {
        tokio::select! {
            _ = token.cancelled() => break Ok(()),
            result = socket.read(&mut buffer) => {
                match result {
                    Ok(0) => break Ok(()), // Peer EOF
                    Ok(n) => println!("received {n} bytes"),
                    Err(error) => break Err(error),
                }
            }
        }
    };
    // Explicit async cleanup before the handler reports completion.
    let closing = socket.shutdown().await;
    outcome.and(closing)
}
```

Dropping a token by itself does not call `cancel()`. The drop guard is a fallback signal, not evidence that tasks finished; the normal path awaits all connections. If the entire supervisor future is dropped, its JoinSet aborts tasks and cannot finish their asynchronous cleanup. Keep the supervisor alive through shutdown when that cleanup is required.

## Graceful Shutdown Pattern

```rust
use anyhow::Result;
use tokio::task::JoinSet;
use tokio::time::{timeout, Duration};
use tokio_util::sync::CancellationToken;

#[tokio::main]
async fn main() -> Result<()> {
    let shutdown = CancellationToken::new();
    let app = run_app(shutdown.clone());
    tokio::pin!(app);

    tokio::select! {
        result = &mut app => result,
        signal = tokio::signal::ctrl_c() => {
            // Signal failure also goes through the application's shutdown path.
            shutdown.cancel();
            let result = app.await;
            signal?;
            result
        }
    }
}

async fn run_app(shutdown: CancellationToken) -> Result<()> {
    let _cancel_on_drop = shutdown.clone().drop_guard();
    let mut tasks = JoinSet::new();
    for worker_id in 0..2 {
        tasks.spawn(worker_task(worker_id, shutdown.child_token()));
    }

    let mut first_error: Option<anyhow::Error> = None;
    tokio::select! {
        _ = shutdown.cancelled() => {}
        joined = tasks.join_next() => {
            match joined {
                Some(Ok(Ok(()))) | None => {}
                Some(Ok(Err(error))) => first_error = Some(error),
                Some(Err(error)) => first_error = Some(error.into()),
            }
        }
    }
    // Also stop siblings if a worker completed or failed before the signal.
    shutdown.cancel();

    let graceful = timeout(Duration::from_secs(30), async {
        while let Some(joined) = tasks.join_next().await {
            let result = match joined {
                Ok(result) => result,
                Err(error) => Err(error.into()),
            };
            if let Err(error) = result {
                first_error.get_or_insert(error);
            }
        }
    }).await;

    if graceful.is_err() {
        // Policy after grace expires: abort, then observe all remaining joins.
        first_error.get_or_insert_with(|| anyhow::anyhow!("shutdown grace expired"));
        tasks.abort_all();
        while let Some(joined) = tasks.join_next().await {
            match joined {
                Ok(Ok(())) => {}
                Ok(Err(error)) => { first_error.get_or_insert(error); }
                Err(error) if error.is_cancelled() => {}
                Err(error) => { first_error.get_or_insert(error.into()); }
            }
        }
    }

    match first_error {
        Some(error) => Err(error),
        None => Ok(()),
    }
}

async fn worker_task(id: usize, shutdown: CancellationToken) -> Result<()> {
    let mut tick = tokio::time::interval(Duration::from_secs(1));
    loop {
        tokio::select! {
            _ = shutdown.cancelled() => break,
            _ = tick.tick() => println!("worker {id}: periodic work"),
        }
    }
    // Stand-in for this worker's asynchronous cleanup; it is awaited before Ok.
    tokio::task::yield_now().await;
    Ok(())
}
```

A grace timeout is a policy boundary, not a hard execution deadline. A task that does not yield can delay it, and already-running blocking work cannot be aborted. Aborting also skips unfinished async cleanup; await cooperative completion for resources that require it.

## DropGuard Pattern

```rust
use tokio_util::sync::CancellationToken;

// Auto-cancel on drop
let token = CancellationToken::new();
let guard = token.clone().drop_guard();

let handle = tokio::spawn({
    let token = token.clone();
    async move {
        token.cancelled().await;
        println!("Cancelled!");
    }
});

drop(guard); // Requests cancellation
handle.await?; // Separately observe that the task completed
```

## See Also

- [async-joinset-structured](./async-joinset-structured.md) - Managing multiple tasks
- [async-select-racing](./async-select-racing.md) - select! for cancellation
- [async-tokio-runtime](./async-tokio-runtime.md) - Runtime shutdown
