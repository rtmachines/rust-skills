# num-float-compare

> Choose numeric, approximate or bitwise float equality deliberately; use `total_cmp` for a defined total order

## Why It Matters

Floating-point arithmetic rounds: `0.1_f64 + 0.2 == 0.3` is false. Numeric equality also treats NaN as unequal to every value, including itself. `partial_cmp` returns `None` for NaN; unwrapping that result inside a sort comparator panics. Use a domain-appropriate tolerance for approximate equality, `to_bits()` for representation equality, and `total_cmp` (stable since Rust 1.62) when its total-order policy is desired.

## Bad

```rust
fn is_unit_length(x: f64, y: f64) -> bool {
    (x * x + y * y).sqrt() == 1.0  // almost always false due to rounding
}

fn sort_scores(scores: &mut Vec<f64>) {
    scores.sort_by(|a, b| a.partial_cmp(b).unwrap());
    // panics (unwrap on None) if any score is NaN
}
```

## Good

```rust
// Approximate equality for finite values with a positive absolute tolerance.
fn approx_eq(a: f64, b: f64, epsilon: f64) -> bool {
    (a - b).abs() < epsilon
}

fn is_unit_length(x: f64, y: f64) -> bool {
    approx_eq((x * x + y * y).sqrt(), 1.0, 1e-9)
}

// total ordering includes both signs of NaN and distinguishes signed zero
fn sort_scores(scores: &mut Vec<f64>) {
    scores.sort_by(|a, b| a.total_cmp(b));
}

// direct NaN check when needed
fn safe_reciprocal(x: f64) -> Option<f64> {
    if x == 0.0 || x.is_nan() {
        None
    } else {
        Some(1.0 / x)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn float_addition_is_not_exact() {
        assert_ne!(0.1_f64 + 0.2, 0.3);  // IEEE 754 rounding
        assert!(approx_eq(0.1 + 0.2, 0.3, 1e-10));
    }

    #[test]
    fn nan_is_not_equal_to_itself() {
        let nan = f64::NAN;
        assert_ne!(nan, nan);  // NaN != NaN by IEEE 754
    }

    #[test]
    fn total_cmp_handles_nan() {
        let positive_nan = f64::from_bits(0x7ff8_0000_0000_0000);
        let mut v = vec![3.0_f64, positive_nan, 1.0, positive_nan, 2.0];
        sort_scores(&mut v);
        // These positive NaNs sort to the end; negative NaNs sort first.
        assert_eq!(&v[..3], &[1.0, 2.0, 3.0]);
        assert!(v[3].is_nan());
        assert!(v[4].is_nan());
    }

    #[test]
    fn unit_length_uses_tolerance() {
        assert!(is_unit_length(1.0, 0.0));
        assert!(is_unit_length(0.6, 0.8));  // 3-4-5 right triangle scaled
    }

    #[test]
    fn numeric_and_bitwise_equality_differ() {
        assert_eq!(0.0_f64, -0.0_f64);
        assert_ne!(0.0_f64.to_bits(), (-0.0_f64).to_bits());
        let negative_nan = f64::from_bits(0xfff8_0000_0000_0000);
        assert!(negative_nan.total_cmp(&f64::NEG_INFINITY).is_lt());
    }
}
```

## Key Points

- **Epsilon choice**: an absolute epsilon (`1e-9`) is simple but wrong for very large or very small values. For general-purpose code, a relative epsilon `(a - b).abs() / a.abs().max(b.abs()) < epsilon` is more robust — but requires handling the zero case.
- **`f64::total_cmp`** defines a strict total order: `-NaN < -∞ < … < -0.0 < +0.0 < … < +∞ < NaN`. It never panics and is available on `f32` and `f64`.
- **`is_nan` / `is_infinite` / `is_finite`**: use these predicates before arithmetic on untrusted floats.
- **`==` is numeric equality, not bitwise equality**: positive and negative zero compare equal, while a NaN is unequal to itself. Use `to_bits()` when the exact representation matters. If all NaNs must sort last regardless of sign, write that policy explicitly instead of assuming `total_cmp` provides it.

## See Also

- [num-overflow-explicit](num-overflow-explicit.md) - handle integer overflow explicitly
