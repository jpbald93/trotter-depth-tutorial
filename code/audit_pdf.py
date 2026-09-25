#!/usr/bin/env python3
"""Post-compilation artifact audit; run after pdfLaTeX twice."""
import json
import re
import subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
paper=root/'paper'
source=(paper/'trotter_tutorial.tex').read_text()
assert source.count(r'\end{document}')==1
assert all(int(v)<=16 for v in re.findall(r'\d+',source))
assert not re.search(r'\d+\.\d+',source)
log=(paper/'trotter_tutorial.log').read_text()
assert not re.search(r'undefined|^!',log,re.M)
subprocess.run(['pdftotext','-layout',str(paper/'trotter_tutorial.pdf'),str(paper/'trotter_tutorial.txt')],check=True)
text=(paper/'trotter_tutorial.txt').read_text()
results=json.loads((root/'code/output/results.json').read_text())
required=[f"{results['exact']:.8f}",f"{results['commutator_norm']:.3f}",str(results['parameters']['seed']),'jpbald93@gmail.com']
required += [f"{r['n_cont']:.2f}" for r in results['optima']]
for value in required:
    assert value in text, f'Generated value missing from PDF: {value}'
    print('PDF value confirmed:',value)
# All integer optimum-table entries must appear together on their generated row.
for r in results['optima']:
    row=rf"{r['n_cont']:.2f}\s+{r['n_pred']}\s+{r['n_cancel']:.2f}\s+{r['n_cancel_integer']}\s+{r['n_emp']}"
    assert re.search(row,text),row
for r in results['optima']:
    print(f"PDF cancellation confirmed: k={r['k']}, p={r['p']:g}, n_cancel={r['n_cancel']:.2f}, integer={r['n_cancel_integer']}")
for r in results['stopping']:
    value=f"{r['error_ratio']:.2f}"
    assert re.search(rf"{r['median']:g}\s+{re.escape(value)}\s+{100*r['early']:.1f}\s+{100*r['late']:.1f}",text)
    print(f"PDF e(stop)/e_min confirmed: k={r['k']}, p={r['p']:g}, S={r['shots']}, ratio={value}")
info=subprocess.check_output(['pdfinfo',str(paper/'trotter_tutorial.pdf')],text=True)
pages=int(re.search(r'Pages:\s+(\d+)',info).group(1))
assert pages>0,pages
print('Pages:',pages)
print('Source document terminators: 1')
print('LaTeX errors / undefined references / undefined citations: 0')
print('PDF GENERATED-NUMBER AUDIT PASS')
