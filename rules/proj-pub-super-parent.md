# proj-pub-super-parent

> Use `pub(super)` for visibility within the parent module and its descendants

## Why It Matters

`pub(super)` restricts an item to its immediate parent module and that parent's descendants, including sibling modules. It does not mean that only the parent itself can access the item. The defining module determines the boundary: `pub(super)` in `parser::shared` stays within `parser`, whereas the same visibility in `parser` reaches the crate root and its descendants.

## Bad

```rust
// src/parser/mod.rs
// The parent of parser is the crate root, so codegen can also access this.
pub(super) struct Token {
    pub(super) text: String,
}
```

## Good

Keep shared definitions private in the parent, or place them in a child module with `pub(super)` visibility:

```rust
// src/parser/mod.rs
mod shared {
    // Visible within parser and its descendants, including lexer and ast.
    pub(super) struct Token {
        pub(super) text: String,
    }

    pub(super) fn token(text: &str) -> Token {
        Token { text: text.to_owned() }
    }
}

mod lexer {
    use super::shared::{Token, token};

    pub(super) fn lex(input: &str) -> Vec<Token> {
        input.split_whitespace().map(token).collect()
    }
}

mod ast {
    use super::shared::Token;

    pub(super) fn parse(tokens: Vec<Token>) -> Vec<String> {
        tokens.into_iter().map(|token| token.text).collect()
    }
}

pub fn parse(input: &str) -> Vec<String> {
    ast::parse(lexer::lex(input))
}
```

The public facade returns public types; the restricted `Token` does not leak into its signature.

## Visibility Hierarchy

```text
src/
├── lib.rs
├── parser/
│   ├── mod.rs       # declares private shared, lexer and ast modules
│   ├── shared.rs    # alternative file for pub(super) Token
│   ├── lexer.rs     # can use parser::shared::Token
│   └── ast.rs       # can use parser::shared::Token
└── codegen.rs       # cannot access private parser::shared or its Token
```

This tree shows the file-based alternative to the inline modules above. If `Token` were declared `pub(super)` directly in `parser/mod.rs`, `codegen` could access it. A private `Token` in `parser/mod.rs` is another valid way to share it only with parser descendants.

## Pattern: Layered Visibility

```rust
// src/database/mod.rs
// Private definitions are accessible to this module and its descendants.
struct RawConnection { /* ... */ }

// Entire crate can see this through an accessible module path or re-export.
pub(crate) struct Pool { /* ... */ }

// Public API, if database itself is publicly reachable.
pub struct Database { /* ... */ }
```

## Pattern: Test Helpers

```rust
// src/parser/mod.rs
#[cfg(test)]
mod tests {
    // Visible to parser and its descendants, not only this tests module.
    pub(super) fn make_test_token() -> String {
        "test".to_owned()
    }
}

mod lexer {
    #[cfg(test)]
    mod tests {
        use super::super::tests::make_test_token;

        #[test]
        fn shares_parser_test_helper() {
            assert_eq!(make_test_token(), "test");
        }
    }
}
```

## Comparison

| Visibility | Scope | Use Case |
|------------|-------|----------|
| `pub` | External callers through public paths | Public API |
| `pub(crate)` | Crate-wide | Internal shared utilities |
| `pub(super)` | Parent module and its descendants | Sibling-module helpers |
| `pub(in path)` | Named ancestor and its descendants | Precise ancestor boundary |
| (private) | Defining module and its descendants | Implementation details |

## When to Use pub(super)

- Helpers in a child module that sibling modules need
- Shared types restricted to the parent's module tree
- Test utilities shared by descendants of the parent
- An explicit parent boundary after checking where the item is defined

## See Also

- [proj-pub-crate-internal](./proj-pub-crate-internal.md) - Crate visibility
- [proj-pub-use-reexport](./proj-pub-use-reexport.md) - Re-export patterns
- [proj-mod-by-feature](./proj-mod-by-feature.md) - Feature organization
