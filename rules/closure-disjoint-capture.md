# closure-disjoint-capture

> Capture only what you use; lean on edition-2021 disjoint closure captures

## Why It Matters

Before the 2021 edition, closures captured whole variables rather than disjoint fields; moving or exclusively borrowing an aggregate could block access to sibling fields. Since Rust 2021, closures can capture individual fields, including in `move` closures. Reference only the fields you need. Binding a field to a local can make captures explicit, but is not required for a precise `move` capture.

## Bad

```rust
struct Config {
    threshold: i32,
    label: String,
}

fn demo_bad() {
    let config = Config { threshold: 10, label: String::from("demo") };

    // Using the whole struct captures it, even in edition 2021+.
    fn check_config(config: &Config) -> bool { config.threshold > 0 }
    let check = move || check_config(&config);

    // Access after the whole-struct move is an error:
    // println!("{}", config.label); // error: use of moved value

    assert!(check());
}
```

## Good

```rust
struct Config {
    threshold: i32,
    label: String,
}

fn demo_good() {
    let config = Config { threshold: 10, label: String::from("active") };

    // Edition 2021: the closure captures only `config.threshold` (a Copy field).
    // `config.label` is NOT captured, so it remains accessible.
    let check = || config.threshold > 0;

    // Both are usable simultaneously.
    println!("label: {}", config.label);  // fine — not captured by `check`
    assert!(check());
}

// `move` also captures disjoint fields in edition 2021+.
fn make_checker(config: Config) -> (impl Fn() -> bool, String) {
    let checker = move || config.threshold > 0;

    // `config.label` is still available here.
    (checker, config.label)
}

fn demo_bind_first() {
    let cfg = Config { threshold: 5, label: String::from("info") };
    let (check, label) = make_checker(cfg);
    println!("label returned: {label}");
    assert!(check());
}
```

## Key Points

- **Edition 2021 rule:** closures capture the *minimal* path used — `foo.bar` rather than `foo`. This reduces spurious borrow conflicts.
- **`move` changes how captures are taken, not the field-precision rule.** `move || config.threshold > 0` can capture just that field. Using `&config` captures the aggregate; dereferences and other capture-precision limits also matter.
- **Copy types** (integers, booleans) are copied into the closure rather than moved, so the original remains valid even with `move`.
- **Borrow when suitable:** use `move` when the closure needs ownership of its captures. Moving a reference does not extend the referent's lifetime (see [closure-move-capture](closure-move-capture.md)).

## See Also

- [own-borrow-over-clone](own-borrow-over-clone.md) - prefer borrowing over cloning
- [closure-move-capture](closure-move-capture.md) - when to use `move` and how to clone selectively
