import Mathlib.Algebra.BigOperators.Group.Finset.Basic
import Mathlib.Algebra.Order.BigOperators.Group.Finset
import Mathlib.Algebra.Module.LinearMap.Defs
import Mathlib.Order.Interval.Set.Defs
import Mathlib.Data.Real.Basic
import Mathlib.Data.Fintype.Fin
import Mathlib.Algebra.BigOperators.Ring.Finset
import Mathlib.Tactic.Ring

/-!
# MD_0038: per-step drift bound when the invariant holds only to a tolerance

## Informal statement

Let `V` be a real vector space, `ℓ : V → ℝ` linear and `f : V → V` any map with
`|ℓ (f y)| ≤ δ` for every `y`, where `δ ≥ 0` (H0', H1). Fix `s ≥ 1`, coefficients
`a i j`, `b i` and arbitrary dense-output weights `β i` (H2). Take step sizes `h n ≥ 0`,
start points `y n` and stage derivatives `k n i` (H3), with end point
`ỹ (n+1) = y n + h n ∑ b i k n i`. Every stage solves its stage equation or (for `n ≥ 1`
and the first stage) is an FSAL reuse `k n 1 = f (z n)`, `z n ∈ {ỹ n, y n}` (H4). The
post-step maps `P n` preserve `ℓ` and `y (n+1) = P n (ỹ (n+1))` (H5). The dense output
on step `n` is `u n θ = y n + h n ∑ β i θ k n i` (H6). Then for every `n` and every
`θ ∈ [0, 1]`,

  `|ℓ (u n θ) - ℓ (y 0)| ≤ δ ((∑_{m < n} h m) ∑ |b i| + h n ∑ |β i θ|)`.

With `β i 1 = b i` and `B` bounding `∑ |β i θ|` on `[0, 1]`, the right side is at most
`δ (t (n+1) - t 0) B`, where `t (m+1) = t m + h m`.

## Conventions used here

* Stages are indexed by `Fin s`; the ledger's first stage `i = 1` is the index with
  `i.val = 0`. The hypotheses `hs : 1 ≤ s` (H2) and `hδ : 0 ≤ δ` (H0') are carried as
  stated; `statement` uses neither (`statement_elapsed` uses `hδ`).
* `ỹ (n+1)`, `u n θ` and the FSAL point `ỹ n` (for `n ≥ 1`) are written out as explicit
  terms: `ỹ n` is `y (n-1) + h (n-1) • ∑ j, b j • k (n-1) j`, with natural subtraction,
  read only under `1 ≤ n`.
* `β i` is a function `ℝ → ℝ`; only its values on `Set.Icc 0 1` enter the conclusion.
* `∑_{m < n}` is `∑ m ∈ Finset.range n`.
* The corollary `statement_elapsed` takes `B` as any real with `∑ i, |β i θ| ≤ B` for every
  `θ ∈ [0, 1]`. The ledger's `B` is the supremum, which is such a bound whenever it is
  finite, so this form implies the ledger's. The node times `t` are a sequence with
  `t (m+1) = t m + h m`; `t 0` is free.

## Proof recipe

1. `abs_ell_stage`: every disjunct of H4 makes `k n i` a value of `f`, so
   `|ℓ (k n i)| ≤ δ` by H0'.
2. `abs_ell_comb`: by linearity and `Finset.abs_sum_le_sum_abs`,
   `|ℓ (c • ∑ i, w i • k n i)| ≤ δ (c ∑ |w i|)` for `c ≥ 0`.
3. `abs_ell_y`: induction on `n`: `ℓ (y (n+1)) = ℓ (y n) + ℓ (h n • ∑ b i • k n i)` by H5,
   then the triangle inequality and step 2 with `w = b`.
4. `statement`: split `ℓ (u n θ) - ℓ (y 0)` as `(ℓ (y n) - ℓ (y 0)) + ℓ (h n • …)` and use
   steps 3 and 2.
5. `statement_elapsed`: `∑ |b i| = ∑ |β i 1| ≤ B`, `∑ |β i θ| ≤ B`, and
   `t (n+1) - t 0 = ∑_{m < n+1} h m`.
-/

namespace MathDept.MD_0038

open Finset

variable {V : Type*} [AddCommGroup V] [Module ℝ V]

/-- Step 1: every stage derivative is a value of `f`, hence `|ℓ (k n i)| ≤ δ`. -/
theorem abs_ell_stage (ℓ : V →ₗ[ℝ] ℝ) (f : V → V) (δ : ℝ) (s : ℕ) (a : Fin s → Fin s → ℝ)
    (b : Fin s → ℝ) (h : ℕ → ℝ) (y : ℕ → V) (k : ℕ → Fin s → V)
    (H0 : ∀ v, |ℓ (f v)| ≤ δ)
    (H4 : ∀ n i, k n i = f (y n + h n • ∑ j, a i j • k n j) ∨
      (1 ≤ n ∧ i.val = 0 ∧
        (k n i = f (y (n-1) + h (n-1) • ∑ j, b j • k (n-1) j) ∨ k n i = f (y n))))
    (n : ℕ) (i : Fin s) : |ℓ (k n i)| ≤ δ := by
  rcases H4 n i with hk | ⟨_, _, hk | hk⟩ <;> rw [hk] <;> exact H0 _

/-- Step 2: a nonnegative multiple of a combination of the stages moves `ℓ` by at most
`δ c ∑ |w i|`. -/
theorem abs_ell_comb (ℓ : V →ₗ[ℝ] ℝ) (δ : ℝ) (s : ℕ) (kn : Fin s → V)
    (hk : ∀ i, |ℓ (kn i)| ≤ δ) (c : ℝ) (hc : 0 ≤ c) (w : Fin s → ℝ) :
    |ℓ (c • ∑ i, w i • kn i)| ≤ δ * (c * ∑ i, |w i|) := by
  rw [map_smul, map_sum, smul_eq_mul, abs_mul, abs_of_nonneg hc]
  have h1 : |∑ i, ℓ (w i • kn i)| ≤ ∑ i, |w i| * δ := by
    refine (Finset.abs_sum_le_sum_abs _ _).trans (Finset.sum_le_sum fun i _ => ?_)
    rw [map_smul, smul_eq_mul, abs_mul]
    exact mul_le_mul_of_nonneg_left (hk i) (abs_nonneg _)
  rw [← Finset.sum_mul] at h1
  calc c * |∑ i, ℓ (w i • kn i)| ≤ c * ((∑ i, |w i|) * δ) :=
        mul_le_mul_of_nonneg_left h1 hc
    _ = δ * (c * ∑ i, |w i|) := by ring

/-- Step 3: drift of the start points. -/
theorem abs_ell_y (ℓ : V →ₗ[ℝ] ℝ) (δ : ℝ) (s : ℕ) (b : Fin s → ℝ)
    (h : ℕ → ℝ) (hh : ∀ n, 0 ≤ h n) (y : ℕ → V) (k : ℕ → Fin s → V) (P : ℕ → V → V)
    (hk : ∀ n i, |ℓ (k n i)| ≤ δ)
    (H5P : ∀ n v, ℓ (P n v) = ℓ v)
    (H5 : ∀ n, y (n+1) = P n (y n + h n • ∑ i, b i • k n i)) (n : ℕ) :
    |ℓ (y n) - ℓ (y 0)| ≤ δ * ((∑ m ∈ Finset.range n, h m) * ∑ i, |b i|) := by
  induction n with
  | zero => simp
  | succ n ih =>
    have hstep : ℓ (y (n+1)) - ℓ (y 0) =
        (ℓ (y n) - ℓ (y 0)) + ℓ (h n • ∑ i, b i • k n i) := by
      rw [H5, H5P, map_add]; ring
    rw [hstep, Finset.sum_range_succ]
    have h2 := abs_ell_comb ℓ δ s (k n) (hk n) (h n) (hh n) b
    calc |(ℓ (y n) - ℓ (y 0)) + ℓ (h n • ∑ i, b i • k n i)|
        ≤ |ℓ (y n) - ℓ (y 0)| + |ℓ (h n • ∑ i, b i • k n i)| := abs_add_le _ _
      _ ≤ δ * ((∑ m ∈ Finset.range n, h m) * ∑ i, |b i|) + δ * (h n * ∑ i, |b i|) :=
          add_le_add ih h2
      _ = δ * ((∑ m ∈ Finset.range n, h m + h n) * ∑ i, |b i|) := by ring

theorem statement (ℓ : V →ₗ[ℝ] ℝ) (f : V → V) (δ : ℝ) (hδ : 0 ≤ δ)
    (H0 : ∀ v, |ℓ (f v)| ≤ δ) (s : ℕ) (hs : 1 ≤ s)
    (a : Fin s → Fin s → ℝ) (b : Fin s → ℝ) (β : Fin s → ℝ → ℝ)
    (h : ℕ → ℝ) (hh : ∀ n, 0 ≤ h n) (y : ℕ → V) (k : ℕ → Fin s → V) (P : ℕ → V → V)
    (H4 : ∀ n i, k n i = f (y n + h n • ∑ j, a i j • k n j) ∨
      (1 ≤ n ∧ i.val = 0 ∧
        (k n i = f (y (n-1) + h (n-1) • ∑ j, b j • k (n-1) j) ∨ k n i = f (y n))))
    (H5P : ∀ n v, ℓ (P n v) = ℓ v)
    (H5 : ∀ n, y (n+1) = P n (y n + h n • ∑ i, b i • k n i)) :
    ∀ n, ∀ θ ∈ Set.Icc (0:ℝ) 1,
      |ℓ (y n + h n • ∑ i, β i θ • k n i) - ℓ (y 0)| ≤
        δ * ((∑ m ∈ Finset.range n, h m) * ∑ i, |b i| + h n * ∑ i, |β i θ|) := by
  intro n θ _
  have hk := abs_ell_stage ℓ f δ s a b h y k H0 H4
  have hy := abs_ell_y ℓ δ s b h hh y k P hk H5P H5 n
  have hu := abs_ell_comb ℓ δ s (k n) (hk n) (h n) (hh n) (fun i => β i θ)
  have hsplit : ℓ (y n + h n • ∑ i, β i θ • k n i) - ℓ (y 0) =
      (ℓ (y n) - ℓ (y 0)) + ℓ (h n • ∑ i, β i θ • k n i) := by
    rw [map_add]; ring
  rw [hsplit]
  calc |(ℓ (y n) - ℓ (y 0)) + ℓ (h n • ∑ i, β i θ • k n i)|
      ≤ |ℓ (y n) - ℓ (y 0)| + |ℓ (h n • ∑ i, β i θ • k n i)| := abs_add_le _ _
    _ ≤ _ := add_le_add hy hu
    _ = _ := by ring

/-- The ledger's corollary: the elapsed time runs to the end of the step holding the read
point. -/
theorem statement_elapsed (ℓ : V →ₗ[ℝ] ℝ) (f : V → V) (δ : ℝ) (hδ : 0 ≤ δ)
    (H0 : ∀ v, |ℓ (f v)| ≤ δ) (s : ℕ) (hs : 1 ≤ s)
    (a : Fin s → Fin s → ℝ) (b : Fin s → ℝ) (β : Fin s → ℝ → ℝ)
    (h : ℕ → ℝ) (hh : ∀ n, 0 ≤ h n) (y : ℕ → V) (k : ℕ → Fin s → V) (P : ℕ → V → V)
    (H4 : ∀ n i, k n i = f (y n + h n • ∑ j, a i j • k n j) ∨
      (1 ≤ n ∧ i.val = 0 ∧
        (k n i = f (y (n-1) + h (n-1) • ∑ j, b j • k (n-1) j) ∨ k n i = f (y n))))
    (H5P : ∀ n v, ℓ (P n v) = ℓ v)
    (H5 : ∀ n, y (n+1) = P n (y n + h n • ∑ i, b i • k n i))
    (hβ1 : ∀ i, β i 1 = b i) (B : ℝ) (hB : ∀ θ ∈ Set.Icc (0:ℝ) 1, ∑ i, |β i θ| ≤ B)
    (t : ℕ → ℝ) (ht : ∀ m, t (m+1) = t m + h m) :
    ∀ n, ∀ θ ∈ Set.Icc (0:ℝ) 1,
      |ℓ (y n + h n • ∑ i, β i θ • k n i) - ℓ (y 0)| ≤ δ * (t (n+1) - t 0) * B := by
  intro n θ hθ
  have hmain := statement ℓ f δ hδ H0 s hs a b β h hh y k P H4 H5P H5 n θ hθ
  have hb : ∑ i, |b i| ≤ B := by
    have := hB 1 ⟨zero_le_one, le_refl _⟩
    simpa only [hβ1] using this
  have htel : ∀ m, t m - t 0 = ∑ j ∈ Finset.range m, h j := by
    intro m
    induction m with
    | zero => simp
    | succ m ih => rw [Finset.sum_range_succ, ← ih, ht]; ring
  have hsum0 : 0 ≤ ∑ m ∈ Finset.range n, h m := Finset.sum_nonneg fun m _ => hh m
  have hinner : (∑ m ∈ Finset.range n, h m) * ∑ i, |b i| + h n * ∑ i, |β i θ| ≤
      (t (n+1) - t 0) * B := by
    rw [htel, Finset.sum_range_succ, add_mul]
    exact add_le_add (mul_le_mul_of_nonneg_left hb hsum0)
      (mul_le_mul_of_nonneg_left (hB θ hθ) (hh n))
  calc _ ≤ _ := hmain
    _ ≤ δ * ((t (n+1) - t 0) * B) := mul_le_mul_of_nonneg_left hinner hδ
    _ = _ := by ring

end MathDept.MD_0038
