# anti-expect-lazy

> Don't use expect for recoverable errors

## Why It Matters

`.expect()` panics with a custom message, but it's still a panic. Using it for errors that could reasonably occur in production (network failures, file not found, invalid input) crashes the program instead of handling the error gracefully.

Reserve `.expect()` for programming errors where panic is appropriate.

## Bad

```rust
// Network failures are expected - don't panic
let response = client.get(url).await.expect("failed to fetch");

// Files might not exist
let config = fs::read_to_string("config.toml").expect("config not found");

// User input can be invalid
let age: u32 = input.parse().expect("invalid age");

// Database queries can fail
let user = db.find_user(id).await.expect("user not found");
```

## Good

```rust
// Handle recoverable errors properly
let response = client.get(url).await
    .context("failed to fetch URL")?;

// Return error if file doesn't exist
let config = fs::read_to_string("config.toml")
    .context("failed to read config file")?;

// Validate and return error
let age: u32 = input.parse()
    .map_err(|_| Error::InvalidInput("age must be a number"))?;

// Handle missing data
let user = db.find_user(id).await?
    .ok_or(Error::NotFound("user"))?;
```

## When expect() Is Appropriate

Use `.expect()` for invariants that indicate bugs. At the application boundary, a required startup failure can also justify terminating; this is a policy decision, not proof that an OS error is a programming bug:

```rust
// Mutex poisoning indicates a bug elsewhere
let guard = mutex.lock().expect("mutex poisoned");

// Regex is known valid at compile time
let re = Regex::new(r"^\d{4}$").expect("invalid regex");

// Startup policy: this application cannot run without this worker.
// Builder::spawn returns io::Result; thread::spawn already panics on OS failure.
let handle = std::thread::Builder::new()
    .spawn(|| work())
    .expect("required startup worker should be available");
// Retain and eventually join the handle, or explicitly choose to detach it.

// Static data that must be valid
let config: Config = toml::from_str(EMBEDDED_CONFIG)
    .expect("embedded config is invalid");
```

## Pattern: expect() vs unwrap()

```rust
// unwrap: no context, hard to debug
let x = option.unwrap();

// expect: gives context, still panics
let x = option.expect("value should exist after validation");

// ?: proper error handling
let x = option.ok_or(Error::MissingValue)?;
```

## Decision Guide

| Situation | Use |
|-----------|-----|
| User input | `?` with error |
| File/network I/O | `?` with error |
| Database operations | `?` with error |
| Parsed constants | `.expect()` |
| Thread creation | Handle OS failure, or terminate by an explicit startup policy |
| Mutex poisoning | Recover deliberately or use `.expect()` for a protected invariant |
| After validation check | `.expect()` with explanation |
| Never expected to fail | `.expect()` documenting invariant |

## See Also

- [err-expect-bugs-only](./err-expect-bugs-only.md) - When to use expect
- [err-no-unwrap-prod](./err-no-unwrap-prod.md) - Avoiding unwrap
- [anti-unwrap-abuse](./anti-unwrap-abuse.md) - Unwrap anti-pattern
