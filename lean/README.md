# Lean companion (optional)

Machine-checks five algebraic statements used in the tutorial (see the paper's
paragraph on formal checks for exactly what is and is not covered).

Portable setup, from this `lean/` directory, on any machine:

```sh
curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh   # installs elan if needed
lake exe cache get      # downloads prebuilt Mathlib oleans pinned by lake-manifest.json
bash gate.sh            # builds TrotterOpt and checks the five theorems and their axioms
```

The toolchain (`lean-toolchain`) and every dependency revision (`lake-manifest.json`)
are pinned, so this reproduces the same build. `.lake/` is build state and is not
part of the distributed source.

### What the gate checks
`gate.sh` passes only if all of the following hold:
- the source contains no `sorry`, `admit`, `native_decide` or axiom declaration of any kind (including `private axiom`);
- the source checks cleanly against Mathlib;
- each of the five named theorems has an axiom report, and there are exactly five;
- every theorem depends only on Lean's standard axioms (`propext`, `Classical.choice`, `Quot.sound`).

Lean wraps long axiom lists over several lines, so the gate flattens the output before parsing it. It has been negative-tested against each of these on copies:
- a private axiom;
- an extra axiom on a wrapped continuation line, caught by the parser alone;
- deleted `#print axioms` lines;
- `sorry`.

All of them fail.
