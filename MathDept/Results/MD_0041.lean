import MathDept.Results.MD_0035

/-!
# MD_0041: the Nyquist-weighted sum of a Fourier derivative vanishes

## Informal statement

With `D` the Nyquist-zeroed Fourier derivative of MD_0035 (`N ≥ 2` even, `L > 0`), for every
`g ∈ ℂ^N`, `∑_j (-1)^j (D g)_j = 0`.

## Conventions used here

* `omega`, `hat`, `kappa` and `D` are MD_0035's definitions, imported unchanged
  (`MathDept.Results.MD_0035`), so `D` is literally the same operator. The ledger's
  symbol is `s_n = i κ_n`, with `κ_{N/2} = 0`.
* Grid and mode indices are `Fin N`; powers of `ω` are integer powers with exponent
  `(j : ℤ) * (m : ℤ)`. The sign weight `(-1)^j` is `(-1 : ℂ) ^ (j : ℕ)`.
* The helper lemmas (orthogonality `orth`, Fourier-side pairing `pair`, `ω^{N/2} = -1`)
  are restated in each of MD_0041, MD_0042, MD_0046 so each file depends on MD_0035 only.

## Proof recipe

1. `pair`: `∑_j w_j (Dg)_j = (1/N) ∑_m i κ_m ĝ_m W_m` with `W_m = ∑_j w_j ω^{jm}`.
2. `omega_sign`: `(-1)^j = ω^{j N/2}` (`ω^{N/2}` is a primitive square root of unity).
3. For `w = (-1)^j`, `W_m = ∑_j ω^{j(N/2 + m)}`, which is `0` unless `m = N/2`
   (`sum_omega_zpow`, `dvd_sub_iff`); at `m = N/2`, `κ_m = 0` (`kappa_half`).

The hypothesis `0 < L` is carried as in the ledger and is not used (the identity holds for
every `L`, the `L = 0` case being Lean's `x / 0 = 0`).
-/

namespace MathDept.MD_0041

open Complex Finset MathDept.MD_0035

lemma omega_ne_zero (N : ℕ) : omega N ≠ 0 := Complex.exp_ne_zero _

lemma omega_mul (N : ℕ) (a b c : ℤ) (h : a + b = c) :
    omega N ^ a * omega N ^ b = omega N ^ c := by
  rw [← zpow_add₀ (omega_ne_zero N), h]

lemma dvd_sub_iff {N : ℕ} (a b : Fin N) :
    (N : ℤ) ∣ ((a : ℕ) : ℤ) - ((b : ℕ) : ℤ) ↔ a = b := by
  constructor
  · intro hd
    have ha := a.isLt
    have hb := b.isLt
    have h0 := Int.eq_zero_of_abs_lt_dvd hd (by rw [abs_lt]; constructor <;> omega)
    ext; omega
  · rintro rfl; simp

/-- The pairing of a weight with `D g`, written on the Fourier side. -/
lemma pair (N : ℕ) (L : ℝ) (w g : Fin N → ℂ) :
    ∑ j : Fin N, w j * D N L g j
      = (1 / (N : ℂ)) * ∑ m : Fin N, I * (kappa N L m : ℂ) * hat N g m *
          ∑ j : Fin N, w j * omega N ^ (((j : ℕ) : ℤ) * ((m : ℕ) : ℤ)) := by
  simp only [D, Finset.mul_sum]
  rw [Finset.sum_comm]
  refine Finset.sum_congr rfl fun m _ => Finset.sum_congr rfl fun j _ => ?_
  ring

lemma kappa_half {N : ℕ} {L : ℝ} (m : Fin N) (hh : (m : ℕ) = N / 2) : kappa N L m = 0 := by
  unfold kappa
  rw [if_neg (by omega), if_pos hh]

lemma omega_half {N : ℕ} (hN : 2 ≤ N) (heven : Even N) :
    omega N ^ (N / 2) = -1 := by
  obtain ⟨k, rfl⟩ := heven
  have hk : (k + k) / 2 = k := by omega
  rw [hk]
  have hp := omega_isPrimitiveRoot (k + k) (by omega)
  have h2 := hp.pow_of_dvd (p := k) (by omega) ⟨2, by ring⟩
  have : (k + k) / k = 2 := by
    rw [show k + k = 2 * k by ring]; exact Nat.mul_div_cancel _ (by omega)
  rw [this] at h2
  exact h2.eq_neg_one_of_two_right

lemma omega_sign {N : ℕ} (hN : 2 ≤ N) (heven : Even N) (j : ℕ) :
    omega N ^ ((j : ℤ) * ((N / 2 : ℕ) : ℤ)) = (-1 : ℂ) ^ j := by
  rw [mul_comm, _root_.zpow_mul, zpow_natCast, zpow_natCast, omega_half hN heven]

/-- Nyquist pairing: `(-1)^j` against `D g` is zero. -/
lemma sign_sum {N : ℕ} (hN : 2 ≤ N) (heven : Even N) (L : ℝ) (g : Fin N → ℂ) :
    ∑ j : Fin N, (-1 : ℂ) ^ (j : ℕ) * D N L g j = 0 := by
  have hN0 : N ≠ 0 := by omega
  obtain ⟨k, hk⟩ := heven
  rw [pair]
  apply mul_eq_zero_of_right
  apply Finset.sum_eq_zero
  intro m _
  by_cases hm : (m : ℕ) = N / 2
  · rw [kappa_half m hm]; simp
  · have hW : ∑ j : Fin N, (-1 : ℂ) ^ (j : ℕ) * omega N ^ (((j : ℕ) : ℤ) * ((m : ℕ) : ℤ)) = 0 := by
      have hc : ∀ j : Fin N, (-1 : ℂ) ^ (j : ℕ) * omega N ^ (((j : ℕ) : ℤ) * ((m : ℕ) : ℤ))
          = omega N ^ (((j : ℕ) : ℤ) * (((N / 2 : ℕ) : ℤ) + ((m : ℕ) : ℤ))) := by
        intro j
        rw [← omega_sign hN ⟨k, hk⟩,
          omega_mul N _ _ (((j : ℕ) : ℤ) * (((N / 2 : ℕ) : ℤ) + ((m : ℕ) : ℤ))) (by ring)]
      simp_rw [hc]
      rw [sum_omega_zpow N hN0, if_neg]
      intro hd
      have hd2 : (N : ℤ) ∣ ((m : ℕ) : ℤ) - ((⟨N / 2, by omega⟩ : Fin N) : ℕ) := by
        have := Int.dvd_sub hd (dvd_refl (N : ℤ))
        have he : (((N / 2 : ℕ) : ℤ) + ((m : ℕ) : ℤ)) - N
            = ((m : ℕ) : ℤ) - ((⟨N / 2, by omega⟩ : Fin N) : ℕ) := by
          simp only; omega
        rwa [he] at this
      exact hm (congrArg Fin.val ((dvd_sub_iff _ _).mp hd2))
    rw [hW, mul_zero]

theorem statement :
    ∀ (N : ℕ) (_hN : 2 ≤ N) (_heven : Even N) (L : ℝ) (_hL : 0 < L) (g : Fin N → ℂ),
      ∑ j : Fin N, (-1 : ℂ) ^ (j : ℕ) * D N L g j = 0 := by
  intro N hN heven L _ g
  exact sign_sum hN heven L g

end MathDept.MD_0041
