# Rust Skills — corrected edition

![rules](https://img.shields.io/badge/rules-265-blue)
![categories](https://img.shields.io/badge/categories-26-blue)
![edition](https://img.shields.io/badge/edition-2024-orange)
![license](https://img.shields.io/badge/license-MIT-green)

265 Rust rules for use with an AI coding agent. This fork corrects the
101 findings in the Polish review of upstream commit
`fd2a861ab0406a4ac536a55274d14ea6fd1ca9c9`. It is based on upstream 1.5.1;
the correction identifier is `1.5.1+local.1`.

See [LOCAL_CHANGES.md](LOCAL_CHANGES.md) for the correction ledger, verification
results and limitations. Examples use edition 2024 unless stated otherwise;
individual APIs and dependencies may have additional version requirements.
The targeted regression suite was run on Rust 1.99.0, with a separately selected
nightly for portable SIMD. This is not a certification of the entire collection
on Rust 1.96 or the legacy CI toolchain, Rust 1.95.0.

The entry point is `SKILL.md`, with supporting material in `rules/`. Installation
and invocation depend on your agent; see the CLI's
[supported agents](https://github.com/vercel-labs/skills/blob/main/docs/agents.md)
for its current integration list.

## Why

These rules explain Rust patterns, tradeoffs and common failure modes. Each rule
is small and focused, so an agent can read the material relevant to the task.
Apply it with the project's edition, MSRV, API contracts and workload in mind;
a priority label or a passing test does not establish safety or performance.

## Install this corrected edition

Use the [Skills CLI](https://github.com/vercel-labs/skills) from your project's
directory. It requires Node.js 22.20 or later and npm/npx:

```bash
npx skills add rtmachines/rust-skills --skill rust-skills
```

In interactive use, select the target agents when prompted; inside an agent,
the CLI may select that agent automatically. Installation is project-scoped by
default; add `--global` for your user account or `--agent` to choose explicitly:

```bash
# Codex, current project
npx skills add rtmachines/rust-skills --skill rust-skills --agent codex

# Claude Code, all projects for this user
npx skills add rtmachines/rust-skills --skill rust-skills --agent claude-code --global

# Inspect the skill available in this fork without installing it
npx skills add rtmachines/rust-skills --list
```

Use `--copy` if symlinks are unsuitable for your setup. See the
[CLI reference](https://github.com/vercel-labs/skills/blob/main/docs/commands.md)
for the complete options. The older `npx add-skill` interface is deprecated;
these instructions use `npx skills add`.

The original project is [leonardomso/rust-skills](https://github.com/leonardomso/rust-skills).
Installing from the original project does not include this fork's corrections.

## How to use it

After installation, select `rust-skills` using your agent's skill picker or
invocation syntax. For example, ask:

```text
Use the rust-skills skill to review this function. Read the relevant rule files,
check the project's Rust edition and MSRV, and explain any applicable exceptions.
```

Some agents expose `/rust-skills`; others use a picker or a different prefix.
When using a manual checkout, give the agent the path to `rust-skills/SKILL.md`
and access to its sibling `rules/` directory.

## See it in action

Ask the agent to review a function like this:

```rust
// before
fn first_word(s: &String) -> String {
    s.clone().split_whitespace().next().unwrap().to_string()
}
```

With these rules loaded, it knows to take `&str` instead of `&String`, drop the
needless `clone()` and allocation, and return an `Option` instead of panicking:

```rust
// after — applies own-slice-over-vec, own-borrow-over-clone, anti-unwrap-abuse
fn first_word(s: &str) -> Option<&str> {
    s.split_whitespace().next()
}
```

## What's in here

265 rules split into 26 categories:

| Category | Rules | What it covers |
|----------|-------|----------------|
| **Ownership & Borrowing** | 12 | When to borrow vs clone, Arc/Rc, lifetimes |
| **Error Handling** | 12 | thiserror for libs, anyhow for apps, the `?` operator |
| **Memory** | 17 | SmallVec, arenas, avoiding allocations, `mem::take`, drop order |
| **Unsafe Code** | 7 | `SAFETY:` comments, Miri, `MaybeUninit`, 2024-edition unsafe |
| **API Design** | 17 | Builder pattern, newtypes, sealed traits, `FromIterator` |
| **Async** | 18 | Tokio patterns, channels, async fn in traits, cancel safety |
| **Concurrency** | 4 | rayon, scoped threads, atomic ordering, thread-locals |
| **Optimization** | 12 | LTO, inlining, PGO, SIMD |
| **Numeric & Arithmetic** | 5 | Overflow handling, `as` vs `TryFrom`, float compare, `NonZero` |
| **Type Safety** | 13 | Newtypes, parse don't validate, `Deref`, `Display`/`Debug` |
| **Trait & Generics Design** | 6 | dyn vs generic, associated types, blanket impls, object safety, orphan rule |
| **Conversions** | 3 | `TryFrom`, `FromStr`, `AsMut` |
| **Const & Compile-Time** | 4 | `const fn`, const vs static, const generics, `const {}` blocks |
| **Serde** | 8 | rename_all, default, flatten, enum tagging, validate-on-deserialize |
| **Pattern Matching** | 5 | `let-else`, `matches!`, if-let chains, exhaustive matches |
| **Macros** | 8 | `macro_rules!` hygiene, fragment specifiers, proc-macros with syn/quote |
| **Closures** | 5 | Fn/FnMut/FnOnce bounds, returning `impl Fn`, move & disjoint capture |
| **Collections** | 4 | HashMap/BTreeMap/IndexMap, Vec/VecDeque, sets, `BinaryHeap` |
| **Naming** | 16 | Following Rust API Guidelines |
| **Testing** | 15 | Proptest, mockall, criterion, loom, snapshot tests |
| **Docs** | 12 | Doc examples, intra-doc links, README/crate-doc unification |
| **Observability** | 7 | tracing over log, spans, structured fields, redacting secrets |
| **Performance** | 13 | Iterators, entry API, faster hashers, I/O buffering |
| **Project Structure** | 14 | Workspaces, module layout, features, MSRV |
| **Linting** | 13 | Clippy config, CI setup, `unexpected_cfgs` |
| **Anti-patterns** | 15 | Common mistakes and how to fix them |

Each rule has:

- Why it matters
- A bad code example
- A good code example
- Links to related rules and sources

## How it works

The design is built for low token cost and easy auditing:

- **[`SKILL.md`](./SKILL.md)** is a lightweight index — every rule listed as a one-line summary, grouped by category, with a link to its file. The agent reads this first.
- **[`rules/`](./rules)** holds one Markdown file per rule (`<prefix>-<name>.md`). The agent can open the subset relevant to your code instead of loading all 265 rules.
- **Prefixes** (`own-`, `err-`, `unsafe-`, `async-`, …) map directly to categories, so an agent reviewing async code can pull just `async-`, `conc-`, and `own-` rules.

Git stores `CLAUDE.md` and `AGENTS.md` as symlinks to `SKILL.md`. If your checkout
does not preserve symlinks, open `SKILL.md` directly. Keep the directory layout
intact so its relative links to `rules/` resolve.

## Manual checkout

Clone the complete corrected repository:

```bash
git clone --branch master https://github.com/rtmachines/rust-skills.git rust-skills
```

Place that directory in a skill location supported by your agent, or configure
the agent to read `rust-skills/SKILL.md` from the checkout. Preserve at least:

```text
rust-skills/
  SKILL.md
  rules/
    own-borrow-over-clone.md
    ...
```

`SKILL.md` is an index: copying it alone into `AGENTS.md`, `.cursorrules`, or
another instruction file omits the linked rule files. For an agent that reads
project instruction files, add a reference to the complete checkout instead of
replacing the project's existing instructions. For example, with the cloned
directory inside the project:

```text
For Rust work, read rust-skills/SKILL.md and the relevant files under
rust-skills/rules/. Apply each rule in the context of this project's edition,
MSRV, dependencies and requirements.
```

To update an unmodified manual checkout from this fork:

```bash
git -C rust-skills pull --ff-only
```

## All rules

See [SKILL.md](./SKILL.md) for the full list with links to each rule file.

## Sources & attribution

This fork builds on [leonardomso/rust-skills](https://github.com/leonardomso/rust-skills) and preserves its attribution and MIT license. The original collection summarizes official Rust guidance, books and patterns from open-source crates; this fork adds the corrections documented in [LOCAL_CHANGES.md](LOCAL_CHANGES.md). Neither the original project nor this fork is endorsed by the Rust project or the authors of the referenced crates.

**Official Rust documentation**
- [The Rust Reference](https://doc.rust-lang.org/reference/)
- [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/)
- [The Rustonomicon](https://doc.rust-lang.org/nomicon/) (unsafe code)
- [Rust 2024 Edition Guide](https://doc.rust-lang.org/edition-guide/rust-2024/)
- [The Cargo Book](https://doc.rust-lang.org/cargo/)
- [Standard library docs](https://doc.rust-lang.org/std/) and [release notes](https://doc.rust-lang.org/releases.html)

**Books & guides**
- [The Rust Performance Book](https://nnethercote.github.io/perf-book/) — Nicholas Nethercote
- [Rust Design Patterns](https://rust-unofficial.github.io/patterns/) — rust-unofficial
- [Rust Atomics and Locks](https://marabos.nl/atomics/) — Mara Bos
- [Effective Rust](https://effective-rust.com/) — David Drysdale

**Tooling**
- [Clippy lint documentation](https://rust-lang.github.io/rust-clippy/)
- [Miri](https://github.com/rust-lang/miri)

**Real-world codebases studied for idioms**
- ripgrep, tokio, serde, clap, polars, axum, cargo, hyper, bevy, rayon, and dtolnay's crates (thiserror, anyhow, syn)

This project is MIT-licensed. Referenced upstream materials remain under their own licenses — the official Rust documentation and API Guidelines are dual [MIT](https://github.com/rust-lang/rust/blob/master/LICENSE-MIT) / [Apache-2.0](https://github.com/rust-lang/rust/blob/master/LICENSE-APACHE).

## Contributing

Open issues and pull requests against [rtmachines/rust-skills](https://github.com/rtmachines/rust-skills). See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow. To add or change a rule:

1. Create `rules/<prefix>-<name>.md` using a `kebab-case` id with an existing category prefix (`own-`, `err-`, `mem-`, …).
2. Follow the format of existing rules: a `>` one-line summary, then `## Why It Matters`, `## Bad`, `## Good`, and `## See Also` (with links that resolve).
3. Verify changed examples with their documented edition, toolchain and dependency versions. Label nightly-only examples and fragments that need additional context.
4. Run `python checks/gen_index.py` to regenerate the index, then `python checks/validate.py` and `python checks/gen_index.py --check`. Do not hand-edit the generated index.
5. Run the relevant [regression checks](checks/regressions/README.md) for code changes and record any verification limits.

````markdown
# prefix-rule-name

> One-line imperative summary.

## Why It Matters

Two to four sentences.

## Bad

```rust
// the anti-pattern
```

## Good

```rust
// the recommended pattern
```

## See Also

- [other-rule](other-rule.md) - why it's related
````

## License

MIT
