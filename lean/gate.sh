#!/bin/bash
# Gate for the Lean formalisation. It passes only if all of these hold:
#  * the sources contain no `sorry`, `admit`, `native_decide`, `axiom` keyword (anywhere,
#    including one on a line of its own), `#eval`, `run_cmd`, `initialize`, `IO`, `debug.`,
#    or syntax-extension commands (`macro`, `elab`, `syntax`, `notation`, `import Lean`, ...),
#    which could redefine `#print axioms`;
#  * the only `set_option` lines are whole-line `set_option linter.<name> true|false` commands
#    (lint switches only; any other set_option, or a linter option with trailing `in`, fails);
#  * the library builds without errors;
#  * the gate itself (not a file in the repo) generates the `#print axioms` report for each
#    REQUIRED declaration, and each report is present exactly once, with no extra reports;
#  * each REQUIRED declaration (with its transitive dependencies) uses only Lean's standard
#    axioms (propext, Classical.choice, Quot.sound).
# REQUIRED names are fully qualified: the generated check file contains only `import TrotterOpt`.
# Trust boundary: the token filter is a heuristic over the project's .lean sources. The gate assumes
# the pinned toolchain, Mathlib and lake configuration are unmodified. It is not a sandbox, and it
# does not audit declarations other than the REQUIRED ones.
# Lean wraps long axiom lists across several lines, so the output is flattened before parsing.
export PATH="$HOME/.elan/bin:$PATH"
cd "$(dirname "$0")" || exit 1
NS="TrotterOpt"
REQUIRED="key_poly key_ineq trotter_global_min trotter_opt_value hoeffding_shots"
SOURCES="$NS.lean $(find "$NS" -name '*.lean' 2>/dev/null | LC_ALL=C sort)"
[ -e .lake/packages/mathlib ] || lake exe cache get || { echo "FAIL: could not fetch Mathlib cache"; exit 1; }
[ -f "$NS.lean" ] && [ -d "$NS" ] || { echo "FAIL: library sources not found"; exit 1; }
grep -nHE "\bsorry\b|\badmit\b|native_decide|\baxiom\b|#eval|\brun_cmd\b|\binitialize\b|\bIO\b|\bdebug\.|\bmacro|\belab|\bsyntax\b|\bnotation\b|\binfix|\bprefix\b|\bpostfix\b|import Lean|open Lean" $SOURCES; gs=$?
[ "$gs" -eq 0 ] && { echo "FAIL: forbidden token"; exit 1; }
[ "$gs" -eq 1 ] || { echo "FAIL: could not scan sources"; exit 1; }
so=$(grep -nHE "\bset_option\b" $SOURCES | grep -vE '^[^:]+:[0-9]+:set_option linter\.[A-Za-z0-9_.]+ (true|false)[[:space:]]*$')
[ -n "$so" ] && { printf '%s\n' "$so"; echo "FAIL: forbidden token (set_option)"; exit 1; }
build=$(lake build $NS 2>&1); bstatus=$?
printf '%s\n' "$build" | tail -3
[ "$bstatus" -eq 0 ] || { printf '%s\n' "$build"; echo "FAIL: build"; exit 1; }
# The `#print axioms` queries are generated here rather than read from a file in the repo.
chk=$(mktemp --suffix=.lean -p . .gatecheck_XXXX)
trap 'rm -f "$chk"' EXIT
{ echo "import $NS"; for t in $REQUIRED; do echo "#print axioms $t"; done; } > "$chk"
out=$(lake env lean "$chk" 2>&1); status=$?
printf '%s\n' "$out"
[ "$status" -eq 0 ] || { echo "FAIL: axiom report"; exit 1; }
echo "$out" | grep -qE "(^|:)[[:space:]]*error" && { echo "FAIL: Lean reported an error"; exit 1; }
flat=$(printf '%s\n' "$out" | awk '/^'"'"'/{if(buf!="")print buf; buf=$0; next} {buf=buf" "$0} END{if(buf!="")print buf}')
reports=$(printf '%s\n' "$flat" | grep -E "depends on axioms|does not depend on any axioms")
n=0
for t in $REQUIRED; do
  re=$(printf '%s' "$t" | sed 's/\./\\./g')
  c=$(printf '%s\n' "$reports" | grep -cE "^'$re' (depends on axioms|does not depend)")
  [ "$c" -eq 1 ] || { echo "FAIL: expected one axiom report for $t, found $c"; exit 1; }
  n=$((n+1))
done
[ "$(printf '%s\n' "$reports" | grep -c .)" -eq "$n" ] || { echo "FAIL: unexpected extra reports"; exit 1; }
printf '%s\n' "$reports" | grep "depends on axioms" | grep -qv '\]' && { echo "FAIL: unterminated axiom list"; exit 1; }
bad=$(printf '%s\n' "$reports" | grep "depends on axioms" | sed 's/.*depends on axioms: *\[//; s/\].*//' \
      | tr ',' '\n' | sed 's/^ *//; s/ *$//' | grep -v '^$' | sort -u \
      | grep -vE '^(propext|Classical\.choice|Quot\.sound)$')
[ -n "$bad" ] && { echo "FAIL: nonstandard axioms: $bad"; exit 1; }
echo "PASS ($n theorems, standard axioms only)"
