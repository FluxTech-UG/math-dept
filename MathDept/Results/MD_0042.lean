import MathDept.Results.MD_0035

/-!
# MD_0042: the weights annihilated by the Fourier derivative are `span {1, (-1)^j}`

## Informal statement

With `D` the Nyquist-zeroed Fourier derivative of MD_0035 (`N ≥ 2` even, `L > 0`),
`{w ∈ ℂ^N : ∑_j w_j (D g)_j = 0 for every g} = span_ℂ {1, (-1)^j}`.

## Conventions used here

* `omega`, `hat`, `kappa` and `D` are MD_0035's definitions, imported unchanged
  (`MathDept.Results.MD_0035`), so `D` is literally the same operator. The ledger's
  symbol is `s_n = i κ_n`, with `κ_{N/2} = 0`.
* Grid and mode indices are `Fin N`; powers of `ω` are integer powers with exponent
  `(j : ℤ) * (m : ℤ)`. The sign weight `(-1)^j` is `(-1 : ℂ) ^ (j : ℕ)`.
* The helper lemmas (orthogonality `orth`, Fourier-side pairing `pair`, `ω^{N/2} = -1`)
  are restated in each of MD_0041, MD_0042, MD_0046 so each file depends on MD_0035 only.

## Proof recipe

1. `⊇`: `∑_j (Dg)_j = 0` is MD_0035; `∑_j (-1)^j (Dg)_j = 0` is `sign_sum` (MD_0041's argument).
2. `⊆`, `W_zero`: test against the character `g_j = ω^{jm}`, whose transform is `N δ_{·m}`
   (`orth`); `pair` gives `i κ_m W_m = 0`, and `κ_m ≠ 0` for `m ∉ {0, N/2}` (`kappa_ne_zero`,
   which uses `L ≠ 0`).
3. `reconW`: `N w_j = ∑_m W_m ω^{-jm}`; with `W` supported on `{0, N/2}` (`sum_two`) and
   `ω^{-jN/2} = (-1)^j`, `w = (W_0/N)·1 + (W_{N/2}/N)·(-1)^j`.

Every ledger hypothesis is used: `2 ≤ N` and `Even N` for the mode `N/2` and
`ω^{N/2} = -1`, `0 < L` (as `L ≠ 0`) in step 2.
-/

namespace MathDept.MD_0042

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

/-- Orthogonality in the form used below. -/
lemma orth {N : ℕ} (hN : N ≠ 0) (a b : Fin N) :
    ∑ m : Fin N, omega N ^ (((m : ℕ) : ℤ) * (((a : ℕ) : ℤ) - ((b : ℕ) : ℤ)))
      = if a = b then (N : ℂ) else 0 := by
  rw [sum_omega_zpow N hN]
  by_cases hab : a = b
  · rw [if_pos ((dvd_sub_iff a b).mpr hab), if_pos hab]
  · rw [if_neg (fun h => hab ((dvd_sub_iff a b).mp h)), if_neg hab]

/-- The pairing of a weight with `D g`, written on the Fourier side. -/
lemma pair (N : ℕ) (L : ℝ) (w g : Fin N → ℂ) :
    ∑ j : Fin N, w j * D N L g j
      = (1 / (N : ℂ)) * ∑ m : Fin N, I * (kappa N L m : ℂ) * hat N g m *
          ∑ j : Fin N, w j * omega N ^ (((j : ℕ) : ℤ) * ((m : ℕ) : ℤ)) := by
  simp only [D, Finset.mul_sum]
  rw [Finset.sum_comm]
  refine Finset.sum_congr rfl fun m _ => Finset.sum_congr rfl fun j _ => ?_
  ring

lemma kappa_ne_zero {N : ℕ} {L : ℝ} (hL : L ≠ 0) (m : Fin N) (h0 : (m : ℕ) ≠ 0)
    (hh : (m : ℕ) ≠ N / 2) : kappa N L m ≠ 0 := by
  have hm := m.isLt
  unfold kappa
  split_ifs with h1
  · exact div_ne_zero (mul_ne_zero (mul_ne_zero two_ne_zero Real.pi_ne_zero)
      (Nat.cast_ne_zero.mpr h0)) hL
  · refine div_ne_zero (mul_ne_zero (mul_ne_zero two_ne_zero Real.pi_ne_zero) ?_) hL
    rw [sub_ne_zero]
    exact_mod_cast (show (m : ℕ) ≠ N by omega)

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

/-- The two modes `0` and `N/2` as elements of `Fin N`. -/
def m0 {N : ℕ} (hN : 2 ≤ N) : Fin N := ⟨0, by omega⟩
def mh {N : ℕ} (hN : 2 ≤ N) : Fin N := ⟨N / 2, by omega⟩

lemma sum_two {N : ℕ} (hN : 2 ≤ N) (F : Fin N → ℂ)
    (hF : ∀ m : Fin N, (m : ℕ) ≠ 0 → (m : ℕ) ≠ N / 2 → F m = 0) :
    ∑ m : Fin N, F m = F (m0 hN) + F (mh hN) := by
  apply Finset.sum_eq_add
  · intro h; have := congrArg Fin.val h; simp [m0, mh] at this; omega
  · intro c _ hc
    apply hF
    · intro h; apply hc.1; ext; simp [m0, h]
    · intro h; apply hc.2; ext; simp [mh, h]
  · simp
  · simp

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

/-- Inverse DFT on the weight side: `N w_j = ∑_m W_m ω^{-jm}`, `W_m = ∑_l w_l ω^{lm}`. -/
lemma reconW {N : ℕ} (hN : N ≠ 0) (w : Fin N → ℂ) (j : Fin N) :
    (N : ℂ) * w j = ∑ m : Fin N, (∑ l : Fin N, w l * omega N ^ (((l : ℕ) : ℤ) * ((m : ℕ) : ℤ))) *
      omega N ^ (-(((j : ℕ) : ℤ) * ((m : ℕ) : ℤ))) := by
  simp only [Finset.sum_mul]
  rw [Finset.sum_comm]
  have : ∀ l : Fin N, ∑ m : Fin N, w l * omega N ^ (((l : ℕ) : ℤ) * ((m : ℕ) : ℤ)) *
      omega N ^ (-(((j : ℕ) : ℤ) * ((m : ℕ) : ℤ))) = if l = j then (N : ℂ) * w j else 0 := by
    intro l
    have h2 : ∀ m : Fin N, w l * omega N ^ (((l : ℕ) : ℤ) * ((m : ℕ) : ℤ)) *
        omega N ^ (-(((j : ℕ) : ℤ) * ((m : ℕ) : ℤ)))
        = w l * omega N ^ (((m : ℕ) : ℤ) * (((l : ℕ) : ℤ) - ((j : ℕ) : ℤ))) := by
      intro m
      rw [mul_assoc, omega_mul N _ _ (((m : ℕ) : ℤ) * (((l : ℕ) : ℤ) - ((j : ℕ) : ℤ))) (by ring)]
    simp_rw [h2]
    rw [← Finset.mul_sum, orth hN]
    split_ifs with h
    · subst h; ring
    · simp
  rw [Finset.sum_congr rfl fun l _ => this l]
  simp

/-- A weight annihilating the range of `D` has `W_m = 0` off the modes `0`, `N/2`. -/
lemma W_zero {N : ℕ} (hN : 2 ≤ N) {L : ℝ} (hL : L ≠ 0) (w : Fin N → ℂ)
    (hw : ∀ g : Fin N → ℂ, ∑ j : Fin N, w j * D N L g j = 0) (m : Fin N)
    (h0 : (m : ℕ) ≠ 0) (hh : (m : ℕ) ≠ N / 2) :
    ∑ l : Fin N, w l * omega N ^ (((l : ℕ) : ℤ) * ((m : ℕ) : ℤ)) = 0 := by
  have hN0 : N ≠ 0 := by omega
  have key := hw (fun j => omega N ^ (((j : ℕ) : ℤ) * ((m : ℕ) : ℤ)))
  rw [pair] at key
  have hg : ∀ n : Fin N, hat N (fun j => omega N ^ (((j : ℕ) : ℤ) * ((m : ℕ) : ℤ))) n
      = if m = n then (N : ℂ) else 0 := by
    intro n
    unfold hat
    beta_reduce
    rw [← orth hN0 m n]
    exact Finset.sum_congr rfl fun j _ =>
      omega_mul N _ _ (((j : ℕ) : ℤ) * (((m : ℕ) : ℤ) - ((n : ℕ) : ℤ))) (by ring)
  simp only [hg, mul_ite, ite_mul, mul_zero, zero_mul, Finset.sum_ite_eq,
    Finset.mem_univ,
    if_true] at key
  have hNc : (N : ℂ) ≠ 0 := Nat.cast_ne_zero.mpr hN0
  have hk := kappa_ne_zero hL m h0 hh
  simp only [one_div] at key
  rcases (by simpa [hNc, I_ne_zero] using key :
      kappa N L m = 0 ∨ ∑ l : Fin N, w l * omega N ^ (((l : ℕ) : ℤ) * ((m : ℕ) : ℤ)) = 0)
    with h | h
  · exact absurd h hk
  · exact h

theorem statement :
    ∀ (N : ℕ) (_hN : 2 ≤ N) (_heven : Even N) (L : ℝ) (_hL : 0 < L),
      {w : Fin N → ℂ | ∀ g : Fin N → ℂ, ∑ j : Fin N, w j * D N L g j = 0}
        = (Submodule.span ℂ ({(fun _ => (1 : ℂ)), (fun j : Fin N => (-1 : ℂ) ^ (j : ℕ))} :
            Set (Fin N → ℂ)) : Set (Fin N → ℂ)) := by
  intro N hN heven L hL
  have hN0 : N ≠ 0 := by omega
  have hNc : (N : ℂ) ≠ 0 := Nat.cast_ne_zero.mpr hN0
  ext w
  simp only [Set.mem_ofPred_eq, SetLike.mem_coe, Submodule.mem_span_pair]
  constructor
  · intro hw
    set W := fun m : Fin N => ∑ l : Fin N, w l * omega N ^ (((l : ℕ) : ℤ) * ((m : ℕ) : ℤ))
      with hWdef
    refine ⟨W (m0 hN) / N, W (mh hN) / N, ?_⟩
    funext j
    have e := reconW hN0 w j
    rw [sum_two hN] at e
    · have hs : omega N ^ (-(((j : ℕ) : ℤ) * ((N / 2 : ℕ) : ℤ))) = (-1 : ℂ) ^ (j : ℕ) := by
        rw [zpow_neg, omega_sign hN heven, ← inv_pow, inv_neg_one]
      simp only [m0, mh] at e
      rw [hs] at e
      simp only [Pi.add_apply, Pi.smul_apply, smul_eq_mul, mul_one]
      apply mul_left_cancel₀ hNc
      rw [e]
      simp only [W, m0, mh]
      field_simp
      simp
    · intro m h0 hh
      rw [W_zero hN hL.ne' w hw m h0 hh, zero_mul]
  · rintro ⟨c, d, rfl⟩ g
    have h1 := MathDept.MD_0035.statement N hN heven L hL g
    have h2 := sign_sum hN heven L g
    simp only [Pi.add_apply, Pi.smul_apply, smul_eq_mul, mul_one, add_mul,
      Finset.sum_add_distrib, mul_assoc, ← Finset.mul_sum, h1, h2, mul_zero, add_zero]

end MathDept.MD_0042
