#!/usr/bin/env python3
"""Regenerate the manuscript's numerical inputs, figures, tables and checks.
No internet is needed: Crossref metadata verified during preparation is shipped.
"""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[name] = '1'
from pathlib import Path
import json
import time
import hashlib
import numpy as np
import scipy
import sympy as sp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from simulator import SpinChain, L, J, HX, TIME, THETA, PHI, TOLERANCE

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT/'paper'
OUT = ROOT/'code'/'output'
OUT.mkdir(exist_ok=True)
START = time.perf_counter()
NMAX = 64
NS = np.arange(1,NMAX+1)
PS = (0.0001,0.0005,0.002)
SHOTS = (10_000,1_000_000,10_000_000_000)
REPS = 400
SEED = 20260924
DELTA = .05
M = NMAX-1
NCAL = 16
PCAL = 1e-7
TAIL_START = 32
LOWER_PERCENTILE = 10
UPPER_PERCENTILE = 90

# Symbolic identities, including both parameterizations of the minimum.
a,b,k,alpha,x = sp.symbols('a b k alpha x',positive=True)
nstar = (k*a/(alpha*b))**(1/(k+alpha))
claimed = (k+alpha)/alpha * a**(alpha/(k+alpha)) * (alpha*b/k)**(k/(k+alpha))
assert sp.simplify(sp.expand_power_base((a/x**k+b*x**alpha).subs(x,nstar)-claimed,force=True)) == 0
assert sp.simplify(sp.expand_power_base((sp.diff(a/x**k+b*x**alpha,x)).subs(x,nstar),force=True)) == 0
linear = (k+1)*a**(1/(k+1))*(b/k)**(k/(k+1))
assert sp.simplify(claimed.subs(alpha,1)-linear)==0
# Numerical substitution independently checks expression evaluation.
for kval in (1,2,4):
    for av in (.5,1.,1.5):
        d={a:.73,b:.002,k:kval,alpha:av}
        ns=float(nstar.subs(d)); ev=.73/ns**kval+.002*ns**av
        assert np.isclose(ev,float(claimed.subs(d)),rtol=1e-12)

model=SpinChain()
assert model.commutator_norm>TOLERANCE
clean={k:np.array([model.simulate(int(n),k,0) for n in NS]) for k in (1,2)}
assert all(np.all(abs(clean[k]-model.exact)>TOLERANCE) for k in clean)
# Independent dense-exponential action plus Pauli-twirl noise cross-check.
from scipy.linalg import expm
from itertools import product
from simulator import kron_all
small=SpinChain(size=3)
I=np.eye(2); X=np.array([[0,1],[1,0]]); Y=np.array([[0,-1j],[1j,0]]); Z=np.diag([1,-1])
def dense_depolarize(rho,supp,p):
    twirl=np.zeros_like(rho,dtype=complex)
    for local in product((I,X,Y,Z),repeat=len(supp)):
        ops=[I]*small.L
        for q,P in zip(supp,local): ops[q]=P
        P=kron_all(ops)
        twirl += P@rho@P.conj().T
    return (1-p)*rho+p*twirl/(4**len(supp))

def dense_layer(rho,kind,angle,p):
    terms=small.flips if kind=='x' else small.zz
    for q,term in enumerate(terms):
        H=np.eye(small.d)[:,term] if kind=='x' else np.diag(term)
        U=expm(-1j*angle*H)
        rho=U@rho@U.conj().T
        rho=dense_depolarize(rho,(q,) if kind=='x' else (q,q+1),p)
    return rho

dt=TIME/3
choi_min=0.0
for testp in (0,.3,1):
    for kind,angle,fast in (('x',HX*dt,small.x_layer),('zz',J*dt,small.zz_layer)):
        assert np.allclose(dense_layer(small.rho0.copy(),kind,angle,testp),
                           fast(small.rho0.copy(),angle,testp),atol=1e-13)
    for supp in small.replacements:
        assert np.allclose(small.depolarize(small.rho0,supp,testp),
                           dense_depolarize(small.rho0,supp,testp),atol=1e-13)
        # Unnormalised Choi matrix sum_ij |i><j| tensor D(|i><j|).
        blocks=[]
        for i in range(small.d):
            row=[]
            for j in range(small.d):
                E=np.zeros((small.d,small.d),dtype=complex); E[i,j]=1
                output=small.depolarize(E,supp,testp)
                assert np.isclose(np.trace(output),float(i==j),atol=1e-13)
                row.append(output)
            blocks.append(row)
        choi=np.block(blocks)
        assert np.allclose(choi,choi.conj().T,atol=1e-13)
        mineig=float(np.linalg.eigvalsh(choi).min());choi_min=min(choi_min,mineig)
        assert mineig>-TOLERANCE
rr=small.depolarize(small.rho0,(0,),1)
assert np.allclose(rr,small.depolarize(rr,(0,),1))
# Concrete first-order rigorous coefficient; no second-order bound is used.
HZ=np.diag(J*np.sum(model.zz,axis=0))
HXmat=model.H-HZ
block_comm=float(np.linalg.norm(HXmat@HZ-HZ@HXmat,2))
A_bound=block_comm*TIME**2
noise_bound=2*model.gates(1)

calibration={}
for order in (1,2):
    tail=NS>=TAIL_START
    A=float(np.median(abs(clean[order][tail]-model.exact)*NS[tail]**order))
    response=abs(model.simulate(NCAL,order,PCAL)-clean[order][NCAL-1])/(PCAL*NCAL)
    calibration[order]={'A':A,'noise_response':float(response)}

results=[]; curves={}
for order in (1,2):
    for p in PS:
        mu=np.array([model.simulate(int(n),order,p) for n in NS])
        curves[(order,p)]=mu
        A=calibration[order]['A'];B=p*calibration[order]['noise_response']
        nc=(order*A/B)**(1/(order+1))
        ncancel=(A/B)**(1/(order+1))
        cancel_integer=int(NS[np.argmin(abs(A/NS**order-B*NS))])
        candidates=np.unique(np.maximum(1,[int(np.floor(nc)),int(np.ceil(nc))]))
        ni=int(min(candidates,key=lambda n:A/n**order+B*n))
        empirical=int(NS[np.argmin(abs(mu-model.exact))])
        assert 1<empirical<NMAX, 'Each demonstrated noise case must have an interior minimum.'
        _,rho=model.simulate(empirical,order,p,return_rho=True)
        assert np.linalg.eigvalsh(rho).min()>-TOLERANCE
        assert np.isclose(mu[empirical-1],np.dot(model.obs,np.diag(rho)).real,atol=1e-14)
        results.append(dict(k=order,p=p,A=A,B=B,n_cont=nc,n_pred=ni,n_emp=empirical,
                            n_cancel=ncancel,n_cancel_integer=cancel_integer,
                            n_bound=float(np.sqrt(A_bound/(noise_bound*p))) if order==1 else None,
                            err_emp=float(abs(mu[empirical-1]-model.exact)),
                            err_pred=float(abs(mu[ni-1]-model.exact)),
                            model_min=float(A/ni**order+B*ni)))

def sample_stops(mu,shots,seed):
    rng=np.random.default_rng(seed)
    tau=2*np.sqrt(np.log(2*M/DELTA)/shots)
    samples=2*rng.binomial(shots,(mu+1)/2,size=(REPS,len(mu)))/shots-1
    flags=abs(np.diff(samples,axis=1))<=tau
    # Return the smaller n in the first indistinguishable pair; NMAX if none.
    stops=np.where(flags.any(axis=1),flags.argmax(axis=1)+1,NMAX)
    return stops,tau

stoprows=[]
for idx,r in enumerate(results):
    mu=curves[(r['k'],r['p'])]
    for shots in SHOTS:
        seed=SEED+idx*len(SHOTS)+SHOTS.index(shots)
        stops,tau=sample_stops(mu,shots,seed)
        repeat,_=sample_stops(mu,shots,seed)
        assert np.array_equal(stops,repeat)
        median=float(np.median(stops))
        assert median.is_integer(), "Error at median requires a grid depth in these cases."
        error_ratio=float(abs(mu[int(median)-1]-model.exact)/r['err_emp'])
        stoprows.append(dict(k=r['k'],p=r['p'],shots=shots,tau=tau,
            median=median,error_ratio=error_ratio,lo=float(np.quantile(stops,LOWER_PERCENTILE/100)),
            hi=float(np.quantile(stops,UPPER_PERCENTILE/100)),early=float(np.mean(stops<r['n_emp'])),
            late=float(np.mean(stops>r['n_emp'])),censored=float(np.mean(stops==NMAX))))
# Post-hoc observations: reported, not enforced (different parameters may legitimately differ).
posthoc=dict(k2_bias_positive_n_ge_2=bool(np.all(clean[2][1:]-model.exact>0)),
             k2_bias_negative_n_eq_1=bool(clean[2][0]-model.exact<0),
             cancel_matches=int(sum(r['n_cancel_integer']==r['n_emp'] for r in results if r['k']==2)),
             cancel_cases=int(sum(r['k']==2 for r in results)))
print('Post-hoc diagnostics (not assertions):',posthoc)
assert any(r['early']>.5 for r in stoprows)
assert any(r['late']>.5 for r in stoprows)
# Repeat a physical circuit, not just a pseudo-random shot stream.
assert model.simulate(7,2,PS[1])==model.simulate(7,2,PS[1])

plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.23})
fig,axes=plt.subplots(1,2,figsize=(10,3.5),sharey=True)
colors=['#0072B2','#D55E00','#009E73']
for ax,order in zip(axes,(1,2)):
    ax.loglog(NS,abs(clean[order]-model.exact),'k:',label='noiseless')
    for col,p in zip(colors,PS):
        r=next(r for r in results if r['k']==order and r['p']==p)
        ax.loglog(NS,abs(curves[(order,p)]-model.exact),color=col,label=f'p={p:g}')
        ax.loglog(NS,r['A']/NS**order+r['B']*NS,'--',color=col,alpha=.7)
        ax.plot(r['n_emp'],r['err_emp'],'o',color=col,zorder=5)
    ax.set(title=f'Order k={order}',xlabel='Steps n')
axes[0].set_ylabel('Absolute observable error')
from matplotlib.lines import Line2D
handles=[Line2D([],[],color='k',ls=':',label='noiseless')]+\
        [Line2D([],[],color=c,label=f'p={p:g}') for c,p in zip(colors,PS)]+\
        [Line2D([],[],color='gray',ls='--',label='positive surrogate (each p)'),
         Line2D([],[],color='gray',marker='o',ls='',label='empirical minimum')]
fig.tight_layout(rect=(0,0.13,1,1))
fig.legend(handles=handles,loc='lower center',ncol=6,fontsize=8,frameon=False)
fig.savefig(PAPER/'error_curves.pdf');plt.close(fig)

fig,axes=plt.subplots(1,2,figsize=(10,3.6),sharey=False)
for ax,order in zip(axes,(1,2)):
    p=PS[1];mu=curves[(order,p)];cleanbias=clean[order]-model.exact
    ax.semilogx(NS,cleanbias,marker='.',markersize=3,label='algorithmic signed bias')
    ax.semilogx(NS,mu-clean[order],marker='.',markersize=3,label='noise-induced signed shift')
    ax.semilogx(NS,mu-model.exact,'--',marker='.',markersize=3,label='total signed bias')
    linear_band=1e-4
    ax.set_yscale('symlog',linthresh=linear_band)
    ax.axhspan(-linear_band,linear_band,color='gray',alpha=.12,zorder=0)
    ax.axhline(0,color='k',lw=.7);ax.set(title=f'Order k={order}, p={p:g}',xlabel='Steps n')
axes[0].set_ylabel('Signed expectation difference')
handles,labels=axes[1].get_legend_handles_labels()
fig.legend(handles,labels,loc='upper center',ncol=3,fontsize=8)
fig.tight_layout(rect=(0,0,1,.9));fig.savefig(PAPER/'signed_bias.pdf');plt.close(fig)

# Separate each noise rate/order so overlapping cases cannot hide intervals.
fig,axes=plt.subplots(2,3,figsize=(10,5.8),sharex=True,sharey=True,layout='constrained')
for row,order in enumerate((1,2)):
    for ax,col,p in zip(axes[row],colors,PS):
        rows=[r for r in stoprows if r['k']==order and r['p']==p]
        med=np.array([r['median'] for r in rows]);lo=np.array([r['lo'] for r in rows]);hi=np.array([r['hi'] for r in rows])
        ax.errorbar(SHOTS,med,yerr=[med-lo,hi-med],marker='o',markersize=4,
                    color=col,capsize=6,capthick=2,elinewidth=2,zorder=3)
        # Display exact numerical intervals even when their width is zero or subpixel.
        for shot,m,l,h in zip(SHOTS,med,lo,hi):
            ax.annotate(f'[{l:g}, {h:g}]',(shot,m),xytext=(0,7 if m<55 else -16),
                        textcoords='offset points',ha='center',fontsize=8,
                        zorder=10,bbox=dict(facecolor='white',edgecolor='none',alpha=1,pad=.7))
        opt=next(r['n_emp'] for r in results if r['k']==order and r['p']==p)
        ax.axhline(opt,color=col,ls=':',alpha=.8)
        ax.set(xscale='log',title=f'k={order}, p={p:g}',ylim=(-2,NMAX+6))
        ax.set_xlim(SHOTS[0]/15,SHOTS[-1]*15)
fig.supxlabel('Shots per estimate S');fig.supylabel('Chosen steps')
fig.savefig(PAPER/'stopping.pdf',bbox_inches='tight');plt.close(fig)

# Experimental quantities and bibliography metadata are generated; mathematical constants may be literals.
def texnum(value):
    s=f'{value:.3g}'
    if 'e' in s:
        mant,exp=s.split('e');return rf'{mant}\times 10^{{{int(exp)}}}'
    return s
macros={'PageMargin':'0.9in','LineSpread':'1.08','PlotWidth':'0.98',
 'AuthorEmail':'jpbald93@gmail.com','AIAstra':'GPT-6 Astra','AIOpus':'Claude Opus 5.5 (Anthropic)','AIPlatform':'the Genspark platform','RepoURL':r'\url{https://github.com/jpbald93/trotter-depth-tutorial}','Nqubits':str(L),'HilbertDim':str(model.d),'Jval':str(J),'Hval':str(HX),'Tval':str(TIME),'ThetaVal':str(THETA),'PhiVal':str(PHI),
 'Nmax':str(NMAX),'Ncal':str(NCAL),'TailStart':str(TAIL_START),'Pcal':texnum(PCAL),'Reps':str(REPS),'Seed':str(SEED),
 'DeltaVal':str(DELTA),'LowerPercentile':str(LOWER_PERCENTILE),'UpperPercentile':str(UPPER_PERCENTILE),
 'ExactVal':f'{model.exact:.8f}','CommVal':f'{model.commutator_norm:.3f}',
 'Tolerance':texnum(TOLERANCE),'CleanOne':texnum(abs(clean[1][-1]-model.exact)),'CleanTwo':texnum(abs(clean[2][-1]-model.exact)),
 'AOne':texnum(calibration[1]['A']),'ATwo':texnum(calibration[2]['A']),
 'COne':texnum(calibration[1]['noise_response']),'CTwo':texnum(calibration[2]['noise_response']),
 'GOne':str(model.gates(1)),'GTwo':str(model.gates(2)),
 'Comparisons':str(M),
 'BlockComm':texnum(block_comm),'ABound':texnum(A_bound),'NoiseBound':str(noise_bound),
 'ALooseness':texnum(A_bound/calibration[1]['A']),
 'CLooseness':texnum(noise_bound/calibration[1]['noise_response']),
 'CancelMatches':str(sum(r['n_cancel_integer']==r['n_emp'] for r in results if r['k']==2)),
 'CancelCases':str(sum(r['k']==2 for r in results)),
 'LateHighCases':str(sum(r['median']>next(x['n_emp'] for x in results if (x['k'],x['p'])==(r['k'],r['p'])) for r in stoprows if r['shots']==SHOTS[-1])),
 'HighCases':str(sum(r['shots']==SHOTS[-1] for r in stoprows)),
 'EarlyHighDepth':f"{stoprows[2]['median']:g}",'EarlyHighOpt':str(results[0]['n_emp']),
 'BoundaryDepth':str(results[-1]['n_emp']),
 'BoundaryBias':texnum(clean[2][0]-model.exact)}
for name,p in zip(('PLow','PMid','PHigh'),PS):macros[name]=texnum(p)
for name,s in zip(('ShotsLow','ShotsMid','ShotsHigh'),SHOTS):macros[name]=texnum(s)
for name,s in zip(('TauLow','TauMid','TauHigh'),SHOTS):macros[name]=texnum(2*np.sqrt(np.log(2*M/DELTA)/s))
PAPER.joinpath('generated_numbers.tex').write_text('% Generated by code/run_all.py; do not edit.\n'+''.join('\\newcommand{\\'+key+'}{'+val+'}\n' for key,val in macros.items()))
header=r'''\begin{tabular}{ccrrrrrrr}
\toprule
$k$ & $p$ & $n_*$ & $n_{\rm pred}$ & $n_{\rm cancel}$ & $\arg\min_n |A/n^k-Bn|$ & $n_{\rm emp}$ & $e(n_{\rm emp})$ & $E(n_{\rm pred})$\\
\midrule
'''
lines=[f"{r['k']} & ${texnum(r['p'])}$ & {r['n_cont']:.2f} & {r['n_pred']} & {r['n_cancel']:.2f} & {r['n_cancel_integer']} & {r['n_emp']} & ${texnum(r['err_emp'])}$ & ${texnum(r['model_min'])}$ \\\\ \n" for r in results]
PAPER.joinpath('optimum_table.tex').write_text(header+''.join(lines)+'\\bottomrule\n\\end{tabular}\n')
header=r'''\begin{tabular}{ccrrrrrr}
\toprule
$k$ & $p$ & $S$ & Median & $e(\mathrm{stop})/e_{\min}$ & Early (\%) & Late (\%) & Cap (\%)\\
\midrule
'''
lines=[f"{r['k']} & ${texnum(r['p'])}$ & ${texnum(r['shots'])}$ & {r['median']:g} & {r['error_ratio']:.2f} & {100*r['early']:.1f} & {100*r['late']:.1f} & {100*r['censored']:.1f} \\\\ \n" for r in stoprows]
PAPER.joinpath('stopping_table.tex').write_text(header+''.join(lines)+'\\bottomrule\n\\end{tabular}\n')
header=r"""\begin{tabular}{crr}
\toprule
$p$ & Rigorous-bound $n_*$ & $n_{\rm emp}$\\
\midrule
"""
lines=[f"${texnum(r['p'])}$ & {r['n_bound']:.2f} & {r['n_emp']} \\\\ \n" for r in results if r['k']==1]
PAPER.joinpath('bound_table.tex').write_text(header+''.join(lines)+'\\bottomrule\n\\end{tabular}\n')
refs=json.loads(PAPER.joinpath('crossref_verified.json').read_text())
bib=['\\begin{thebibliography}{9}\n']
for key,ref in refs.items():
    authors=', '.join(a['given']+' '+a['family'] for a in ref['author'])
    year=ref['published']['date-parts'][0][0]
    pages=ref.get('page') or ref.get('article-number','')
    issue=ref.get('issue','')
    bib.append(f"\\bibitem{{{key}}} {authors}, \\emph{{{ref['title'][0]}}}, {ref['container-title'][0]} \\textbf{{{ref.get('volume','')}}} "+(f"({issue})" if issue else '')+f" ({year})"+(f", {pages}" if pages else '')+f". \\href{{https://doi.org/{ref['DOI']}}}{{doi:{ref['DOI']}}}.\n")
bib.append('\\end{thebibliography}\n');PAPER.joinpath('generated_bibliography.tex').write_text(''.join(bib))
summary={'parameters':{'L':L,'J':J,'h':HX,'time':TIME,'theta':THETA,'phi':PHI,'seed':SEED,'repetitions':REPS,
 'ncal':NCAL,'pcal':PCAL,'tail_start':TAIL_START,'percentiles':[LOWER_PERCENTILE,UPPER_PERCENTILE],'tolerance':TOLERANCE},
 'rigorous_first_order':{'block_commutator_norm':block_comm,'A_bound':A_bound,'noise_slope':noise_bound},
 'choi_min_eigenvalue':choi_min,
 'exact':model.exact,'commutator_norm':model.commutator_norm,'calibration':calibration,'optima':results,'stopping':stoprows,
 'versions':{'numpy':np.__version__,'scipy':scipy.__version__,'sympy':sp.__version__,'matplotlib':matplotlib.__version__}}
OUT.joinpath('results.json').write_text(json.dumps(summary,indent=2))
np.savez(OUT/'curves.npz',n=NS,exact=model.exact,**{f'k{k}_p{p:g}':v for (k,p),v in curves.items()},**{f'clean_k{k}':v for k,v in clean.items()})
# Audit manuscript data literals and use of generated macros.
manuscript=PAPER/'trotter_tutorial.tex'
if manuscript.exists():
    import re
    source=manuscript.read_text()
    # Plain small integers are allowed for structural mathematical constants.
    # Empirical quantities remain generated macros/tables, not manuscript literals.
    assert all(int(v)<=16 for v in re.findall(r'\d+',source)), 'Unexpected numerical data literal'
    assert not re.search(r'\d+\.\d+',source), 'Hand-written decimal in manuscript'
    for macro in macros:
        assert re.search(r'\\'+macro+r'\b',source), f'Unused generated macro: {macro}'
    assert source.count(r'\end{document}')==1
elapsed=time.perf_counter()-START
print('Verified symbolic minimum and stationary-point identities (linear and general power).')
print(f'Observable commutator norm: {model.commutator_norm:.8g}; exact expectation: {model.exact:.8f}')
print('k p predicted_cont predicted_integer empirical error_at_empirical')
for r in results:
    print(f"{r['k']} {r['p']:g} {r['n_cont']:.6f} {r['n_pred']} {r['n_emp']} {r['err_emp']:.8g}")
print('Checks: channel trace/Hermiticity/positivity/Choi CP, dense X/ZZ/noise action, interior minima, nonconservation, nonzero Trotter error at every depth, fixed-seed reproducibility.')
print(f'Generated all tables, three figures, numerical macros, and verified-metadata bibliography in {elapsed:.2f} seconds.')
print('ALL ASSERTIONS PASS')
