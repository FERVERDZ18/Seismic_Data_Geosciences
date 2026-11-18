"""Auditable Python port of Ilya Zaliapin's normalmix_1D.m (GPL-3.0).

Derived from dttrugman/Nearest_Neighbor_Cluster commit
636d07beb89bde7d7deb502db78beebb45528cca, eq_cluster/normalmix_1D.m.
The upstream GPL and original bytes are preserved in authors_2013_exact/.
This is a port; actual unmodified .m executions are separately preserved.

The author EM estimates mixture weights, but the final boundary equation does
NOT include those weights. This behavior is preserved explicitly. New guards
only expose failure/iteration exhaustion and never supply a substitute cutoff.
"""
import math
import numpy as np


def author_normalmix(log_eta, max_iterations=10000):
    x=np.asarray(log_eta,dtype=float)
    x=x[np.isfinite(x)]
    result=dict(status='not_estimable',threshold_log10=None,finite_events=len(x),
                initial_means=[-6.,-3.],initial_sigmas=[1.,1.],parameter_tolerance=.001,
                cutoff_uses_mixture_weights=False,port_not_native_MATLAB=True,
                upstream_commit='636d07beb89bde7d7deb502db78beebb45528cca')
    if len(x)<2:return {**result,'reason':'insufficient_finite_input'}
    weight,weight2=.5,.5
    mu1,mu2,sigma1,sigma2=-6.,-3.,1.,1.
    for iteration in range(1,max_iterations+1):
        density1=weight/np.sqrt(2*np.pi*sigma1**2)*np.exp(-.5*((x-mu1)/sigma1)**2)
        density2=weight2/np.sqrt(2*np.pi*sigma2**2)*np.exp(-.5*((x-mu2)/sigma2)**2)
        denominator=density1+density2
        if np.any(denominator<=0) or not np.all(np.isfinite(denominator)):
            return {**result,'reason':'zero_or_nonfinite_posterior_denominator','iterations':iteration}
        p1,p2=density1/denominator,density2/denominator
        A,A2=float(np.sum(p1)/len(x)),float(np.sum(p2)/len(x))
        if min(np.sum(p1),np.sum(p2))<=0:
            return {**result,'reason':'empty_component','iterations':iteration}
        m1,m2=float(np.sum(p1*x)/np.sum(p1)),float(np.sum(p2*x)/np.sum(p2))
        s1=float(np.sqrt(np.sum(p1*(x-m1)**2)/np.sum(p1)))
        s2=float(np.sqrt(np.sum(p2*(x-m2)**2)/np.sum(p2)))
        epsilon=max(abs(weight-A),abs(mu1-m1),abs(mu2-m2),abs(sigma1-s1),abs(sigma2-s2))
        weight,weight2,mu1,mu2,sigma1,sigma2=A,A2,m1,m2,s1,s2
        if not all(math.isfinite(v) for v in (weight,weight2,mu1,mu2,sigma1,sigma2)) or min(sigma1,sigma2)<=0:
            return {**result,'reason':'degenerate_EM_parameters','iterations':iteration}
        if epsilon<=.001:break
    else:return {**result,'reason':'iteration_guard','iterations':max_iterations}
    aa=-2*sigma1**2+2*sigma2**2
    bb=2*mu2*2*sigma1**2-2*mu1*2*sigma2**2
    cc=-mu2**2*2*sigma1**2+mu1**2*2*sigma2**2-math.log(sigma2/sigma1)*2*sigma1**2*2*sigma2**2
    discriminant=bb**2-4*aa*cc
    result.update(means=[mu1,mu2],sigmas=[sigma1,sigma2],weights=[weight,weight2],
                  epsilon=epsilon,iterations=iteration,quadratic=[aa,bb,cc],discriminant=discriminant)
    if aa==0 or discriminant<0:
        return {**result,'reason':'no_finite_real_quadratic_boundary'}
    c1=(-bb+math.sqrt(discriminant))/(2*aa)
    c2=(-bb-math.sqrt(discriminant))/(2*aa)
    c=c1 if mu1<c1<mu2 else c2
    result.update(author_returned_boundary=c,boundary_between_means=bool(min(mu1,mu2)<c<max(mu1,mu2)))
    if not math.isfinite(c) or not result['boundary_between_means']:
        return {**result,'reason':'boundary_not_finite_between_component_means'}
    return {**result,'status':'estimable','threshold_log10':c,'reason':None}
