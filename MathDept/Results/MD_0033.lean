import Mathlib.Algebra.BigOperators.Group.Finset.Basic
import Mathlib.Algebra.Module.LinearMap.Defs
import Mathlib.Order.Interval.Set.Defs
import Mathlib.Data.Real.Basic
import Mathlib.Data.Fintype.Fin

/-!
# MD_0033: a Runge-Kutta run with FSAL and an invariant-preserving post-step map keeps a linear first integral, dense output included

## Informal statement

Let `V` be a real vector space, `ℓ : V → ℝ` linear and `f : V → V` any map with
`ℓ (f y) = 0` for every `y` (H0, H1). Fix `s ≥ 1`, coefficients `a i j`, `b i` and
arbitrary dense-output weights `β i : [0, 1] → ℝ` (H2). Take step sizes `h n`, start
points `y n` and stage derivatives `k n i` for `n ∈ ℕ` (H3), with end point
`ỹ (n+1) = y n + h n ∑ b i k n i`. Every stage either solves its stage equation
`k n i = f (y n + h n ∑ a i j k n j)`, or (for `n ≥ 1` and the first stage) is an FSAL
reuse `k n 1 = f (z n)` with `z n ∈ {ỹ n, y n}` (H4). The post-step maps `P n` preserve
`ℓ` and `y (n+1) = P n (ỹ (n+1))` (H5). The dense output on step `n` is
`u n θ = y n + h n ∑ β i θ k n i` (H6). Then for every `n` and every `θ ∈ [0, 1]`,
`ℓ (u n θ) = ℓ (y 0)` and `ℓ (ỹ (n+1)) = ℓ (y (n+1)) = ℓ (y 0)`.

## Conventions used here

* Stages are indexed by `Fin s`; the ledger's first stage `i = 1` is the index with
  `i.val = 0`. The hypothesis `_hs : 1 ≤ s` is carried as in H2; the proof does not use it.
* `ỹ (n+1)`, `u n θ` and the FSAL point `ỹ n` (for `n ≥ 1`) are written out as explicit
  terms: `ỹ n` is `y (n-1) + h (n-1) • ∑ j, b j • k (n-1) j`, with natural subtraction,
  read only under `1 ≤ n`.
* `β i` is a function `ℝ → ℝ`; only its values on `Set.Icc 0 1` enter the conclusion.
* The piecewise output `u(t) = u n ((t - t n) / h n)` on `[t n, t (n+1)]` is a
  reparametrization of the family `u n θ`, so the statement is given in the `(n, θ)`
  form; the `t` form follows by substitution and is not formalized.
* `y 0` is the given initial point; no hypothesis constrains it.

## Proof recipe

1. `ell_stage`: every disjunct of H4 makes `k n i` a value of `f`, so `ℓ (k n i) = 0`
   by H0.
2. `ell_comb`: by linearity, `ℓ (y n + c • ∑ i, w i • k n i) = ℓ (y n)` for any scalar `c`
   and weights `w`.
3. `ell_y`: induction on `n`, using H5 and step 2 with `w = b`.
4. `statement`: steps 2 and 3, with `w = fun i => β i θ` and `w = b`.
-/

namespace MathDept.MD_0033

open Finset

variable {V : Type*} [AddCommGroup V] [Module ℝ V]

/-- Step 1: every stage derivative is a value of `f`, hence killed by `ℓ`. -/
theorem ell_stage (ℓ : V →ₗ[ℝ] ℝ) (f : V → V) (s : ℕ) (a : Fin s → Fin s → ℝ)
    (b : Fin s → ℝ) (h : ℕ → ℝ) (y : ℕ → V) (k : ℕ → Fin s → V)
    (H0 : ∀ v, ℓ (f v) = 0)
    (H4 : ∀ n i, k n i = f (y n + h n • ∑ j, a i j • k n j) ∨
      (1 ≤ n ∧ i.val = 0 ∧
        (k n i = f (y (n-1) + h (n-1) • ∑ j, b j • k (n-1) j) ∨ k n i = f (y n))))
    (n : ℕ) (i : Fin s) : ℓ (k n i) = 0 := by
  rcases H4 n i with hk | ⟨_, _, hk | hk⟩ <;> rw [hk, H0]

/-- Step 2: a combination of the stages does not move `ℓ`. -/
theorem ell_comb (ℓ : V →ₗ[ℝ] ℝ) (s : ℕ) (yn : V) (kn : Fin s → V)
    (hk : ∀ i, ℓ (kn i) = 0) (c : ℝ) (w : Fin s → ℝ) :
    ℓ (yn + c • ∑ i, w i • kn i) = ℓ yn := by
  simp [map_add, map_smul, map_sum, hk]

theorem statement (ℓ : V →ₗ[ℝ] ℝ) (f : V → V) (s : ℕ) (_hs : 1 ≤ s)
    (a : Fin s → Fin s → ℝ) (b : Fin s → ℝ) (β : Fin s → ℝ → ℝ)
    (h : ℕ → ℝ) (y : ℕ → V) (k : ℕ → Fin s → V) (P : ℕ → V → V)
    (H0 : ∀ v, ℓ (f v) = 0)
    (H4 : ∀ n i, k n i = f (y n + h n • ∑ j, a i j • k n j) ∨
      (1 ≤ n ∧ i.val = 0 ∧
        (k n i = f (y (n-1) + h (n-1) • ∑ j, b j • k (n-1) j) ∨ k n i = f (y n))))
    (H5P : ∀ n v, ℓ (P n v) = ℓ v)
    (H5 : ∀ n, y (n+1) = P n (y n + h n • ∑ i, b i • k n i)) :
    ∀ n, ∀ θ ∈ Set.Icc (0:ℝ) 1,
      ℓ (y n + h n • ∑ i, β i θ • k n i) = ℓ (y 0) ∧
      ℓ (y n + h n • ∑ i, b i • k n i) = ℓ (y 0) ∧
      ℓ (y (n+1)) = ℓ (y 0) := by
  have hk := ell_stage ℓ f s a b h y k H0 H4
  -- Step 3.
  have hy : ∀ n, ℓ (y n) = ℓ (y 0) := by
    intro n
    induction n with
    | zero => rfl
    | succ m ih => rw [H5, H5P, ell_comb ℓ s _ _ (hk m), ih]
  intro n θ _
  refine ⟨?_, ?_, hy (n+1)⟩
  · rw [ell_comb ℓ s _ _ (hk n), hy n]
  · rw [ell_comb ℓ s _ _ (hk n), hy n]

end MathDept.MD_0033
