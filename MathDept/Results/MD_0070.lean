import Mathlib.MeasureTheory.Integral.IntervalIntegral.AbsolutelyContinuousFun
import Mathlib.Analysis.SpecialFunctions.Sqrt

/-!
# MD_0070: the balanced realisation is passive for arbitrary time-varying coefficients

## Informal statement

Let `p_j, r_j, c_k, ξ_k, a : [0, T] → [0, ∞)` (finitely many terms) and `u` be given.
(Y-form) If `ζ̇_j = -p_j ζ_j + √r_j u` and `y = ∑_j √r_j ζ_j`, then
`u y = d/dt (1/2) ∑ ζ_j² + ∑ p_j ζ_j²` a.e., so `∫₀ᵀ u y ≥ -(1/2) ∑ ζ_j(0)²`.
(Z-form) If `ζ̇_k = -ξ_k ζ_k + √(c_k ξ_k) u` and
`y = a u + ∑_k (c_k u - √(c_k ξ_k) ζ_k)`, then
`u y - d/dt (1/2) ∑ ζ_k² = a u² + ∑_k (√c_k u - √ξ_k ζ_k)² ≥ 0` a.e.
For constant coefficients both realise `∑ r_j/(s + p_j)` and `a + ∑ c_k s/(s + ξ_k)`.

## Conventions used here

* Index type `ι` with `[Fintype ι]`; coefficients are `ι → ℝ → ℝ`, states `ζ : ι → ℝ → ℝ`.
* `energy ζ t = (1/2) ∑ j, ζ j t ^ 2`.
* A Carathéodory solution on `[0, T]` is Mathlib's `AbsolutelyContinuousOnInterval (ζ j) 0 T`
  with the state equation as `HasDerivAt` at a.e. `t ∈ Icc 0 T` (`integral_Y`, `integral_Z`),
  or equivalently the integral form `ζ j t = ζ j 0 + ∫ s in 0..t, rhs` on `Icc 0 T` with the
  right-hand side `IntervalIntegrable` (`integral_Y_integral_form`). A bare a.e.-derivative
  hypothesis without absolute continuity is not enough (Cantor-function counterexample).
* `∫ t in 0..T, u t * y t` is Mathlib's interval integral; when `u y` is not integrable it is
  `0` and the bound holds trivially, so no integrability of `u y` is assumed.
* Measurability, boundedness of the coefficients and `u ∈ L²` are existence hypotheses: none of
  the inequalities uses them, so the formal statements omit them (they are stronger).
  Nonnegativity of `p` (Y) and of `a, c, ξ` (Z) is used, a.e. on `[0, T]`.
* The constant-coefficient realisation claims are stated in the Laplace domain as algebraic
  identities over `ℂ` (`transfer_Y`, `transfer_Z`), for `s` off the poles.

## Proof recipe

1. `hasDerivAt_energy`: `d/dt energy = ∑ ζ_j ζ̇_j` (`HasDerivAt.fun_sum`, `HasDerivAt.pow`).
2. `pointwise_Y`, `pointwise_Z`: substitute the state equation; in Z use `√(cξ) = √c √ξ`,
   `(√c)² = c`, `(√ξ)² = ξ` (`Real.sqrt_mul`, `Real.sq_sqrt`).
3. `ac_energy`: `energy ζ` is absolutely continuous (Finset induction, `fun_mul`, `fun_add`).
4. `integral_Y`, `integral_Z`: FTC for absolutely continuous functions
   (`AbsolutelyContinuousOnInterval.integral_deriv_eq_sub`), `deriv energy ≤ u y` a.e. by step 2,
   `intervalIntegral.integral_mono_ae_restrict`, `energy T ≥ 0`; non-integrable case by
   `intervalIntegral.integral_undef`.
5. `of_integral_form`: the integral form gives absolute continuity
   (`IntervalIntegrable.absolutelyContinuousOnInterval_intervalIntegral`, `ac_congr`) and the
   a.e. derivative (`IntervalIntegrable.ae_hasDerivAt_integral`).
6. `transfer_Y`, `transfer_Z`: solve `ζ̂ = √(·) û / (s + ·)` and simplify.
-/

namespace MathDept.MD_0070

open MeasureTheory Set Finset

variable {ι : Type*} [Fintype ι]

/-- Storage `(1/2) ∑ ζ_j²`. -/
noncomputable def energy (ζ : ι → ℝ → ℝ) (t : ℝ) : ℝ := (1 / 2) * ∑ j, ζ j t ^ 2

lemma hasDerivAt_energy (ζ : ι → ℝ → ℝ) (ζ' : ι → ℝ) (t : ℝ)
    (h : ∀ j, HasDerivAt (ζ j) (ζ' j) t) :
    HasDerivAt (energy ζ) (∑ j, ζ j t * ζ' j) t := by
  have hs : HasDerivAt (fun s => ∑ j, ζ j s ^ 2) (∑ j, (2 : ℕ) * ζ j t ^ (2 - 1) * ζ' j) t := by
    apply HasDerivAt.fun_sum
    intro j _
    exact (h j).pow 2
  have := hs.const_mul (1 / 2 : ℝ)
  refine this.congr_deriv ?_
  rw [Finset.mul_sum]
  refine Finset.sum_congr rfl fun j _ => ?_
  push_cast; ring

/-- Y-form, pointwise. -/
theorem pointwise_Y (p r ζ : ι → ℝ → ℝ) (u : ℝ → ℝ) (t : ℝ)
    (hζ : ∀ j, HasDerivAt (ζ j) (-p j t * ζ j t + √(r j t) * u t) t) :
    HasDerivAt (energy ζ)
      (u t * (∑ j, √(r j t) * ζ j t) - ∑ j, p j t * ζ j t ^ 2) t := by
  convert hasDerivAt_energy ζ _ t hζ using 1
  rw [Finset.mul_sum, ← Finset.sum_sub_distrib]
  refine Finset.sum_congr rfl fun j _ => ?_
  ring

/-- Z-form, pointwise. -/
theorem pointwise_Z (c ξ ζ : ι → ℝ → ℝ) (a u : ℝ → ℝ) (t : ℝ)
    (hc : ∀ k, 0 ≤ c k t) (hξ : ∀ k, 0 ≤ ξ k t)
    (hζ : ∀ k, HasDerivAt (ζ k) (-ξ k t * ζ k t + √(c k t * ξ k t) * u t) t) :
    HasDerivAt (energy ζ)
      (u t * (a t * u t + ∑ k, (c k t * u t - √(c k t * ξ k t) * ζ k t))
        - a t * u t ^ 2 - ∑ k, (√(c k t) * u t - √(ξ k t) * ζ k t) ^ 2) t := by
  convert hasDerivAt_energy ζ _ t hζ using 1
  have key : ∀ k, u t * (c k t * u t - √(c k t * ξ k t) * ζ k t)
      - (√(c k t) * u t - √(ξ k t) * ζ k t) ^ 2
      = ζ k t * (-ξ k t * ζ k t + √(c k t * ξ k t) * u t) := by
    intro k
    have h1 : √(c k t) ^ 2 = c k t := Real.sq_sqrt (hc k)
    have h2 : √(ξ k t) ^ 2 = ξ k t := Real.sq_sqrt (hξ k)
    have h3 : √(c k t * ξ k t) = √(c k t) * √(ξ k t) := Real.sqrt_mul (hc k) _
    rw [h3]
    linear_combination (-(u t) ^ 2) * h1 - (ζ k t) ^ 2 * h2
  rw [← Finset.sum_congr rfl fun k _ => key k]
  simp only [Finset.sum_sub_distrib, ← Finset.mul_sum]
  ring

lemma energy_nonneg (ζ : ι → ℝ → ℝ) (t : ℝ) : 0 ≤ energy ζ t := by
  unfold energy; positivity

lemma ac_energy (ζ : ι → ℝ → ℝ) {a b : ℝ}
    (hac : ∀ j, AbsolutelyContinuousOnInterval (ζ j) a b) :
    AbsolutelyContinuousOnInterval (energy ζ) a b := by
  classical
  have key : ∀ s : Finset ι,
      AbsolutelyContinuousOnInterval (fun t => ∑ j ∈ s, ζ j t ^ 2) a b := by
    intro s
    induction s using Finset.induction_on with
    | empty =>
      have h0 : AbsolutelyContinuousOnInterval (fun _ : ℝ => (0 : ℝ)) a b :=
        (LipschitzWith.const (α := ℝ) (0 : ℝ)).lipschitzOnWith.absolutelyContinuousOnInterval
      simpa only [Finset.sum_empty] using h0
    | insert j s hj ih =>
      simp only [Finset.sum_insert hj, sq]
      exact ((hac j).fun_mul (hac j)).fun_add (by simpa only [sq] using ih)
  exact (key Finset.univ).const_mul (1 / 2)

/-- Y-form, integrated, for Carathéodory solutions: `ζ_j` absolutely continuous on `[0, T]`,
the state equation holding a.e. on `[0, T]`, `p_j ≥ 0` a.e. on `[0, T]`. -/
theorem integral_Y (p r ζ : ι → ℝ → ℝ) (u : ℝ → ℝ) {T : ℝ} (hT : 0 ≤ T)
    (hp : ∀ᵐ t, t ∈ Icc 0 T → ∀ j, 0 ≤ p j t)
    (hac : ∀ j, AbsolutelyContinuousOnInterval (ζ j) 0 T)
    (hode : ∀ᵐ t, t ∈ Icc 0 T → ∀ j, HasDerivAt (ζ j) (-p j t * ζ j t + √(r j t) * u t) t) :
    -(1 / 2) * ∑ j, ζ j 0 ^ 2 ≤ ∫ t in (0)..T, u t * ∑ j, √(r j t) * ζ j t := by
  by_cases hint : IntervalIntegrable (fun t => u t * ∑ j, √(r j t) * ζ j t) volume 0 T
  · have hE := ac_energy ζ hac
    have hFTC := hE.integral_deriv_eq_sub
    have hle : ∫ t in (0)..T, deriv (energy ζ) t ≤ ∫ t in (0)..T, u t * ∑ j, √(r j t) * ζ j t := by
      refine intervalIntegral.integral_mono_ae_restrict hT hE.intervalIntegrable_deriv hint ?_
      rw [Filter.EventuallyLE, ae_restrict_iff' measurableSet_Icc]
      filter_upwards [hp, hode] with t hpt hot ht
      rw [(pointwise_Y p r ζ u t (hot ht)).deriv]
      have : 0 ≤ ∑ j, p j t * ζ j t ^ 2 :=
        Finset.sum_nonneg fun j _ => mul_nonneg (hpt ht j) (sq_nonneg _)
      linarith
    have h0 := energy_nonneg ζ T
    have : energy ζ 0 = (1 / 2) * ∑ j, ζ j 0 ^ 2 := rfl
    linarith
  · rw [intervalIntegral.integral_undef hint]
    have : 0 ≤ ∑ j, ζ j 0 ^ 2 := Finset.sum_nonneg fun j _ => sq_nonneg _
    linarith

/-- Absolute continuity on `uIcc a b` sees only the values on `uIcc a b`. -/
lemma ac_congr {f g : ℝ → ℝ} {a b : ℝ} (hf : AbsolutelyContinuousOnInterval f a b)
    (h : EqOn f g (uIcc a b)) : AbsolutelyContinuousOnInterval g a b := by
  unfold AbsolutelyContinuousOnInterval at *
  refine hf.congr' ?_
  filter_upwards [Filter.mem_inf_of_right
    (Filter.mem_principal_self (AbsolutelyContinuousOnInterval.disjWithin a b))] with E hE
  refine Finset.sum_congr rfl fun i hi => ?_
  rw [h (hE.1 i hi).1, h (hE.1 i hi).2]

/-- A state given in integral form on `[0, T]` is absolutely continuous there and has
derivative equal to its integrand at a.e. `t ∈ [0, T]`. -/
lemma of_integral_form (z f : ℝ → ℝ) {T : ℝ} (hT : 0 ≤ T)
    (hf : IntervalIntegrable f volume 0 T)
    (hz : ∀ t ∈ Icc 0 T, z t = z 0 + ∫ s in (0)..t, f s) :
    AbsolutelyContinuousOnInterval z 0 T ∧
      ∀ᵐ t, t ∈ Icc 0 T → HasDerivAt z (f t) t := by
  have hmem : (0 : ℝ) ∈ uIcc 0 T := by simp
  have hg : AbsolutelyContinuousOnInterval (fun t => z 0 + ∫ s in (0)..t, f s) 0 T := by
    have hc : AbsolutelyContinuousOnInterval (fun _ : ℝ => z 0) 0 T :=
      (LipschitzWith.const (α := ℝ) (z 0)).lipschitzOnWith.absolutelyContinuousOnInterval
    exact hc.fun_add (hf.absolutelyContinuousOnInterval_intervalIntegral hmem)
  refine ⟨ac_congr hg (fun t ht => (hz t (by rwa [uIcc_of_le hT] at ht)).symm), ?_⟩
  have h0 : ∀ᵐ t : ℝ, t ≠ 0 := by simp [ae_iff, measure_singleton]
  have h1 : ∀ᵐ t : ℝ, t ≠ T := by simp [ae_iff, measure_singleton]
  filter_upwards [hf.ae_hasDerivAt_integral, h0, h1] with t hd ht0 htT ht
  have hIoo : t ∈ Ioo 0 T := ⟨lt_of_le_of_ne ht.1 (Ne.symm ht0), lt_of_le_of_ne ht.2 htT⟩
  have hd' := (hd (by rw [uIcc_of_le hT]; exact ht) 0 hmem).const_add (z 0)
  refine hd'.congr_of_eventuallyEq ?_
  filter_upwards [Ioo_mem_nhds hIoo.1 hIoo.2] with s hs
  exact hz s (Ioo_subset_Icc_self hs)

/-- Y-form, integrated, with the state equation in integral form
`ζ_j(t) = ζ_j(0) + ∫₀ᵗ (-p_j ζ_j + √r_j u)` on `[0, T]` (integrand interval integrable). -/
theorem integral_Y_integral_form (p r ζ : ι → ℝ → ℝ) (u : ℝ → ℝ) {T : ℝ} (hT : 0 ≤ T)
    (hp : ∀ᵐ t, t ∈ Icc 0 T → ∀ j, 0 ≤ p j t)
    (hint : ∀ j, IntervalIntegrable (fun s => -p j s * ζ j s + √(r j s) * u s) volume 0 T)
    (hode : ∀ j, ∀ t ∈ Icc 0 T,
      ζ j t = ζ j 0 + ∫ s in (0)..t, (-p j s * ζ j s + √(r j s) * u s)) :
    -(1 / 2) * ∑ j, ζ j 0 ^ 2 ≤ ∫ t in (0)..T, u t * ∑ j, √(r j t) * ζ j t := by
  have h := fun j => of_integral_form (ζ j) _ hT (hint j) (hode j)
  refine integral_Y p r ζ u hT hp (fun j => (h j).1) ?_
  have hall : ∀ᵐ t, ∀ j, t ∈ Icc 0 T →
      HasDerivAt (ζ j) (-p j t * ζ j t + √(r j t) * u t) t :=
    ae_all_iff.mpr fun j => (h j).2
  filter_upwards [hall] with t ht hmem j using ht j hmem

/-- Z-form, integrated, for Carathéodory solutions (absolutely continuous states). -/
theorem integral_Z (c ξ ζ : ι → ℝ → ℝ) (a u : ℝ → ℝ) {T : ℝ} (hT : 0 ≤ T)
    (hcoef : ∀ᵐ t, t ∈ Icc 0 T → 0 ≤ a t ∧ ∀ k, 0 ≤ c k t ∧ 0 ≤ ξ k t)
    (hac : ∀ k, AbsolutelyContinuousOnInterval (ζ k) 0 T)
    (hode : ∀ᵐ t, t ∈ Icc 0 T →
      ∀ k, HasDerivAt (ζ k) (-ξ k t * ζ k t + √(c k t * ξ k t) * u t) t) :
    -(1 / 2) * ∑ k, ζ k 0 ^ 2 ≤
      ∫ t in (0)..T, u t * (a t * u t + ∑ k, (c k t * u t - √(c k t * ξ k t) * ζ k t)) := by
  by_cases hint : IntervalIntegrable
      (fun t => u t * (a t * u t + ∑ k, (c k t * u t - √(c k t * ξ k t) * ζ k t))) volume 0 T
  · have hE := ac_energy ζ hac
    have hFTC := hE.integral_deriv_eq_sub
    have hle : ∫ t in (0)..T, deriv (energy ζ) t ≤
        ∫ t in (0)..T, u t * (a t * u t + ∑ k, (c k t * u t - √(c k t * ξ k t) * ζ k t)) := by
      refine intervalIntegral.integral_mono_ae_restrict hT hE.intervalIntegrable_deriv hint ?_
      rw [Filter.EventuallyLE, ae_restrict_iff' measurableSet_Icc]
      filter_upwards [hcoef, hode] with t hct hot ht
      obtain ⟨ha, hck⟩ := hct ht
      rw [(pointwise_Z c ξ ζ a u t (fun k => (hck k).1) (fun k => (hck k).2) (hot ht)).deriv]
      have h1 : 0 ≤ a t * u t ^ 2 := mul_nonneg ha (sq_nonneg _)
      have h2 : 0 ≤ ∑ k, (√(c k t) * u t - √(ξ k t) * ζ k t) ^ 2 :=
        Finset.sum_nonneg fun k _ => sq_nonneg _
      linarith
    have h0 := energy_nonneg ζ T
    have : energy ζ 0 = (1 / 2) * ∑ k, ζ k 0 ^ 2 := rfl
    linarith
  · rw [intervalIntegral.integral_undef hint]
    have : 0 ≤ ∑ k, ζ k 0 ^ 2 := Finset.sum_nonneg fun k _ => sq_nonneg _
    linarith

/-- Constant coefficients, Y-form: in the Laplace domain (`s ζ̂_j = -p_j ζ̂_j + √r_j û`)
the output is `∑_j r_j / (s + p_j) · û`. -/
theorem transfer_Y (p r : ι → ℝ) (hr : ∀ j, 0 ≤ r j) (s U : ℂ) (Z : ι → ℂ)
    (hs : ∀ j, s + p j ≠ 0) (hZ : ∀ j, s * Z j = -(p j : ℂ) * Z j + (√(r j) : ℂ) * U) :
    ∑ j, (√(r j) : ℂ) * Z j = (∑ j, (r j : ℂ) / (s + p j)) * U := by
  rw [Finset.sum_mul]
  refine Finset.sum_congr rfl fun j _ => ?_
  have hZj : Z j = (√(r j) : ℂ) * U / (s + p j) := by
    rw [eq_div_iff (hs j)]; linear_combination hZ j
  have hsq : ((√(r j) : ℝ) : ℂ) * (√(r j) : ℂ) = (r j : ℂ) := by
    rw [← Complex.ofReal_mul, Real.mul_self_sqrt (hr j)]
  rw [hZj, ← hsq]; field_simp

/-- Constant coefficients, Z-form: in the Laplace domain (`s ζ̂_k = -ξ_k ζ̂_k + √(c_k ξ_k) û`)
the output `a û + ∑_k (c_k û - √(c_k ξ_k) ζ̂_k)` is `(a + ∑_k c_k s / (s + ξ_k)) û`. -/
theorem transfer_Z (c ξ : ι → ℝ) (a : ℝ) (hc : ∀ k, 0 ≤ c k) (hξ : ∀ k, 0 ≤ ξ k)
    (s U : ℂ) (Z : ι → ℂ) (hs : ∀ k, s + ξ k ≠ 0)
    (hZ : ∀ k, s * Z k = -(ξ k : ℂ) * Z k + (√(c k * ξ k) : ℂ) * U) :
    (a : ℂ) * U + ∑ k, ((c k : ℂ) * U - (√(c k * ξ k) : ℂ) * Z k)
      = ((a : ℂ) + ∑ k, (c k : ℂ) * s / (s + ξ k)) * U := by
  rw [add_mul, Finset.sum_mul]
  congr 1
  refine Finset.sum_congr rfl fun k _ => ?_
  have hZk : Z k = (√(c k * ξ k) : ℂ) * U / (s + ξ k) := by
    rw [eq_div_iff (hs k)]; linear_combination hZ k
  have hsq : ((√(c k * ξ k) : ℝ) : ℂ) * (√(c k * ξ k) : ℂ) = (c k : ℂ) * ξ k := by
    rw [← Complex.ofReal_mul, Real.mul_self_sqrt (mul_nonneg (hc k) (hξ k)),
      Complex.ofReal_mul]
  rw [hZk, mul_div_assoc', ← mul_assoc, hsq]
  field_simp
  have hinv : ((ξ k : ℂ) + s) * ((ξ k : ℂ) + s)⁻¹ = 1 :=
    mul_inv_cancel₀ (by rw [add_comm]; exact hs k)
  linear_combination (-((c k : ℂ) * U)) * hinv

universe w in
/-- MD_0070 as one statement: the Y-form pointwise identity, the integrated Y-form bound for
absolutely continuous (Carathéodory) states, the Z-form pointwise identity with its sign
`u y - d/dt energy = a u² + ∑ (√c u - √ξ ζ)² ≥ 0`, and the constant-coefficient transfer
functions of both forms. -/
theorem statement :
    (∀ (ι : Type w) [Fintype ι] (p r ζ : ι → ℝ → ℝ) (u : ℝ → ℝ) (t : ℝ),
      (∀ j, HasDerivAt (ζ j) (-p j t * ζ j t + √(r j t) * u t) t) →
      HasDerivAt (energy ζ) (u t * ∑ j, √(r j t) * ζ j t - ∑ j, p j t * ζ j t ^ 2) t) ∧
    (∀ (ι : Type w) [Fintype ι] (p r ζ : ι → ℝ → ℝ) (u : ℝ → ℝ) (T : ℝ), 0 ≤ T →
      (∀ᵐ t, t ∈ Icc 0 T → ∀ j, 0 ≤ p j t) →
      (∀ j, AbsolutelyContinuousOnInterval (ζ j) 0 T) →
      (∀ᵐ t, t ∈ Icc 0 T → ∀ j, HasDerivAt (ζ j) (-p j t * ζ j t + √(r j t) * u t) t) →
      -(1 / 2) * ∑ j, ζ j 0 ^ 2 ≤ ∫ t in (0)..T, u t * ∑ j, √(r j t) * ζ j t) ∧
    (∀ (ι : Type w) [Fintype ι] (c ξ ζ : ι → ℝ → ℝ) (a u : ℝ → ℝ) (t : ℝ),
      0 ≤ a t → (∀ k, 0 ≤ c k t) → (∀ k, 0 ≤ ξ k t) →
      (∀ k, HasDerivAt (ζ k) (-ξ k t * ζ k t + √(c k t * ξ k t) * u t) t) →
      HasDerivAt (energy ζ)
        (u t * (a t * u t + ∑ k, (c k t * u t - √(c k t * ξ k t) * ζ k t))
          - (a t * u t ^ 2 + ∑ k, (√(c k t) * u t - √(ξ k t) * ζ k t) ^ 2)) t ∧
      0 ≤ a t * u t ^ 2 + ∑ k, (√(c k t) * u t - √(ξ k t) * ζ k t) ^ 2) ∧
    (∀ (ι : Type w) [Fintype ι] (p r : ι → ℝ), (∀ j, 0 ≤ r j) → ∀ (s U : ℂ) (Z : ι → ℂ),
      (∀ j, s + p j ≠ 0) → (∀ j, s * Z j = -(p j : ℂ) * Z j + (√(r j) : ℂ) * U) →
      ∑ j, (√(r j) : ℂ) * Z j = (∑ j, (r j : ℂ) / (s + p j)) * U) ∧
    (∀ (ι : Type w) [Fintype ι] (c ξ : ι → ℝ) (a : ℝ), (∀ k, 0 ≤ c k) → (∀ k, 0 ≤ ξ k) →
      ∀ (s U : ℂ) (Z : ι → ℂ), (∀ k, s + ξ k ≠ 0) →
      (∀ k, s * Z k = -(ξ k : ℂ) * Z k + (√(c k * ξ k) : ℂ) * U) →
      (a : ℂ) * U + ∑ k, ((c k : ℂ) * U - (√(c k * ξ k) : ℂ) * Z k)
        = ((a : ℂ) + ∑ k, (c k : ℂ) * s / (s + ξ k)) * U) := by
  refine ⟨fun ι _ => pointwise_Y, fun ι _ p r ζ u T hT => integral_Y p r ζ u hT,
    fun ι _ c ξ ζ a u t ha hc hξ hζ => ⟨?_, ?_⟩, fun ι _ => transfer_Y,
    fun ι _ => transfer_Z⟩
  · simpa only [sub_add_eq_sub_sub] using pointwise_Z c ξ ζ a u t hc hξ hζ
  · exact add_nonneg (mul_nonneg ha (sq_nonneg _)) (Finset.sum_nonneg fun k _ => sq_nonneg _)

end MathDept.MD_0070
