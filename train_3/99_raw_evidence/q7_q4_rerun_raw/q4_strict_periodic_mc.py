import math
import csv
import json
from pathlib import Path
import numpy as np
from numba import njit

# =========================
# Problem constants (nm)
# =========================
L = 10000.0
H = L / 2.0
DELTA = 1.8
R_A = 30.0
LEN_A = 5000.0
HALF_A = LEN_A / 2.0
R_B = 200.0

TH_AA = 2 * R_A + DELTA       # 61.8 nm
TH_AB = R_A + R_B + DELTA     # 231.8 nm
TH_BB = 2 * R_B + DELTA       # 401.8 nm
TH_AE = R_A + DELTA           # 31.8 nm
TH_BE = R_B + DELTA           # 201.8 nm

V_A_UM3 = math.pi * (R_A / 1000.0) ** 2 * (LEN_A / 1000.0)
V_B_UM3 = 4.0 / 3.0 * math.pi * (R_B / 1000.0) ** 3
C_A = 1.05 * V_A_UM3
C_B = 0.05 * V_B_UM3

# Stateless RNG constants. Intentional uint64 wraparound.
C1 = np.uint64(0x9E3779B97F4A7C15)
C2 = np.uint64(0xBF58476D1CE4E5B9)
C3 = np.uint64(0x94D049BB133111EB)
TA = np.uint64(0xD2B74407B1CE6E93)
TB = np.uint64(0xCA5A826395121157)

@njit(cache=True)
def _splitmix64(x):
    z = np.uint64(x + C1)
    z = np.uint64((z ^ (z >> np.uint64(30))) * C2)
    z = np.uint64((z ^ (z >> np.uint64(27))) * C3)
    return np.uint64(z ^ (z >> np.uint64(31)))

@njit(cache=True)
def _u01(seed, trial, obj_type, idx, field):
    # Stable per-(trial,type,index,field) random number => exact CRN / prefix nesting.
    x = np.uint64(seed)
    x ^= np.uint64(trial + 1) * C1
    x ^= (TA if obj_type == 0 else TB)
    x ^= np.uint64(idx + 1) * C2
    x ^= np.uint64(field + 1) * C3
    z = _splitmix64(x)
    return float(z >> np.uint64(11)) * (1.0 / 9007199254740992.0)  # 2^-53

@njit(cache=True)
def _sample_A(seed, trial, idx):
    cx = -H + L * _u01(seed, trial, 0, idx, 0)
    cy = -H + L * _u01(seed, trial, 0, idx, 1)
    cz = -H + L * _u01(seed, trial, 0, idx, 2)
    mu = 2.0 * _u01(seed, trial, 0, idx, 3) - 1.0
    phi = 2.0 * math.pi * _u01(seed, trial, 0, idx, 4)
    s = math.sqrt(max(0.0, 1.0 - mu * mu))
    ux = s * math.cos(phi)
    uy = s * math.sin(phi)
    uz = mu
    a = np.empty(3, dtype=np.float64)
    b = np.empty(3, dtype=np.float64)
    a[0] = cx - HALF_A * ux; b[0] = cx + HALF_A * ux
    a[1] = cy - HALF_A * uy; b[1] = cy + HALF_A * uy
    a[2] = cz - HALF_A * uz; b[2] = cz + HALF_A * uz
    return a, b

@njit(cache=True)
def _sample_B(seed, trial, idx):
    c = np.empty(3, dtype=np.float64)
    c[0] = -H + L * _u01(seed, trial, 1, idx, 0)
    c[1] = -H + L * _u01(seed, trial, 1, idx, 1)
    c[2] = -H + L * _u01(seed, trial, 1, idx, 2)
    return c

@njit(cache=True)
def _A_crosses_x(a, b):
    xmin = min(a[0], b[0]) - R_A
    xmax = max(a[0], b[0]) + R_A
    return xmin < -H or xmax > H

@njit(cache=True)
def _B_crosses_x(c):
    return c[0] - R_B < -H or c[0] + R_B > H

@njit(cache=True)
def _bbox_intersects_D_for_A(a, b, sx, sy, sz):
    # Same interval-overlap semantics requested for B, generalized to capsule bbox.
    shifts = (sx * L, sy * L, sz * L)
    for d in range(3):
        lo = min(a[d], b[d]) + shifts[d] - R_A
        hi = max(a[d], b[d]) + shifts[d] + R_A
        if not (lo < H and hi > -H):
            return False
    return True

@njit(cache=True)
def _make_A_images(a, b, out_a, out_b):
    # Original first, then periodic return images whose capsule bbox intersects D.
    n = 0
    out_a[n, :] = a
    out_b[n, :] = b
    n += 1
    for sx in (-1, 0, 1):
        for sy in (-1, 0, 1):
            for sz in (-1, 0, 1):
                if sx == 0 and sy == 0 and sz == 0:
                    continue
                if _bbox_intersects_D_for_A(a, b, sx, sy, sz):
                    shx = sx * L; shy = sy * L; shz = sz * L
                    out_a[n, 0] = a[0] + shx; out_b[n, 0] = b[0] + shx
                    out_a[n, 1] = a[1] + shy; out_b[n, 1] = b[1] + shy
                    out_a[n, 2] = a[2] + shz; out_b[n, 2] = b[2] + shz
                    n += 1
    return n

@njit(cache=True)
def _make_B_images(c, out_c):
    # Exact algorithm specified by user: bounding-interval intersection with D.
    n = 0
    out_c[n, :] = c
    n += 1
    for sx in (-1, 0, 1):
        for sy in (-1, 0, 1):
            for sz in (-1, 0, 1):
                if sx == 0 and sy == 0 and sz == 0:
                    continue
                ct0 = c[0] + sx * L
                ct1 = c[1] + sy * L
                ct2 = c[2] + sz * L
                if (ct0 - R_B < H and ct0 + R_B > -H and
                    ct1 - R_B < H and ct1 + R_B > -H and
                    ct2 - R_B < H and ct2 + R_B > -H):
                    out_c[n, 0] = ct0
                    out_c[n, 1] = ct1
                    out_c[n, 2] = ct2
                    n += 1
    return n

@njit(cache=True)
def _point_seg_dist2(p, a, b):
    vx = b[0] - a[0]; vy = b[1] - a[1]; vz = b[2] - a[2]
    wx = p[0] - a[0]; wy = p[1] - a[1]; wz = p[2] - a[2]
    vv = vx*vx + vy*vy + vz*vz
    if vv <= 1e-30:
        dx = p[0]-a[0]; dy = p[1]-a[1]; dz = p[2]-a[2]
        return dx*dx + dy*dy + dz*dz
    t = (wx*vx + wy*vy + wz*vz) / vv
    if t < 0.0: t = 0.0
    elif t > 1.0: t = 1.0
    qx = a[0] + t*vx; qy = a[1] + t*vy; qz = a[2] + t*vz
    dx = p[0]-qx; dy = p[1]-qy; dz = p[2]-qz
    return dx*dx + dy*dy + dz*dz

@njit(cache=True)
def _seg_seg_dist2(p1, q1, p2, q2):
    # Closest distance between two finite 3-D segments (Ericson-style robust form).
    d1x=q1[0]-p1[0]; d1y=q1[1]-p1[1]; d1z=q1[2]-p1[2]
    d2x=q2[0]-p2[0]; d2y=q2[1]-p2[1]; d2z=q2[2]-p2[2]
    rx=p1[0]-p2[0]; ry=p1[1]-p2[1]; rz=p1[2]-p2[2]
    a=d1x*d1x+d1y*d1y+d1z*d1z
    e=d2x*d2x+d2y*d2y+d2z*d2z
    f=d2x*rx+d2y*ry+d2z*rz
    eps=1e-20
    if a <= eps and e <= eps:
        return rx*rx+ry*ry+rz*rz
    if a <= eps:
        s=0.0
        t=f/e
        if t<0.0:t=0.0
        elif t>1.0:t=1.0
    else:
        c=d1x*rx+d1y*ry+d1z*rz
        if e <= eps:
            t=0.0
            s=-c/a
            if s<0.0:s=0.0
            elif s>1.0:s=1.0
        else:
            b=d1x*d2x+d1y*d2y+d1z*d2z
            denom=a*e-b*b
            if abs(denom)>eps:
                s=(b*f-c*e)/denom
                if s<0.0:s=0.0
                elif s>1.0:s=1.0
            else:
                s=0.0
            t=(b*s+f)/e
            if t<0.0:
                t=0.0
                s=-c/a
                if s<0.0:s=0.0
                elif s>1.0:s=1.0
            elif t>1.0:
                t=1.0
                s=(b-c)/a
                if s<0.0:s=0.0
                elif s>1.0:s=1.0
    cx=(p1[0]+d1x*s)-(p2[0]+d2x*t)
    cy=(p1[1]+d1y*s)-(p2[1]+d2y*t)
    cz=(p1[2]+d1z*s)-(p2[2]+d2z*t)
    return cx*cx+cy*cy+cz*cz

@njit(cache=True)
def _seg_plane_x_dist(a, b, xp):
    lo = min(a[0], b[0]); hi = max(a[0], b[0])
    if lo <= xp <= hi:
        return 0.0
    return min(abs(a[0]-xp), abs(b[0]-xp))

@njit(cache=True)
def _find(parent, x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x

@njit(cache=True)
def _union(parent, rank, a, b):
    ra = _find(parent, a); rb = _find(parent, b)
    if ra == rb:
        return
    if rank[ra] < rank[rb]:
        parent[ra] = rb
    elif rank[ra] > rank[rb]:
        parent[rb] = ra
    else:
        parent[rb] = ra
        rank[ra] += 1

@njit(cache=True)
def simulate_one(NA, NB, seed, trial):
    # Returns Y_total, Y_self_A, Y_self_B, Y_self_any, Y_network_only
    # Fast exact self-short precheck from true x-boundary crossing.
    selfA = False
    selfB = False
    for i in range(NA):
        a, b = _sample_A(seed, trial, i)
        if _A_crosses_x(a, b):
            selfA = True
            break
    for j in range(NB):
        c = _sample_B(seed, trial, j)
        if _B_crosses_x(c):
            selfB = True
            break
    if selfA or selfB:
        return 1, 1 if selfA else 0, 1 if selfB else 0, 1, 0

    # No self-short: build actual periodic image sets and contact graph.
    nobj = NA + NB
    Lnode = nobj
    Rnode = nobj + 1
    parent = np.arange(nobj + 2, dtype=np.int64)
    rank = np.zeros(nobj + 2, dtype=np.int8)

    # At most 8 images for extents < L/2 under {-1,0,1} shifts; allocate 27 safely.
    A_a = np.empty((NA, 27, 3), dtype=np.float64)
    A_b = np.empty((NA, 27, 3), dtype=np.float64)
    A_n = np.empty(NA, dtype=np.int64)
    B_c = np.empty((NB, 27, 3), dtype=np.float64)
    B_n = np.empty(NB, dtype=np.int64)

    # Generate images + electrode contacts.
    for i in range(NA):
        a, b = _sample_A(seed, trial, i)
        n = _make_A_images(a, b, A_a[i], A_b[i])
        A_n[i] = n
        touchL = False; touchR = False
        for k in range(n):
            if _seg_plane_x_dist(A_a[i,k], A_b[i,k], -H) <= TH_AE:
                touchL = True
            if _seg_plane_x_dist(A_a[i,k], A_b[i,k], H) <= TH_AE:
                touchR = True
        if touchL: _union(parent, rank, i, Lnode)
        if touchR: _union(parent, rank, i, Rnode)

    for j in range(NB):
        c = _sample_B(seed, trial, j)
        n = _make_B_images(c, B_c[j])
        B_n[j] = n
        touchL = False; touchR = False
        for k in range(n):
            if abs(B_c[j,k,0] + H) <= TH_BE:
                touchL = True
            if abs(B_c[j,k,0] - H) <= TH_BE:
                touchR = True
        node = NA + j
        if touchL: _union(parent, rank, node, Lnode)
        if touchR: _union(parent, rank, node, Rnode)

    if _find(parent, Lnode) == _find(parent, Rnode):
        # This should be impossible after explicit self precheck, but keep safe.
        return 1, 0, 0, 0, 1

    thaa2 = TH_AA * TH_AA
    thab2 = TH_AB * TH_AB
    thbb2 = TH_BB * TH_BB

    # A-A
    for i in range(NA):
        for j in range(i+1, NA):
            linked = False
            for p in range(A_n[i]):
                for q in range(A_n[j]):
                    if _seg_seg_dist2(A_a[i,p], A_b[i,p], A_a[j,q], A_b[j,q]) <= thaa2:
                        linked = True; break
                if linked: break
            if linked:
                _union(parent, rank, i, j)

    # A-B
    for i in range(NA):
        for j in range(NB):
            linked = False
            for p in range(A_n[i]):
                for q in range(B_n[j]):
                    if _point_seg_dist2(B_c[j,q], A_a[i,p], A_b[i,p]) <= thab2:
                        linked = True; break
                if linked: break
            if linked:
                _union(parent, rank, i, NA+j)

    # B-B
    for i in range(NB):
        for j in range(i+1, NB):
            linked = False
            for p in range(B_n[i]):
                for q in range(B_n[j]):
                    dx=B_c[i,p,0]-B_c[j,q,0]
                    dy=B_c[i,p,1]-B_c[j,q,1]
                    dz=B_c[i,p,2]-B_c[j,q,2]
                    if dx*dx+dy*dy+dz*dz <= thbb2:
                        linked = True; break
                if linked: break
            if linked:
                _union(parent, rank, NA+i, NA+j)

    total = 1 if _find(parent, Lnode) == _find(parent, Rnode) else 0
    return total, 0, 0, 0, total

@njit(cache=True)
def run_mc_counts(NA, NB, M, seed, trial_offset=0):
    total = 0; selfA = 0; selfB = 0; selfAny = 0; networkOnly = 0
    for t in range(M):
        a,b,c,d,e = simulate_one(NA, NB, seed, trial_offset+t)
        total += a; selfA += b; selfB += c; selfAny += d; networkOnly += e
    return total, selfA, selfB, selfAny, networkOnly

def wilson(k, n, z=1.96):
    if n == 0:
        return (float('nan'), float('nan'))
    ph = k/n
    den = 1 + z*z/n
    cen = (ph + z*z/(2*n))/den
    rad = z*math.sqrt(ph*(1-ph)/n + z*z/(4*n*n))/den
    return cen-rad, cen+rad

def summarize(NA, NB, M, seed, trial_offset=0):
    counts = run_mc_counts(NA, NB, M, seed, trial_offset)
    kt, ka, kb, ks, kn = map(int, counts)
    lo, hi = wilson(kt, M)
    return {
        'N_A': NA, 'N_B': NB, 'M': M, 'seed': int(seed), 'trial_offset': trial_offset,
        'conduct_count': kt, 'self_A_count': ka, 'self_B_count': kb,
        'self_any_count': ks, 'network_only_count': kn,
        'p_hat': kt/M, 'wilson_low': lo, 'wilson_high': hi,
        'p_self_hat': ks/M, 'p_network_only_hat': kn/M,
        'cost_yuan': C_A*NA + C_B*NB,
        'certified_feasible': lo >= 0.90,
        'certified_infeasible': hi < 0.90,
        'status': 'FEASIBLE' if lo >= 0.90 else ('INFEASIBLE' if hi < 0.90 else 'UNRESOLVED')
    }

def analytic_p_self(NA, NB):
    pA = LEN_A/(2*L) + math.pi*R_A/(2*L)
    pB = 2*R_B/L
    return 1 - (1-pA)**NA * (1-pB)**NB

def unit_tests(seed=20260818):
    tests=[]
    # B image tests requested by user.
    def bimgs(c):
        out=np.empty((27,3),dtype=np.float64)
        n=_make_B_images(np.array(c,dtype=np.float64),out)
        return out[:n].copy()
    for name,c,expect_self in [
        ('B center (4900,0,0)', (4900.,0.,0.), True),
        ('B center (0,0,0)', (0.,0.,0.), False),
        ('B center (4950,0,0)', (4950.,0.,0.), True),
    ]:
        imgs=bimgs(c)
        tL=np.any(np.abs(imgs[:,0]+H)<=TH_BE)
        tR=np.any(np.abs(imgs[:,0]-H)<=TH_BE)
        actual=bool(tL and tR)
        tests.append({'test':name,'expected':expect_self,'actual':actual,'pass':actual==expect_self,'images':imgs.tolist()})

    # Test 4: one B self-short probability.
    M=100000
    k=0
    for t in range(M):
        c=_sample_B(np.uint64(seed),t,0)
        if _B_crosses_x(c): k+=1
    ph=k/M; target=0.04
    tests.append({'test':'single-B self-short MC','expected':target,'actual':ph,'abs_error':abs(ph-target),'pass':abs(ph-target)<0.005})

    # Test 5: N_B=57 at least one B self-short.
    k=0
    for t in range(M):
        hit=False
        for j in range(57):
            c=_sample_B(np.uint64(seed),t,j)
            if _B_crosses_x(c):
                hit=True; break
        if hit:k+=1
    ph=k/M; target=1-0.96**57
    tests.append({'test':'N_B=57 at least one self-short','expected':target,'actual':ph,'abs_error':abs(ph-target),'pass':abs(ph-target)<0.01})

    return tests

def main():
    outdir = Path(__file__).resolve().parent
    seed = np.uint64(20260818)

    tests = unit_tests(int(seed))
    (outdir/'unit_tests.json').write_text(json.dumps(tests,ensure_ascii=False,indent=2),encoding='utf-8')
    if not all(x['pass'] for x in tests):
        raise RuntimeError('Unit tests failed; refusing frontier MC.')

    # Cost frontier strictly cheaper than the analytic incumbent (0,57).
    frontier=[(0,56),(1,48),(2,39),(3,30),(4,21),(5,12),(6,3)]
    candidates=[(0,57)] + frontier
    rows=[]
    for NA,NB in candidates:
        r=summarize(NA,NB,50000,seed,0)
        r['analytic_p_self']=analytic_p_self(NA,NB)
        rows.append(r)
        print(r)

    with open(outdir/'q4_frontier_M50000.csv','w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    (outdir/'q4_frontier_M50000.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')

    meta={
        'L_nm':L,'delta_nm':DELTA,'rA_nm':R_A,'lenA_nm':LEN_A,'rB_nm':R_B,
        'thresholds_nm':{'AA':TH_AA,'AB':TH_AB,'BB':TH_BB,'A-electrode':TH_AE,'B-electrode':TH_BE},
        'V_A_um3':V_A_UM3,'V_B_um3':V_B_UM3,'cost_A_each':C_A,'cost_B_each':C_B,
        'seed':int(seed),
        'CRN':'stateless per-trial/per-type/per-index random stream; every candidate uses prefixes of the same A/B objects',
        'geometry_note':'A uses capsule-axis approximation with retained periodic images by bbox overlap; B follows requested center-image interval-overlap algorithm exactly.'
    }
    (outdir/'run_metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
    main()
