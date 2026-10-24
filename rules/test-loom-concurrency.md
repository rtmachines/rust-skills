# test-loom-concurrency

> Use `loom` to explore bounded models of lock-free and concurrent code

## Why It Matters

Stress tests can miss an interleaving despite many runs. Loom systematically explores the schedules and memory behaviors that its instrumented operations and configured model bounds represent. A successful model run is evidence about that model, not a proof of every production execution or every behavior allowed by the C11 memory model. Loom has modeling limitations, including incomplete coverage of some relaxed-memory behaviors. Tokio uses Loom to check synchronization primitives.

## Bad

```rust
// Repeated OS-scheduled runs do not establish coverage of every interleaving.
#[test]
fn stress_test_flag() {
    use std::sync::{Arc, atomic::{AtomicBool, Ordering}};
    let flag = Arc::new(AtomicBool::new(false));
    let other = Arc::clone(&flag);
    let writer = std::thread::spawn(move || {
        other.store(true, Ordering::Relaxed);
    });
    writer.join().unwrap();
    assert!(flag.load(Ordering::Relaxed));
}
```

This test checks a post-join result; neither repeated success nor a join establishes that a separate publication protocol has correct memory ordering.

## Good

Use instrumented primitives under a dedicated model-checking configuration. The minimal fixture below uses a normal Loom dependency because the library itself is compiled with Loom types. A larger production project can keep this setup in a separate verification crate.

```toml
# Cargo.toml
[package]
name = "my-crate"
version = "0.1.0"
edition = "2024"

[dependencies]
loom = "0.7"

[lints.rust]
unexpected_cfgs = { level = "warn", check-cfg = ['cfg(loom)'] }
```

```rust
// src/lib.rs
pub mod flag;
```

```rust
// src/flag.rs
#[cfg(loom)]
use loom::sync::atomic::{AtomicBool, Ordering};
#[cfg(not(loom))]
use std::sync::atomic::{AtomicBool, Ordering};

pub struct Flag(AtomicBool);

impl Flag {
    // Loom's constructor is not const.
    #[cfg(loom)]
    pub fn new() -> Self {
        Self(AtomicBool::new(false))
    }

    #[cfg(not(loom))]
    pub const fn new() -> Self {
        Self(AtomicBool::new(false))
    }

    pub fn set(&self) {
        self.0.store(true, Ordering::Release);
    }

    pub fn is_set(&self) -> bool {
        self.0.load(Ordering::Acquire)
    }
}
```

```rust
// tests/loom_flag.rs — a separate crate imports the library by its crate name.
#![cfg(loom)]

use loom::sync::Arc;
use my_crate::flag::Flag;

#[test]
fn flag_is_set_after_writer_joins() {
    loom::model(|| {
        let flag = Arc::new(Flag::new());
        let other = Arc::clone(&flag);
        let writer = loom::thread::spawn(move || other.set());

        // Before join, either result is valid.
        let _seen = flag.is_set();
        writer.join().unwrap();
        assert!(flag.is_set(), "flag must be set after join");
    });
}
```

This small model demonstrates constructor adaptation, instrumented atomics, and thread scheduling. Because the assertion follows `join`, it does not distinguish Release/Acquire from Relaxed or verify publication of a separate payload. Test a real payload/ordering invariant when that is the algorithm's contract.

Run with the custom cfg (it is not a Cargo feature):

```bash
RUSTFLAGS="--cfg loom" cargo test --test loom_flag
```

Also check the ordinary configuration:

```bash
cargo test
```

## Key Points

- Keep model closures small and record any preemption, branch, permutation, or time bounds used.
- Replace the synchronization and shared-memory operations that the model must observe with Loom's instrumented equivalents; uninstrumented std operations are outside that model.
- Use `loom::model` as the entry point, and ensure instrumented objects are created inside it.
- Check Loom's documented memory-model limitations rather than equating a passing run with exhaustive C11 coverage.
- Model the actual invariant; joins and unrelated synchronization can hide the ordering defect you intended to test.

## See Also

- [conc-atomic-ordering](conc-atomic-ordering.md) - Choose correct memory orderings
- [test-criterion-bench](test-criterion-bench.md) - Benchmark after correctness checks
