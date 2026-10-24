# async-cancel-safety

> Ensure futures used in `tokio::select!` branches are cancellation-safe

## Why It Matters

`tokio::select!` polls multiple futures concurrently and, the moment one branch completes, it **drops every other branch** — including any state those futures held. A future that was halfway through reading bytes into a local buffer, or halfway through draining a channel into a `Vec`, loses that progress silently. This is not a compiler error; it compiles fine and the bug only surfaces under concurrent load. Tokio documents which of its primitives are cancellation-safe; everything else must be treated with care.

## Bad

```rust
use tokio::io::{AsyncReadExt, BufReader};
use tokio::net::TcpStream;
use tokio::sync::mpsc;

// Not cancel-safe: read_exact keeps its progress counter inside the future.
// The caller owns buf, but retrying read_exact may overwrite the prefix whose
// length was lost when the previous future was dropped.
async fn bad_example(stream: &mut BufReader<TcpStream>, rx: &mut mpsc::Receiver<u8>) {
    let mut buf = [0u8; 1024];
    tokio::select! {
        // If recv wins, read_exact may have consumed bytes without returning
        // their count. This function then discards buf and that progress.
        result = stream.read_exact(&mut buf) => {
            println!("read {} bytes", result.unwrap());
        }
        msg = rx.recv() => {
            println!("got message: {:?}", msg);
        }
    }
}
```

## Good

```rust
use tokio::io::{AsyncReadExt, BufReader};
use tokio::net::TcpStream;
use tokio::sync::mpsc;

// Cancel-safe: the buffer lives OUTSIDE the select loop.
// If the recv branch fires, buf retains whatever was already read,
// and the next iteration continues filling it.
async fn good_example<R: tokio::io::AsyncRead + Unpin>(
    stream: &mut BufReader<R>,
    rx: &mut mpsc::Receiver<u8>,
) -> std::io::Result<()> {
    let mut buf = [0u8; 1024];
    let mut filled = 0;
    let mut commands_open = true;

    loop {
        tokio::select! {
            n = stream.read(&mut buf[filled..]) => {
                // If read loses the race, it consumes no bytes. On success,
                // retain the returned progress outside the raced future.
                let n = n?;
                if n == 0 {
                    return if filled == 0 {
                        Ok(())
                    } else {
                        Err(std::io::Error::new(
                            std::io::ErrorKind::UnexpectedEof,
                            "EOF in a partial 1024-byte frame",
                        ))
                    };
                }
                filled += n;
                if filled == buf.len() {
                    println!("buffer full: {:?}", &buf[..]);
                    filled = 0;
                }
            }
            msg = rx.recv(), if commands_open => {
                match msg {
                    Some(msg) => println!("got message: {msg}"),
                    None => commands_open = false, // Continue reading, without polling a closed input
                }
            }
        }
    }
}
```

## What Is and Is Not Cancel-Safe

| Operation | Cancel-safe? | Notes |
|---|---|---|
| `mpsc::Receiver::recv()` | Yes | drops nothing on cancel |
| `broadcast::Receiver::recv()` | Yes | position tracked in receiver |
| `watch::Receiver::changed()` | Yes | no data consumed on cancel |
| `&mut oneshot::Receiver` kept outside the race | Yes | receiver and result remain available |
| `tokio::time::sleep` | Cancels on drop | recreating it starts a new delay; pin and retain it to preserve a deadline |
| `AsyncRead::read()` | Yes | partial reads surfaced to caller |
| `AsyncRead::read_exact()` | **No** | caller buffer may contain bytes, but the future's progress counter is lost |
| `AsyncRead::read_to_end()` | **No** | do not assume that cancelling preserves all consumed bytes or progress |
| `tokio::sync::Mutex::lock()` | **No** for queue progress | dropping the wait loses its position in the fair queue |
| `&mut JoinHandle<T>` kept outside the race | Yes | task output remains available through the retained handle |
| collecting into a `Vec` inside a future | **No** | partial state is inside the future |

## Patterns for Non-Cancel-Safe Operations

1. **Move state outside `select!`** — keep the accumulation buffer or partial result as a local variable in the surrounding scope, not inside the future passed to `select!`.

2. **Use a pinned future held across iterations** — pin the future once and reuse it:

```rust
use std::pin::pin;
use tokio::io::AsyncReadExt;

async fn pinned_read_example<R: AsyncReadExt + Unpin>(mut reader: R) {
    let mut buf = vec![0u8; 64];
    // pin the future so it survives across select iterations
    let read_fut = pin!(reader.read_to_end(&mut buf));
    // ... use read_fut inside select! across multiple iterations
    // When the future completes it won't be cancelled mid-way
    let _ = read_fut.await;
}
```

3. **Use `tokio_util::io::poll_read_buf`** or similar cancel-safe adapters from `tokio-util`.

4. **Retain a task handle outside the race** — await `&mut JoinHandle<T>`, not an owned handle. Dropping the owned handle detaches the task and loses access to its result.

```rust
async fn race_task<F>(
    work: F,
    shutdown: tokio_util::sync::CancellationToken,
) -> Result<Option<F::Output>, tokio::task::JoinError>
where
    F: std::future::Future + Send + 'static,
    F::Output: Send + 'static,
{
    let mut handle = tokio::spawn(work);
    tokio::select! {
        result = &mut handle => result.map(Some),
        _ = shutdown.cancelled() => {
            // Policy: abort this task, then observe completion.
            // For async cleanup, signal cooperatively and await instead.
            handle.abort();
            match handle.await {
                Ok(value) => Ok(Some(value)), // Completion can win the race
                Err(error) if error.is_cancelled() => Ok(None),
                Err(error) => Err(error),
            }
        }
    }
}
```

This helper must itself be driven to completion; cancelling its supervisor future would drop the local handle and detach the task. Already-running `spawn_blocking` work cannot be stopped by aborting its handle. Preserve required cleanup and results in an owner that remains alive.

## See Also

- [async-select-racing](async-select-racing.md) - use `tokio::select!` for racing/timeouts
- [async-bounded-channel](async-bounded-channel.md) - use bounded channels for backpressure
- [async-no-lock-await](async-no-lock-await.md) - choose lock scope by the protected invariant
