# Regression checks for the corrected local edition

These suites exercise selected corrected examples directly from the Markdown
rules. They complement the original heuristic extractor; they do not claim to
compile every block or prove the soundness of all unsafe code. Deliberately
invalid examples are checked only for the expected compiler rejection.

Use installed toolchains and a Python version of at least 3.11. Cargo operations
in these suites use `--offline`, so the declared dependencies must already be
cached. No toolchain or crate is installed by the scripts. Choose an output
directory outside this repository for each suite.

From the repository root:

```text
python checks/regressions/core/check.py --toolchain stable --nightly nightly-2026-05-22 --output ../validation-core
python checks/regressions/api/check.py --toolchain stable --output ../validation-api
python checks/regressions/guidance/verify.py --output ../validation-guidance
```

For async/runtime regressions, follow the instructions in
[`runtime/README.md`](runtime/README.md). `--nightly` is optional for the core
suite: omitting it explicitly skips the portable SIMD check. Replace the
toolchain names with installed versions only after checking API compatibility.
The guidance suite uses installed `stable` and `1.85.0` toolchains.

## Scope and evidence

- **Core:** slice and FFI boundaries, checked matrix sizes in debug/release,
  resource drop order, arena cleanup on ordinary return and unwinding, numeric
  edge cases, documented string/layout properties, and portable SIMD with
  independent offsets, remainder lengths and nonuniform values. The core suite
  generates its extracted Rust sources under `core/target/review/` and puts build
  artifacts and logs under `--output`. Package versions are locked in
  `core/Cargo.lock`. Layout checks apply to the explicitly selected target.
- **API/types:** see [`api/README.md`](api/README.md), including downstream
  consumer tests, expected compiler diagnostics and proc-macro fixtures.
- **Guidance/tooling:** doctests, manifests, module privacy, test discovery,
  wrappers, environment restoration in an isolated helper process, Loom,
  selected dependencies, Clippy and stable rustfmt. Some checks need
  platform-specific scaffolding. The executed environment was Windows x86_64.
- **Runtime:** async lifecycle and cancellation, channels, error propagation,
  iterator/resource behavior, serialization and logging; see its own README.

Fixtures sometimes provide omitted application types, simulate an external
resource, or isolate an operation from unrelated derives. This is documented in
the scripts and the correction ledger; it is not an end-to-end application test.
Historical/version and performance guidance was corrected against primary
sources; these regression suites do not benchmark it. Miri was not run.

Local results and the finding-by-finding correction ledger are documented in
[`../../LOCAL_CHANGES.md`](../../LOCAL_CHANGES.md).
