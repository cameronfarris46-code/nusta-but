#!/usr/bin/env python3
"""Run the sample test cases against your parser.

    make test

or directly:

    python3 test/run_tests.py            # build first with `make`
    python3 test/run_tests.py -v         # show the full diff for each failure

For every file in test/cases/*.mC it runs obj/mcc on it and compares the output
with test/exp/<name>.exp.

Two things are deliberately NOT required to match:

  * SYMBOL TABLE indices. The handout says these vary with your hashing and
    probing strategy, so entries are compared as a set and the numbers on the
    left are ignored.

  * Pass-through AST nodes. The handout says your AST may have more or fewer
    nodes than the expected output as long as it is equivalent. A node for a
    chain production (expression -> addExpr -> term -> factor, and statement,
    decl, assignStmt) that has exactly one child is collapsed into that child
    on BOTH sides before comparing, and nested list nodes are flattened.

So a run can report PASS while `diff` against the .exp file still shows
differences. That is expected and is how the project is graded.
"""
import argparse
import difflib
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from astcmp import compare                                      # noqa: E402

CASES = os.path.join(HERE, 'cases')
EXPS = os.path.join(HERE, 'exp')
TIMEOUT = 10


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-v', '--verbose', action='store_true',
                    help='print the full got/expected diff for each failure')
    ap.add_argument('--program', default=os.path.join(ROOT, 'obj', 'mcc'))
    a = ap.parse_args()

    if not os.access(a.program, os.X_OK):
        print(f'{a.program} not found or not executable. Run `make` first.')
        return 2

    names = sorted(f[:-3] for f in os.listdir(CASES) if f.endswith('.mC'))
    npass = 0
    timeouts = 0
    for n in names:
        case = os.path.join(CASES, n + '.mC')
        exp = os.path.join(EXPS, n + '.exp')
        if timeouts >= 3:
            print(f'  SKIP     {n}  (the first three cases all timed out)')
            continue
        try:
            p = subprocess.run([a.program, case], capture_output=True,
                               text=True, timeout=TIMEOUT, errors='replace')
            got = (p.stdout or '') + (p.stderr or '')
            timeouts = 0
        except subprocess.TimeoutExpired:
            timeouts += 1
            print(f'  TIMEOUT  {n}  (no output after {TIMEOUT}s)')
            continue

        with open(exp, encoding='utf-8') as fh:
            want = fh.read()
        c = compare(got, want)

        if c.ok:
            npass += 1
            tag = 'PASS' if c.exact else 'PASS*'
            note = '' if c.exact else '  (equivalent, not byte-identical)'
            print(f'  {tag:<6} {n}{note}')
        else:
            print(f'  FAIL   {n}')
            if c.ast_note:
                print(f'         AST: {c.ast_note}')
            if c.sym_note:
                print(f'         symbol table: {c.sym_note}')
            if a.verbose:
                d = difflib.unified_diff(want.splitlines(), got.splitlines(),
                                         'expected', 'yours', lineterm='')
                for line in d:
                    print('         ' + line)

    print()
    print(f'{npass}/{len(names)} passed')
    if timeouts >= 3:
        print('Your program did not terminate. Look for a loop in printAst '
              'that never reaches a leaf, or a cycle in the tree.')
    if npass and npass < len(names):
        print('Re-run with -v to see the full diff for the failures.')
    return 0 if npass == len(names) else 1


if __name__ == '__main__':
    sys.exit(main())
