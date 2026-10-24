# test-cfg-test-module

> Put unit tests in `#[cfg(test)] mod tests { }` within each module

## Why It Matters

The `#[cfg(test)]` attribute excludes the whole test module, including helpers and imports, from ordinary builds. Functions marked `#[test]` are already test-only without it; `cargo test --release` still enables test code. Placing tests in a `tests` submodule within the same file keeps tests close to the code they test while maintaining separation. This is Rust's idiomatic unit test pattern.

## Bad

```rust
// Ungated helpers/imports are compiled in normal builds too.
mod tests {
    fn make_fixture() { /* test-only setup unnecessarily compiled */ }

    #[test]
    fn test_something() { ... }  // The #[test] function itself is test-only.
}

// Tests in separate file without access to private items
// src/my_module.rs
fn private_helper() { ... }

// tests/my_module_test.rs
// Can't access private_helper!
```

## Good

```rust
// src/my_module.rs

fn public_api() -> i32 {
    private_helper() * 2
}

fn private_helper() -> i32 {
    21
}

#[cfg(test)]
mod tests {
    use super::*;  // Access to private items
    
    #[test]
    fn test_public_api() {
        assert_eq!(public_api(), 42);
    }
    
    #[test]
    fn test_private_helper() {
        assert_eq!(private_helper(), 21);  // Can test private!
    }
}
```

## Module Structure

```rust
// src/lib.rs
mod parser;
mod lexer;
mod ast;

// src/parser.rs
pub fn parse(input: &str) -> Result<Ast, Error> {
    let tokens = tokenize(input)?;
    build_ast(tokens)
}

fn tokenize(input: &str) -> Result<Vec<Token>, Error> { ... }
fn build_ast(tokens: Vec<Token>) -> Result<Ast, Error> { ... }

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_parse_simple() {
        let ast = parse("1 + 2").unwrap();
        assert_eq!(ast.evaluate(), 3);
    }
    
    #[test]
    fn test_tokenize() {
        let tokens = tokenize("1 + 2").unwrap();
        assert_eq!(tokens.len(), 3);
    }
}
```

## Test Helpers

```rust
#[cfg(test)]
mod tests {
    use super::*;
    
    // Test-only helpers
    fn create_test_data() -> Data {
        Data {
            id: 1,
            name: "test".into(),
            values: vec![1, 2, 3],
        }
    }
    
    fn assert_valid(data: &Data) {
        assert!(data.id > 0);
        assert!(!data.name.is_empty());
    }
    
    #[test]
    fn test_processing() {
        let data = create_test_data();
        let result = process(&data);
        assert_valid(&result);
    }
}
```

## Multiple Test Modules

```rust
// For larger test suites, use submodules
#[cfg(test)]
mod tests {
    use super::*;
    
    mod parsing {
        use super::*;
        
        #[test]
        fn test_parse_number() { ... }
        
        #[test]
        fn test_parse_string() { ... }
    }
    
    mod validation {
        use super::*;
        
        #[test]
        fn test_validate_range() { ... }
    }
}
```

## See Also

- [test-use-super](./test-use-super.md) - Importing from parent module
- [test-integration-dir](./test-integration-dir.md) - Integration tests
- [test-descriptive-names](./test-descriptive-names.md) - Test naming
