# proj-msrv-declare

> Declare `rust-version` (MSRV) in Cargo.toml and test it in CI

## Why It Matters

Setting `package.rust-version` causes Cargo to emit a clear, actionable error when the installed toolchain is too old, instead of a cryptic type or feature error deep inside your code. The 2024-edition resolver (resolver = "3", the default for edition 2024) is MSRV-aware: it prefers compatible dependency versions when possible, but this fallback is not a guarantee that every resolved dependency supports your MSRV. Edition 2024 itself requires Rust 1.85 or newer; test the resolved dependency graph on your declared compiler floor. Without a declared MSRV, you have no contract with downstream users and no CI gate to catch regressions.

## Bad

```toml
[package]
name = "my-crate"
version = "0.1.0"
edition = "2021"
# no rust-version — users get cryptic errors on old toolchains,
# and nothing prevents a dep bump from silently raising the floor
```

## Good

```toml
[package]
name = "my-crate"
version = "0.1.0"
edition = "2024"
rust-version = "1.85"  # oldest toolchain you commit to supporting

[workspace]
resolver = "3"  # default for edition 2024; enables MSRV-aware dep resolution
```

CI job pinning the MSRV toolchain (GitHub Actions example):

```yaml
# .github/workflows/msrv.yml
- name: Install MSRV toolchain
  uses: dtolnay/rust-toolchain@master
  with:
    toolchain: "1.85"

- name: Check MSRV
  run: cargo check --all-features
```

## Choosing and Maintaining MSRV

- Pick the oldest stable toolchain your users are realistically running (check distro packages, embedded targets, corporate freeze windows).
- Do not go lower than needed — a lower MSRV widens the set of eligible dependency versions and can force you onto older, buggier releases.
- Follow your library's published compatibility policy when raising MSRV, and document the change in your changelog; do not assume every downstream user accepts a minor-release MSRV increase.
- Run `cargo msrv` (the `cargo-msrv` tool) to find the actual floor automatically.

## See Also

- [proj-workspace-deps](proj-workspace-deps.md) - use workspace dependency inheritance
- [lint-cargo-metadata](lint-cargo-metadata.md) - warn on missing Cargo.toml metadata
- [doc-cargo-metadata](doc-cargo-metadata.md) - fill Cargo.toml metadata fields
