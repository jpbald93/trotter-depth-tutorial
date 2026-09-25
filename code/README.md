# Reproduce the tutorial

From this `code` directory, one line regenerates and compiles everything:

```sh
python3 run_all.py && cd ../paper && pdflatex -interaction=nonstopmode -halt-on-error trotter_tutorial.tex && pdflatex -interaction=nonstopmode -halt-on-error trotter_tutorial.tex
```

Requirements: Python 3 with numpy, scipy, sympy, matplotlib; pdfLaTeX with the standard amsmath, amsthm, mathtools, booktabs, graphicx, geometry, lmodern and hyperref packages. `pdftotext` is used for the final manuscript audit, not the numerical experiment. Install the Python dependencies with `python3 -m pip install numpy scipy sympy matplotlib` if necessary. Preparation versions are pinned in `requirements.txt` (use `python3 -m pip install -r requirements.txt` for the same package releases). After compilation, run `python3 audit_pdf.py` from `code` to check page count, errors/references, and generated values in extracted PDF text. The generator requires no network access and restricts BLAS to one thread. A full numerical regeneration takes about one minute on the preparation machine; machine-dependent timings are printed.

`run_all.py` regenerates all numerical manuscript macros, tables, three PDF figures, and bibliography content. It prints exactly `ALL ASSERTIONS PASS` as its last line on success. `simulator.py` implements the dense density-matrix simulation. The observable is a nonconserved central-site Pauli Z, not total magnetization. Every primitive rotation is followed by gate-support depolarization. Adjacent half rotations in the symmetric formula are deliberately not merged. All depths 1 through 64 are evaluated.

Outputs in `output/results.json` contain all optima, shot results, calibration coefficients and package versions; `output/curves.npz` contains complete expectation curves. Shot samples use a fixed base seed and deterministic case offsets. Generating independent depth samples before scanning for the first stop is statistically equivalent to sampling sequentially. Highest shot counts are sampled using the exact binomial model and are not experimental resource recommendations.

Reference metadata are the genuine Crossref responses in `../paper/crossref_verified.json`; their verification endpoints and returned titles are recorded in `../paper/REFERENCES_VERIFIED.md`. The generator formats only these verified entries into the bibliography. Experimental numerical values and author-email digits are supplied through generated macros and tables, bound to the computation parameters. Plain small integers are allowed for mathematical constants and structural labels; the source audit rejects handwritten decimal data and unused macros. Automatic section/equation/page numbering is handled by LaTeX.

Checks include symbolic optimization identities, nonconservation, Trotter-error magnitude, channel replacement properties, dense X/ZZ and Pauli-twirl noise comparisons, Choi complete-positivity checks, trace/Hermiticity, positivity at empirical minima, interior grid minima, early and late stopping cases, same-seed shot reproducibility, repeat-circuit determinism, and exactly one document terminator. They are not a claim of a proof of correctness for every numerical implementation detail.

The optional formal gate is `bash ../lean/gate.sh`. It checks five named theorems and their axioms using Lean 4 and Mathlib. On a fresh machine it first runs `lake exe cache get` to download the pinned Mathlib build; see `../lean/README.md`. The checked optimization is restricted to the linear noise power and positive natural-number order. The shot theorem checks the difference-of-means, multiple-comparison budget algebra only; it does not formalize the probability inequality or simulation.
