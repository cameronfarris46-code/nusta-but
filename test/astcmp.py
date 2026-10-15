#!/usr/bin/env python3
"""AST and symbol-table comparison for CS 4318 Project Phase 2.

The handout is explicit that an exactly-matching AST is NOT the standard:

    "Some internal nodes may be equivalent, so your AST may have more or fewer
     nodes than the expected output. Your output should be equivalent to the
     expected output when ran with the sample input."

    "Don't worry about the indices used in the symbol table, as these may vary
     depending on the hashing and mapping strategy you use."

So a raw diff would fail submissions the assignment permits. This module
normalises both the expected output and the student's output the same way and
compares the normal forms. It ALSO reports whether the raw text matched, so
near-misses can be eyeballed rather than silently passed.

Two normalisations, and only two:

  1. CHAIN COLLAPSE. A node whose grammar production is a pure chain (a single
     nonterminal on the right-hand side) carries no information of its own. In
     the mC grammar those are expression -> addExpr -> term -> factor, plus
     statement, decl and assignStmt in its one-child form. A node of one of
     those kinds that has exactly one child is replaced by that child.

     This is what makes expression(addExpr(term(factor(integer,4)))) and a bare
     integer,4 compare equal, which is what the handout means by equivalent.

  2. LIST FLATTENING. declList, statementList, argList and formalDeclList are
     lists. The template's own example code for declList builds them nested
     (declList(declList(decl), decl)) while the expected output prints them
     flat. Both describe the same sequence, so a list node directly containing
     a node of its own kind is spliced.

Nothing else is normalised. funBody, compoundStmt, funcTypeName, var and the
rest must be present, because each one carries real structure (the braces, the
grouping of a function's type and name, an array subscript).

Symbol table: compared as a SET of (type, scope, id, suffix). Indices and
therefore print order are dropped, per the handout.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Set, Tuple

# Productions of the mC grammar whose right-hand side is a single nonterminal.
CHAIN = {'expression', 'addExpr', 'term', 'factor', 'statement', 'decl',
         'assignStmt', 'localDeclList'}

# Nodes that represent a sequence.
LISTS = {'declList', 'statementList', 'argList', 'formalDeclList'}

SYMTAB_HEADER = re.compile(r'^\s*SYMBOL\s+TABLE\s*:?\s*$', re.I)
# e.g. "678: int main:i"  /  "242: void :main()"  /  "506: int :arr[]"
SYMTAB_ROW = re.compile(r'^\s*(\d+)\s*:\s*(\S+)\s+([^:]*):(.*?)\s*$')
# Lines the parser may emit before the tree, which are not part of the tree.
NOISE = re.compile(r'^\s*(error|warning)\s*:', re.I)


@dataclass
class Node:
    kind: str
    value: Optional[str] = None
    children: List['Node'] = field(default_factory=list)

    def label(self) -> str:
        return self.kind if self.value is None else f'{self.kind},{self.value}'

    def render(self, depth: int = 0) -> List[str]:
        out = ['  ' * depth + self.label()]
        for c in self.children:
            out += c.render(depth + 1)
        return out

    def size(self) -> int:
        return 1 + sum(c.size() for c in self.children)


# --------------------------------------------------------------------------
# parsing the program's stdout


def split_output(text: str) -> Tuple[List[str], List[str], List[str]]:
    """Return (ast_lines, symtab_lines, diagnostic_lines).

    Diagnostics are the error:/warning: lines, which may be interleaved
    anywhere because they are printed as the parse runs.
    """
    ast: List[str] = []
    sym: List[str] = []
    diag: List[str] = []
    in_sym = False
    for raw in text.splitlines():
        if not raw.strip():
            continue
        if NOISE.match(raw):
            diag.append(raw.strip())
            continue
        if SYMTAB_HEADER.match(raw):
            in_sym = True
            continue
        (sym if in_sym else ast).append(raw.rstrip())
    return ast, sym, diag


def parse_tree(lines: Sequence[str]) -> Optional[Node]:
    """Build a tree from indented lines. Indentation is taken as-is, so a
    student using 4 spaces per level still parses correctly: only the relative
    ordering of indents matters."""
    root: Optional[Node] = None
    stack: List[Tuple[int, Node]] = []
    for raw in lines:
        indent = len(raw) - len(raw.lstrip())
        body = raw.strip()
        if not body:
            continue
        kind, _, value = body.partition(',')
        node = Node(kind.strip(), value.strip() if _ else None)
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not stack:
            if root is None:
                root = node
            else:
                # A second node at column 0: wrap so nothing is silently lost.
                if root.kind != '<multiple roots>':
                    root = Node('<multiple roots>', None, [root])
                root.children.append(node)
        else:
            stack[-1][1].children.append(node)
        stack.append((indent, node))
    return root


# --------------------------------------------------------------------------
# normalisation


def normalise(n: Optional[Node]) -> Optional[Node]:
    if n is None:
        return None
    kids = [normalise(c) for c in n.children]
    kids = [k for k in kids if k is not None]

    if n.kind in LISTS:
        flat: List[Node] = []
        for k in kids:
            if k.kind == n.kind:
                flat.extend(k.children)
            else:
                flat.append(k)
        kids = flat

    if n.kind in CHAIN and len(kids) == 1 and n.value is None:
        return kids[0]

    return Node(n.kind, n.value, kids)


def trees_equal(a: Optional[Node], b: Optional[Node]) -> bool:
    if a is None or b is None:
        return a is b
    if a.kind != b.kind or a.value != b.value:
        return False
    if len(a.children) != len(b.children):
        return False
    return all(trees_equal(x, y) for x, y in zip(a.children, b.children))


def first_difference(a: Optional[Node], b: Optional[Node],
                     path: str = '') -> Optional[str]:
    """A human-readable location for the first place two trees diverge."""
    if a is None and b is None:
        return None
    if a is None:
        return f'{path or "root"}: nothing produced, expected {b.label()}'
    if b is None:
        return f'{path or "root"}: produced {a.label()}, expected nothing'
    here = f'{path}/{a.kind}' if path else a.kind
    if a.kind != b.kind or a.value != b.value:
        return f'{path or "root"}: got {a.label()}, expected {b.label()}'
    if len(a.children) != len(b.children):
        return (f'{here}: {len(a.children)} child(ren), expected '
                f'{len(b.children)} '
                f'(got [{", ".join(c.label() for c in a.children)}], '
                f'expected [{", ".join(c.label() for c in b.children)}])')
    for i, (x, y) in enumerate(zip(a.children, b.children)):
        d = first_difference(x, y, f'{here}[{i}]')
        if d:
            return d
    return None


# --------------------------------------------------------------------------
# symbol table


def parse_symtab(lines: Sequence[str]) -> Set[Tuple[str, str, str]]:
    """(data_type, scope, id-with-suffix). The index is deliberately dropped."""
    out: Set[Tuple[str, str, str]] = set()
    for raw in lines:
        m = SYMTAB_ROW.match(raw)
        if not m:
            continue
        _idx, dtype, scope, rest = m.groups()
        out.add((dtype.strip(), scope.strip(), rest.strip()))
    return out


# --------------------------------------------------------------------------
# the public entry point


@dataclass
class Comparison:
    ast_ok: bool
    sym_ok: bool
    exact: bool
    ast_note: str = ''
    sym_note: str = ''
    got_nodes: int = 0
    want_nodes: int = 0

    @property
    def ok(self) -> bool:
        return self.ast_ok and self.sym_ok


def compare(actual_text: str, expected_text: str) -> Comparison:
    a_ast, a_sym, _a_diag = split_output(actual_text)
    e_ast, e_sym, _e_diag = split_output(expected_text)

    ta = normalise(parse_tree(a_ast))
    te = normalise(parse_tree(e_ast))

    ast_ok = trees_equal(ta, te)
    ast_note = '' if ast_ok else (first_difference(ta, te) or 'trees differ')

    sa, se = parse_symtab(a_sym), parse_symtab(e_sym)
    sym_ok = sa == se
    if sym_ok:
        sym_note = ''
    elif not a_sym:
        sym_note = ('no symbol table printed (the expected output has '
                    f'{len(se)} entr{"y" if len(se) == 1 else "ies"})')
    else:
        missing = sorted(f'{d} {s}:{i}' for d, s, i in se - sa)
        extra = sorted(f'{d} {s}:{i}' for d, s, i in sa - se)
        bits = []
        if missing:
            bits.append('missing ' + '; '.join(missing))
        if extra:
            bits.append('unexpected ' + '; '.join(extra))
        sym_note = ', '.join(bits)

    exact = ([l.rstrip() for l in actual_text.strip().splitlines()]
             == [l.rstrip() for l in expected_text.strip().splitlines()])

    return Comparison(ast_ok=ast_ok, sym_ok=sym_ok, exact=exact,
                      ast_note=ast_note, sym_note=sym_note,
                      got_nodes=ta.size() if ta else 0,
                      want_nodes=te.size() if te else 0)
