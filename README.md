# Noise-limited Trotter depth and a shot-noise stopping rule: a reproducible tutorial

Josh Bald, independent researcher (Ontario, Canada).

Paper: [`paper/trotter_tutorial.pdf`](paper/trotter_tutorial.pdf) (10 pages).

This is an **expository tutorial** and claims no novelty. It works through the standard trade-off between product-formula (Trotter) discretization error and accumulated gate noise, which has been studied before, notably by Knee and Munro, Phys. Rev. A 91, 052327 (2015). It also demonstrates a finite-shot stopping heuristic. It separates three kinds of statement:
- theorems, which are proved;
- model assumptions;
- numerical observations on one small, fully simulated spin chain.

## Contents
- `paper/`: manuscript source and PDF, generated tables, numerical macros and figures, and the Crossref records behind every reference.
- `code/`: the simulator and a single script (`run_all.py`) that regenerates every number, table and figure and checks them with assertions. `audit_pdf.py` checks the compiled PDF against the generated outputs.
- `lean/`: a Lean 4 / Mathlib companion that machine-checks five algebraic statements the tutorial uses. The paper states exactly what is and is not formalized.

## Reproduce
```sh
cd code
pip install -r requirements.txt
python3 run_all.py          # last line: ALL ASSERTIONS PASS
cd ../paper
pdflatex trotter_tutorial.tex && pdflatex trotter_tutorial.tex
cd ../code && python3 audit_pdf.py
```
Optional formal check (see `lean/README.md`):
```sh
cd lean && lake exe cache get && bash gate.sh   # PASS (5 theorems, standard axioms only)
```

## Licence and AI assistance
Text: CC BY 4.0 (`LICENSE-CC-BY-4.0.txt`). Code: MIT (`LICENSE-code-MIT.txt`).

The large-language-model assistants GPT-6 Astra and Claude Opus 5.5 (Anthropic), accessed through the Genspark platform, were used in the preparation of this tutorial. The author is responsible for the content.
