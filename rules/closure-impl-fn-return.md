# closure-impl-fn-return

> Return closures as `impl Fn`/`FnMut`/`FnOnce`, not `Box<dyn Fn>`

## Why It Matters

`impl Fn` in return position hides one concrete callable type and enables static dispatch without requiring heap allocation. `Box<dyn Fn>` erases the callable's type and typically adds allocation and indirect-call costs. Use it when owning heterogeneous callbacks is useful. A generic struct can store one concrete closure type, and noncapturing closures can coerce to a common function pointer; merely storing or returning a closure does not require boxing.

## Bad

```rust
// Allocates on the heap for no benefit — single concrete closure type.
fn adder_bad(n: i32) -> Box<dyn Fn(i32) -> i32> {
    Box::new(move |x| x + n)
}

fn multiplier_bad(n: i32) -> Box<dyn Fn(i32) -> i32> {
    Box::new(move |x| x * n)
}
```

## Good

```rust
// Zero allocation, statically dispatched.
fn adder(n: i32) -> impl Fn(i32) -> i32 {
    move |x| x + n
}

fn multiplier(n: i32) -> impl Fn(i32) -> i32 {
    move |x| x * n
}

fn apply(f: impl Fn(i32) -> i32, value: i32) -> i32 {
    f(value)
}

fn demo() {
    let add5 = adder(5);
    let mul3 = multiplier(3);

    assert_eq!(apply(add5, 10), 15);
    assert_eq!(apply(mul3, 10), 30);
}
```

## Key Points

**When `Box<dyn Fn>` is useful:**

Different capturing closures have distinct types. Boxing is one way to erase those differences; a single closure containing the condition is another. These noncapturing branches can instead coerce to one function-pointer type:

```rust
fn make_transform(double: bool) -> fn(i32) -> i32 {
    if double {
        |x| x * 2
    } else {
        |x| x + 100
    }
}

// One capturing closure also works with return-position impl Fn.
fn make_capturing_transform(double: bool, offset: i32) -> impl Fn(i32) -> i32 {
    move |x| if double { x * 2 } else { x + offset }
}

// Boxing is convenient for an open collection of heterogeneous closures:
struct Pipeline {
    steps: Vec<Box<dyn Fn(i32) -> i32>>,
}

impl Pipeline {
    fn new() -> Self {
        Self { steps: Vec::new() }
    }

    fn add_step(&mut self, f: impl Fn(i32) -> i32 + 'static) {
        self.steps.push(Box::new(f));
    }

    fn run(&self, mut value: i32) -> i32 {
        for step in &self.steps {
            value = step(value);
        }
        value
    }
}

fn demo_pipeline() {
    let mut p = Pipeline::new();
    p.add_step(|x| x + 1);
    p.add_step(|x| x * 3);
    assert_eq!(p.run(4), 15);
}
```

**Returning `FnMut`:** The binding at the call site must be `mut`.

```rust
fn counter(start: i32) -> impl FnMut() -> i32 {
    let mut n = start;
    move || {
        let current = n;
        n += 1;
        current
    }
}

fn demo_counter() {
    let mut next = counter(0);
    assert_eq!(next(), 0);
    assert_eq!(next(), 1);
}
```

## See Also

- [anti-type-erasure](anti-type-erasure.md) - avoid `Box<dyn Trait>` when `impl Trait` works
- [closure-static-vs-dyn](closure-static-vs-dyn.md) - static vs dynamic dispatch trade-offs for callbacks
