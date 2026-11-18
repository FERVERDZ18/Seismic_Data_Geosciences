"""Final optimized exhaustive control: identical source scalar factors cached O(N)."""
from spherical_weighted_v2 import np,njit,prange,radius_km,YEAR_SECONDS

@njit(cache=True)
def cached_candidate(t,s,c,l,factors,i,j,d):
    dt=t[i]-t[j]
    if dt<=0:return np.inf,np.nan,np.nan
    r=radius_km(s[i],c[i],l[i],s[j],c[j],l[j])
    return dt*(r*1000.)**d*factors[j],dt/YEAR_SECONDS,r

@njit(cache=True,parallel=True)
def cached_balanced_exhaustive(t,s,c,l,m,d,w):
    n=len(t);eta=np.full(n,np.inf);parent=np.full(n,-1,dtype=np.int64)
    dt=np.full(n,np.nan);radius=np.full(n,np.nan);factors=np.empty(n)
    # Same scalar pow expression and evaluation order as original candidate.
    # All O(N) factor preparation is inside this timed kernel.
    for j in range(n):factors[j]=10.**(-w*m[j])
    for offset in prange(n):
        i=offset//2 if offset%2==0 else n-1-offset//2
        best=np.inf;p=-1;bt=np.nan;br=np.nan
        for j in range(i):
            value,tv,rv=cached_candidate(t,s,c,l,factors,i,j,d)
            if value<best:best=value;p=j;bt=tv;br=rv
        eta[i]=best;parent[i]=p;dt[i]=bt;radius[i]=br
    return eta,parent,dt,radius

