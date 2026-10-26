import Mathlib.RingTheory.RootsOfUnity.Complex
import Mathlib.Algebra.Field.GeomSum
import Mathlib.Algebra.BigOperators.Fin
import Mathlib.Algebra.Order.Group.Int

/-!
# MD_0039: the 3/2-rule dealiased product satisfies discrete integration by parts

## Informal statement

Let `N ≥ 2` be even, `M = 3N/2`, `L > 0`, `ω_N = exp (2πi/N)`, `ω_M = exp (2πi/M)`, and
`ĝ_m = ∑_j g_j ω_N^{-jm}`, extended `N`-periodically in `m ∈ ℤ`. Let `D` be the spectral
derivative of MD_0035, `(Dg)_j = (1/N) ∑_{m=0}^{N-1} i κ_m ĝ_m ω_N^{jm}` with `κ_m = 2πm/L`
for `0 ≤ m < N/2`, `κ_{N/2} = 0`, `κ_m = 2π(m-N)/L` for `N/2 < m < N`. The embedding is
`(Eg)_p = (1/N) (∑_{m=-N/2+1}^{N/2-1} ĝ_m ω_M^{pm} + ½ ĝ_{N/2} (ω_M^{pN/2} + ω_M^{-pN/2}))`
for `p ∈ {0, ..., M-1}`, the product coefficients are
`c_q = (1/M) ∑_p (Ea)_p (Eb)_p ω_M^{-pq}`, and
`Π(a, b)_j = ∑_{q=-N/2+1}^{N/2-1} c_q ω_N^{jq}`. Then for all `a, b ∈ ℂ^N`,
`∑_j (Π(a, Db)_j + Π(b, Da)_j) = 0`.

## Conventions used here

* Grid indices are `Fin N` (and `Fin M` on the fine grid); the mode index of `D` is
  `Fin N` read through `Fin.val`, as in MD_0035. Signed mode indices are integers: `ĝ` is
  `hat N g : ℤ → ℂ`, defined by the H1 sum for every integer `m`, which is the
  `N`-periodic extension. All powers of `ω` are integer powers (`zpow`).
* `N/2` is natural division cast to `ℤ` (exact since `N` is even); the signed range
  `m = -N/2+1, ..., N/2-1` is `Finset.Ioo (-(N/2)) (N/2)` in `ℤ`. `M = 3 * N / 2` in `ℕ`.
* `D`, `κ`, `ω`, `ĝ` are restated here (not imported from MD_0035) with the same
  definitions, so the file is self-contained.

## Proof recipe

1. `sum_omega_zpow`: `∑_{j : Fin n} ω_n^{jq} = n` if `n ∣ q`, else `0`.
2. `sum_Pi`: `∑_j Π(x, y)_j = N c_0`, since among `|q| < N/2` only `q = 0` is a multiple
   of `N`.
3. `E_eq`: `(Eg)_p = ∑_{m=-N/2}^{N/2} (w_m ĝ_m / N) ω_M^{pm}` with weight `w_m = ½` at
   `m = ±N/2` and `1` otherwise (uses `ĝ_{-N/2} = ĝ_{N/2}`, `hat_neg_half`).
4. `sum_prod_modes`: for coefficient functions `A, B`, the fine-grid sum of the product
   of two such mode sums is `M ∑_m A_m B_{-m}`: `m + m' ≡ 0 (mod M)` with
   `|m|, |m'| ≤ N/2 < M/2` forces `m' = -m`. This is where the dealiasing makes the
   identity exact.
5. `hat_D`: for `|m| ≤ N/2`, `(Dg)^_m = i κˢ_m ĝ_m` with the signed, odd wavenumber
   `κˢ_m = 2πm/L` for `|m| < N/2` and `0` at `m = ±N/2` (`exists_rep`, the Nyquist zero).
6. `pair_cancel` and `statement`: `c_0(a, Db) + c_0(b, Da)` is a sum over `m` of
   `w_m w_{-m} â_m b̂_{-m} i (κˢ_{-m} + κˢ_m) / N²` after reindexing `m ↦ -m` in the
   second sum, and `κˢ` is odd.
-/

namespace MathDept.MD_0039

open Complex Finset

/-- `ω_n = exp (2πi/n)`. -/
noncomputable def omega (n : ℕ) : ℂ := Complex.exp (2 * Real.pi * I / n)

/-- H1: `ĝ_m = ∑_j g_j ω_N^{-jm}` for every integer `m` (the `N`-periodic extension). -/
noncomputable def hat (N : ℕ) (g : Fin N → ℂ) (m : ℤ) : ℂ :=
  ∑ j : Fin N, g j * omega N ^ (-(((j : ℕ) : ℤ) * m))

/-- H2: wavenumbers with the Nyquist mode zeroed (MD_0035, H3). -/
noncomputable def kappa (N : ℕ) (L : ℝ) (m : Fin N) : ℝ :=
  if (m : ℕ) < N / 2 then 2 * Real.pi * (m : ℕ) / L
  else if (m : ℕ) = N / 2 then 0
  else 2 * Real.pi * (((m : ℕ) : ℝ) - N) / L

/-- H2: `(D g)_j = (1/N) ∑_{m=0}^{N-1} i κ_m ĝ_m ω_N^{jm}`. -/
noncomputable def D (N : ℕ) (L : ℝ) (g : Fin N → ℂ) (j : Fin N) : ℂ :=
  (1 / (N : ℂ)) * ∑ m : Fin N,
    I * (kappa N L m : ℂ) * hat N g ((m : ℕ) : ℤ) * omega N ^ (((j : ℕ) : ℤ) * ((m : ℕ) : ℤ))

/-- H1: `M = 3N/2`. -/
def M (N : ℕ) : ℕ := 3 * N / 2

/-- H3: the embedding of `g` on the `M`-point grid, Nyquist mode as a cosine. -/
noncomputable def E (N : ℕ) (g : Fin N → ℂ) (p : Fin (M N)) : ℂ :=
  (1 / (N : ℂ)) *
    (∑ m ∈ Ioo (-((N / 2 : ℕ) : ℤ)) ((N / 2 : ℕ) : ℤ),
        hat N g m * omega (M N) ^ (((p : ℕ) : ℤ) * m)
      + (1 / 2) * hat N g ((N / 2 : ℕ) : ℤ) *
        (omega (M N) ^ (((p : ℕ) : ℤ) * ((N / 2 : ℕ) : ℤ))
          + omega (M N) ^ (-(((p : ℕ) : ℤ) * ((N / 2 : ℕ) : ℤ)))))

/-- H4: the coefficients `c_q = (1/M) ∑_p (Ea)_p (Eb)_p ω_M^{-pq}`. -/
noncomputable def c (N : ℕ) (a b : Fin N → ℂ) (q : ℤ) : ℂ :=
  (1 / (M N : ℂ)) * ∑ p : Fin (M N), E N a p * E N b p * omega (M N) ^ (-(((p : ℕ) : ℤ) * q))

/-- H4: `Π(a, b)_j = ∑_{q=-N/2+1}^{N/2-1} c_q ω_N^{jq}`. -/
noncomputable def Pi (N : ℕ) (a b : Fin N → ℂ) (j : Fin N) : ℂ :=
  ∑ q ∈ Ioo (-((N / 2 : ℕ) : ℤ)) ((N / 2 : ℕ) : ℤ), c N a b q * omega N ^ (((j : ℕ) : ℤ) * q)

/-! ### Roots of unity -/

lemma omega_isPrimitiveRoot (n : ℕ) (hn : n ≠ 0) : IsPrimitiveRoot (omega n) n := by
  unfold omega
  exact Complex.isPrimitiveRoot_exp n hn

lemma omega_ne_zero (n : ℕ) : omega n ≠ 0 := Complex.exp_ne_zero _

lemma omega_zpow_mul_self (n : ℕ) (hn : n ≠ 0) (k : ℤ) : omega n ^ ((n : ℤ) * k) = 1 := by
  rw [zpow_mul, zpow_natCast, (omega_isPrimitiveRoot n hn).pow_eq_one, one_zpow]

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

/-! ### Periodicity of the transform -/

lemma hat_periodic (N : ℕ) (hN : N ≠ 0) (g : Fin N → ℂ) (m t : ℤ) :
    hat N g (m + N * t) = hat N g m := by
  unfold hat
  apply Finset.sum_congr rfl
  intro j _
  rw [show -(((j : ℕ) : ℤ) * (m + N * t)) = -(((j : ℕ) : ℤ) * m) + (N : ℤ) * (-(j * t)) by ring,
    zpow_add₀ (omega_ne_zero N), omega_zpow_mul_self N hN, mul_one]

lemma hat_neg_half (N : ℕ) (hN : 2 ≤ N) (heven : Even N) (g : Fin N → ℂ) :
    hat N g (-((N / 2 : ℕ) : ℤ)) = hat N g ((N / 2 : ℕ) : ℤ) := by
  have he := Nat.even_iff.mp heven
  rw [← hat_periodic N (by omega) g (-((N / 2 : ℕ) : ℤ)) 1]
  congr 1
  omega

/-! ### Step 2: the grid sum of `Π` -/

lemma sum_Pi (N : ℕ) (hN : 2 ≤ N) (x y : Fin N → ℂ) :
    ∑ j : Fin N, Pi N x y j = N * c N x y 0 := by
  unfold Pi
  rw [Finset.sum_comm]
  simp_rw [← Finset.mul_sum]
  simp_rw [sum_omega_zpow N (by omega : N ≠ 0)]
  have key : ∀ q ∈ Ioo (-((N / 2 : ℕ) : ℤ)) ((N / 2 : ℕ) : ℤ),
      c N x y q * (if (N : ℤ) ∣ q then (N : ℂ) else 0) = if q = 0 then N * c N x y q else 0 := by
    intro q hq
    rw [Finset.mem_Ioo] at hq
    by_cases h0 : q = 0
    · subst h0; simp [mul_comm]
    · have : ¬ (N : ℤ) ∣ q := by
        intro hd
        apply h0
        apply Int.eq_zero_of_abs_lt_dvd hd
        rw [abs_lt]; constructor <;> omega
      simp [this, h0]
  rw [Finset.sum_congr rfl key, Finset.sum_ite_eq']
  rw [if_pos (by rw [Finset.mem_Ioo]; omega)]

/-! ### Step 3: the embedding as one sum over `|m| ≤ N/2` -/

/-- The weight of mode `m` in the embedding: `½` at `m = ±N/2`, else `1`. -/
noncomputable def wt (N : ℕ) (m : ℤ) : ℂ :=
  if m = ((N / 2 : ℕ) : ℤ) ∨ m = -((N / 2 : ℕ) : ℤ) then 1 / 2 else 1

lemma E_eq (N : ℕ) (hN : 2 ≤ N) (heven : Even N) (g : Fin N → ℂ) (p : Fin (M N)) :
    E N g p = ∑ m ∈ Icc (-((N / 2 : ℕ) : ℤ)) ((N / 2 : ℕ) : ℤ),
      (wt N m * hat N g m / N) * omega (M N) ^ (((p : ℕ) : ℤ) * m) := by
  set h : ℤ := ((N / 2 : ℕ) : ℤ) with hh
  have h1 : 1 ≤ h := by omega
  rw [show Icc (-h) h = insert h (insert (-h) (Ioo (-h) h)) by
    ext m; simp only [Finset.mem_Icc, Finset.mem_insert, Finset.mem_Ioo]; omega]
  rw [Finset.sum_insert (by simp only [Finset.mem_insert, Finset.mem_Ioo]; omega),
    Finset.sum_insert (by simp only [Finset.mem_Ioo]; omega)]
  have hw1 : wt N h = 1 / 2 := by simp [wt, ← hh]
  have hw2 : wt N (-h) = 1 / 2 := by simp [wt, ← hh]
  have hS : ∑ m ∈ Ioo (-h) h, (wt N m * hat N g m / N) * omega (M N) ^ (((p : ℕ) : ℤ) * m)
      = (1 / (N : ℂ)) * ∑ m ∈ Ioo (-h) h, hat N g m * omega (M N) ^ (((p : ℕ) : ℤ) * m) := by
    rw [Finset.mul_sum]
    apply Finset.sum_congr rfl
    intro m hm
    rw [Finset.mem_Ioo] at hm
    have : wt N m = 1 := by
      unfold wt; rw [if_neg (by omega)]
    rw [this]; ring
  rw [hS, hw1, hw2, hat_neg_half N hN heven g,
    show ((p : ℕ) : ℤ) * (-h) = -(((p : ℕ) : ℤ) * h) by ring]
  unfold E
  rw [← hh]
  ring

/-! ### Step 4: the fine-grid sum of a product of two mode sums -/

lemma sum_prod_modes (N : ℕ) (hN : 2 ≤ N) (heven : Even N) (A B : ℤ → ℂ) :
    ∑ p : Fin (M N),
      (∑ m ∈ Icc (-((N / 2 : ℕ) : ℤ)) ((N / 2 : ℕ) : ℤ), A m * omega (M N) ^ (((p : ℕ) : ℤ) * m)) *
      (∑ m ∈ Icc (-((N / 2 : ℕ) : ℤ)) ((N / 2 : ℕ) : ℤ), B m * omega (M N) ^ (((p : ℕ) : ℤ) * m))
    = (M N : ℂ) * ∑ m ∈ Icc (-((N / 2 : ℕ) : ℤ)) ((N / 2 : ℕ) : ℤ), A m * B (-m) := by
  have he := Nat.even_iff.mp heven
  have hM : ((M N : ℕ) : ℤ) = 3 * ((N / 2 : ℕ) : ℤ) := by unfold M; omega
  have hM0 : M N ≠ 0 := by unfold M; omega
  set h : ℤ := ((N / 2 : ℕ) : ℤ) with hh
  simp_rw [Finset.sum_mul_sum]
  rw [Finset.sum_comm, Finset.mul_sum]
  apply Finset.sum_congr rfl
  intro m hm
  rw [Finset.sum_comm]
  have inner : ∀ m' ∈ Icc (-h) h, ∑ p : Fin (M N),
      A m * omega (M N) ^ (((p : ℕ) : ℤ) * m) * (B m' * omega (M N) ^ (((p : ℕ) : ℤ) * m'))
      = if m' = -m then (M N : ℂ) * (A m * B (-m)) else 0 := by
    intro m' hm'
    rw [Finset.mem_Icc] at hm hm'
    have : ∀ p : Fin (M N),
        A m * omega (M N) ^ (((p : ℕ) : ℤ) * m) * (B m' * omega (M N) ^ (((p : ℕ) : ℤ) * m'))
        = A m * B m' * omega (M N) ^ (((p : ℕ) : ℤ) * (m + m')) := by
      intro p
      rw [mul_add, zpow_add₀ (omega_ne_zero _)]
      ring
    rw [Finset.sum_congr rfl (fun p _ => this p), ← Finset.mul_sum, sum_omega_zpow _ hM0]
    by_cases hmm : m' = -m
    · subst hmm; simp [mul_comm]
    · have : ¬ ((M N : ℕ) : ℤ) ∣ m + m' := by
        intro hd
        apply hmm
        have := Int.eq_zero_of_abs_lt_dvd hd (by rw [abs_lt]; constructor <;> omega)
        omega
      simp [this, hmm]
  rw [Finset.sum_congr rfl inner, Finset.sum_ite_eq']
  rw [Finset.mem_Icc] at hm
  rw [if_pos (by rw [Finset.mem_Icc]; omega)]

/-! ### Step 5: the transform of `D g` on `|m| ≤ N/2` -/

/-- The signed wavenumber: `2πm/L` for `|m| < N/2`, `0` otherwise (in particular at
`m = ±N/2`). -/
noncomputable def kappaS (N : ℕ) (L : ℝ) (m : ℤ) : ℝ :=
  if -((N / 2 : ℕ) : ℤ) < m ∧ m < ((N / 2 : ℕ) : ℤ) then 2 * Real.pi * m / L else 0

lemma kappaS_neg (N : ℕ) (L : ℝ) (m : ℤ) : kappaS N L (-m) = -kappaS N L m := by
  unfold kappaS
  by_cases hm : -((N / 2 : ℕ) : ℤ) < m ∧ m < ((N / 2 : ℕ) : ℤ)
  · rw [if_pos hm, if_pos (by omega)]
    push_cast; ring
  · rw [if_neg hm, if_neg (by omega)]; simp

/-- Every `|m| ≤ N/2` has a representative `k` in `{0, ..., N-1}` whose wavenumber is the
signed one. -/
lemma exists_rep (N : ℕ) (hN : 2 ≤ N) (heven : Even N) (L : ℝ) (m : ℤ)
    (hm : m ∈ Icc (-((N / 2 : ℕ) : ℤ)) ((N / 2 : ℕ) : ℤ)) :
    ∃ k : Fin N, (N : ℤ) ∣ ((k : ℕ) : ℤ) - m ∧ kappa N L k = kappaS N L m := by
  have he := Nat.even_iff.mp heven
  rw [Finset.mem_Icc] at hm
  by_cases c1 : 0 ≤ m ∧ m < ((N / 2 : ℕ) : ℤ)
  · have hk : ((m.toNat : ℕ) : ℤ) = m := Int.toNat_of_nonneg c1.1
    refine ⟨⟨m.toNat, by omega⟩, ?_, ?_⟩
    · show (N : ℤ) ∣ ((m.toNat : ℕ) : ℤ) - m
      rw [hk, sub_self]; exact dvd_zero _
    · unfold kappa kappaS
      show (if m.toNat < N / 2 then 2 * Real.pi * ((m.toNat : ℕ) : ℝ) / L
        else if m.toNat = N / 2 then 0 else 2 * Real.pi * (((m.toNat : ℕ) : ℝ) - N) / L) = _
      rw [if_pos (by omega), if_pos (by omega)]
      have : ((m.toNat : ℕ) : ℝ) = (m : ℝ) := by exact_mod_cast hk
      rw [this]
  by_cases c2 : m = ((N / 2 : ℕ) : ℤ) ∨ m = -((N / 2 : ℕ) : ℤ)
  · refine ⟨⟨N / 2, by omega⟩, ?_, ?_⟩
    · show (N : ℤ) ∣ ((N / 2 : ℕ) : ℤ) - m
      rcases c2 with c2 | c2
      · rw [c2, sub_self]; exact dvd_zero _
      · exact ⟨1, by omega⟩
    · unfold kappa kappaS
      show (if N / 2 < N / 2 then 2 * Real.pi * ((N / 2 : ℕ) : ℝ) / L
        else if N / 2 = N / 2 then 0 else 2 * Real.pi * (((N / 2 : ℕ) : ℝ) - N) / L) = _
      rw [if_neg (lt_irrefl _), if_pos rfl, if_neg (by omega)]
  · have hk : (((m + N).toNat : ℕ) : ℤ) = m + N := Int.toNat_of_nonneg (by omega)
    refine ⟨⟨(m + N).toNat, by omega⟩, ?_, ?_⟩
    · show (N : ℤ) ∣ (((m + N).toNat : ℕ) : ℤ) - m
      exact ⟨1, by omega⟩
    · unfold kappa kappaS
      show (if (m + N).toNat < N / 2 then 2 * Real.pi * (((m + N).toNat : ℕ) : ℝ) / L
        else if (m + N).toNat = N / 2 then 0
        else 2 * Real.pi * ((((m + N).toNat : ℕ) : ℝ) - N) / L) = _
      rw [if_neg (by omega), if_neg (by omega), if_pos (by omega)]
      have : (((m + N).toNat : ℕ) : ℝ) = (m : ℝ) + N := by exact_mod_cast hk
      rw [this]; ring

lemma hat_D (N : ℕ) (hN : 2 ≤ N) (heven : Even N) (L : ℝ) (g : Fin N → ℂ) (m : ℤ)
    (hm : m ∈ Icc (-((N / 2 : ℕ) : ℤ)) ((N / 2 : ℕ) : ℤ)) :
    hat N (D N L g) m = I * (kappaS N L m : ℂ) * hat N g m := by
  have hN0 : N ≠ 0 := by omega
  obtain ⟨k, hkd, hkk⟩ := exists_rep N hN heven L m hm
  calc hat N (D N L g) m
      = ∑ j : Fin N, ∑ m' : Fin N, (1 / (N : ℂ) * (I * (kappa N L m' : ℂ) * hat N g ((m' : ℕ) : ℤ)))
          * omega N ^ (((j : ℕ) : ℤ) * (((m' : ℕ) : ℤ) - m)) := by
        rw [hat]
        apply Finset.sum_congr rfl
        intro j _
        unfold D
        rw [Finset.mul_sum, Finset.sum_mul]
        apply Finset.sum_congr rfl
        intro m' _
        rw [show ((j : ℕ) : ℤ) * (((m' : ℕ) : ℤ) - m)
            = ((j : ℕ) : ℤ) * ((m' : ℕ) : ℤ) + -(((j : ℕ) : ℤ) * m) by ring,
          zpow_add₀ (omega_ne_zero N)]
        ring
    _ = ∑ m' : Fin N, (1 / (N : ℂ) * (I * (kappa N L m' : ℂ) * hat N g ((m' : ℕ) : ℤ)))
          * (if (N : ℤ) ∣ ((m' : ℕ) : ℤ) - m then (N : ℂ) else 0) := by
        rw [Finset.sum_comm]
        apply Finset.sum_congr rfl
        intro m' _
        rw [← Finset.mul_sum, sum_omega_zpow N hN0]
    _ = ∑ m' : Fin N, if m' = k then I * (kappaS N L m : ℂ) * hat N g m else 0 := by
        apply Finset.sum_congr rfl
        intro m' _
        by_cases hmk : m' = k
        · rw [hmk, if_pos hkd, if_pos rfl, hkk]
          obtain ⟨t, ht⟩ := hkd
          rw [show ((k : ℕ) : ℤ) = m + N * t by omega, hat_periodic N hN0]
          field_simp
        · have hnd : ¬ (N : ℤ) ∣ ((m' : ℕ) : ℤ) - m := by
            intro hd
            apply hmk
            have h3 := dvd_sub hd hkd
            rw [show ((m' : ℕ) : ℤ) - m - (((k : ℕ) : ℤ) - m) = ((m' : ℕ) : ℤ) - ((k : ℕ) : ℤ) by
              ring] at h3
            have := m'.isLt
            have := k.isLt
            have h4 := Int.eq_zero_of_abs_lt_dvd h3 (by rw [abs_lt]; constructor <;> omega)
            exact Fin.ext (by omega)
          rw [if_neg hnd, if_neg hmk, mul_zero]
    _ = I * (kappaS N L m : ℂ) * hat N g m := by
        rw [Finset.sum_ite_eq']
        simp

/-! ### Step 6: pairing `m` with `-m` -/

lemma sum_neg_reindex (N : ℕ) (f : ℤ → ℂ) :
    ∑ m ∈ Icc (-((N / 2 : ℕ) : ℤ)) ((N / 2 : ℕ) : ℤ), f m
      = ∑ m ∈ Icc (-((N / 2 : ℕ) : ℤ)) ((N / 2 : ℕ) : ℤ), f (-m) := by
  apply Finset.sum_nbij' (fun m => -m) (fun m => -m)
  · intro m hm; simp only [Finset.mem_Icc] at hm ⊢; omega
  · intro m hm; simp only [Finset.mem_Icc] at hm ⊢; omega
  · intro m _; simp
  · intro m _; simp
  · intro m _; simp

lemma pair_cancel (N : ℕ) (F G : ℤ → ℂ)
    (hFG : ∀ m ∈ Icc (-((N / 2 : ℕ) : ℤ)) ((N / 2 : ℕ) : ℤ), F m + G (-m) = 0) :
    ∑ m ∈ Icc (-((N / 2 : ℕ) : ℤ)) ((N / 2 : ℕ) : ℤ), F m
      + ∑ m ∈ Icc (-((N / 2 : ℕ) : ℤ)) ((N / 2 : ℕ) : ℤ), G m = 0 := by
  rw [sum_neg_reindex N G, ← Finset.sum_add_distrib]
  exact Finset.sum_eq_zero hFG

theorem statement :
    ∀ (N : ℕ) (_hN : 2 ≤ N) (_heven : Even N) (L : ℝ) (_hL : 0 < L) (a b : Fin N → ℂ),
      ∑ j : Fin N, (Pi N a (D N L b) j + Pi N b (D N L a) j) = 0 := by
  intro N hN heven L _ a b
  rw [Finset.sum_add_distrib, sum_Pi N hN, sum_Pi N hN, ← mul_add]
  apply mul_eq_zero_of_right
  unfold c
  simp only [mul_zero, neg_zero, zpow_zero, mul_one]
  rw [← mul_add]
  apply mul_eq_zero_of_right
  simp only [E_eq N hN heven]
  rw [sum_prod_modes N hN heven, sum_prod_modes N hN heven, ← mul_add]
  apply mul_eq_zero_of_right
  apply pair_cancel
  intro m hm
  have hm' : -m ∈ Icc (-((N / 2 : ℕ) : ℤ)) ((N / 2 : ℕ) : ℤ) := by
    rw [Finset.mem_Icc] at hm ⊢; omega
  simp only [neg_neg]
  rw [hat_D N hN heven L b (-m) hm', hat_D N hN heven L a m hm, kappaS_neg]
  push_cast
  ring

end MathDept.MD_0039
