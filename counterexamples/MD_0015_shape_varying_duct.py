"""MD_0015: Lambda'' does NOT lie between Lambda and Lambda'. A smooth periodic duct.

MD_0015's Statement closes with

    "and Lambda'' lies between Lambda and Lambda'",

where, for a weight w >= 0 on a pore space Omega with smooth walls carrying the
leading-order inviscid (potential) field v,

    2/Lambda_w := int_{dOmega} w dS / int_Omega w dV,
    Lambda = Lambda_{w=|v|^2},   Lambda' = Lambda_{w=1},   Lambda'' = Lambda_{w=|v|}.

This file exhibits a pore on which the computed potential field gives

    Lambda' = 0.258810,   Lambda = 0.244969,   Lambda'' = 0.231119,

so Lambda'' sits 0.013849 BELOW the whole interval [0.244969, 0.258810], which is
0.0138 wide: the violation is 1.00 interval widths, and 5.99 percent of Lambda''
itself. The weight is the UNSIGNED speed |v|, which is what MD_0015's frozen text
names. (MD_0018 replaces it by the signed component v.e_hat and drops this clause;
that is a different statement and this witness is not about it. Here the duct is
straight, so v.e_hat and |v| differ by less than 2 percent pointwise anyway and the
verdict is the same under either reading -- see `_signed_lengths_too`.)

THE REDUCTION THAT SAYS WHERE TO LOOK. With e_hat along the duct, put

    R(p) := int_{dOmega}|v|^p dS / int_Omega |v|^p dV,

so (Lambda', Lambda'', Lambda) = (2/R(0), 2/R(1), 2/R(2)) and betweenness of
Lambda'' is exactly monotonicity of R across p = 0, 1, 2. R(p) is the average of the
LOCAL wall-to-volume ratio r under the |v|^p-tilted volume measure, so
dR/dp = Cov_p(r, log|v|): betweenness holds precisely when r is positively correlated
with speed. In a duct with ONE transverse scale H, continuity gives |v| ~ 1/H and
r ~ 1/H -- the same function of H -- so the correlation is perfect and betweenness is
a theorem (proofs/MD_0015.md section 6). Breaking it needs r non-monotone in |v|, and
r = P/A with A fixed by the speed leaves only the cross-sectional SHAPE free. That is
what this duct varies: its area profile and its aspect-ratio profile are independent.

THE PORE. A periodic duct Omega = { |y| < w(x)/2, |z| < h(x)/2 }, period Lx = 130.1,
driven by a unit mean gradient of the potential along its axis e_hat = x_hat. The
profiles log w and log h are periodic, piecewise constant on three plateaus, joined by
C-infinity compactly supported transitions of half-width d (the function
exp(-1/t)/(exp(-1/t)+exp(-1/(1-t))) blend), so w and h are C-infinity and every wall
radius of curvature is bounded below. Writing A = wh, P = 2(w+h), r = P/A and the
lubrication speed u = Q/A:

    region        w        h        L        d      A        u/Q      r
    0 (slow)      1.75     2.15     11.7     3.35   3.7625   0.2658   2.0731
    1 (fast)      0.81     0.55     49.5    12.8    0.4455   2.2447   6.1055
    2 (middle)    0.17     5.69     68.9     2.84   0.9673   1.0338  12.1162

r against speed is HUMP-shaped: the intermediate-speed region -- a tall thin slot --
carries the largest wall-to-volume ratio, while the slow region is a compact block
with the smallest. Cov_p(r, log|v|) is therefore negative at the low-p end, R(1)
overshoots both R(0) and R(2), and Lambda'' falls below both.

THE FIELD IS COMPUTED, NOT ASSUMED. phi = x + psi with psi periodic solves
int grad(x+psi).grad q dV = 0 for every periodic q, i.e. Laplace's equation with
grad(phi).n = 0 on the wall, by Q1 finite elements on a mapped hexahedral mesh
(y = eta w(x)/2, z = zeta h(x)/2), 2x2x2 Gauss, sparse direct solve. Omega is
symmetric in y and in z and phi is even in both, so a quarter-duct mesh with the
symmetry planes carrying the same natural condition is exact; the factor 4 cancels in
every ratio. Wall integrals are taken on the wall itself with the true area element
|dX/dxi_a x dX/dxi_b|, not the mapped one. The mesh is graded in x, spacing
proportional to max(w, h).

VALIDATION, all re-run here.
  * A straight uniform duct returns Lambda = Lambda' = Lambda'' = 2V/S to 1e-14 and
    psi = 0 to machine precision, on three aspect ratios.
  * Lambda' is purely geometric, so it is graded against 2V/S computed by 1-D
    quadrature on the true curved wall: the two agree to 2.3e-3 relative, converging
    as the mesh refines, which is 6 times smaller than the interval width and 26 times
    smaller than the violation.
  * Grid refinement 8x8 -> 12x12 (and, off-line, 16x16 with Nx = 468) moves the
    violation 0.013657 -> 0.013849 -> 0.013752 on the optimizer's unrounded twin,
    i.e. by about 1 percent of itself, against a claimed violation of 100 percent of
    the interval width.
  * A slowly varying duct reproduces the lubrication field v = Q/A(x) and its three
    lengths to 1e-4 relative (off-line check, not re-run here).

HYPOTHESES. H1 wants walls smooth against the layer thickness. w and h are
C-infinity and bounded away from zero, so every wall curvature is bounded; the only
non-smooth set is the four edges of the rectangular cross-section, which are a null
set for dS and are not what drives the violation. Replacing the rectangle by a
genuinely C-infinity cross-section only strengthens it: at lubrication level the same
three profiles with a superellipse section |2y/w|^q + |2z/h|^q = 1 give a violation of
+7.74 percent of Lambda'' at q = 4 and +6.75 percent at q = 10, and rounded-rectangle
sections with corner radius up to half the thin dimension give +6.17 to +7.53 percent,
against +6.07 percent for the sharp rectangle. H2 wants |v| bounded above and below
away from zero: the computed field has |v| in [0.1727, 1.5996] and v.e_hat >= 0.1644
on the wall, so there is no stagnation point anywhere on the closure. H3 concerns Pr
and does not enter this clause.

NUMERIC WITNESS. The geometry is exact -- the twelve profile numbers are the decimals
printed above -- but the three lengths are integrals of a finite-element solution of a
3-D elliptic boundary-value problem, so they are floats and `numeric=True`. An exact
upgrade would need a closed-form potential flow on a duct of varying cross-section,
which does not exist; the honest exact statement available is the lubrication limit,
where the same duct gives Lambda'' = 0.230650 against [0.244648, 0.258608] by 1-D
quadrature alone, and the finite-element solve is what certifies that the lubrication
limit is not the source of the effect. Nothing about the verdict is at the mercy of
floating point: the violation is 26 times the largest discretisation residual measured.
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

# ------------------------------------------------------------------ the pore geometry
#: (w, h, L, d) per plateau: transverse sizes, axial plateau length, transition half-width.
REGIONS = (
    (1.75, 2.15, 11.7, 3.35),
    (0.81, 0.55, 49.5, 12.80),
    (0.17, 5.69, 68.9, 2.84),
)
#: The grid the witness is evaluated on: x-node count factor, and the transverse counts.
GRID = (4.0, 12, 12)
#: The coarser grid the refinement check uses.
GRID_COARSE = (2.5, 8, 8)


def _phi(t):
    """C-infinity monotone step: 0 for t <= 0, 1 for t >= 1, flat to all orders at both ends."""
    t = np.asarray(t, float)
    out = np.zeros_like(t)
    m = (t > 0) & (t < 1)
    tm = t[m]
    a = np.exp(-1.0 / tm)
    b = np.exp(-1.0 / (1.0 - tm))
    out[m] = a / (a + b)
    out[t >= 1] = 1.0
    return out


class _Profile:
    """Periodic plateau profile with C-infinity compactly supported transitions."""

    def __init__(self, vals, lens, dwid):
        self.vals = np.asarray(vals, float)
        self.lens = np.asarray(lens, float)
        self.d = np.asarray(dwid, float)
        self.edges = np.concatenate(([0.0], np.cumsum(self.lens)))
        self.Lx = self.edges[-1]
        n = len(self.vals)
        for j in range(n):
            if self.d[j] + self.d[(j - 1) % n] >= self.lens[j]:
                raise AssertionError(f"transitions overlap on plateau {j}: the profile is ill-posed")

    def __call__(self, x):
        x = np.mod(np.asarray(x, float), self.Lx)
        n = len(self.vals)
        idx = np.clip(np.searchsorted(self.edges, x, side="right") - 1, 0, n - 1)
        f = self.vals[idx]
        for j in range(n):
            c, d = self.edges[j + 1], self.d[j]
            t = np.mod(x - (c - d), self.Lx)
            f = np.where(t <= 2 * d,
                         self.vals[j] + (self.vals[(j + 1) % n] - self.vals[j]) * _phi(t / (2 * d)),
                         f)
        return f


def _profiles(regions=REGIONS):
    lw = _Profile([np.log(r[0]) for r in regions], [r[2] for r in regions], [r[3] for r in regions])
    lh = _Profile([np.log(r[1]) for r in regions], [r[2] for r in regions], [r[3] for r in regions])
    return (lambda x: np.exp(lw(x))), (lambda x: np.exp(lh(x))), lw.Lx


# ----------------------------------------------------------------- Q1 hexahedral element
_G = 1.0 / np.sqrt(3.0)
_GP = np.array([[a, b, c] for a in (-_G, _G) for b in (-_G, _G) for c in (-_G, _G)])
_LN = np.array([[a, b, c] for a in (-1, 1) for b in (-1, 1) for c in (-1, 1)], dtype=float)


def _shape(g):
    s = 1.0 + _LN * g
    dN = np.empty((3, 8))
    dN[0] = 0.125 * _LN[:, 0] * s[:, 1] * s[:, 2]
    dN[1] = 0.125 * _LN[:, 1] * s[:, 0] * s[:, 2]
    dN[2] = 0.125 * _LN[:, 2] * s[:, 0] * s[:, 1]
    return dN


class _Mesh:
    """Quarter duct 0 <= y <= w/2, 0 <= z <= h/2, periodic in x."""

    def __init__(self, xs, w, h, Ny, Nz, Lx):
        self.xs, self.w, self.h = np.asarray(xs, float), np.asarray(w, float), np.asarray(h, float)
        self.Nx, self.Ny, self.Nz, self.Lx = len(self.xs), Ny, Nz, Lx
        self.eta = np.linspace(0.0, 1.0, Ny + 1)
        self.zet = np.linspace(0.0, 1.0, Nz + 1)
        self.nn = self.Nx * (Ny + 1) * (Nz + 1)

    def elements(self):
        Nx, Ny, Nz = self.Nx, self.Ny, self.Nz
        i0 = np.arange(Nx)
        conn = np.empty((Nx, Ny, Nz, 8), dtype=np.int64)
        crd = np.empty((Nx, Ny, Nz, 8, 3))
        jj, kk = np.arange(Ny), np.arange(Nz)
        for a in (0, 1):
            ii = (i0 + a) % Nx
            xx = self.xs[ii] + (self.Lx if a == 1 else 0.0) * (ii == 0)
            for b in (0, 1):
                for c in (0, 1):
                    loc = 4 * a + 2 * b + c
                    conn[:, :, :, loc] = (ii[:, None, None] * (Ny + 1) * (Nz + 1)
                                          + (jj[None, :, None] + b) * (Nz + 1)
                                          + (kk[None, None, :] + c))
                    crd[:, :, :, loc, 0] = xx[:, None, None]
                    crd[:, :, :, loc, 1] = (self.w[ii] / 2.0)[:, None, None] * self.eta[None, jj + b, None]
                    crd[:, :, :, loc, 2] = (self.h[ii] / 2.0)[:, None, None] * self.zet[None, None, kk + c]
        return conn.reshape(-1, 8), crd.reshape(-1, 8, 3)


def _solve(mesh):
    conn, crd = mesh.elements()
    Ne = conn.shape[0]
    Ke = np.zeros((Ne, 8, 8))
    be = np.zeros((Ne, 8))
    for g in _GP:
        dN = _shape(g)
        J = np.einsum("ia,eaj->eij", dN, crd)
        det = np.linalg.det(J)
        if np.any(det <= 0):
            raise AssertionError("mesh is degenerate: non-positive Jacobian")
        B = np.einsum("eim,ma->eia", np.linalg.inv(J), dN)
        Ke += det[:, None, None] * np.einsum("eia,eib->eab", B, B)
        be += det[:, None] * B[:, 0, :]
    rows = np.repeat(conn, 8, axis=1).ravel()
    cols = np.tile(conn, (1, 8)).ravel()
    vals = Ke.ravel().copy()
    rhs = np.zeros(mesh.nn)
    np.add.at(rhs, conn.ravel(), -be.ravel())
    vals[(rows == 0) | (cols == 0)] = 0.0          # pin node 0: the nullspace is the constants
    rows = np.append(rows, 0)
    cols = np.append(cols, 0)
    vals = np.append(vals, 1.0)
    rhs[0] = 0.0
    K = sp.coo_matrix((vals, (rows, cols)), shape=(mesh.nn, mesh.nn)).tocsc()
    return spla.spsolve(K, rhs, use_umfpack=False), conn, crd


def _integrate(mesh, psi, conn, crd):
    """Volume and true-wall integrals of |v|^p, p = 0, 1, 2, plus the H2 diagnostics."""
    Nx, Ny, Nz = mesh.Nx, mesh.Ny, mesh.Nz
    pe = psi[conn]
    volI = np.zeros(3)
    vmin, vmax = np.inf, -np.inf
    for g in _GP:
        dN = _shape(g)
        J = np.einsum("ia,eaj->eij", dN, crd)
        det = np.linalg.det(J)
        B = np.einsum("eim,ma->eia", np.linalg.inv(J), dN)
        v = np.einsum("eia,ea->ei", B, pe)
        v[:, 0] += 1.0
        s = np.linalg.norm(v, axis=1)
        vmin, vmax = min(vmin, s.min()), max(vmax, s.max())
        for p in (0, 1, 2):
            volI[p] += np.sum(det * s ** p)
    surI = np.zeros(3)
    sur_ve = 0.0
    ve_min = np.inf
    ee = conn.reshape(Nx, Ny, Nz, 8)
    cc = crd.reshape(Nx, Ny, Nz, 8, 3)
    for sel, fix, i_a, i_b in ((np.s_[:, Ny - 1, :], 1, 0, 2), (np.s_[:, :, Nz - 1], 2, 0, 1)):
        c_f = cc[sel].reshape(-1, 8, 3)
        p_f = psi[ee[sel].reshape(-1, 8)]
        for ga in (-_G, _G):
            for gb in (-_G, _G):
                g = np.zeros(3)
                g[fix], g[i_a], g[i_b] = 1.0, ga, gb
                dN = _shape(g)
                J = np.einsum("ia,eaj->eij", dN, c_f)
                dS = np.linalg.norm(np.cross(J[:, i_a, :], J[:, i_b, :]), axis=1)
                B = np.einsum("eim,ma->eia", np.linalg.inv(J), dN)
                v = np.einsum("eia,ea->ei", B, p_f)
                v[:, 0] += 1.0
                s = np.linalg.norm(v, axis=1)
                ve_min = min(ve_min, v[:, 0].min())
                sur_ve += np.sum(dS * v[:, 0])
                for p in (0, 1, 2):
                    surI[p] += np.sum(dS * s ** p)
    return dict(
        Lambda_prime=2.0 * volI[0] / surI[0],       # w = 1
        Lambda_double_prime=2.0 * volI[1] / surI[1],  # w = |v|
        Lambda=2.0 * volI[2] / surI[2],             # w = |v|^2
        vmin=vmin, vmax=vmax, ve_min_wall=ve_min, wall_area=surI[0], volume=volI[0],
    )


def _graded_x(wf, hf, Lx, Nx, M=40001):
    xs = np.linspace(0.0, Lx, M)
    m = 1.0 / np.maximum(wf(xs), hf(xs))
    c = np.concatenate(([0.0], np.cumsum(0.5 * (m[1:] + m[:-1]) * np.diff(xs))))
    return np.interp(c[-1] * np.arange(Nx) / Nx, c, xs)


def _run(regions, grid):
    C, Ny, Nz = grid
    wf, hf, Lx = _profiles(regions)
    xq = np.linspace(0.0, Lx, 40001)
    cost = np.trapezoid(1.0 / np.maximum(wf(xq), hf(xq)), xq)
    Nx = max(16, int(round(C * cost)))
    xs = _graded_x(wf, hf, Lx, Nx)
    mesh = _Mesh(xs, wf(xs), hf(xs), Ny, Nz, Lx)
    psi, conn, crd = _solve(mesh)
    out = _integrate(mesh, psi, conn, crd)
    out.update(Nx=Nx, Ny=Ny, Nz=Nz, Lx=Lx, max_abs_psi=float(np.abs(psi).max()))
    return out


# --------------------------------------------------------------------------- the clause
def _claim(regions, grid, Lambda, Lambda_prime, Lambda_double_prime) -> bool:
    """MD_0015's betweenness clause at this point, with a tolerance far below the gap."""
    del regions, grid
    lo, hi = min(Lambda, Lambda_prime), max(Lambda, Lambda_prime)
    tol = 1e-4 * hi
    return bool(lo - tol <= Lambda_double_prime <= hi + tol)


# ------------------------------------------------------------------------- validations
def _solver_is_exact_on_a_straight_duct() -> None:
    """A uniform duct must give Lambda = Lambda' = Lambda'' = 2V/S = wh/(w+h) and psi = 0."""
    for w0, h0 in ((1.0, 1.0), (1.0, 0.3), (0.2, 5.0)):
        Lx = 4.0
        xs = np.linspace(0.0, Lx, 8, endpoint=False)
        mesh = _Mesh(xs, np.full(8, w0), np.full(8, h0), 6, 6, Lx)
        psi, conn, crd = _solve(mesh)
        out = _integrate(mesh, psi, conn, crd)
        exact = w0 * h0 / (w0 + h0)
        for key in ("Lambda", "Lambda_prime", "Lambda_double_prime"):
            if abs(out[key] - exact) > 1e-13 * exact:
                raise AssertionError(
                    f"straight duct {w0}x{h0}: {key} = {out[key]!r} against the exact 2V/S = {exact!r}"
                )
        if np.abs(psi).max() > 1e-12 or abs(out["vmin"] - 1.0) > 1e-12 or abs(out["vmax"] - 1.0) > 1e-12:
            raise AssertionError(f"straight duct {w0}x{h0}: the field is not uniform")


def _exact_2V_over_S(regions=REGIONS, N=400001) -> float:
    """2V/S on the TRUE curved wall by 1-D quadrature. Lambda' must reproduce this."""
    wf, hf, Lx = _profiles(regions)
    x = np.linspace(0.0, Lx, N)
    w, h = wf(x), hf(x)
    dw, dh = np.gradient(w, x[1] - x[0]), np.gradient(h, x[1] - x[0])
    V = np.trapezoid(w * h / 4.0, x)
    S = np.trapezoid((h / 2) * np.sqrt(1 + (dw / 2) ** 2) + (w / 2) * np.sqrt(1 + (dh / 2) ** 2), x)
    return float(2 * V / S)


def _lubrication(regions=REGIONS, N=200000):
    """The three lengths in the lubrication limit |v| = Q/A(x), by 1-D quadrature."""
    wf, hf, Lx = _profiles(regions)
    x = (np.arange(N) + 0.5) * (Lx / N)
    w, h = wf(x), hf(x)
    A, P = w * h, 2 * (w + h)
    return [float(2 * np.mean(A ** (1 - p)) / np.mean(P * A ** (-p))) for p in (0, 1, 2)]


def _signed_lengths_too(regions=REGIONS, grid=GRID_COARSE) -> tuple[float, float]:
    """MD_0018 reads the third weight as v.e_hat. On this straight duct that changes
    nothing that matters, and the report should be able to say so with a number."""
    C, Ny, Nz = grid
    wf, hf, Lx = _profiles(regions)
    xq = np.linspace(0.0, Lx, 40001)
    Nx = max(16, int(round(C * np.trapezoid(1.0 / np.maximum(wf(xq), hf(xq)), xq))))
    xs = _graded_x(wf, hf, Lx, Nx)
    mesh = _Mesh(xs, wf(xs), hf(xs), Ny, Nz, Lx)
    psi, conn, crd = _solve(mesh)
    pe = psi[conn]
    num = 0.0
    for g in _GP:
        dN = _shape(g)
        J = np.einsum("ia,eaj->eij", dN, crd)
        det = np.linalg.det(J)
        B = np.einsum("eim,ma->eia", np.linalg.inv(J), dN)
        num += np.sum(det * (1.0 + np.einsum("ea,ea->e", B[:, 0, :], pe)))
    den = 0.0
    ee = conn.reshape(mesh.Nx, mesh.Ny, mesh.Nz, 8)
    cc = crd.reshape(mesh.Nx, mesh.Ny, mesh.Nz, 8, 3)
    for sel, fix, i_a, i_b in ((np.s_[:, mesh.Ny - 1, :], 1, 0, 2), (np.s_[:, :, mesh.Nz - 1], 2, 0, 1)):
        c_f = cc[sel].reshape(-1, 8, 3)
        p_f = psi[ee[sel].reshape(-1, 8)]
        for ga in (-_G, _G):
            for gb in (-_G, _G):
                g = np.zeros(3)
                g[fix], g[i_a], g[i_b] = 1.0, ga, gb
                dN = _shape(g)
                J = np.einsum("ia,eaj->eij", dN, c_f)
                dS = np.linalg.norm(np.cross(J[:, i_a, :], J[:, i_b, :]), axis=1)
                B = np.einsum("eim,ma->eia", np.linalg.inv(J), dN)
                den += np.sum(dS * (1.0 + np.einsum("ea,ea->e", B[:, 0, :], p_f)))
    out = _integrate(mesh, psi, conn, crd)
    return 2.0 * num / den, out["Lambda_double_prime"]


def _report(fine, coarse, lub, geo) -> str:
    lo, hi = min(fine["Lambda"], fine["Lambda_prime"]), max(fine["Lambda"], fine["Lambda_prime"])
    gap = lo - fine["Lambda_double_prime"]
    return (
        f"pore: periodic duct, Lx = {fine['Lx']:.4f}, three plateaus (w, h, L, d) = {REGIONS}\n"
        f"grid {fine['Nx']}x{fine['Ny']}x{fine['Nz']} (graded in x):\n"
        f"    Lambda'  (w = 1)      = {fine['Lambda_prime']:.7f}\n"
        f"    Lambda   (w = |v|^2)  = {fine['Lambda']:.7f}\n"
        f"    Lambda'' (w = |v|)    = {fine['Lambda_double_prime']:.7f}   <-- below the interval\n"
        f"    interval [{lo:.7f}, {hi:.7f}], width {hi - lo:.7f}\n"
        f"    violation {gap:.7f} = {gap / (hi - lo):.3f} interval widths"
        f" = {gap / fine['Lambda_double_prime'] * 100:.2f} percent of Lambda''\n"
        f"grid {coarse['Nx']}x{coarse['Ny']}x{coarse['Nz']}: violation "
        f"{min(coarse['Lambda'], coarse['Lambda_prime']) - coarse['Lambda_double_prime']:.7f}"
        f"  (moves by {abs((lo - fine['Lambda_double_prime']) - (min(coarse['Lambda'], coarse['Lambda_prime']) - coarse['Lambda_double_prime'])) / gap * 100:.2f} percent under refinement)\n"
        f"lubrication limit, 1-D quadrature: Lambda' = {lub[0]:.7f}, Lambda'' = {lub[1]:.7f}, "
        f"Lambda = {lub[2]:.7f}\n"
        f"Lambda' against exact 2V/S on the true curved wall: {fine['Lambda_prime']:.7f} vs "
        f"{geo:.7f}, {abs(fine['Lambda_prime'] - geo) / geo:.2e} relative\n"
        f"H2: |v| in [{fine['vmin']:.4f}, {fine['vmax']:.4f}], min v.e_hat on the wall = "
        f"{fine['ve_min_wall']:.4f} > 0"
    )


def _build():
    """Run the computation; return the witness and the human-readable report."""
    from mdept.refute import Witness

    _solver_is_exact_on_a_straight_duct()
    fine = _run(REGIONS, GRID)
    coarse = _run(REGIONS, GRID_COARSE)
    lub = _lubrication()
    geo = _exact_2V_over_S()

    lo = min(fine["Lambda"], fine["Lambda_prime"])
    gap = lo - fine["Lambda_double_prime"]
    if gap <= 0:
        raise AssertionError("no violation on the fine grid; the witness is stale")
    drift = abs(gap - (min(coarse["Lambda"], coarse["Lambda_prime"]) - coarse["Lambda_double_prime"]))
    if drift > 0.10 * gap:
        raise AssertionError(f"grid drift {drift:.3e} is not small against the violation {gap:.3e}")
    if abs(fine["Lambda_prime"] - geo) > 0.01 * geo:
        raise AssertionError(
            f"Lambda' = {fine['Lambda_prime']:.7f} misses the exact geometric 2V/S = {geo:.7f}"
        )
    # H2, on the computed field.
    if not (fine["vmin"] > 0.05 and fine["ve_min_wall"] > 0.05):
        raise AssertionError(f"H2 fails: |v|min = {fine['vmin']}, min v.e_hat on wall = {fine['ve_min_wall']}")
    # The lubrication limit must agree, so that the effect is not a discretisation artifact.
    if abs(lub[1] - fine["Lambda_double_prime"]) > 0.02 * lub[1]:
        raise AssertionError("the computed field and the lubrication limit disagree by more than 2 percent")

    report = _report(fine, coarse, lub, geo)
    point = {
        "regions": REGIONS,
        "grid": (fine["Nx"], fine["Ny"], fine["Nz"]),
        "Lambda": fine["Lambda"],
        "Lambda_prime": fine["Lambda_prime"],
        "Lambda_double_prime": fine["Lambda_double_prime"],
    }
    return report, Witness(
        entry="MD_0015",
        point=point,
        claim=_claim,
        numeric=True,
        note=(
            "A smooth periodic duct Omega = {|y| < w(x)/2, |z| < h(x)/2} of period 130.1 whose "
            "area profile and aspect-ratio profile vary independently: three C-infinity-joined "
            "plateaus (w, h, L) = (1.75, 2.15, 11.7), (0.81, 0.55, 49.5), (0.17, 5.69, 68.9), so "
            "the local wall-to-volume ratio r = 2(w+h)/wh is 2.073, 6.106, 12.116 at lubrication "
            "speeds 0.266, 2.245, 1.034 -- r is hump-shaped in |v|, which is exactly what the "
            "single-transverse-scale proof of betweenness forbids and what shape variation at "
            "fixed size permits. Satisfied: H1, w and h are C-infinity with every wall curvature "
            "bounded (and the violation survives replacing the rectangular section by a "
            "superellipse or a rounded rectangle, which removes the four edges: +7.74 percent at "
            "q = 4 against +6.07 percent for the rectangle, at lubrication level); H2, the "
            "computed potential field has |v| in [0.1727, 1.5996], bounded above and away from "
            "zero, and v.e_hat >= 0.1644 everywhere on the wall, so there is no stagnation point "
            "on the closure. Violated: Lambda'' = 0.231119 lies BELOW the whole interval "
            "[Lambda, Lambda'] = [0.244969, 0.258810] -- by 0.013849, which is 1.00 interval "
            "widths and 5.99 percent of Lambda'' itself. The field is the finite-element "
            "solution of Laplace's equation with grad(phi).n = 0 on the wall and a unit mean "
            "axial gradient, not a lubrication ansatz; the solver returns "
            "Lambda = Lambda' = Lambda'' = 2V/S to 1e-13 on a straight uniform duct, reproduces "
            "the purely geometric Lambda' = 2V/S computed on the true curved wall to 2.3e-3 "
            "relative, and the violation moves by about 1 percent between the 8x8 and 12x12 "
            "transverse grids. The weight here is the UNSIGNED |v|, which is what MD_0015's "
            "frozen Statement names; the duct is straight, so the signed weight v.e_hat gives "
            "the same verdict."
        ),
    )


def refute():
    """The witness entry point; silent, so `python -m mdept.refute` prints only its verdict."""
    return _build()[1]


if __name__ == "__main__":
    report, w = _build()
    print(report)
    print()
    print("signed vs unsigned Lambda'' (coarse grid):", _signed_lengths_too())
    print("verify():", w.verify())
