"""Verify corrected guidance by extracting its current Markdown examples.

Usage: python verify.py --output <owned-directory-outside-the-repository>
The fixtures, Cargo build output and logs are written only under --output.
Uses installed toolchains and cached dependencies; does not fetch or install.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tomllib

REPO = Path(__file__).resolve().parents[3]
RULES = REPO / 'rules'
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--case', action='append', help='Run only selected named cases; repeat as needed')
args = parser.parse_args()
OUT = args.output.resolve()
if OUT == REPO or REPO in OUT.parents:
    raise SystemExit('--output must be outside the repository')
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'logs').mkdir(exist_ok=True)
RESULTS: list[dict] = []
COMMANDS: list[dict] = []
ENV = os.environ.copy()
ENV['CARGO_TARGET_DIR'] = str(OUT / 'target')
(OUT / 'tmp').mkdir(exist_ok=True)
ENV['TEMP'] = ENV['TMP'] = str(OUT / 'tmp')
ENV['CARGO_INCREMENTAL'] = '0'


def text(rule: str) -> str:
    return (RULES / f'{rule}.md').read_text(encoding='utf-8-sig')


def section(rule: str, heading: str) -> str:
    return text(rule).split(heading, 1)[1].split('\n## ', 1)[0]


def blocks(source: str, language: str = 'rust') -> list[str]:
    return re.findall(r'^```' + re.escape(language) + r'\s*\n(.*?)^```\s*$', source, re.M | re.S)


def block(rule: str, heading: str, language: str = 'rust', index: int = 0) -> str:
    return blocks(section(rule, heading), language)[index]


def write(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding='utf-8')


def run(label: str, command: list[str], cwd: Path, *, env=None, expected=0, diagnostic=None) -> str:
    completed = subprocess.run(command, cwd=cwd, env=env or ENV, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               encoding='utf-8', errors='replace', timeout=180)
    output = completed.stdout
    log = OUT / 'logs' / f'{label}.txt'
    write(log, '$ ' + ' '.join(command) + '\n' + output + f'\nexit={completed.returncode}\n')
    ok = completed.returncode == expected and (diagnostic is None or diagnostic in output)
    COMMANDS.append({'name': label, 'command': command, 'cwd': str(cwd), 'exit': completed.returncode,
                     'expected_exit': expected, 'diagnostic': diagnostic, 'pass': ok, 'log': str(log)})
    if not ok:
        raise AssertionError(f'{label}: unexpected result, see {log}')
    return output


def case(name, ids, action):
    if args.case and name not in args.case:
        return
    try:
        action()
        RESULTS.append({'name': name, 'findings': ids, 'status': 'pass'})
        print(name + ': pass', flush=True)
    except Exception as error:
        RESULTS.append({'name': name, 'findings': ids, 'status': 'fail', 'error': str(error)})
        print(name + ': FAIL: ' + str(error), flush=True)


def package(name: str, lib: str = '', extra: str = '', manifest: str | None = None) -> Path:
    path = OUT / 'fixtures' / name
    if manifest is None:
        manifest = '[package]\nname="my-crate"\nversion="0.1.0"\nedition="2024"\n' + extra
    # These packages are intentionally independent fixtures.
    write(path / 'Cargo.toml', manifest)
    write(path / 'src/lib.rs', lib)
    return path


def rustc(name: str, source: str, *, test=False, release=False, expected=0, diagnostic=None, execute=False):
    path = OUT / 'fixtures' / name
    write(path / 'main.rs', source)
    exe = path / ('probe.exe' if os.name == 'nt' else 'probe')
    command = ['rustc', '+stable', '--edition=2024', str(path / 'main.rs'), '-o', str(exe)]
    if test:
        command.append('--test')
    if release:
        command += ['-C', 'opt-level=3', '-C', 'debug-assertions=off', '-C', 'overflow-checks=off']
    run(name + '-compile', command, path, expected=expected, diagnostic=diagnostic)
    if execute:
        run(name + '-run', [str(exe)], path)


def wrappers():
    source = block('lint-unsafe-doc', '## Good')
    source += r'''
#[cfg(test)] mod tests {
    use super::*;
    #[test] fn valid_raw_borrow() {
        let bytes = [1, 2, 3];
        // SAFETY: this immutable live array satisfies the documented contract.
        assert_eq!(unsafe { read_data(bytes.as_ptr(), bytes.len()) }, &bytes);
    }
    #[test] fn safe_get_checks_bounds() {
        let buffer = Buffer { data: vec![7] };
        assert_eq!(buffer.get(0), &7);
        assert!(std::panic::catch_unwind(|| buffer.get(1)).is_err());
        let empty = Buffer { data: vec![] };
        assert!(std::panic::catch_unwind(|| empty.get(0)).is_err());
    }
}
'''
    rustc('wrappers-debug', source, test=True, execute=True)
    rustc('wrappers-release', source, test=True, release=True, execute=True)
    unsafe_call = source.split('#[cfg(test)]')[0] + '\nfn main() { let bytes=[1]; let _ = read_data(bytes.as_ptr(),1); }'
    rustc('wrappers-safe-caller-rejected', unsafe_call, expected=1, diagnostic='E0133')


def divide_and_get():
    source = block('doc-panics-section', '## Good')
    divide = source[source.index('/// Divides two numbers.'):]
    divide += r'''
#[test] fn division_boundaries() {
    assert_eq!(checked_divide(10,2),Some(5));
    assert_eq!(checked_divide(1,0),None);
    assert_eq!(checked_divide(i32::MIN,-1),None);
    assert!(std::panic::catch_unwind(||divide(i32::MIN,-1)).is_err());
}
'''
    rustc('divide-release', divide, test=True, release=True, execute=True)
    example = re.search(r'^/// ```\n(.*?)^/// ```', source, re.M | re.S).group(1)
    example = re.sub(r'^/// ?', '', example, flags=re.M)
    rustc('vec-get', 'fn main() {\n' + example + '\n}', execute=True)


def should_panic():
    source = block('test-should-panic', '## Using Fallible Setup')
    helpers = 'fn setup_test_data()->Result<Vec<u8>, &\'static str> {Ok(vec![])}\nfn process_invalid(_: &[u8]) {panic!("invalid data")}\n'
    rustc('should-panic', helpers + source, test=True, execute=True)


def conversions():
    source = block('name-into-ownership', '## Standard Library Examples')
    rustc('into-conversions', 'use std::{path::PathBuf,ffi::OsString};\nfn main(){\n'+source+'\n}', execute=True)
    source = block('name-to-expensive', '## Standard Library Examples')
    rustc('to-conversions', 'use std::path::Path;\nfn main(){let slice=&[1u8,2];let path=Path::new("a");let string=String::new();\n'+source+'\n}', execute=True)
    paths = re.findall(r'^(std::\S+)\s*//', block('name-acronym-word', '## Standard Library Examples'), re.M)
    rustc('std-names', '\n'.join('use '+p+';' for p in paths)+'\nfn main(){}')
    source = block('lint-warn-perf', '## Allocation Patterns')
    empty = source.split('// Pre-allocation')[0]
    rustc('empty-vec', 'fn main(){\n'+empty+'\nassert_eq!(vec.capacity(),0);}', execute=True)


def serde_and_tokio_mockall():
    serde = block('name-lifetime-short', '## Serde Convention')
    tokio = block('test-tokio-async', '## Runtime Configuration')
    tokio = tokio.replace('// Each test gets its own current-thread runtime.',
        'assert_eq!(tokio::runtime::Handle::current().runtime_flavor(),tokio::runtime::RuntimeFlavor::CurrentThread);')
    returns = block('test-mockall-mocking', '## Return Values')
    lib = '#![allow(dead_code,unused_imports,unused_variables)]\n'+serde+r'''
#[test] fn borrowed_request() {
    let request:Request<'_>=serde_json::from_str(r#"{"name":"alice","tags":["rust"]}"#).unwrap();
    assert_eq!(request.name,"alice"); assert_eq!(request.tags,["rust"]);
}
use std::time::Duration;
'''+tokio+r'''
use mockall::automock;
#[automock] trait Source {fn count(&self)->i32;fn double(&self,x:i32)->i32;fn next(&self)->i32;fn get_name(&self)->String;}
#[test] fn consecutive_mock_returns() {
let mut mock=MockSource::new();
'''+returns+r'''
assert_eq!([mock.next(),mock.next(),mock.next()],[1,2,3]);
}
'''
    # Extracted declarations also compile as the fixture's ordinary library.
    deps='[dependencies]\nserde={version="=1.0.228",features=["derive"]}\nserde_json="=1.0.145"\nmockall="=0.15.0"\ntokio={version="=1.52.3",features=["macros","rt-multi-thread","time","test-util"]}\n'
    path=package('dependencies',lib,deps)
    run('dependencies', ['cargo','+stable','test','--offline'],path)


def environment():
    good=block('test-fixture-raii','## Good')
    guard=good[good.index('// Custom RAII guard'):good.index('// Entry point')]
    main=r'''
fn main() {
    let key="RUST_SKILLS_CORRECTED_ENV_FIXTURE";
    // SAFETY: this helper process never starts another thread.
    unsafe {std::env::remove_var(key)};
    {let _guard=unsafe {EnvGuard::set(key,"temporary")};}
    assert!(std::env::var_os(key).is_none());
    #[cfg(windows)] let original={use std::os::windows::ffi::OsStringExt;std::ffi::OsString::from_wide(&[0xD800])};
    #[cfg(unix)] let original={use std::os::unix::ffi::OsStringExt;std::ffi::OsString::from_vec(vec![0xFF])};
    unsafe {std::env::set_var(key,&original)};
    {let _guard=unsafe {EnvGuard::set(key,"temporary")};}
    assert_eq!(std::env::var_os(key),Some(original));
    unsafe {std::env::remove_var(key)};
}
'''
    rustc('environment-subprocess',guard+main,execute=True)


def loom():
    source=section('test-loom-concurrency','## Good')
    manifest=blocks(source,'toml')[0]
    rust=blocks(source)
    path=package('loom',rust[0],manifest=manifest)
    write(path/'src/flag.rs',rust[1]);write(path/'tests/loom_flag.rs',rust[2])
    run('loom-ordinary',['cargo','+stable','test','--offline'],path)
    env=ENV.copy();env['RUSTFLAGS']='--cfg loom'
    run('loom-instrumented',['cargo','+stable','test','--offline','--test','loom_flag'],path,env=env)


def doctests():
    docs=[]
    for rule,heading,prefix in [
        ('doc-hidden-setup','## Pattern: `ignore` and `no_run`','///'),
        ('doc-link-types','## Common Patterns','///'),
        ('doc-module-inner','## Good','//!'),
        ('doc-question-mark','## Doctest Wrapper Pattern','///')]:
        # Extract the nested rustdoc blocks, including their actual hidden lines.
        outer='\n'.join(blocks(section(rule,heading)))
        nested=re.findall(r'^'+re.escape(prefix)+r' ```(?!ignore)([^\n]*)\n(.*?)^'+re.escape(prefix)+r' ```',outer,re.M|re.S)
        for flags,body in nested:
            lines=re.sub(r'^'+re.escape(prefix)+r' ?', '',body,flags=re.M)
            docs.append('//! ```'+flags+'\n'+'\n'.join('//! '+line for line in lines.splitlines())+'\n//! ```\n')
    lib=''.join(docs)+r'''
pub type Error=std::io::Error;
pub type ConfigError=std::io::Error;
pub struct Server;
impl Server {pub async fn bind(_: &str)->Result<Self,Error>{Ok(Self)} pub async fn run(self)->Result<(),Error>{Ok(())}}
pub struct Config; pub struct ConfigBuilder;
impl Config {pub fn builder()->ConfigBuilder{ConfigBuilder}}
impl ConfigBuilder {pub fn timeout(self,_:u64)->Self{self} pub fn build(self)->Result<Config,ConfigError>{Ok(Config)}}
pub struct User; impl User {pub fn example()->Self{Self}}
pub mod auth {
    pub trait Authenticator {fn generate_token(&self,user:&crate::User)->Result<String,crate::Error>;}
    pub struct JwtAuth;
    impl JwtAuth {pub fn new(_: &str)->Self{Self}}
    impl Authenticator for JwtAuth {fn generate_token(&self,_:&crate::User)->Result<String,crate::Error>{Ok(String::from("token"))}}
}
pub struct ParsedConfig{pub key:String}
pub fn parse_config(_: &str)->Result<ParsedConfig,Error>{Ok(ParsedConfig{key:"value".to_owned()})}
'''
    path=package('doctests',lib)
    run('doctests',['cargo','+stable','test','--offline','--doc'],path)


def lint_manifests():
    for index,heading in enumerate(['## Good','## Full Configuration']):
        table=block('lint-pedantic-selective',heading,'toml')
        path=package('pedantic-'+str(index),'//! Fixture.\n',table)
        run('pedantic-'+str(index),['cargo','+stable','clippy','--offline','--','-D','warnings'],path)
    source=blocks(text('lint-cargo-metadata'),'toml')[-1]
    # Last TOML block is the selective group override from the corrected rule.
    metadata='description="Fixture"\nlicense="MIT"\nrepository="https://example.invalid/repo"\nkeywords=["fixture"]\ncategories=["development-tools"]\n'
    path=package('cargo-lints','//! Fixture.\n',metadata+source)
    write(path/'README.md','# Lint fixture\n')
    run('cargo-lints',['cargo','+stable','clippy','--offline','--','-D','warnings'],path)
    path=package('suspicious','//! Fixture.\n',block('lint-warn-suspicious','## Configuration','toml'))
    run('suspicious',['cargo','+stable','clippy','--offline','--','-W','clippy::suspicious','-D','warnings'],path)
    layout=block('proj-mod-rs-dir','## Consistency Rule','toml')
    path=package('module-layout','mod user;\n',layout)
    write(path/'src/user/mod.rs','')
    run('module-layout',['cargo','+stable','clippy','--offline','--','-D','warnings'],path)


def workspace_lints():
    source=block('lint-workspace-lints','## Good','toml')
    root=source.split('# crate-a/Cargo.toml')[0]
    path=OUT/'fixtures/workspace-lints'
    write(path/'Cargo.toml','[workspace]\nresolver="3"\nmembers=["binary","test-utils"]\n'+root)
    overrides=block('lint-workspace-lints','## Per-Crate Overrides','toml')
    for name,part,attribute,body in [
        ('binary',overrides.split('# test-utils/Cargo.toml')[0],'clippy::unwrap_used','std::env::var("RUST_SKILLS_FIXTURE").unwrap();'),
        ('test-utils',overrides.split('# test-utils/Cargo.toml')[1],'clippy::print_stdout','println!("fixture");')]:
        write(path/name/'Cargo.toml',f'[package]\nname="{name}"\nversion="0.1.0"\nedition="2024"\n'+part)
        write(path/name/'src/lib.rs',f'#![allow({attribute})]\n//! Fixture.\n/// Exercises the local source exception.\npub fn exercise(){{{body}}}\n')
    run('workspace-lints',['cargo','+stable','clippy','--offline','--workspace','--','-D','warnings'],path)


def integration_and_visibility():
    source=block('test-integration-dir','## Organizing Many Tests')
    assert '// tests/api/main.rs' in source
    path=package('integration','')
    write(path/'tests/api/main.rs',source.split('// tests/api/auth.rs')[0])
    for name in ['auth','users','orders']:
        write(path/f'tests/api/{name}.rs',f'#[test] fn {name}_discovered(){{assert_eq!(2+2,4);}}')
    output=run('integration',['cargo','+stable','test','--offline','--test','api'],path)
    assert '3 passed' in output
    good=block('proj-pub-super-parent','## Good')
    rustc('visibility-parent','mod parser{\n'+good+'\n}\nfn main(){assert_eq!(parser::parse("a b"),["a","b"]);}',execute=True)
    rustc('visibility-codegen-rejected','mod parser{\n'+good+'\n}\nmod codegen {use crate::parser::shared::Token;} fn main(){}',expected=1,diagnostic='E0603')
    helpers=block('proj-pub-super-parent','## Pattern: Test Helpers')
    rustc('visibility-test-helpers','mod parser{\n'+helpers+'\n}',test=True,execute=True)
    rustc('explicit-private','mod my_module {fn private_helper()->i32{42}\n#[cfg(test)]mod tests {use crate::my_module::private_helper;#[test]fn check(){assert_eq!(private_helper(),42);}}}',test=True,execute=True)
    source=block('test-cfg-test-module','## Good')
    rustc('cfg-test-module',source,test=True,execute=True)
    # Make the documented #[test] placeholder deliberately invalid. It must
    # still be excluded from an ordinary release build without cfg(test).
    ungated=block('test-cfg-test-module','## Bad').split('// Tests in separate file')[0]
    ungated=ungated.replace('...', 'undefined_test_only_symbol();')
    rustc('cfg-test-ordinary-release',ungated+'\nfn main(){}',release=True)


def project_build():
    manifest=block('proj-msrv-declare','## Good','toml')
    path=package('msrv','',manifest=manifest)
    run('msrv-manifest',['cargo','+1.85.0','check','--offline'],path)
    manifest=block('proj-feature-additive','## Good','toml')
    lib=block('proj-feature-additive','## Good')+'\npub fn empty()->Vec<u8>{Vec::new()}\n'
    path=package('features',lib,manifest='[package]\nname="my-crate"\nversion="0.1.0"\nedition="2024"\n'+manifest)
    run('features-default',['cargo','+stable','check','--offline'],path)
    run('features-no-default',['cargo','+stable','check','--offline','--no-default-features'],path)
    build=block('proj-build-rs-minimal','## Good')
    path=package('build-script','#[test] fn capability(){assert!(cfg!(has_btree_map));}\n',block('proj-build-rs-minimal','## Good','toml'))
    write(path/'build.rs',build);write(path/'src/generated.rs','')
    run('build-script',['cargo','+stable','test','--offline'],path)
    run('build-script-cached',['cargo','+stable','test','--offline','--verbose'],path)
    manifest=block('doc-crate-readme','## Bad','toml')
    path=package('readme','',manifest=manifest)
    write(path/'README.md','# Fixture\n')
    output=run('readme',['cargo','+stable','metadata','--offline','--no-deps','--format-version','1'],path)
    assert json.loads(output)['packages'][0]['readme']=='README.md'


def rustfmt():
    config=block('lint-rustfmt-check','## Configuration','toml')
    parsed=tomllib.loads(config)
    assert not {'imports_granularity','group_imports','ignore'} & parsed.keys()
    path=OUT/'fixtures/rustfmt'
    write(path/'rustfmt.toml',config);write(path/'main.rs','fn main() { println!("fixture"); }\n')
    run('rustfmt-apply',['rustfmt','+stable','--config-path',str(path/'rustfmt.toml'),str(path/'main.rs')],path)
    output=run('rustfmt-check',['rustfmt','+stable','--check','--config-path',str(path/'rustfmt.toml'),str(path/'main.rs')],path)
    assert 'Warning' not in output and 'nightly' not in output


case('wrappers',['F01','F32'],wrappers)
case('division-and-doctest',['F39','F86'],divide_and_get)
case('should-panic',['F42'],should_panic)
case('conversions',['F79','F84','F85'],conversions)
case('dependency-examples',['F17','F45','F73'],serde_and_tokio_mockall)
case('environment',['F72'],environment)
case('loom-configurations',['F18','F19'],loom)
case('doctests',['F76','F77'],doctests)
case('lint-manifests',['F46','F47','F74'],lint_manifests)
case('workspace-inheritance',['F41'],workspace_lints)
case('test-discovery-and-privacy',['F21','F43','F80','F81'],integration_and_visibility)
case('project-build',['F14','F75','F78','F82','F83'],project_build)
case('stable-rustfmt',['F71'],rustfmt)
report={'repo':str(REPO),'cases':RESULTS,'commands':COMMANDS,
        'limitations':['No full Rust 1.96 toolchain matrix; MSRV manifest checked on installed 1.85.0.',
            'Mockall behavior executed on cached 0.15.0, not documented 0.12 or baseline lock 0.13.1.',
            'F44 Insta CI correction checked against primary documentation, not an installed Insta runtime.',
            'Some domain scaffolding is supplied solely to compile the exact extracted documentation operations.']}
write(OUT/'results.json',json.dumps(report,indent=2))
raise SystemExit(any(case['status']!='pass' for case in RESULTS))
