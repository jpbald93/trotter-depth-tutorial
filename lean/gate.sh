#!/bin/bash
# Gate for the Lean companion. It passes only if all of these hold:
#  * no sorry / admit / native_decide, and no axiom declaration of any kind
#    (including `private axiom`, and axioms declared mid-line) in any source file;
#  * the source checks against Mathlib without errors;
#  * each of the five REQUIRED theorems has an axiom report;
#  * each theorem depends only on a subset of Lean's standard axioms
#    (propext, Classical.choice, Quot.sound).
# Lean wraps long axiom lists across several lines, so the output is flattened
# before it is parsed. Otherwise an extra axiom on a continuation line would be missed.
export PATH="$HOME/.elan/bin:$PATH"
cd "$(dirname "$0")" || exit 1
REQUIRED="key_poly key_ineq trotter_global_min trotter_opt_value hoeffding_shots"
SOURCES="TrotterOpt/*.lean TrotterOpt.lean"
# Fetch pinned Mathlib oleans on a fresh machine (no-op if already present).
[ -d .lake/packages/mathlib ] || lake exe cache get || { echo "FAIL: could not fetch Mathlib cache"; exit 1; }
if grep -nE "\bsorry\b|\badmit\b|native_decide|(^|[[:space:]])axiom[[:space:]]" $SOURCES; then
  echo "FAIL: forbidden token or axiom declaration"; exit 1; fi
# Check the local source directly against the installed Mathlib oleans, without
# rebuilding or modifying the shared dependency tree linked under .lake/packages.
out=$(lake env lean TrotterOpt/Basic.lean 2>&1)
status=$?
printf '%s\n' "$out"
[ "$status" -eq 0 ] || { echo "FAIL: Lean source check"; exit 1; }
echo "$out" | grep -qE "(^|:)[[:space:]]*error" && { echo "FAIL: Lean reported an error"; exit 1; }
# Flatten: each report starts with a quoted theorem name; join continuation lines onto it.
flat=$(printf '%s\n' "$out" | awk '/^'"'"'|^[^ ]*: *'"'"'/{if(buf!="")print buf; buf=$0; next} {buf=buf" "$0} END{if(buf!="")print buf}')
reports=$(printf '%s\n' "$flat" | grep -E "depends on axioms|does not depend on any axioms")
n=0
for t in $REQUIRED; do
  line=$(printf '%s\n' "$reports" | grep -E "'(TrotterOpt\.)?$t' (depends on axioms|does not depend)")
  [ -n "$line" ] || { echo "FAIL: no axiom report for required theorem $t"; exit 1; }
  n=$((n+1))
done
extra=$(printf '%s\n' "$reports" | grep -c "depends on axioms\|does not depend")
[ "$extra" -eq "$n" ] || { echo "FAIL: expected exactly $n axiom reports, found $extra"; exit 1; }
bad=$(printf '%s\n' "$reports" | grep "depends on axioms" | sed 's/.*depends on axioms: *\[//; s/\].*//' \
      | tr ',' '\n' | sed 's/^ *//; s/ *$//' | grep -v '^$' | sort -u \
      | grep -vE '^(propext|Classical\.choice|Quot\.sound)$')
[ -n "$bad" ] && { echo "FAIL: nonstandard axioms: $bad"; exit 1; }
# Unterminated axiom list (no closing bracket) means the parse above was incomplete.
printf '%s\n' "$reports" | grep "depends on axioms" | grep -qv '\]' && { echo "FAIL: unterminated axiom list"; exit 1; }
echo "PASS ($n theorems, standard axioms only)"
