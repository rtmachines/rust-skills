# Runtime documentation regressions

Run `python generate.py`, then `cargo +stable test --offline` from this directory.
The generator copies corrected Markdown examples into private modules. Test-only
domain stubs provide missing services/types without rewriting the tested function.
Additional contracts cover prose/table claims rather than a second implementation.

Dependency versions are pinned. Run the declared MSRV separately when available.
These checks do not prove exhaustive scheduling, external-service integration,
or universal performance improvements.
