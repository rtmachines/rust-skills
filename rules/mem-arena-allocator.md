# mem-arena-allocator

> Use arena allocators for batch allocations

## Why It Matters

Arena allocators serve allocations from reusable chunks; the common fast path advances a pointer. They can suit request-scoped or parse-tree data. Dropping a `bumpalo::Bump` frees its chunks, but does **not** run destructors for values placed with `Bump::alloc`. A `String`, standard `Vec`, file or other owning resource stored that way needs separate destruction; freeing the arena alone would leak its owned resources.

## Bad

```rust
// Many small allocations during parsing
fn parse(input: &str) -> Vec<Node> {
    let mut nodes = Vec::new();
    for token in tokenize(input) {
        nodes.push(Box::new(Node::new(token)));  // Heap alloc per node!
    }
    nodes
}

// Per-request allocations add up
fn handle_request(req: Request) -> Response {
    let headers = parse_headers(&req);      // Allocates
    let body = parse_body(&req);            // Allocates
    let response = generate_response();     // Allocates
    // All freed individually at end
    response
}
```

## Good

```rust
use bumpalo::Bump;

// Node contains only an arena-backed reference, with no destructor to run.
struct Node<'a> {
    text: &'a str,
}

fn parse<'a>(input: &str, arena: &'a Bump) -> Vec<&'a Node<'a>> {
    input.split_whitespace().map(|token| {
        let text = arena.alloc_str(token);
        let node: &'a Node<'a> = arena.alloc(Node { text });
        node
    }).collect()
}

// Per-request arena
fn handle_request(input: &str) -> String {
    let arena = Bump::new();
    
    let nodes = parse(input, &arena);
    // Return an owned response. The outer Vec drops normally; node and text
    // storage is reclaimed with the arena, without needing per-node Drop.
    nodes.iter().map(|node| node.text).collect::<Vec<_>>().join(" ")
}
```

For a value that needs `Drop`, keep a drop-owning wrapper outside raw arena storage. Enable the `boxed` feature for this example:

```rust
use bumpalo::{boxed::Box as BumpBox, Bump};

let arena = Bump::new();
{
    let text = BumpBox::new_in(String::from("owned heap buffer"), &arena);
    assert_eq!(text.as_str(), "owned heap buffer");
} // BumpBox drops String, releasing its separate heap allocation.
// The arena still owns the backing storage for the String object itself.
```

## Thread-Local Scratch Arena Pattern

```rust
use bumpalo::Bump;
use std::cell::RefCell;

thread_local! {
    static SCRATCH: RefCell<Bump> = RefCell::new(Bump::with_capacity(4 * 1024));
}

// T is independent of the arena borrow: arena references cannot escape.
fn with_scratch<T>(f: impl for<'a> FnOnce(&'a Bump) -> T) -> T {
    SCRATCH.with(|scratch| {
        let mut arena = scratch.borrow_mut();
        struct Reset<'a>(&'a mut Bump);
        impl Drop for Reset<'_> {
            fn drop(&mut self) {
                self.0.reset();
            }
        }
        let reset = Reset(&mut arena);
        f(&*reset.0)
        // Reset runs after the callback, also during unwinding.
    })
}

// Usage
fn process_batch(items: &[u64]) -> Vec<u64> {
    with_scratch(|arena| {
        let temp_data = arena.alloc_slice_copy(items);
        for item in temp_data.iter_mut() {
            *item = item.saturating_mul(2);
        }
        temp_data.to_vec() // owned result; does not borrow scratch storage
    })
}
```

This helper is deliberately non-reentrant: recursively calling `with_scratch` on the same thread panics at `borrow_mut`. Use a separate arena if nested calls are needed. Reset during unwinding reclaims arena chunks, but does not run destructors of raw arena-allocated values; the same ownership restrictions still apply. Aborting the process does not run this cleanup.

## Evidence from ROC Compiler

```rust
// https://github.com/roc-lang/roc/blob/main/crates/compiler/solve/src/to_var.rs
std::thread_local! {
    static SCRATCHPAD: RefCell<Option<bumpalo::Bump>> = 
        RefCell::new(Some(bumpalo::Bump::with_capacity(4 * 1024)));
}

fn take_scratchpad() -> bumpalo::Bump {
    SCRATCHPAD.with(|f| f.take().unwrap())
}

fn put_scratchpad(scratchpad: bumpalo::Bump) {
    SCRATCHPAD.with(|f| {
        f.replace(Some(scratchpad));
    });
}
```

## Bumpalo Collections

These examples require `bumpalo = { version = "3", features = ["boxed", "collections"] }`. Keep owning collection/box wrappers in normal drop scopes when their elements need destruction; allocating the wrapper itself through raw `Bump::alloc` would again skip its destructor.

```rust
use bumpalo::Bump;
use bumpalo::collections::{Vec, String};

fn process<'a>(arena: &'a Bump, input: &str) -> Vec<'a, String<'a>> {
    let mut results = Vec::new_in(arena);
    
    for word in input.split_whitespace() {
        let mut s = String::new_in(arena);
        s.push_str(word);
        s.push_str("_processed");
        results.push(s);
    }
    
    results  // All allocated in arena
}
```

## When to Use Arenas

| Situation | Use Arena? |
|-----------|-----------|
| Parsing (AST nodes) | Yes |
| Request handling | Yes |
| Batch processing | Yes |
| Long-lived data | No |
| Data escaping scope | No (or copy out) |
| Simple programs | Overkill |

## Performance Impact

Arena allocation can reduce per-object allocator work; measure the effect for
the actual allocator, workload and allocation sizes. In bumpalo 3.20.3, reset
retains one chunk and walks/deallocates the other chunks. It has no per-object
destructor loop, but its cost can grow with the number of chunks and the cost
of deallocation. Measure reset latency as well as allocation throughput.

```rust
// Memory trade-off:
// - Arena wastes some memory (unused capacity at the end)
// - But eliminates per-allocation metadata overhead
// - Reset reclaims arena storage, with work for additional chunks
// - Raw arena allocation does not register destructors for owned resources
```

## See Also

- [mem-with-capacity](mem-with-capacity.md) - Pre-allocate when size is known
- [mem-reuse-collections](mem-reuse-collections.md) - Reuse collections with clear()
- [opt-profile-first](perf-profile-first.md) - Profile to verify benefit
