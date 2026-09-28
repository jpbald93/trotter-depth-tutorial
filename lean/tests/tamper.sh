#!/bin/bash
# Tampering tests for gate.sh. Each test copies the Lean project to a scratch directory,
# plants one defect, runs the gate there, and expects it to FAIL at the stated stage.
# The real repository is never modified. Tests run one at a time (Lean builds are memory-heavy).
# Usage: bash tests/tamper.sh            (all tests)
#        bash tests/tamper.sh sorry wrap (a subset)
#        TAMPER_PLANT_ONLY=1 bash tests/tamper.sh   (plant defects only, no Lean, keep scratch dir)
# Exit status 0 iff every selected test is rejected with the expected message.
set -u
export PATH="$HOME/.elan/bin:$PATH"
SRC="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/trotterdepth_tamper_XXXX")"
PLANT_ONLY="${TAMPER_PLANT_ONLY:-0}"
NS=TrotterOpt
C='TrotterOpt/Basic.lean'                       # file that receives the planted defects
E='^#print axioms hoeffding_shots$'                       # regex for the anchor line the defects are inserted before
EL='#print axioms hoeffding_shots'                     # the anchor line itself
FIRST='key_poly'               # first REQUIRED name (spoofed by evalfake)
TGT='key_poly'                   # theorem attacked by falsehyp / wrap (short name)
TGTNS=''               # its namespace ('' = root)
FH_OLD='    ((k : ℝ) + 1) * t ^ k ≤ 1 + (k : ℝ) * t ^ (k + 1) := by'
FH_NEW='    ((k : ℝ) + 1) * t ^ k ≤ (k : ℝ) * t ^ (k + 1) := by'
if [ "$PLANT_ONLY" != 1 ]; then
  [ -e "$SRC/.lake/packages/mathlib" ] || (cd "$SRC" && lake exe cache get) || { echo "cannot fetch Mathlib"; exit 1; }
  PK="$(cd "$SRC/.lake/packages" && pwd -P)"
fi

mk() {  # fresh copy sharing the prebuilt Mathlib packages
  mkdir -p "$WORK/$1/.lake"
  cp -r "$SRC"/{"$NS","$NS.lean",gate.sh,lake-manifest.json,lakefile.toml,lean-toolchain} "$WORK/$1/"
  [ "$PLANT_ONLY" = 1 ] || ln -s "$PK" "$WORK/$1/.lake/packages"
}

digest() { (cd "$WORK/$1" && cat "$NS.lean" $(find "$NS" -name '*.lean' | LC_ALL=C sort) gate.sh | md5sum); }

plant() {
  local d="$WORK/$1"
  case "$1" in
    sorry)    sed -i "s|$E|theorem bogus : (1:ℕ) = 2 := by sorry\n$EL|" "$d/$C" ;;
    ax2line)  sed -i "s|$E|axiom\n  cheat_unused : False\n$EL|" "$d/$C" ;;
    evalfake) sed -i "s|$E|#eval IO.println \"'$FIRST' depends on axioms: [propext]\"\n$EL|" "$d/$C" ;;
    macro)    python3 - "$d/$C" "$EL" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text(); a = sys.argv[2] + "\n"
m = ("macro_rules\n  | `(#print axioms $id:ident) =>\n"
     "    `(#print $(Lean.Syntax.mkStrLit s!\"'{id.getId}' depends on axioms: [propext]\"))\n")
assert s.count(a) >= 1
p.write_text(s.replace(a, m + a, 1))
PY
              ;;
    falsehyp) [ "$(grep -cF -- "$FH_OLD" "$d/$C")" -eq 1 ] || return 1
              sed -i 's|    ((k : ℝ) + 1) \* t \^ k ≤ 1 + (k : ℝ) \* t \^ (k + 1) := by|    ((k : ℝ) + 1) * t ^ k ≤ (k : ℝ) * t ^ (k + 1) := by|' "$d/$C"
              ! grep -qF -- "$FH_OLD" "$d/$C" && [ "$(grep -cF -- "$FH_NEW" "$d/$C")" -eq 1 ] || return 1 ;;
    wrap)     # Tests the output parser alone: the source filter's `axiom` check is switched off in
              # this copy's gate, the attacked theorem is renamed to <name>_orig (with every use in the
              # library), and a replacement theorem with the original name is made to depend on a
              # long-named extra axiom so that Lean wraps it onto a continuation line of the report.
              python3 - "$d" "$NS" "$C" "$EL" "$TGT" <<'PY' || return 1
import sys, pathlib, re
d, ns, c, anchor, tgt = sys.argv[1:6]
d = pathlib.Path(d)
files = [d / (ns + ".lean")] + sorted((d / ns).rglob("*.lean"))
pat = re.compile(r"(?<![A-Za-z0-9_'])" + re.escape(tgt) + r"(?![A-Za-z0-9_'!?])")
hits = 0
for f in files:
    s = f.read_text(); s2, k = pat.subn(tgt + "_orig", s)
    if k: f.write_text(s2); hits += k
cf = d / c; s = cf.read_text()
assert ("theorem " + tgt + "_orig") in s, "declaration not renamed"
a = anchor + "\n"; assert s.count(a) >= 1, "anchor missing"
new = ("axiom zz_extra_axiom_with_a_long_name_for_the_negative_gate_test : True\n"
       "theorem " + tgt + " : True := by\n"
       "  have := @" + tgt + "_orig\n"
       "  exact zz_extra_axiom_with_a_long_name_for_the_negative_gate_test\n\n")
cf.write_text(s.replace(a, new + a, 1))
print("wrap: renamed %d occurrence(s) of %s" % (hits, tgt))
PY
              sed -i 's/|\\baxiom\\b//' "$d/gate.sh"
              ! grep -q 'baxiom' "$d/gate.sh" || return 1 ;;
    *) return 1 ;;
  esac
}

expect() { case "$1" in
  sorry|ax2line|evalfake|macro) echo "FAIL: forbidden token" ;;
  falsehyp) echo "FAIL: build" ;;
  wrap) echo "FAIL: nonstandard axioms" ;;
esac; }

TESTS="${*:-sorry ax2line evalfake macro falsehyp wrap}"
bad=0
for t in $TESTS; do
  mk "$t"
  before="$(digest "$t")"
  if ! plant "$t" || [ "$(digest "$t")" = "$before" ]; then echo "$t: could not plant defect"; bad=1; continue; fi
  if [ "$PLANT_ONLY" = 1 ]; then printf 'planted %-9s (%s)\n' "$t" "$WORK/$t"; continue; fi
  (cd "$WORK/$t" && bash gate.sh > gate.log 2>&1)
  got="$(grep -E '^(PASS|FAIL)' "$WORK/$t/gate.log" | tail -1)"
  want="$(expect "$t")"
  if [[ "$got" == "$want"* ]]; then printf 'ok    %-9s rejected: %s\n' "$t" "$got"
  else printf 'NOT OK %-9s expected "%s", got "%s" (log: %s)\n' "$t" "$want" "$got" "$WORK/$t/gate.log"; bad=1; fi
done
if [ "$PLANT_ONLY" = 1 ]; then echo "PLANT-ONLY: scratch copies kept in $WORK"; exit "$bad"; fi
[ "$bad" -eq 0 ] && { echo "ALL TAMPERING TESTS REJECTED"; rm -rf "$WORK"; }
exit "$bad"
