#!/usr/bin/env python3
"""Compile/run selected *current Markdown* examples, including release boundaries.

No repository snippet with a known UB trigger is run. SIMD uses an explicitly
selected installed nightly; no compiler is installed by this script.
"""
from pathlib import Path
import argparse, json, os, re, subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--toolchain', default='stable')
parser.add_argument('--nightly')
parser.add_argument('--output', type=Path, default=HERE / 'target' / 'review' / 'logs')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
generated = HERE / 'target' / 'review'
generated.mkdir(parents=True, exist_ok=True)

def block(rule, needle, hidden=True):
    text = (ROOT / 'rules' / (rule + '.md')).read_text(encoding='utf-8')
    blocks = re.findall(r'^```rust[^\n]*\n(.*?)^```', text, re.M | re.S)
    selected = [b for b in blocks if needle in b]
    if len(selected) != 1:
        raise ValueError(f'{rule}: expected one block containing {needle!r}, got {len(selected)}')
    lines = []
    for line in selected[0].splitlines():
        if line.startswith('# '):
            if not hidden: continue
            line = line[2:]
        lines.append(line)
    return '\n'.join(lines)

modules=[]
def module(name, code, tests=''):
    modules.append(f'mod {name} {{\n{code}\n{tests}\n}}')

module('safe_slice', block('unsafe-minimize-scope','fn sum_at(values:'), r'''
#[test] fn values_and_boundaries() {
    assert_eq!(sum_at(&[10, 20], 1), 21);
    assert!(std::panic::catch_unwind(|| sum_at(&[], 0)).is_err());
}
''')
module('matrix', block('opt-bounds-check','fn matrix_multiply'), r'''
#[test] fn multiplication_and_empty() {
    let mut out = [0.; 4];
    matrix_multiply(&[1.,2.,3.,4.], &[5.,6.,7.,8.], &mut out, 2);
    assert_eq!(out, [19.,22.,43.,50.]);
    matrix_multiply(&[], &[], &mut [], 0);
}
#[test] fn overflow_is_rejected_before_access_even_in_release() {
    let n = 1usize << (usize::BITS / 2);
    assert!(std::panic::catch_unwind(|| matrix_multiply(&[], &[], &mut [], n)).is_err());
    assert!(std::panic::catch_unwind(|| matrix_multiply(&[], &[], &mut [], 1)).is_err());
}
''')
module('ffi_slices', block('unsafe-extern-block','fn copy_bytes(dst: &mut'), r'''
#[test] fn copy_and_empty() {
    let mut out=[0; 3]; copy_bytes(&mut out, &[1,2,3]);
    assert_eq!(out,[1,2,3]); copy_bytes(&mut [], &[]);
    assert!(std::panic::catch_unwind(|| copy_bytes(&mut [0; 1], &[1,2])).is_err());
}
''')
module('drop_order', block('mem-drop-order','fn process()',hidden=False), r'''
use std::cell::{Cell, RefCell};
thread_local! {
    static EVENTS: RefCell<Vec<&'static str>> = RefCell::new(Vec::new());
    static HELD: Cell<bool> = Cell::new(false);
    static FAIL: Cell<bool> = Cell::new(false);
}
fn event(s:&'static str) { EVENTS.with(|e| e.borrow_mut().push(s)); }
struct Connection; struct Guard; struct Transaction;
fn open_connection()->Connection {event("open"); Connection}
fn acquire_lock()->Guard {HELD.with(|h| h.set(true));event("lock");Guard}
fn begin_transaction()->Transaction {HELD.with(|h| assert!(h.get()));event("begin");Transaction}
fn do_work(_: &Transaction) {event("work");FAIL.with(|f| assert!(!f.get(),"fixture panic"));}
impl Transaction {fn commit(self){HELD.with(|h|assert!(h.get()));event("commit");}}
impl Drop for Transaction {fn drop(&mut self){HELD.with(|h|assert!(h.get()));event("transaction drop");}}
impl Drop for Guard {fn drop(&mut self){HELD.with(|h|h.set(false));event("unlock");}}
impl Drop for Connection {fn drop(&mut self){event("close");}}
#[test] fn commit_holds_lock() {
    EVENTS.with(|e|e.borrow_mut().clear()); FAIL.with(|f|f.set(false)); process();
    EVENTS.with(|e|assert_eq!(*e.borrow(),["open","lock","begin","work","commit","transaction drop","unlock","close"]));
}
#[test] fn unwind_drops_transaction_before_guard() {
    EVENTS.with(|e|e.borrow_mut().clear());FAIL.with(|f|f.set(true));
    assert!(std::panic::catch_unwind(process).is_err());FAIL.with(|f|f.set(false));
    EVENTS.with(|e|assert_eq!(*e.borrow(),["open","lock","begin","work","transaction drop","unlock","close"]));
}
''')
module('arena_nodes', block('mem-arena-allocator',"fn parse<'a>(input: &str, arena:"), r'''
#[test] fn response_owns_its_data() {assert_eq!(handle_request("a  b c"),"a b c");}
''')
module('scratch', block('mem-arena-allocator','fn with_scratch<T>'), r'''
#[test] fn repeat_and_unwind() {
    assert_eq!(process_batch(&[1,2,3]),[2,4,6]);
    assert_eq!(process_batch(&[u64::MAX]),[u64::MAX]);
    assert!(std::panic::catch_unwind(|| with_scratch(|a| {
        a.alloc_slice_copy(&[1u8; 8192]); panic!("fixture panic")
    })).is_err());
    assert_eq!(process_batch(&[4]),[8]);
}
#[test] fn explicit_non_reentrant_contract_recovers_after_unwind() {
    assert!(std::panic::catch_unwind(|| with_scratch(|_| with_scratch(|_| ()))).is_err());
    assert_eq!(process_batch(&[5]),[10]);
}
#[test] fn reset_releases_extra_chunks_on_return_and_unwind() {
    let allocated = std::cell::Cell::new(0);
    let grow = |arena: &Bump| {
        for _ in 0..64 { arena.alloc_slice_copy(&[7u8; 8192]); }
        allocated.set(arena.allocated_bytes());
    };
    with_scratch(grow);
    SCRATCH.with(|s| assert!(s.borrow().allocated_bytes() < allocated.get()));
    // Start the unwind case from a fresh arena so it must allocate extra chunks
    // even if the previous reset retained a large chunk for reuse.
    SCRATCH.with(|s| *s.borrow_mut() = Bump::new());
    assert!(std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        with_scratch(|arena| { grow(arena); panic!("fixture panic"); });
    })).is_err());
    SCRATCH.with(|s| assert!(s.borrow().allocated_bytes() < allocated.get()));
}
''')
module('arena_box', '#[test] fn owned_resource_drops() {\n'+block('mem-arena-allocator','let text = BumpBox::new_in')+'\n'+r'''
let count=std::cell::Cell::new(0);
struct Tracked<'a>(&'a std::cell::Cell<u32>);
impl Drop for Tracked<'_> {fn drop(&mut self){self.0.set(self.0.get()+1);}}
{let _resource=BumpBox::new_in(Tracked(&count), &arena);}
assert_eq!(count.get(),1);
}''')
module('arena_collections',block('mem-arena-allocator',"fn process<'a>(arena:"),r'''
#[test] fn owned_wrappers() {
    let arena=Bump::new();let result=process(&arena,"a b");
    assert_eq!(result[0].as_str(),"a_processed");
}
''')
module('layout','#[test] fn c_layout_on_documented_target() {\n'+block('mem-smaller-integers','struct Wasteful')+'\n}')
module('thin','#[test] #[cfg(target_pointer_width="64")] fn documented_layout() {\n'+block('mem-thinvec','size_of::<Option<Vec<u8>>>')+'\n}')
module('strings',r'''
#[test] #[cfg(target_pointer_width="64")] fn boundaries() {
    use compact_str::CompactString;
    use smartstring::{SmartString, LazyCompact};
    assert_eq!(std::mem::size_of::<SmartString<LazyCompact>>(),24);
    assert!(!CompactString::new("x".repeat(24)).is_heap_allocated());
    assert!(CompactString::new("x".repeat(25)).is_heap_allocated());
    let a:SmartString<LazyCompact>="x".repeat(23).into();
    let b:SmartString<LazyCompact>="x".repeat(24).into();
    assert!(a.is_inline());assert!(!b.is_inline());
}
''')
for rule in ['num-overflow-explicit','num-cast-try-from','num-saturating-clamp','num-float-compare','num-nonzero']:
    module(rule.replace('-','_'),block(rule,'#[cfg(test)]'))

(generated/'lib.rs').write_text('#![allow(dead_code,unused_imports,unused_variables)]\n'+'\n\n'.join(modules)+'\n',encoding='utf-8')
results=[]
env=os.environ.copy()
env['CARGO_TARGET_DIR']=str(args.output.resolve()/'cargo-target')
def run(name,command):
    p=subprocess.run(command,cwd=HERE,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding='utf-8',errors='replace')
    (args.output/(name+'.txt')).write_text('$ '+' '.join(map(str,command))+'\nexit='+str(p.returncode)+'\n'+p.stdout,encoding='utf-8')
    results.append({'name':name,'command':list(map(str,command)),'exit_code':p.returncode})
    print(f'{name}: exit={p.returncode}',flush=True)
    if p.returncode: raise RuntimeError(f'{name} failed; see {args.output/(name+".txt")}')
run('rustc-version',['rustc','+'+args.toolchain,'--version','--verbose'])
lock=['--locked'] if (HERE/'Cargo.lock').exists() else []
for profile in ['debug','release']:
    run('core-'+profile,['cargo','+'+args.toolchain,'test','--manifest-path',str(HERE/'Cargo.toml'),'--offline',*lock,*(['--release'] if profile=='release' else [])])
if args.nightly:
    simd=block('opt-simd-portable','fn dot_product(a:')+r'''
#[test] fn independent_offsets_and_all_remainders() {
    // Small integer-valued floats make every product/sum exact at these sizes,
    // while differing values expose incorrect pairing of logical indices.
    let a: [f32; 64] = std::array::from_fn(|i| (i % 13) as f32 - 6.0);
    let b: [f32; 64] = std::array::from_fn(|i| ((i * 7) % 19) as f32 - 9.0);
    for start_a in 0..8 {for start_b in 0..8 {for len in 0..40 {
        let left=&a[start_a..start_a+len];let right=&b[start_b..start_b+len];
        let scalar: f32=left.iter().zip(right).map(|(x,y)|x*y).sum();
        assert_eq!(dot_product(left,right),scalar,"offsets={start_a},{start_b}; len={len}");
        assert_eq!(sum_simd(left),left.iter().sum::<f32>());
    }}}
}
'''
    (generated/'simd.rs').write_text(simd,encoding='utf-8')
    binary=generated/('simd.exe' if os.name=='nt' else 'simd')
    run('nightly-version',['rustc','+'+args.nightly,'--version'])
    run('simd-build',['rustc','+'+args.nightly,'--edition=2024','--test',str(generated/'simd.rs'),'-o',str(binary)])
    run('simd-run',[str(binary)])
(args.output/'results.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
print('Core regressions passed; '+('SIMD tested.' if args.nightly else 'SIMD not tested (pass --nightly to select an installed toolchain).'))
