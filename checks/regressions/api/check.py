"""Compile extracted corrected examples and test their actual boundary behavior.

Requires Python 3 and rustc/cargo. Proc-macro dependencies must already be cached;
Cargo always runs offline. All generated sources, logs and artifacts go to --output.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--toolchain", default="stable")
args = parser.parse_args()
root = Path(__file__).resolve().parents[3]
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=True)
results = []


def doc(name):
    return (root / "rules" / (name + ".md")).read_text(encoding="utf-8")


def block(name, heading, language="rust", index=0):
    section = doc(name).split("## " + heading + "\n", 1)[1].split("\n## ", 1)[0]
    return re.findall(r"```" + language + r"\n(.*?)```", section, re.S)[index]


def write(path, source):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def run(name, command, expected=0, contains=None):
    completed = subprocess.run(command, cwd=out, text=True, encoding="utf-8", errors="replace",
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    ok = (completed.returncode == 0) if expected == 0 else (completed.returncode != 0)
    if contains:
        ok = ok and contains in completed.stdout
    record = dict(name=name, command=list(map(str, command)), exit_code=completed.returncode,
                  expected="success" if expected == 0 else "rejection", passed=ok)
    results.append(record)
    write(out / (name + ".log"), json.dumps(record, indent=2) + "\n" + completed.stdout)
    write(out / "results.json", json.dumps(results, indent=2))
    print(f"{'PASS' if ok else 'FAIL'} {name}", flush=True)
    if not ok:
        raise RuntimeError(completed.stdout)
    return completed.stdout


def rust(name, source, extra=(), expected=0, contains=None, test=False):
    path = out / (name + ".rs")
    write(path, source)
    artifact = out / (name + (".exe" if os.name == "nt" else ".bin"))
    if "--crate-type=rlib" in extra:
        artifact = out / ("lib" + name + ".rlib")
    command = ["rustc", "+" + args.toolchain, "--edition=2024", "-A", "dead_code", str(path)]
    command += list(extra)
    if test:
        command += ["--test"]
    command += ["-o", str(artifact)]
    run(name + "-build", command, expected, contains)
    if test and expected == 0:
        run(name + "-run", [str(artifact)])
    return artifact


run("toolchain", ["rustc", "+" + args.toolchain, "--version", "--verbose"])
modules = []


def module(name, source, tests):
    modules.append("mod " + name + " {\n" + source + "\n" + tests + "\n}")


module("utf8", block("api-extension-trait", "Scoped Extensions").split("// Only available")[0], r'''
use string_utils::StringExt;
#[test] fn truncates_utf8_and_respects_every_small_byte_budget() {
    for input in ["", "abc", "ąabcdef", "🙂🙂a", "aé日b"] {
        for budget in 0..=input.len()+3 {
            let actual = input.truncate_ellipsis(budget);
            assert!(actual.len() <= budget);
            if input.len() <= budget { assert_eq!(actual, input); }
        }
    }
    assert_eq!("ąabcdef".truncate_ellipsis(4), "...");
    assert_eq!("ąabcdef".truncate_ellipsis(5), "ą...");
    assert_eq!("abc".truncate_ellipsis(1), ".");
    assert_eq!("abcdef".truncate_ellipsis(0), "");
}
''')
module("double", block("macro-prefer-functions", "Good"), r'''
#[test] fn doubles_instead_of_squaring() {
    assert_eq!(double(21_i32), 42);
    assert_eq!(double(-3_i32), -6);
    assert_eq!(double(1.5_f64), 3.0);
}
''')
division = block("type-result-fallible", "Good").split("#[derive", 1)[1].split("// Caller", 1)[0]
module("division", "#[derive" + division, r'''
#[test] fn classifies_zero_overflow_and_valid_results() {
    assert_eq!(divide(10, 0), Err(DivisionError::DivideByZero));
    assert_eq!(divide(i32::MIN, -1), Err(DivisionError::Overflow));
    assert_eq!(divide(i32::MIN, 1), Ok(i32::MIN));
    assert_eq!(divide(10, 2), Ok(5));
}
''')
module("ids", block("type-newtype-ids", "Add Useful Methods"), r'''
#[test] fn preserves_database_ids_or_rejects_out_of_range() {
    assert_eq!(UserId::new(0).try_to_i64().unwrap(), 0);
    assert_eq!(UserId::new(i64::MAX as u64).try_to_i64().unwrap(), i64::MAX);
    assert!(UserId::new(i64::MAX as u64 + 1).try_to_i64().is_err());
    assert!(UserId::from(u64::MAX).try_to_i64().is_err());
}
''')
module("builder", block("api-builder-pattern", "Good").split("// Usage", 1)[0] + r'''
pub struct Client { base_url: String, timeout: Duration, max_retries: u32, auth_token: Option<String> }
#[derive(Debug)] pub enum BuilderError { MissingBaseUrl }
''', r'''
#[test] fn default_and_override_retries_agree_with_documentation() {
    for builder in [ClientBuilder::new(), ClientBuilder::default()] {
        let c = builder.base_url("https://example.test").build().unwrap();
        assert_eq!(c.max_retries, 3);
        assert_eq!(c.timeout, Duration::from_secs(30));
    }
    let c = ClientBuilder::new().base_url("x").max_retries(0).build().unwrap();
    assert_eq!(c.max_retries, 0);
    assert!(ClientBuilder::new().build().is_err());
}
''')
module("capture", block("closure-disjoint-capture", "Good"), r'''
#[test] fn move_preserves_sibling_field() {
    let (callback, label) = make_checker(Config {threshold: 5, label: "retained".into()});
    assert_eq!(label, "retained"); assert!(callback());
}
''')
module("callbacks", block("closure-impl-fn-return", "Key Points"), r'''
#[test] fn both_branches_and_capturing_variant_work_without_box() {
    assert_eq!(make_transform(true)(21), 42);
    assert_eq!(make_transform(false)(21), 121);
    assert_eq!(make_capturing_transform(false, 7)(21), 28);
    demo_pipeline();
}
''')
module("cow", block("own-borrow-over-clone", "Evidence"), r'''
#[test] fn basename_preserves_borrowing_and_handles_owned_and_empty_paths() {
    let borrowed = Cow::Borrowed(&b"dir/file"[..]);
    assert!(matches!(file_name(&borrowed), Some(Cow::Borrowed(b"file"))));
    let owned = Cow::Owned(b"dir/file".to_vec());
    assert!(matches!(file_name(&owned), Some(Cow::Owned(ref name)) if name == b"file"));
    assert_eq!(file_name(&Cow::Borrowed(&b"file"[..])).unwrap().as_ref(), b"file");
    assert!(file_name(&Cow::Borrowed(&b""[..])).is_none());
    assert!(file_name(&Cow::Borrowed(&b"dir/"[..])).is_none());
}
''')
module("redaction", block("api-common-traits", "Manual Implementations"), r'''
#[test] fn debug_redacts_private_password() {
    let output = format!("{:?}", Password("synthetic-secret".into()));
    assert_eq!(output, "Password([REDACTED])");
    assert!(!output.contains("synthetic-secret"));
}
''')
# Remove only the unrelated serialization attributes to compile the exact Debug
# body without bringing Serde into these std-only regression tests.
config_debug = block("api-common-traits", "Serde Traits").split("// With custom serialization", 1)[1]
config_debug = config_debug.replace("#[derive(Clone, Serialize, Deserialize)]", "#[derive(Clone)]")
config_debug = re.sub(r"^\s*#\[serde\([^\n]*\)\]\n", "\n", config_debug, flags=re.M)
module("config_redaction", config_debug, r'''
#[test] fn debug_redacts_optional_api_key() {
    let output = format!("{:?}", Config{verbose:true,api_key:Some("synthetic-key".into())});
    assert!(output.contains("REDACTED")); assert!(!output.contains("synthetic-key"));
    let absent = format!("{:?}", Config{verbose:false,api_key:None}); assert!(absent.contains("None"));
}
''')
module("into", block("api-impl-into", "When NOT to Use impl Into", index=1), r'''
#[test] fn generic_conversion_preserves_values() {
    assert_eq!(hot_path(42u32),42u64); assert_eq!(hot_path(u64::MAX),u64::MAX);
}
''')
module("boundary", block("api-parse-dont-validate", "Parsing at Boundaries") + r'''
struct RawRequest { email: String, age: u8, username: String }
#[derive(Debug)] struct Error;
struct Email(String); struct Age(u8); struct Username(String);
impl Email { fn parse(s: &str) -> Result<Self, Error> { if s.contains('@') { Ok(Self(s.into())) } else { Err(Error) } } }
impl Age { fn parse(n: u8) -> Result<Self, Error> { if n > 0 { Ok(Self(n)) } else { Err(Error) } } }
impl Username { fn parse(s: &str) -> Result<Self, Error> { if !s.is_empty() { Ok(Self(s.into())) } else { Err(Error) } } }
''', r'''
#[test] fn handler_returns_response_and_propagates_parse_errors() {
    let response = handle_request(RawRequest {email:"a@b".into(),age:20,username:"alice".into()}).unwrap();
    assert_eq!(response.email.0, "a@b"); assert_eq!(response.age.0,20); assert_eq!(response.username.0,"alice");
    assert!(handle_request(RawRequest {email:"invalid".into(),age:20,username:"alice".into()}).is_err());
}
''')
module("slices", "", "#[test] fn borrow_before_consuming_vec() {\n" + block("own-slice-over-vec", "The Deref Coercion Chain") + "\n}")
module("trait_object", block("trait-object-safety", "Good"), "#[test] fn both_dispatch_paths_work() { demo(); assert_eq!(apply_generic(&Shout, 42), \"42\"); }")
module("const_fn", "", "#[test] fn usable_in_constant_contexts() {\n" + block("const-fn", "Good") + "\nassert_eq!(ALIGNED,16); assert_eq!(buf.len(),4);\n}")
email = block("api-newtype-safety", "Constructor Patterns").split("// Usage", 1)[0]
module("email", email + r'''
#[derive(Debug)] enum EmailError { InvalidFormat }
fn is_valid_email(s: &str) -> bool { s.contains('@') }
''', '#[test] fn string_newtype_is_cloneable() { let e=Email::new("a@b").unwrap(); assert_eq!(e.clone().as_str(),"a@b"); }')
rust("extracted-examples", "\n".join(modules), test=True)
rust("division-release", "mod division {\n#[derive" + division + r'''
#[test] fn rejects_overflow_in_release() { assert_eq!(divide(i32::MIN,-1),Err(DivisionError::Overflow)); }
}''', extra=["-C", "opt-level=3", "-C", "overflow-checks=off"], test=True)

# Downstream boundary: an external customization works; replacing lifecycle does not.
sealed = rust("sealed_api", block("api-sealed-trait", "Partially Sealed"),
              extra=["--crate-type=rlib"])
consumer = r'''
use sealed_api::{ManagedPlugin, Plugin, PluginName};
struct Custom;
impl PluginName for Custom { fn name(&self)->&str { "downstream" } }
#[test] fn external_name_is_used() {
    let p=ManagedPlugin::new(Custom); assert_eq!(p.name(),"downstream"); p.initialize(); p.shutdown();
}
'''
rust("sealed-consumer", consumer, extra=["--extern", "sealed_api="+str(sealed)], test=True)
rust("sealed-reject", consumer + r'''
impl Plugin for Custom {
    fn name(&self)->&str { "forbidden" } fn initialize(&self) {} fn shutdown(&self) {}
}
''', extra=["--extern", "sealed_api="+str(sealed), "--emit=metadata", "--crate-type=lib"], expected=1, contains="E0277")

# Exported macro works through a renamed downstream import with the real helper.
macro = rust("macro_api", block("macro-export-crate-path", "Good"), extra=["--crate-type=rlib"])
rust("macro-consumer", 'use renamed::greet;\n#[test] fn exported_macro_works() { greet!("world"); }',
     extra=["--extern", "renamed="+str(macro)], test=True)

# Compile-only FFI: no foreign operation is linked or executed.
rust("ffi", "use std::ffi::c_void;\n" + block("type-repr-transparent", "Good") +
     block("type-repr-transparent", "FFI Pattern"), extra=["--crate-type=lib", "--emit=metadata"])

rust("dyn-box-self-reject", 'trait T {fn duplicate(&self)->Box<Self>;} fn use_it(_: &dyn T) {}',
     extra=["--crate-type=lib", "--emit=metadata"], expected=1, contains="E0038")
rust("dyn-box-trait-pass", 'trait T {fn duplicate(&self)->Box<dyn T>;} fn use_it(x:&dyn T) {let _=x.duplicate();}',
     extra=["--crate-type=lib", "--emit=metadata"])
rust("static-mut-value", 'static mut N:u64=0; unsafe fn read()->u64 {unsafe {N}}',
     extra=["--crate-type=lib", "--emit=metadata"])
rust("static-mut-ref-reject", 'static mut N:u64=0; unsafe fn read()->&\'static u64 {unsafe {&N}}',
     extra=["--crate-type=lib", "--emit=metadata"], expected=1, contains="static_mut_refs")
rust("promoted-str", r'''
const BYTES:[u8;6]=[109,121,45,97,112,112];
const NAME:&'static str=match std::str::from_utf8(&BYTES) {Ok(s)=>s,Err(_)=>panic!()};
#[test] fn constant_data_can_provide_static_str() {let s:&'static str=NAME; assert_eq!(s.as_bytes(),&BYTES);}
''', test=True)
rust("hashmap-construction", 'struct Point {x:f64,y:f64} fn main(){let _:std::collections::HashMap<Point,()>=std::collections::HashMap::new();}')
rust("hashmap-insert-reject", 'struct Point {x:f64,y:f64} fn main(){let mut m=std::collections::HashMap::new(); m.insert(Point{x:0.,y:0.},());}', expected=1, contains="E0277")
rust("path-views", r'''
use std::path::{Path,PathBuf};
fn exact(p:&Path)->&Path {p} fn flexible(p:impl AsRef<Path>)->PathBuf {p.as_ref().into()}
#[test] fn explicit_and_asref_conversions() {
    let s=String::from("config"); let p=PathBuf::from(&s);
    assert_eq!(exact(&p),exact(Path::new(&s))); assert_eq!(flexible(&s),flexible("config"));
}
''', test=True)
rust("must-use-option", '#![deny(unused_must_use)]\nfn main(){Some(5).map(|x|x*2);}')
rust("must-use-first", '#![deny(unused_must_use)]\nfn main(){[1,2,3].first();}', expected=1, contains="unused return value")
builder = 'use std::time::Duration;\n' + block("api-builder-must-use", "Good").split("// Now warns",1)[0]
rust("must-use-builder", builder + 'fn main(){RequestBuilder{url:"x".into(),timeout:None,headers:vec![]}.timeout(Duration::from_secs(30));}',
     extra=["-D", "unused_must_use"], expected=1, contains="unused return value")
rust("builder-moved-reject", builder + 'fn main(){let r=RequestBuilder{url:"x".into(),timeout:None,headers:vec![]}; let _=r.timeout(Duration::from_secs(30)); let _=r.header("a","b");}',
     expected=1, contains="E0382")
rust("const-defaults", 'struct Buf<const N:usize=64>([u8;N]); fn main(){let _:Buf=Buf([0;64]);}')
rust("never-return", 'fn diverges()->!{loop{}} fn accepts(_:fn()->! ){} fn main(){accepts(diverges);}')

# The actual Cargo lint table must reject an ignored Result.
lint_dir = out / "lint-config"
write(lint_dir / "Cargo.toml", '[package]\nname="api-lint-check"\nversion="0.0.0"\nedition="2024"\n[workspace]\n' + block("api-must-use", "Clippy Lints", "toml"))
write(lint_dir / "src/main.rs", 'fn main(){std::fs::read("absent-fixture");}')
run("cargo-lint-result", ["cargo", "+"+args.toolchain, "clippy", "--offline", "--manifest-path", str(lint_dir/"Cargo.toml")], expected=1, contains="unused `std::result::Result`")

# Actual proc-macro body, not a rewritten parsing approximation.
proc = out / "proc-macro"
write(proc / "Cargo.toml", '[package]\nname="api-derive-check"\nversion="0.0.0"\nedition="2024"\n[workspace]\n[lib]\nproc-macro=true\n[dependencies]\nsyn="=2.0.119"\nquote="1"\nproc-macro2="1"\n')
write(proc / "src/lib.rs", block("macro-proc-error-spans", "Good"))
write(proc / "tests/consumer.rs", r'''
trait MyTrait { fn first_field_name()->&'static str; }
#[derive(api_derive_check::MyTrait)] struct Named<T: Copy> { value:T }
#[test] fn named_generic_struct_derives() {assert_eq!(Named::<u8>::first_field_name(),"value");}
''')
run("proc-consumer", ["cargo", "+"+args.toolchain, "test", "--offline", "--manifest-path", str(proc/"Cargo.toml"), "--test", "consumer"])
for shape, source, diagnostic in [
    ("tuple", "struct Tuple(u8);", "MyTrait requires named fields"),
    ("empty", "struct Empty;", "MyTrait requires at least one field"),
    ("enum", "enum Enum {A}", "MyTrait can only be derived on structs, not enums"),
]:
    write(proc / ("tests/"+shape+".rs"), '#[derive(api_derive_check::MyTrait)]\n'+source)
    run("proc-reject-"+shape, ["cargo", "+"+args.toolchain, "check", "--offline", "--manifest-path", str(proc/"Cargo.toml"), "--test", shape], expected=1, contains=diagnostic)

print(f"All {len(results)} commands matched their expected outcomes.")
