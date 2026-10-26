import Mathlib.RingTheory.RootsOfUnity.Complex
import Mathlib.Algebra.Field.GeomSum
import Mathlib.Algebra.BigOperators.Fin

/-!
# MD_0035: the spectral derivative with zeroed Nyquist mode has zero grid sum

## Informal statement

Let `N ≥ 2` be even, `L > 0`, `ω = exp (2πi/N)`, and for `g ∈ ℂ^N` let
`ĝ_m = ∑_j g_j ω^{-jm}`. With wavenumbers `κ_m = 2πm/L` for `0 ≤ m < N/2`,
`κ_{N/2} = 0`, `κ_m = 2π(m - N)/L` for `N/2 < m < N`, the spectral derivative
`(D g)_j = (1/N) ∑_m i κ_m ĝ_m ω^{jm}` satisfies `∑_j (D g)_j = 0`.

## Conventions used here

* Grid and mode indices are `Fin N`; the value of an index in `{0, ..., N-1}` is its
  `Fin.val`. All powers of `ω` are integer powers (`zpow`) with exponent
  `(j : ℤ) * (m : ℤ)` (or its negative), so `ω^{-jm}` is written literally.
* `κ` is real-valued and enters `D` through the coercion `ℝ → ℂ`; `I` is the imaginary
  unit. `N/2` is natural-number division, exact because `N` is even.
* `L` is a parameter of `κ` and `D`; the hypotheses `2 ≤ N`, `Even N`, `0 < L` are
  carried by `statement` as in the ledger (only `N ≠ 0` is used).

## Proof recipe

1. `sum_omega_zpow`: for `n ≥ 1` and `q : ℤ`, `∑_{j : Fin n} ω_n^{j q}` is `n` when
   `n ∣ q` and `0` otherwise (`ω_n` is a primitive `n`-th root of unity; for `n ∤ q`,
   `ω_n^q ≠ 1` and the geometric sum of `ω_n^q` over `n` terms vanishes).
2. `kappa_zero`: `κ_0 = 0`.
3. `statement`: swap the two sums; the `m`-th term carries `∑_j ω^{jm}`, which vanishes
   for `0 < m < N`; the `m = 0` term carries `κ_0 = 0`.
-/

namespace MathDept.MD_0035

open Complex Finset

/-- `ω_n = exp (2πi/n)`. -/
noncomputable def omega (n : ℕ) : ℂ := Complex.exp (2 * Real.pi * I / n)

/-- H2: `ĝ_m = ∑_j g_j ω^{-jm}`. -/
noncomputable def hat (N : ℕ) (g : Fin N → ℂ) (m : Fin N) : ℂ :=
  ∑ j : Fin N, g j * omega N ^ (-(((j : ℕ) : ℤ) * ((m : ℕ) : ℤ)))

/-- H3: wavenumbers with the Nyquist mode zeroed. -/
noncomputable def kappa (N : ℕ) (L : ℝ) (m : Fin N) : ℝ :=
  if (m : ℕ) < N / 2 then 2 * Real.pi * (m : ℕ) / L
  else if (m : ℕ) = N / 2 then 0
  else 2 * Real.pi * (((m : ℕ) : ℝ) - N) / L

/-- H4: `(D g)_j = (1/N) ∑_m i κ_m ĝ_m ω^{jm}`. -/
noncomputable def D (N : ℕ) (L : ℝ) (g : Fin N → ℂ) (j : Fin N) : ℂ :=
  (1 / (N : ℂ)) * ∑ m : Fin N,
    I * (kappa N L m : ℂ) * hat N g m * omega N ^ (((j : ℕ) : ℤ) * ((m : ℕ) : ℤ))

lemma omega_isPrimitiveRoot (n : ℕ) (hn : n ≠ 0) : IsPrimitiveRoot (omega n) n := by
  unfold omega
  exact Complex.isPrimitiveRoot_exp n hn

/-- Orthogonality of the characters `j ↦ ω_n^{jq}`. -/
lemma sum_omega_zpow (n : ℕ) (hn : n ≠ 0) (q : ℤ) :
    ∑ j : Fin n, omega n ^ (((j : ℕ) : ℤ) * q) = if (n : ℤ) ∣ q then (n : ℂ) else 0 := by
  have hp := omega_isPrimitiveRoot n hn
  have hrw : ∀ j : Fin n, omega n ^ (((j : ℕ) : ℤ) * q) = (omega n ^ q) ^ (j : ℕ) := by
    intro j
    rw [mul_comm, zpow_mul, zpow_natCast]
  simp_rw [hrw]
  rw [Fin.sum_univ_eq_sum_range (fun i => (omega n ^ q) ^ i) n]
  split_ifs with hd
  · rw [(hp.zpow_eq_one_iff_dvd q).mpr hd]
    simp
  · have hne : omega n ^ q ≠ 1 := fun h => hd ((hp.zpow_eq_one_iff_dvd q).mp h)
    rw [geom_sum_eq hne]
    have : (omega n ^ q) ^ n = 1 := by
      rw [← zpow_natCast, ← zpow_mul, mul_comm, zpow_mul, zpow_natCast, hp.pow_eq_one, one_zpow]
    rw [this]
    simp

lemma kappa_zero (N : ℕ) (L : ℝ) (m : Fin N) (hm : (m : ℕ) = 0) (hN : 2 ≤ N) :
    kappa N L m = 0 := by
  unfold kappa
  have : (m : ℕ) < N / 2 := by omega
  rw [if_pos this, hm]
  simp

theorem statement :
    ∀ (N : ℕ) (_hN : 2 ≤ N) (_heven : Even N) (L : ℝ) (_hL : 0 < L) (g : Fin N → ℂ),
      ∑ j : Fin N, D N L g j = 0 := by
  intro N hN _ L _ g
  have hN0 : N ≠ 0 := by omega
  unfold D
  rw [← Finset.mul_sum, Finset.sum_comm]
  simp_rw [← Finset.mul_sum]
  apply mul_eq_zero_of_right
  apply Finset.sum_eq_zero
  intro m _
  rw [sum_omega_zpow N hN0]
  by_cases hm : (m : ℕ) = 0
  · rw [kappa_zero N L m hm hN]
    simp
  · have : ¬ (N : ℤ) ∣ ((m : ℕ) : ℤ) := by
      intro hd
      have := Int.le_of_dvd (by omega) hd
      omega
    simp [this]

end MathDept.MD_0035
