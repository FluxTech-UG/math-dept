import Mathlib.Algebra.BigOperators.Group.Finset.Basic
import Mathlib.Algebra.Module.LinearMap.Defs
import Mathlib.Data.Real.Basic
import Mathlib.Data.Fintype.Fin

/-!
# MD_0036: the embedded error estimate of a Runge-Kutta pair is killed by a linear first integral

## Informal statement

Let `V` be a real vector space, `ℓ : V → ℝ` linear and `f : V → V` any map with
`ℓ (f y) = 0` for every `y` (H0, H1). Fix `s ≥ 1` and coefficients `a i j`, `b i` (H2),
step sizes `h n`, start points `y n` and stage derivatives `k n i` (H3), stages that solve
their stage equation or are an FSAL reuse `k n 1 = f (z n)` with `z n ∈ {ỹ n, y n}` for
`n ≥ 1` (H4), post-step maps `P n` with `ℓ ∘ P n = ℓ` and
`y (n+1) = P n (y n + h n ∑ b i k n i)` (H5), and embedded weights `bhat i` (H8). Then for
every `n`, the error estimate `e n = h n ∑ (b i - bhat i) k n i` satisfies `ℓ (e n) = 0`.

## Conventions used here

* Stages are indexed by `Fin s`; the ledger's first stage `i = 1` is the index with
  `i.val = 0`. The hypothesis `_hs : 1 ≤ s` is carried as in H2; the proof does not use it.
* The FSAL point `ỹ n` (for `n ≥ 1`) is the explicit term
  `y (n-1) + h (n-1) • ∑ j, b j • k (n-1) j`, natural subtraction read only under `1 ≤ n`.
* The dense-output weights `β` of H2 do not enter H0 to H5, H8 or the conclusion, so they
  are omitted from the signature. H5 is carried in full even though the conclusion does
  not need it.
* The file is self-contained: it does not import MD_0033.

## Proof recipe

1. `ell_stage`: every disjunct of H4 makes `k n i` a value of `f`, so `ℓ (k n i) = 0`
   by H0.
2. `statement`: by linearity (`map_smul`, `map_sum`), `ℓ (e n)` is a combination of the
   `ℓ (k n i)`, all zero.
-/

namespace MathDept.MD_0036

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

theorem statement (ℓ : V →ₗ[ℝ] ℝ) (f : V → V) (s : ℕ) (_hs : 1 ≤ s)
    (a : Fin s → Fin s → ℝ) (b : Fin s → ℝ) (bhat : Fin s → ℝ)
    (h : ℕ → ℝ) (y : ℕ → V) (k : ℕ → Fin s → V) (P : ℕ → V → V)
    (H0 : ∀ v, ℓ (f v) = 0)
    (H4 : ∀ n i, k n i = f (y n + h n • ∑ j, a i j • k n j) ∨
      (1 ≤ n ∧ i.val = 0 ∧
        (k n i = f (y (n-1) + h (n-1) • ∑ j, b j • k (n-1) j) ∨ k n i = f (y n))))
    (_H5P : ∀ n v, ℓ (P n v) = ℓ v)
    (_H5 : ∀ n, y (n+1) = P n (y n + h n • ∑ i, b i • k n i)) :
    ∀ n, ℓ (h n • ∑ i, (b i - bhat i) • k n i) = 0 := by
  intro n
  simp [map_smul, map_sum, ell_stage ℓ f s a b h y k H0 H4 n]

end MathDept.MD_0036
