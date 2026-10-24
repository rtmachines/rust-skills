# checks — compile-verify the rule examples

## Corrected local edition

Focused regression suites for the local corrections live in
[`regressions/`](regressions/README.md). They extract selected current Markdown
examples, supply explicitly described scaffolding, and exercise the corrected
boundaries. Read [../LOCAL_CHANGES.md](../LOCAL_CHANGES.md) for executed checks,
exact versions and remaining verification limits.

The original extraction/classification workflow below is preserved. Its baseline
is a legacy list of accepted diagnostics, not evidence that every example is
correct. It was not regenerated to accept the corrected edition's failures.
The full legacy suite could not run in this local environment: Rust 1.95.0 was
not installed, and an offline attempt with Rust 1.99.0 stopped before compilation
because the locked `anyhow 1.0.102` was unavailable in the cache.

## Original workflow

A dev tool that type-checks the ` ```rust ` code blocks in `../rules/*.md` so the
"Good" examples we tell agents to write actually compile. Not part of the
published skill.

## Run

```bash
# structural / link / index checks (no toolchain needed)
python3 checks/validate.py

# compile-check the examples
cd checks
python3 gen.py                                              # extract blocks -> examples/
cargo check --examples --keep-going --message-format=json > check.json
python3 analyze.py check.json                               # classify results
python3 analyze.py check.json --check-baseline baseline.txt # CI gate: fail on NEW suspects
```

Both run in CI (`.github/workflows/ci.yml`): `validate` (Python only) and
`examples` (pinned to Rust 1.95.0, the toolchain `baseline.txt` was generated on).

## Updating the baseline

`baseline.txt` lists the currently-accepted suspects (fragments/pseudocode the
heuristics can't auto-classify). The CI gate fails only on signatures *not* in
it. After intentionally adding/changing examples, regenerate it on the pinned
toolchain and review the diff:

```bash
rustup run 1.95.0 cargo check --examples --keep-going --message-format=json > check.json
python3 analyze.py check.json --emit-baseline > baseline.txt
```

When bumping the pinned toolchain in `ci.yml`, regenerate `baseline.txt` on the
same version in the same commit.

## How it works

`gen.py` extracts each candidate block into `examples/<name>.rs`, wrapping
fragments in an `async fn -> Result<...>` so `?` and `.await` type-check. It
skips blocks that can't compile standalone by design: `## Bad` anti-patterns,
nightly `#![feature]` gates, procedural-macro code, placeholder crate names
(`my_crate`, …), and bare `...` pseudocode.

`analyze.py` buckets each failing example by compiler error code:

- **fragment** — every error is name resolution (undefined symbol/crate). These
  reference helpers defined elsewhere in the rule; expected, ignored.
- **artifact** — caused by extraction (a `&self` method body wrapped as a free
  fn, pseudocode `...`/`???` tokens, dangling doc comments). Not real bugs.
- **low** — only "type annotations needed"; compiles in the rule's real context.
- **SUSPECT** — anything else (type mismatch, no-method, bad syntax, wrong
  arity, missing trait impl). These are the ones to review and fix.

## Notes

- Run on Rust ≥ 1.95: some examples use APIs stabilized in 1.95 (e.g. the
  `MaybeUninit` array `From` conversions) and will spuriously fail on older
  toolchains.
- Generated files (`examples/`, `*.json`, `manifest.json`, `target/`) are
  gitignored; only the source (`gen.py`, `analyze.py`, `Cargo.toml`) is tracked.
