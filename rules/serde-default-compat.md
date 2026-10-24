# serde-default-compat

> Use `#[serde(default)]` for optional and backward-compatible fields

## Why It Matters

Missing required fields ordinarily cause a "missing field" error. Ordinary derived `Option<T>` fields are an exception: they can deserialize an absent key as `None` without this attribute. When you add new fields to a struct over time, older payloads that predate those fields will suddenly break. Marking fields (or the whole container) with `#[serde(default)]` fills missing keys from the type's `Default` implementation, allowing new code to read older payloads. This does not by itself make old code accept every newer payload.

## Bad

```rust
use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize, Debug)]
struct Config {
    host: String,
    port: u16,
    timeout_secs: u64,  // newly added — old configs don't have this, so they fail
    retries: u32,       // newly added — same problem
}
```

## Good

```rust
use serde::{Serialize, Deserialize};

fn default_timeout() -> u64 { 30 }
fn default_retries() -> u32 { 3 }

#[derive(Serialize, Deserialize, Debug)]
struct Config {
    host: String,
    port: u16,
    // fills from Default::default() (0u64) if missing
    #[serde(default)]
    timeout_secs: u64,
    // fills from the named function if missing
    #[serde(default = "default_retries")]
    retries: u32,
    // fills from Default (None) if missing
    #[serde(default)]
    tls_cert_path: Option<String>,
}

// Alternatively, annotate the whole container so every field uses its Default:
#[derive(Serialize, Deserialize, Debug, Default)]
#[serde(default)]
struct FeatureFlags {
    enable_caching: bool,    // false
    enable_metrics: bool,    // false
    max_connections: u32,    // 0
}
```

## Key Points

- **Field-level** `#[serde(default)]` — fills only that field; other required fields still fail if absent.
- **Field-level** `#[serde(default = "path")]` — calls a user-supplied function `fn() -> T`; use this when `Default` would produce the wrong value (e.g. `timeout = 30` rather than `0`).
- **Container-level** `#[serde(default)]` — applies to every field; the struct must implement `Default` (or `#[derive(Default)]`). Convenient for all-optional structs like feature-flag configs.
- The default function must be callable with no arguments and return the field type; generic functions are allowed when their parameters can be inferred.
- `#[serde(default)]` only affects **deserialization**. It has no effect on serialization; pair with `#[serde(skip_serializing_if = "...")]` if you also want to omit defaults on the way out.

## Caveats

Using container-level `#[serde(default)]` makes every field optional to deserializers, which can hide typos in field names. Prefer field-level annotation when only some fields are backward-compatible additions.

## See Also

- [serde-skip-empty](serde-skip-empty.md) - omit None/empty values during serialization
- [api-default-impl](api-default-impl.md) - implement `Default` for sensible defaults
