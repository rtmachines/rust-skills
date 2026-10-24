# API and type corrections: focused regressions

Run from any directory with Python 3 and the selected Rust toolchain installed:

```text
python checks/regressions/api/check.py --output <directory-outside-the-repository> --toolchain stable
```

The script extracts implementations from the Markdown rules, supplies only
missing domain scaffolding, and compiles/tests the corrected contracts in Rust
edition 2024. It writes all generated sources, binaries, Cargo fixtures, logs,
and `results.json` under `--output`; it does not modify the rules. Expected
compile failures must include the relevant diagnostic, not merely exit nonzero.

Covered boundaries include UTF-8 byte budgets, integer overflow and conversion,
builder defaults and ownership, precise closure capture, callback alternatives,
conditional Cow ownership, secret redaction, response return types, dyn
compatibility, static promotion, slice/path conversions, and must-use diagnostics.
Separate downstream crates exercise the sealed lifecycle/open customization API
and the exported macro. FFI declarations are compile-only and never executed.

The proc-macro check uses the actual corrected `Good` block, a generic downstream
consumer, and rejected enum/tuple/empty-struct inputs. It requires cached `syn
2.0.119`, `quote 1`, and `proc-macro2 1`; Cargo always uses `--offline`. No package
is installed or fetched by the script.

The redaction check for `Config` removes only Serde attributes to test its exact
manual Debug body without adding Serde to the std-only suite. The boundary
handler uses small local parser stand-ins; its test covers the corrected result
contract and propagation, not production email validation. Historical
stabilization dates, feature-matrix descriptions and collection complexity are
documentation corrections supported by the audit's primary sources, not claims
that this script benchmarks or exhaustively tests them. The selected compiler
does not establish compatibility with every older version.
