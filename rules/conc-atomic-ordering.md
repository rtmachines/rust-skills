# conc-atomic-ordering

> Use the weakest correct memory `Ordering` for every atomic operation

## Why It Matters

Choose memory ordering from the synchronization proof, then measure performance. Instruction and barrier costs depend on the operation, target and compiler; `SeqCst` does not universally insert a full barrier. Incorrect ordering can expose stale state or permit data races in non-atomic data. Stronger ordering alone does not repair an incorrect ownership or publication protocol.

## Bad

```rust
use std::sync::atomic::{AtomicU64, AtomicBool, Ordering};

static COUNTER: AtomicU64 = AtomicU64::new(0);
static READY: AtomicBool = AtomicBool::new(false);
static DATA: AtomicU64 = AtomicU64::new(0);

// Stronger ordering than an independent counter needs; measure its cost.
fn increment() {
    COUNTER.fetch_add(1, Ordering::SeqCst);
}

fn producer() {
    DATA.store(42, Ordering::SeqCst);
    READY.store(true, Ordering::SeqCst); // overkill for a single flag
}

fn consumer() -> Option<u64> {
    if READY.load(Ordering::SeqCst) {
        Some(DATA.load(Ordering::SeqCst))
    } else {
        None
    }
}
```

## Good

```rust
use std::sync::atomic::{AtomicU64, AtomicBool, Ordering};

static COUNTER: AtomicU64 = AtomicU64::new(0);

// Relaxed: no ordering relative to other memory — fine for independent counters
fn increment() {
    COUNTER.fetch_add(1, Ordering::Relaxed);
}

fn total() -> u64 {
    COUNTER.load(Ordering::Relaxed)
}

// One-shot handoff: call producer once; reusing the slot needs another protocol.
// Acquire/Release: producer writes data THEN sets flag (Release);
// consumer loads flag (Acquire) and is guaranteed to see the preceding write.
static READY: AtomicBool = AtomicBool::new(false);
static VALUE: AtomicU64 = AtomicU64::new(0);

fn producer(value: u64) {
    VALUE.store(value, Ordering::Relaxed);   // write payload first
    READY.store(true, Ordering::Release);    // publish with Release
}

fn consumer() -> Option<u64> {
    if READY.load(Ordering::Acquire) {       // synchronize with Release store
        Some(VALUE.load(Ordering::Relaxed))  // payload visible after Acquire
    } else {
        None
    }
}

// SeqCst: only when you need a single total order across *multiple* atomics.
// Example: Dekker-style mutual exclusion involving two independent flags.
```

## Ordering Quick Reference

| Ordering | Use when |
|----------|----------|
| `Relaxed` | Operation is atomic but needs no ordering relative to other memory (counters, stats) |
| `Acquire` | Load that must see all stores preceding a matching `Release` on another thread |
| `Release` | Store that must be visible before a matching `Acquire` load on another thread |
| `AcqRel` | Read-modify-write (e.g. `compare_exchange`) acting as both Acquire and Release |
| `SeqCst` | Need a single global order observed by all threads across multiple atomic variables |

## Verification with loom

Use `loom` to explore executions of small instrumented concurrent models. It checks interleavings within its model and configured exploration bounds, with documented limitations on memory-model coverage. Passing a model does not prove every C11-permitted reordering or every production execution correct. Use Loom's synchronization types for the operations being modeled and retain a manual ordering proof:

```rust
#[cfg(loom)]
use loom::sync::atomic::{AtomicBool, Ordering};

#[cfg(loom)]
#[test]
fn test_handoff() {
    loom::model(|| {
        // ... spawn threads, assert invariants
    });
}
```

## See Also

- [own-mutex-interior](own-mutex-interior.md) - prefer `Mutex<T>` when lock-free isn't required
- [test-loom-concurrency](test-loom-concurrency.md) - model concurrent code with loom and record exploration limits
- [conc-scoped-threads](conc-scoped-threads.md) - safely share stack data across threads
