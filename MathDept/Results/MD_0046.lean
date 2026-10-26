import MathDept.Results.MD_0035
import Mathlib.LinearAlgebra.Matrix.PosDef
import Mathlib.Analysis.Complex.Basic
import Mathlib.Analysis.SpecialFunctions.Exp

/-!
# MD_0046: diffusion plus a sink off the gaps is positive definite

## Informal statement

With `D` the Nyquist-zeroed Fourier derivative of MD_0035 (`N ≥ 2` even, `L > 0`) and
`K = -D²`: if `h ∈ ℝ^N`, `h ≥ 0`, and `h_j > 0`, `h_k > 0` at two indices with `j - k` odd,
then for every `α > 0` the Hermitian matrix `α K + diag(h)` is positive definite
(`statement`). In particular, if the complement of `S` holds two indices of opposite parity,
the principal submatrix `K_SS` is positive definite (`statement_principal`).

## Conventions used here

* `omega`, `hat`, `kappa` and `D` are MD_0035's definitions, imported unchanged
  (`MathDept.Results.MD_0035`), so `D` is literally the same operator. The ledger's
  symbol is `s_n = i κ_n`, with `κ_{N/2} = 0`.
* Grid and mode indices are `Fin N`; powers of `ω` are integer powers with exponent
  `(j : ℤ) * (m : ℤ)`. The sign weight `(-1)^j` is `(-1 : ℂ) ^ (j : ℕ)`.
* The helper lemmas (orthogonality `orth`, Fourier-side pairing `pair`, `ω^{N/2} = -1`)
  are restated in each of MD_0041, MD_0042, MD_0046 so each file depends on MD_0035 only.
* `Dmat` is `D` as a matrix with the ledger's entries
  `D_{jl} = (1/N) ∑_n i κ_n ω^{(j-l)n}`; `Dmat_mulVec` shows `Dmat *ᵥ g = D g`.
  `K = -(Dmat * Dmat)`. Positive definiteness is Mathlib's `Matrix.PosDef` over `ℂ`.
* `S` is a `Set (Fin N)` and `K_SS` is `(K N L).submatrix (↑) (↑)` on the subtype `S`.

## Proof recipe

1. `Dmat_conjTranspose`: `Dᴴ = -D` (entrywise, `star ω^q = ω^{-q}`), so `K = Dᴴ D` (`K_eq`)
   and `K` is Hermitian.
2. `quad_form`: `x* (αK + diag h) x = α ‖Dx‖² + ∑ h_j |x_j|²`, real and `≥ 0`.
3. `ker_D`: if `D x = 0` then every mode but `0`, `N/2` of `x̂` vanishes (`pair` against
   `ω^{-jm}`, `κ_m ≠ 0`), so `N x_j = x̂_0 + x̂_{N/2} (-1)^j` (inverse DFT `recon`).
4. `ker_D_two`: such an `x` vanishing at two indices of opposite parity is zero.
5. `statement`: a zero quadratic form forces `D x = 0` and `x_j = x_k = 0`, hence `x = 0`.
6. `statement_principal`: apply 5 with `α = 1`, `h = 1_{Sᶜ}`, then `PosDef.submatrix` along
   the injective inclusion `S → Fin N`; on `S × S` the diagonal term vanishes.

Every ledger hypothesis is used (`0 < L` as `L ≠ 0` in step 3).
-/

namespace MathDept.MD_0046

open Complex Finset Matrix MathDept.MD_0035
open scoped ComplexOrder

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

/-- Inverse DFT: `N g_j = ∑_m ĝ_m ω^{jm}`. -/
lemma recon {N : ℕ} (hN : N ≠ 0) (g : Fin N → ℂ) (j : Fin N) :
    (N : ℂ) * g j = ∑ m : Fin N, hat N g m * omega N ^ (((j : ℕ) : ℤ) * ((m : ℕ) : ℤ)) := by
  simp only [hat, Finset.sum_mul]
  rw [Finset.sum_comm]
  have : ∀ l : Fin N, ∑ m : Fin N, g l * omega N ^ (-(((l : ℕ) : ℤ) * ((m : ℕ) : ℤ))) *
      omega N ^ (((j : ℕ) : ℤ) * ((m : ℕ) : ℤ)) = if j = l then (N : ℂ) * g j else 0 := by
    intro l
    have h2 : ∀ m : Fin N, g l * omega N ^ (-(((l : ℕ) : ℤ) * ((m : ℕ) : ℤ))) *
        omega N ^ (((j : ℕ) : ℤ) * ((m : ℕ) : ℤ))
        = g l * omega N ^ (((m : ℕ) : ℤ) * (((j : ℕ) : ℤ) - ((l : ℕ) : ℤ))) := by
      intro m
      rw [mul_assoc, omega_mul N _ _ (((m : ℕ) : ℤ) * (((j : ℕ) : ℤ) - ((l : ℕ) : ℤ))) (by ring)]
    simp_rw [h2]
    rw [← Finset.mul_sum, orth hN]
    split_ifs with h
    · subst h; ring
    · simp
  rw [Finset.sum_congr rfl fun l _ => this l]
  simp

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

/-- Fourier side of the kernel: `D x = 0` kills every mode but `0` and `N/2`. -/
lemma hat_zero_of_D_zero {N : ℕ} (hN : 2 ≤ N) {L : ℝ} (hL : L ≠ 0) (x : Fin N → ℂ)
    (hx : ∀ j, D N L x j = 0) (m : Fin N) (h0 : (m : ℕ) ≠ 0) (hh : (m : ℕ) ≠ N / 2) :
    hat N x m = 0 := by
  have hN0 : N ≠ 0 := by omega
  have key := pair N L (fun j => omega N ^ (-(((j : ℕ) : ℤ) * ((m : ℕ) : ℤ)))) x
  simp only [hx, mul_zero, Finset.sum_const_zero] at key
  have hw : ∀ n : Fin N, ∑ j : Fin N, omega N ^ (-(((j : ℕ) : ℤ) * ((m : ℕ) : ℤ))) *
      omega N ^ (((j : ℕ) : ℤ) * ((n : ℕ) : ℤ)) = if n = m then (N : ℂ) else 0 := by
    intro n
    rw [← orth hN0 n m]
    refine Finset.sum_congr rfl fun j _ => omega_mul N _ _ _ (by ring)
  simp only [hw, mul_ite, mul_zero, Finset.sum_ite_eq', Finset.mem_univ, if_true] at key
  have hNc : (N : ℂ) ≠ 0 := Nat.cast_ne_zero.mpr hN0
  have hk := kappa_ne_zero hL m h0 hh
  simp only [one_div] at key
  rcases (by simpa [hNc, I_ne_zero] using key : kappa N L m = 0 ∨ hat N x m = 0) with h | h
  · exact absurd h hk
  · exact h

/-- The kernel of `D` is spanned by `1` and `(-1)^j`. -/
lemma ker_D {N : ℕ} (hN : 2 ≤ N) (heven : Even N) {L : ℝ} (hL : L ≠ 0) (x : Fin N → ℂ)
    (hx : ∀ j, D N L x j = 0) (j : Fin N) :
    (N : ℂ) * x j = hat N x (m0 hN) + hat N x (mh hN) * (-1 : ℂ) ^ (j : ℕ) := by
  have hN0 : N ≠ 0 := by omega
  rw [recon hN0, sum_two hN]
  · simp only [m0, mh]
    rw [omega_sign hN heven]
    simp
  · intro m h0 hh
    rw [hat_zero_of_D_zero hN hL x hx m h0 hh, zero_mul]

lemma neg_one_pow_odd {N : ℕ} (j k : Fin N) (hodd : Odd (((j : ℕ) : ℤ) - ((k : ℕ) : ℤ))) :
    (-1 : ℂ) ^ (j : ℕ) = -(-1 : ℂ) ^ (k : ℕ) := by
  have h : ((-1 : ℂ)) ^ (((j : ℕ) : ℤ))
      = (-1) ^ (((j : ℕ) : ℤ) - ((k : ℕ) : ℤ)) * (-1) ^ (((k : ℕ) : ℤ)) := by
    rw [← zpow_add₀ (by norm_num)]; ring_nf
  rw [Odd.neg_one_zpow hodd, zpow_natCast, zpow_natCast] at h
  simpa using h

/-- A kernel vector of `D` vanishing at two indices of opposite parity is zero. -/
lemma ker_D_two {N : ℕ} (hN : 2 ≤ N) (heven : Even N) {L : ℝ} (hL : L ≠ 0) (x : Fin N → ℂ)
    (hx : ∀ j, D N L x j = 0) (j k : Fin N) (hodd : Odd (((j : ℕ) : ℤ) - ((k : ℕ) : ℤ)))
    (hj : x j = 0) (hk : x k = 0) : x = 0 := by
  have hN0 : (N : ℂ) ≠ 0 := Nat.cast_ne_zero.mpr (by omega)
  have ej := ker_D hN heven hL x hx j
  have ek := ker_D hN heven hL x hx k
  rw [hj, mul_zero, neg_one_pow_odd j k hodd] at ej
  rw [hk, mul_zero] at ek
  funext i
  have ei := ker_D hN heven hL x hx i
  set a := hat N x (m0 hN)
  set b := hat N x (mh hN)
  set s := (-1 : ℂ) ^ (k : ℕ)
  have hs : s ≠ 0 := pow_ne_zero _ (by norm_num)
  have hbs : b * s = 0 := by linear_combination (ej - ek) / 2
  have hb : b = 0 := (mul_eq_zero.mp hbs).resolve_right hs
  have ha : a = 0 := by linear_combination -ek - s * hb
  rw [ha, hb] at ei
  simpa [hN0] using ei

/-- `D` as a matrix, entries as in the ledger: `D_{jl} = (1/N) ∑_n s_n ω^{(j-l)n}`,
`s_n = i κ_n`. -/
noncomputable def Dmat (N : ℕ) (L : ℝ) : Matrix (Fin N) (Fin N) ℂ :=
  fun j l => (1 / (N : ℂ)) * ∑ n : Fin N,
    I * (kappa N L n : ℂ) * omega N ^ ((((j : ℕ) : ℤ) - ((l : ℕ) : ℤ)) * ((n : ℕ) : ℤ))

/-- `K = -D²`. -/
noncomputable def K (N : ℕ) (L : ℝ) : Matrix (Fin N) (Fin N) ℂ := -(Dmat N L * Dmat N L)

lemma Dmat_mulVec (N : ℕ) (L : ℝ) (g : Fin N → ℂ) : Dmat N L *ᵥ g = D N L g := by
  funext j
  simp only [Matrix.mulVec, dotProduct, Dmat, D, hat, Finset.mul_sum, Finset.sum_mul]
  rw [Finset.sum_comm]
  refine Finset.sum_congr rfl fun n _ => Finset.sum_congr rfl fun l _ => ?_
  rw [← omega_mul N (-(((l : ℕ) : ℤ) * ((n : ℕ) : ℤ))) (((j : ℕ) : ℤ) * ((n : ℕ) : ℤ)) _
    (by ring)]
  ring

lemma star_omega_zpow (N : ℕ) (q : ℤ) : star (omega N ^ q) = omega N ^ (-q) := by
  rw [star_zpow₀]
  have : star (omega N) = (omega N)⁻¹ := by
    unfold omega
    rw [← Complex.exp_neg, Complex.star_def, ← Complex.exp_conj]
    congr 1
    simp [map_div₀, Complex.conj_ofReal, map_ofNat]
    ring
  rw [this, _root_.inv_zpow']

lemma Dmat_conjTranspose (N : ℕ) (L : ℝ) : (Dmat N L)ᴴ = -Dmat N L := by
  ext j l
  simp only [conjTranspose_apply, Dmat, Matrix.neg_apply, star_mul', star_sum,
    star_omega_zpow, one_div, star_inv₀, star_natCast, Complex.star_def, Complex.conj_I,
    Complex.conj_ofReal]
  rw [← neg_mul, Finset.mul_sum, Finset.mul_sum]
  refine Finset.sum_congr rfl fun n _ => ?_
  rw [show -((((l : ℕ) : ℤ) - ((j : ℕ) : ℤ)) * ((n : ℕ) : ℤ))
    = (((j : ℕ) : ℤ) - ((l : ℕ) : ℤ)) * ((n : ℕ) : ℤ) by ring]
  ring

lemma K_eq (N : ℕ) (L : ℝ) : K N L = (Dmat N L)ᴴ * Dmat N L := by
  rw [Dmat_conjTranspose, K, neg_mul]

lemma K_isHermitian (N : ℕ) (L : ℝ) : (K N L).IsHermitian := by
  rw [K_eq]; exact isHermitian_conjTranspose_mul_self _

lemma quad_form (N : ℕ) (L : ℝ) (h : Fin N → ℝ) (α : ℝ) (x : Fin N → ℂ) :
    star x ⬝ᵥ (((α : ℂ) • K N L + Matrix.diagonal (fun j => (h j : ℂ))) *ᵥ x)
      = ((α * ∑ j, ‖D N L x j‖ ^ 2 + ∑ j, h j * ‖x j‖ ^ 2 : ℝ) : ℂ) := by
  rw [add_mulVec, smul_mulVec, dotProduct_add, dotProduct_smul, K_eq,
    ← mulVec_mulVec, dotProduct_mulVec, ← star_mulVec, Dmat_mulVec]
  simp only [dotProduct, mulVec_diagonal, Pi.star_apply, Complex.star_def, smul_eq_mul]
  push_cast
  simp only [Complex.conj_mul']
  congr 1
  refine Finset.sum_congr rfl fun j _ => ?_
  rw [mul_left_comm, Complex.conj_mul']

theorem statement :
    ∀ (N : ℕ) (_hN : 2 ≤ N) (_heven : Even N) (L : ℝ) (_hL : 0 < L) (h : Fin N → ℝ)
      (_hh : ∀ j, 0 ≤ h j)
      (_hpar : ∃ j k : Fin N, Odd (((j : ℕ) : ℤ) - ((k : ℕ) : ℤ)) ∧ 0 < h j ∧ 0 < h k)
      (α : ℝ) (_hα : 0 < α),
      ((α : ℂ) • K N L + Matrix.diagonal (fun j => (h j : ℂ))).PosDef := by
  intro N hN heven L hL h hh hpar α hα
  obtain ⟨j, k, hodd, hj, hk⟩ := hpar
  apply Matrix.PosDef.of_dotProduct_mulVec_pos
  · refine IsHermitian.add ?_ ?_
    · unfold IsHermitian
      rw [conjTranspose_smul, (K_isHermitian N L).eq, Complex.star_def, Complex.conj_ofReal]
    · exact isHermitian_diagonal_of_self_adjoint _
        (funext fun i => by simp [Complex.conj_ofReal])
  · intro x hx
    rw [quad_form]
    have hA : 0 ≤ ∑ i, ‖D N L x i‖ ^ 2 := Finset.sum_nonneg fun i _ => by positivity
    have hB : 0 ≤ ∑ i, h i * ‖x i‖ ^ 2 :=
      Finset.sum_nonneg fun i _ => mul_nonneg (hh i) (by positivity)
    have hP : 0 < α * ∑ i, ‖D N L x i‖ ^ 2 + ∑ i, h i * ‖x i‖ ^ 2 := by
      by_contra hP
      push Not at hP
      have hA0 : ∑ i, ‖D N L x i‖ ^ 2 = 0 := by
        have : α * ∑ i, ‖D N L x i‖ ^ 2 = 0 := by nlinarith [mul_nonneg hα.le hA]
        exact (mul_eq_zero.mp this).resolve_left hα.ne'
      have hB0 : ∑ i, h i * ‖x i‖ ^ 2 = 0 := by nlinarith [mul_nonneg hα.le hA]
      rw [Finset.sum_eq_zero_iff_of_nonneg (fun i _ => by positivity)] at hA0
      rw [Finset.sum_eq_zero_iff_of_nonneg
        (fun i _ => mul_nonneg (hh i) (by positivity))] at hB0
      have hDx : ∀ i, D N L x i = 0 := fun i => by
        simpa using hA0 i (Finset.mem_univ i)
      have hxj : x j = 0 := by
        have := hB0 j (Finset.mem_univ j)
        simpa [hj.ne'] using this
      have hxk : x k = 0 := by
        have := hB0 k (Finset.mem_univ k)
        simpa [hk.ne'] using this
      exact hx (ker_D_two hN heven hL.ne' x hDx j k hodd hxj hxk)
    exact_mod_cast hP

/-- The "in particular": a principal submatrix `K_SS` is positive definite when the
complement of `S` holds two indices of opposite parity. -/
theorem statement_principal :
    ∀ (N : ℕ) (_hN : 2 ≤ N) (_heven : Even N) (L : ℝ) (_hL : 0 < L) (S : Set (Fin N))
      (_hS : ∃ j k : Fin N, j ∉ S ∧ k ∉ S ∧ Odd (((j : ℕ) : ℤ) - ((k : ℕ) : ℤ))),
      ((K N L).submatrix ((↑) : S → Fin N) ((↑) : S → Fin N)).PosDef := by
  classical
  intro N hN heven L hL S hS
  obtain ⟨j, k, hj, hk, hodd⟩ := hS
  have hP := statement N hN heven L hL (fun i => if i ∈ S then 0 else 1)
    (fun i => by split_ifs <;> norm_num)
    ⟨j, k, hodd, by simp [hj], by simp [hk]⟩ 1 one_pos
  have hsub := hP.submatrix (e := ((↑) : S → Fin N)) Subtype.val_injective
  convert hsub using 1
  ext a b
  by_cases hab : a = b
  · subst hab; simp [a.2]
  · have : (a : Fin N) ≠ b := fun h => hab (Subtype.ext h)
    simp [this]

end MathDept.MD_0046
