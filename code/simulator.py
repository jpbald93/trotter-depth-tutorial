"""Dense density-matrix product formulas with gate-support depolarization."""
import numpy as np
from scipy.linalg import eigh

L = 6
J = 0.7
HX = 1.05
TIME = 0.8
THETA = 0.9
PHI = 0.0
TOLERANCE = 1e-10


def kron_all(ops):
    ans = np.array([[1.0 + 0j]])
    for op in ops:
        ans = np.kron(ans, op)
    return ans


class SpinChain:
    def __init__(self, size=L, theta=THETA, phi=PHI, time=TIME):
        self.L, self.d, self.time = size, 2**size, time
        self.bits = ((np.arange(self.d)[:, None] >> np.arange(size-1, -1, -1)) & 1)
        self.z = 1 - 2*self.bits
        self.flips = [np.arange(self.d) ^ (1 << (size-1-q)) for q in range(size)]
        self.zz = [self.z[:,q]*self.z[:,q+1] for q in range(size-1)]
        self.H = np.diag(J * np.sum(self.zz, axis=0)).astype(complex)
        for f in self.flips:
            self.H[np.arange(self.d),f] += HX
        local = np.array([np.cos(theta/2),np.exp(1j*phi)*np.sin(theta/2)])
        psi = local
        for _ in range(size-1):
            psi = np.kron(psi,local)
        self.psi = psi
        self.rho0 = np.outer(psi,psi.conj())
        self.obs = self.z[:,size//2]
        self.O = np.diag(self.obs)
        w,v = eigh(self.H)
        exact = v @ (np.exp(-1j*time*w)*(v.conj().T@psi))
        self.exact = float(np.real(np.vdot(exact,self.obs*exact)))
        self.commutator_norm = float(np.linalg.norm(self.H@self.O-self.O@self.H,2))
        self.replacements = {}
        for supp in [(q,) for q in range(size)]+[(q,q+1) for q in range(size-1)]:
            env = [q for q in range(size) if q not in supp]
            indices=[]
            for a in range(2**len(supp)):
                idx=np.zeros(2**len(env),dtype=int)
                for j,q in enumerate(supp):
                    idx |= ((a >> (len(supp)-1-j)) & 1) << (size-1-q)
                for j,q in enumerate(env):
                    idx |= ((np.arange(len(idx)) >> (len(env)-1-j)) & 1) << (size-1-q)
                indices.append(idx)
            self.replacements[supp]=indices

    def depolarize(self,rho,supp,p):
        if p == 0:
            return rho
        ids=self.replacements[supp]
        reduced=sum(rho[np.ix_(idx,idx)] for idx in ids)/len(ids)
        out=(1-p)*rho
        for idx in ids:
            out[np.ix_(idx,idx)] += p*reduced
        return out

    def x_layer(self,rho,angle,p):
        c,s=np.cos(angle),np.sin(angle)
        for q,f in enumerate(self.flips):
            # (cI-isX) rho (cI+isX), without dense matrix products.
            rho=c*c*rho+s*s*rho[np.ix_(f,f)]+1j*c*s*(rho[:,f]-rho[f,:])
            rho=self.depolarize(rho,(q,),p)
        return rho

    def zz_layer(self,rho,angle,p):
        for q,z in enumerate(self.zz):
            phase=np.exp(-1j*angle*z)
            rho=phase[:,None]*rho*phase.conj()[None,:]
            rho=self.depolarize(rho,(q,q+1),p)
        return rho

    def simulate(self,n,k,p,return_rho=False):
        rho=self.rho0.copy()
        dt=self.time/n
        for _ in range(n):
            if k == 1:
                rho=self.x_layer(rho,HX*dt,p)
                rho=self.zz_layer(rho,J*dt,p)
            elif k == 2:
                rho=self.x_layer(rho,HX*dt/2,p)
                rho=self.zz_layer(rho,J*dt,p)
                rho=self.x_layer(rho,HX*dt/2,p)
            else:
                raise ValueError('Only implemented orders: 1 and 2')
        assert abs(np.trace(rho)-1)<TOLERANCE
        assert np.max(np.abs(rho-rho.conj().T))<TOLERANCE
        expectation=float(np.real(np.dot(self.obs,np.diag(rho))))
        return (expectation,rho) if return_rho else expectation

    def gates(self,k):
        return self.L*(1 if k==1 else 2)+self.L-1
