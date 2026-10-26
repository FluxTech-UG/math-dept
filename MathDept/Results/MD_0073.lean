import Mathlib.Analysis.Calculus.ImplicitFunction.Bivariate
import Mathlib.Analysis.Calculus.Deriv.Mul
import Mathlib.Analysis.Calculus.Deriv.Shift
import Mathlib.Analysis.Calculus.Deriv.Polynomial
import Mathlib.Analysis.Complex.Basic
import Mathlib.LinearAlgebra.Matrix.Charpoly.Coeff
import Mathlib.LinearAlgebra.Charpoly.ToMatrix
import Mathlib.LinearAlgebra.Eigenspace.Zero
import Mathlib.LinearAlgebra.Matrix.ToLinearEquiv
import Mathlib.Topology.Instances.Matrix
import Mathlib.Algebra.Polynomial.FieldDivision
import Mathlib.Algebra.BigOperators.Field

/-!
# MD_0073: the left-right eigenvector budget sums exactly to the eigenvalue

## Informal statement

Let `A = ∑_{e=1}^E A_e` with `A_e ∈ ℂ^{N×N}`, `A v = λ v`, `w* A = λ w*`, `w* v ≠ 0`, and
`s_e := w* A_e v / (w* v)`. Then `∑_e s_e = λ` (`statement_sum`), and if `λ` is algebraically
simple then `s_e = d/dε λ(A + ε A_e)|_{ε=0}`, where `λ(A + ε A_e)` is the unique eigenvalue of
`A + ε A_e` near `λ` for small `|ε|` (`statement_deriv`).

## Conventions used here

* Matrices are `Matrix (Fin N) (Fin N) ℂ`, the split is `P : Fin E → Matrix ..` with
  `A = ∑ e, P e`. `λ` is `lam` (`λ` is a Lean keyword).
* `w*` is `star w` used as a row: `w* A = λ w*` is `star w ᵥ* A = lam • star w`, `w* v` is
  `star w ⬝ᵥ v`, and `s_e` is `share (P e) v w`.
* Algebraically simple: `A.charpoly.rootMultiplicity lam = 1`.
* "The unique eigenvalue near `λ` for small `|ε|`" is stated as: there are `r > 0`, `δ > 0` and
  `f : ℂ → ℂ` with `f 0 = λ` such that for `‖ε‖ < δ`, `f ε` is an eigenvalue of `A + ε A_e`
  (a nonzero `x` with `(A + ε A_e) x = f ε • x`), `‖f ε - λ‖ < r`, and every eigenvalue `μ` of
  `A + ε A_e` with `‖μ - λ‖ < r` equals `f ε`; and `HasDerivAt f s_e 0`.

## Proof recipe

1. `statement_sum`: linearity of `X ↦ w* X v` and `A v = λ v`.
2. `hasDerivAt_det_add` (Jacobi): `d/dt det (M + t B) = tr (adj (M + t₀ B) B)`, from the
   Leibniz expansion (`trace_adjugate_mul`) and `HasDerivAt.fun_finsetProd`.
3. `eq_smul_of_simple`: algebraic multiplicity one forces a one-dimensional eigenspace
   (`LinearMap.finrank_eigenspace_le`), for `A` and for `Aᵀ`.
4. `adjugate_eq`: `adj (λ • 1 - A) = c v w*`, since its columns lie in the right kernel and its
   rows in the left kernel.
5. `trace_adjugate_ne_zero`: `tr adj (λ • 1 - A) = χ_A'(λ) ≠ 0` by simplicity
   (`one_lt_rootMultiplicity_iff_isRoot_iterate_derivative`).
6. `deriv_core`: the bivariate implicit function theorem (`implicitFunctionOfBivariate`) applied
   to `p(ε, z) = det (z • 1 - (A + ε B))`, with the partials of step 2, gives the branch, its
   local uniqueness and its differentiability; the chain rule on `p(ε, f ε) = 0` with step 4
   gives `f'(0) = c w* B v / (c w* v) = s_e`.
-/

namespace MathDept.MD_0073

open Matrix Finset Polynomial Filter
open scoped Topology

variable {n : Type*} [Fintype n] [DecidableEq n]

/-- Leibniz form of `tr (adj M * B)`. -/
lemma trace_adjugate_mul (M B : Matrix n n ℂ) :
    trace (adjugate M * B) = ∑ σ : Equiv.Perm n, (Equiv.Perm.sign σ : ℂ) *
      ∑ i, (∏ j ∈ univ.erase i, M (σ j) j) * B (σ i) i := by
  have h1 : trace (adjugate M * B) = ∑ k, (M.updateRow k (B k)).det := by
    simp only [trace, Matrix.diag, Matrix.mul_apply]
    rw [Finset.sum_comm]
    refine Finset.sum_congr rfl fun k _ => ?_
    rw [det_eq_sum_mul_adjugate_row (M.updateRow k (B k)) k]
    refine Finset.sum_congr rfl fun i _ => ?_
    rw [updateRow_self, mul_comm]
    congr 1
    rw [adjugate_apply, adjugate_apply, updateRow_idem]
  rw [h1]
  simp only [det_apply']
  rw [Finset.sum_comm]
  refine Finset.sum_congr rfl fun σ _ => ?_
  rw [← Finset.mul_sum, ← Equiv.sum_comp σ]
  congr 1
  refine Finset.sum_congr rfl fun i _ => ?_
  rw [mul_comm _ (B _ _), ← Finset.mul_prod_erase univ _ (mem_univ i)]
  simp only [updateRow_apply, if_true]
  congr 1
  refine Finset.prod_congr rfl fun j hj => ?_
  rw [if_neg (fun h => (Finset.mem_erase.mp hj).1 (σ.injective h))]

/-- Jacobi's formula at `0`: `d/dt det (M + t B) = tr (adj M * B)`. -/
lemma hasDerivAt_det_add_zero (M B : Matrix n n ℂ) :
    HasDerivAt (fun t : ℂ => (M + t • B).det) (trace (adjugate M * B)) 0 := by
  rw [trace_adjugate_mul]
  simp only [det_apply']
  apply HasDerivAt.fun_sum
  intro σ _
  apply HasDerivAt.const_mul
  have h := HasDerivAt.fun_finsetProd (u := univ) (x := (0 : ℂ))
    (f := fun (i : n) (t : ℂ) => M (σ i) i + t * B (σ i) i) (f' := fun i => B (σ i) i)
    (fun i _ => by
      simpa using ((hasDerivAt_id (0 : ℂ)).mul_const (B (σ i) i)).const_add (M (σ i) i))
  convert h using 1
  · funext t; simp [smul_eq_mul]
  · refine Finset.sum_congr rfl fun i _ => ?_
    simp [smul_eq_mul]

/-- Jacobi's formula at any point. -/
lemma hasDerivAt_det_add (M B : Matrix n n ℂ) (t₀ : ℂ) :
    HasDerivAt (fun t : ℂ => (M + t • B).det) (trace (adjugate (M + t₀ • B) * B)) t₀ := by
  have h := HasDerivAt.comp_sub_const t₀ t₀
    (by rw [sub_self]; exact hasDerivAt_det_add_zero (M + t₀ • B) B)
  have e : (fun t : ℂ => (M + t • B).det) = fun t => (M + t₀ • B + (t - t₀) • B).det := by
    funext t
    rw [add_assoc, ← add_smul, add_sub_cancel]
  rw [e]
  exact h

/-- `(μ • 1 - M) x = 0` is the eigen-relation `M x = μ x`. -/
lemma sub_mulVec_eq_zero_iff {N : ℕ} (M : Matrix (Fin N) (Fin N) ℂ) (μ : ℂ) (x : Fin N → ℂ) :
    (μ • (1 : Matrix (Fin N) (Fin N) ℂ) - M) *ᵥ x = 0 ↔ M *ᵥ x = μ • x := by
  rw [sub_mulVec, smul_mulVec, one_mulVec, sub_eq_zero, eq_comm]

lemma vecMul_sub_eq_zero_iff {N : ℕ} (M : Matrix (Fin N) (Fin N) ℂ) (μ : ℂ) (x : Fin N → ℂ) :
    x ᵥ* (μ • (1 : Matrix (Fin N) (Fin N) ℂ) - M) = 0 ↔ Mᵀ *ᵥ x = μ • x := by
  rw [vecMul_sub, vecMul_smul, vecMul_one, sub_eq_zero, eq_comm, mulVec_transpose]

/-- An eigenvalue is a zero of `det (μ • 1 - M)`. -/
lemma eigen_iff_det {N : ℕ} (M : Matrix (Fin N) (Fin N) ℂ) (μ : ℂ) :
    (∃ x ≠ 0, M *ᵥ x = μ • x) ↔ (μ • (1 : Matrix (Fin N) (Fin N) ℂ) - M).det = 0 := by
  rw [← exists_mulVec_eq_zero_iff]
  simp only [sub_mulVec_eq_zero_iff]

/-- Algebraic simplicity forces geometric simplicity. -/
lemma eq_smul_of_simple {N : ℕ} (A : Matrix (Fin N) (Fin N) ℂ) (lam : ℂ)
    (hs : A.charpoly.rootMultiplicity lam = 1) (v : Fin N → ℂ) (hv0 : v ≠ 0)
    (hv : A *ᵥ v = lam • v) (x : Fin N → ℂ) (hx : A *ᵥ x = lam • x) : ∃ c : ℂ, x = c • v := by
  have hle : Module.finrank ℂ (Module.End.eigenspace (Matrix.toLin' A) lam) ≤ 1 := by
    have := LinearMap.finrank_eigenspace_le (Matrix.toLin' A) lam
    rwa [Matrix.charpoly_toLin', hs] at this
  obtain ⟨u, hu⟩ := finrank_le_one_iff.mp hle
  have mv : v ∈ Module.End.eigenspace (Matrix.toLin' A) lam := by
    rw [Module.End.mem_eigenspace_iff, Matrix.toLin'_apply]; exact hv
  have mx : x ∈ Module.End.eigenspace (Matrix.toLin' A) lam := by
    rw [Module.End.mem_eigenspace_iff, Matrix.toLin'_apply]; exact hx
  obtain ⟨a, ha⟩ := hu ⟨v, mv⟩
  obtain ⟨b, hb⟩ := hu ⟨x, mx⟩
  have ha' : a • (u : Fin N → ℂ) = v := congrArg Subtype.val ha
  have hb' : b • (u : Fin N → ℂ) = x := congrArg Subtype.val hb
  have ha0 : a ≠ 0 := by rintro rfl; apply hv0; rw [← ha']; simp
  refine ⟨b / a, ?_⟩
  rw [← ha', ← hb', smul_smul, div_mul_cancel₀ _ ha0]

/-- At a simple eigenvalue the adjugate of `λ • 1 - A` is a multiple of `v w*`. -/
lemma adjugate_eq {N : ℕ} (A : Matrix (Fin N) (Fin N) ℂ) (lam : ℂ)
    (hs : A.charpoly.rootMultiplicity lam = 1) (v w : Fin N → ℂ) (hv : A *ᵥ v = lam • v)
    (hw : star w ᵥ* A = lam • star w) (hwv : star w ⬝ᵥ v ≠ 0) :
    ∃ c : ℂ, ∀ i j, adjugate (lam • (1 : Matrix (Fin N) (Fin N) ℂ) - A) i j
      = c * v i * star w j := by
  set M := lam • (1 : Matrix (Fin N) (Fin N) ℂ) - A with hM
  set K := adjugate M
  have hv0 : v ≠ 0 := by rintro rfl; simp at hwv
  have hw0 : star w ≠ 0 := by intro h; rw [h] at hwv; simp at hwv
  have hdet : M.det = 0 := by
    rw [← exists_mulVec_eq_zero_iff]; exact ⟨v, hv0, (sub_mulVec_eq_zero_iff A lam v).mpr hv⟩
  have hcol : ∀ j, ∃ a : ℂ, (fun i => K i j) = a • v := by
    intro j
    have hMK : M *ᵥ (fun i => K i j) = 0 := by
      funext i
      have := congrFun (congrFun (mul_adjugate M) i) j
      rw [hdet, zero_smul] at this
      simpa [mulVec, dotProduct, mul_apply] using this
    exact eq_smul_of_simple A lam hs v hv0 hv _ ((sub_mulVec_eq_zero_iff A lam _).mp hMK)
  have hrow : ∀ i, ∃ b : ℂ, (fun j => K i j) = b • star w := by
    intro i
    have hKM : (fun j => K i j) ᵥ* M = 0 := by
      funext j
      have := congrFun (congrFun (adjugate_mul M) i) j
      rw [hdet, zero_smul] at this
      simpa [vecMul, dotProduct, mul_apply] using this
    have hsT : Aᵀ.charpoly.rootMultiplicity lam = 1 := by rw [charpoly_transpose]; exact hs
    have hwT : Aᵀ *ᵥ star w = lam • star w := by rw [mulVec_transpose]; exact hw
    exact eq_smul_of_simple Aᵀ lam hsT (star w) hw0 hwT _
      ((vecMul_sub_eq_zero_iff A lam _).mp hKM)
  choose α hα using hcol
  choose β hβ using hrow
  obtain ⟨i₀, hi₀⟩ := Function.ne_iff.mp hv0
  refine ⟨β i₀ / v i₀, fun i j => ?_⟩
  have h1 : K i j = α j * v i := by simpa using congrFun (hα j) i
  have h2 : K i₀ j = β i₀ * star w j := by simpa using congrFun (hβ i₀) j
  have h3 : K i₀ j = α j * v i₀ := by simpa using congrFun (hα j) i₀
  rw [h1]
  have hi : v i₀ ≠ 0 := by simpa using hi₀
  have h4 : α j = β i₀ / v i₀ * star w j := by
    rw [div_mul_eq_mul_div, eq_div_iff hi, ← h3, h2]
  rw [h4]; ring

/-- The budget share `s_e = w* A_e v / (w* v)`, with `w*` the conjugate transpose of `w`. -/
noncomputable def share {N : ℕ} (B : Matrix (Fin N) (Fin N) ℂ) (v w : Fin N → ℂ) : ℂ :=
  (star w ⬝ᵥ (B *ᵥ v)) / (star w ⬝ᵥ v)

/-- Clause 1: the shares sum to the eigenvalue. -/
theorem statement_sum (N E : ℕ) (P : Fin E → Matrix (Fin N) (Fin N) ℂ)
    (A : Matrix (Fin N) (Fin N) ℂ) (hA : A = ∑ e, P e) (lam : ℂ) (v w : Fin N → ℂ)
    (hv : A *ᵥ v = lam • v) (_hw : star w ᵥ* A = lam • star w) (hwv : star w ⬝ᵥ v ≠ 0) :
    ∑ e, share (P e) v w = lam := by
  simp only [share]
  rw [← Finset.sum_div]
  have h : ∑ e, star w ⬝ᵥ (P e *ᵥ v) = star w ⬝ᵥ (A *ᵥ v) := by
    rw [hA, Matrix.sum_mulVec, dotProduct_sum]
  rw [h, hv, dotProduct_smul, smul_eq_mul, mul_div_assoc, div_self hwv, mul_one]

lemma trace_rank_one {N : ℕ} (K B : Matrix (Fin N) (Fin N) ℂ) (c : ℂ) (v w : Fin N → ℂ)
    (hK : ∀ i j, K i j = c * v i * star w j) :
    trace (K * B) = c * (star w ⬝ᵥ (B *ᵥ v)) := by
  simp only [trace, Matrix.diag, Matrix.mul_apply, hK, dotProduct, mulVec, Pi.star_apply,
    Finset.mul_sum]
  rw [Finset.sum_comm]
  exact Finset.sum_congr rfl fun _ _ => Finset.sum_congr rfl fun _ _ => by ring

lemma charpoly_eval_eq {N : ℕ} (A : Matrix (Fin N) (Fin N) ℂ) (z : ℂ) :
    A.charpoly.eval z = (-A + z • (1 : Matrix (Fin N) (Fin N) ℂ)).det := by
  rw [eval_charpoly, neg_add_eq_sub, Matrix.scalar_apply, Matrix.smul_one_eq_diagonal]

/-- Simplicity makes `χ_A'(λ) = tr adj (λ • 1 - A)` nonzero. -/
lemma trace_adjugate_ne_zero {N : ℕ} (A : Matrix (Fin N) (Fin N) ℂ) (lam : ℂ)
    (hs : A.charpoly.rootMultiplicity lam = 1) :
    trace (adjugate (lam • (1 : Matrix (Fin N) (Fin N) ℂ) - A) * 1) ≠ 0 := by
  have h1 := hasDerivAt_det_add (-A) (1 : Matrix (Fin N) (Fin N) ℂ) lam
  have h2 := A.charpoly.hasDerivAt lam
  have e : (fun z => A.charpoly.eval z)
      = fun t : ℂ => (-A + t • (1 : Matrix (Fin N) (Fin N) ℂ)).det := by
    funext z; exact charpoly_eval_eq A z
  rw [e] at h2
  have h3 := h1.unique h2
  rw [neg_add_eq_sub] at h3
  rw [h3]
  intro h0
  have hne : A.charpoly ≠ 0 := (charpoly_monic A).ne_zero
  have hroot : A.charpoly.IsRoot lam := (rootMultiplicity_pos hne).mp (by rw [hs]; norm_num)
  have h4 := (one_lt_rootMultiplicity_iff_isRoot_iterate_derivative hne).mpr (fun m hm => by
    interval_cases m
    · simpa using hroot
    · simpa [IsRoot] using h0)
  omega

lemma smulRight_one_eq (c : ℂ) :
    ContinuousLinearMap.toSpanSingleton ℂ c = c • ContinuousLinearMap.id ℂ ℂ := by
  ext; simp

/-- Clause 2 for one perturbation direction `B`. -/
theorem deriv_core {N : ℕ} (A B : Matrix (Fin N) (Fin N) ℂ) (lam : ℂ) (v w : Fin N → ℂ)
    (hv : A *ᵥ v = lam • v) (hw : star w ᵥ* A = lam • star w) (hwv : star w ⬝ᵥ v ≠ 0)
    (hs : A.charpoly.rootMultiplicity lam = 1) :
    ∃ r > 0, ∃ δ > 0, ∃ f : ℂ → ℂ, f 0 = lam ∧
      (∀ ε : ℂ, ‖ε‖ < δ → (∃ x ≠ 0, (A + ε • B) *ᵥ x = f ε • x) ∧ ‖f ε - lam‖ < r ∧
        ∀ μ : ℂ, ‖μ - lam‖ < r → (∃ x ≠ 0, (A + ε • B) *ᵥ x = μ • x) → μ = f ε) ∧
      HasDerivAt f (share B v w) 0 := by
  have hv0 : v ≠ 0 := by rintro rfl; simp at hwv
  let p : ℂ → ℂ → ℂ := fun ε z => (z • (1 : Matrix (Fin N) (Fin N) ℂ) - (A + ε • B)).det
  let g₁ : ℂ → ℂ → ℂ := fun ε z =>
    trace (adjugate (z • (1 : Matrix (Fin N) (Fin N) ℂ) - (A + ε • B)) * (-B))
  let g₂ : ℂ → ℂ → ℂ := fun ε z =>
    trace (adjugate (z • (1 : Matrix (Fin N) (Fin N) ℂ) - (A + ε • B)) * 1)
  let f₁ : ℂ → ℂ → ℂ →L[ℂ] ℂ := fun ε z => g₁ ε z • ContinuousLinearMap.id ℂ ℂ
  let f₂ : ℂ → ℂ → ℂ →L[ℂ] ℂ := fun ε z => g₂ ε z • ContinuousLinearMap.id ℂ ℂ
  have df₁ : ∀ᶠ q in 𝓝 ((0 : ℂ), lam), HasFDerivAt (p · q.2) (f₁ q.1 q.2) q.1 := by
    refine Eventually.of_forall fun q => ?_
    have h := hasDerivAt_det_add (q.2 • (1 : Matrix (Fin N) (Fin N) ℂ) - A) (-B) q.1
    have e1 : ∀ t : ℂ, q.2 • (1 : Matrix (Fin N) (Fin N) ℂ) - A + t • (-B)
        = q.2 • (1 : Matrix (Fin N) (Fin N) ℂ) - (A + t • B) := fun t => by
      rw [smul_neg]; abel
    simp only [e1] at h
    have h' := h.hasFDerivAt
    rw [smulRight_one_eq] at h'
    exact h'
  have df₂ : ∀ᶠ q in 𝓝 ((0 : ℂ), lam), HasFDerivAt (p q.1 ·) (f₂ q.1 q.2) q.2 := by
    refine Eventually.of_forall fun q => ?_
    have h := hasDerivAt_det_add (-(A + q.1 • B)) (1 : Matrix (Fin N) (Fin N) ℂ) q.2
    have e1 : ∀ t : ℂ, -(A + q.1 • B) + t • (1 : Matrix (Fin N) (Fin N) ℂ)
        = t • (1 : Matrix (Fin N) (Fin N) ℂ) - (A + q.1 • B) := fun t => by abel
    simp only [e1] at h
    have h' := h.hasFDerivAt
    rw [smulRight_one_eq] at h'
    exact h'
  have hcont : Continuous fun q : ℂ × ℂ =>
      adjugate (q.2 • (1 : Matrix (Fin N) (Fin N) ℂ) - (A + q.1 • B)) :=
    ((continuous_snd.smul continuous_const).sub
      (continuous_const.add (continuous_fst.smul continuous_const))).matrix_adjugate
  have cf₁ : ContinuousAt ↿f₁ ((0 : ℂ), lam) :=
    (((hcont.matrix_mul continuous_const).matrix_trace).smul continuous_const).continuousAt
  have cf₂ : ContinuousAt ↿f₂ ((0 : ℂ), lam) :=
    (((hcont.matrix_mul continuous_const).matrix_trace).smul continuous_const).continuousAt
  obtain ⟨c, hc⟩ := adjugate_eq A lam hs v w hv hw hwv
  have e0 : lam • (1 : Matrix (Fin N) (Fin N) ℂ) - (A + (0 : ℂ) • B)
      = lam • (1 : Matrix (Fin N) (Fin N) ℂ) - A := by simp
  have hg₂ : g₂ 0 lam = c * (star w ⬝ᵥ v) := by
    simp only [g₂, e0]
    rw [trace_rank_one _ _ c v w hc, one_mulVec]
  have hg₁ : g₁ 0 lam = -(c * (star w ⬝ᵥ (B *ᵥ v))) := by
    simp only [g₁, e0]
    rw [Matrix.mul_neg, trace_neg, trace_rank_one _ _ c v w hc]
  have hb : g₂ 0 lam ≠ 0 := by
    have h := trace_adjugate_ne_zero A lam hs
    simp only [g₂, e0]
    exact h
  have if₂u : (f₂ ((0 : ℂ), lam).1 ((0 : ℂ), lam).2).IsInvertible := by
    refine ContinuousLinearMap.IsInvertible.of_inverse
      (g := (g₂ 0 lam)⁻¹ • ContinuousLinearMap.id ℂ ℂ) ?_ ?_
    · ext; simp [f₂, hb]
    · ext; simp [f₂, hb]
  set ψ := implicitFunctionOfBivariate df₁ df₂ cf₁ cf₂ if₂u with hψdef
  have hiff := eventually_apply_eq_iff_implicitFunctionOfBivariate df₁ df₂ cf₁ cf₂ if₂u
  have hzero := eventually_apply_implicitFunctionOfBivariate df₁ df₂ cf₁ cf₂ if₂u
  have htend := tendsto_implicitFunctionOfBivariate df₁ df₂ cf₁ cf₂ if₂u
  have hL := hasStrictFDerivAt_implicitFunctionOfBivariate df₁ df₂ cf₁ cf₂ if₂u
  rw [← hψdef] at hiff hzero htend hL
  have hψ0 : ψ 0 = lam := (hiff.self_of_nhds).mp rfl
  have hp0 : p 0 lam = 0 := by
    show (lam • (1 : Matrix (Fin N) (Fin N) ℂ) - (A + (0 : ℂ) • B)).det = 0
    rw [e0, ← eigen_iff_det]
    exact ⟨v, hv0, hv⟩
  obtain ⟨r, hr, hr'⟩ := Metric.eventually_nhds_iff.mp hiff
  obtain ⟨δ₁, hδ₁, hδ₁'⟩ := Metric.eventually_nhds_iff.mp hzero
  obtain ⟨δ₂, hδ₂, hδ₂'⟩ := Metric.tendsto_nhds_nhds.mp htend r hr
  refine ⟨r, hr, min (min δ₁ δ₂) r, by positivity, ψ, hψ0, ?_, ?_⟩
  · intro ε hε
    have hε' : dist ε 0 < min (min δ₁ δ₂) r := by rwa [dist_zero_right]
    simp only [lt_min_iff] at hε'
    obtain ⟨⟨h1, h2⟩, h3⟩ := hε'
    refine ⟨?_, ?_, ?_⟩
    · rw [eigen_iff_det]
      have := hδ₁' h1
      simp only [hp0] at this
      exact this
    · rw [← dist_eq_norm]; exact hδ₂' h2
    · intro μ hμ hμe
      rw [eigen_iff_det] at hμe
      have hd : dist (ε, μ) ((0 : ℂ), lam) < r := by
        rw [Prod.dist_eq, max_lt_iff]
        exact ⟨h3, by rwa [dist_eq_norm]⟩
      have := (hr' hd).mp (by simp only [hp0]; exact hμe)
      exact this.symm
  · have hF := (hasStrictFDerivAt_uncurry_coprod df₁ df₂ cf₁ cf₂).hasFDerivAt
    have hγ : HasFDerivAt (fun ε : ℂ => (ε, ψ ε))
        ((ContinuousLinearMap.id ℂ ℂ).prod (-(f₂ ((0 : ℂ), lam).1 ((0 : ℂ), lam).2).inverse ∘L
          f₁ ((0 : ℂ), lam).1 ((0 : ℂ), lam).2)) 0 :=
      (hasFDerivAt_id (0 : ℂ)).prodMk hL.hasFDerivAt
    have hpt : (fun ε : ℂ => (ε, ψ ε)) 0 = ((0 : ℂ), lam) := by simp [hψ0]
    rw [← hpt] at hF
    have hcomp := hF.comp (0 : ℂ) hγ
    have hconst : HasFDerivAt (fun ε => p ε (ψ ε)) (0 : ℂ →L[ℂ] ℂ) 0 :=
      (hasFDerivAt_const (p 0 lam) (0 : ℂ)).congr_of_eventuallyEq hzero
    have huniq := hcomp.unique hconst
    have h1 := congrArg (fun T : ℂ →L[ℂ] ℂ => T 1) huniq
    have hd := hL.hasFDerivAt.hasDerivAt
    simp only [f₁, f₂] at h1 hd
    simp at h1 hd
    rw [hψ0] at h1
    generalize (g₂ 0 lam • ContinuousLinearMap.id ℂ ℂ).inverse 1 = X at h1 hd
    have h2 : g₁ 0 lam * 1 + -(g₂ 0 lam * (g₁ 0 lam * X)) = 0 := h1
    clear h1
    have hc0 : c ≠ 0 := by rintro rfl; apply hb; rw [hg₂, zero_mul]
    rw [hg₂] at h2 hb
    rw [hg₁] at h2 hd
    have hwv' : star w ⬝ᵥ v ≠ 0 := fun h => hb (by rw [h, mul_zero])
    have hD : share B v w = -(-(c * (star w ⬝ᵥ (B *ᵥ v))) * X) := by
      simp only [share]
      rw [div_eq_iff hwv']
      apply mul_left_cancel₀ hc0
      linear_combination -h2
    rw [hD]
    exact hd

/-- Clause 2: at an algebraically simple eigenvalue, `s_e` is the derivative at `ε = 0` of the
unique eigenvalue of `A + ε A_e` near `λ`. -/
theorem statement_deriv (N E : ℕ) (P : Fin E → Matrix (Fin N) (Fin N) ℂ)
    (A : Matrix (Fin N) (Fin N) ℂ) (_hA : A = ∑ e, P e) (lam : ℂ) (v w : Fin N → ℂ)
    (hv : A *ᵥ v = lam • v) (hw : star w ᵥ* A = lam • star w) (hwv : star w ⬝ᵥ v ≠ 0)
    (hs : A.charpoly.rootMultiplicity lam = 1) (e : Fin E) :
    ∃ r > 0, ∃ δ > 0, ∃ f : ℂ → ℂ, f 0 = lam ∧
      (∀ ε : ℂ, ‖ε‖ < δ → (∃ x ≠ 0, (A + ε • P e) *ᵥ x = f ε • x) ∧ ‖f ε - lam‖ < r ∧
        ∀ μ : ℂ, ‖μ - lam‖ < r → (∃ x ≠ 0, (A + ε • P e) *ᵥ x = μ • x) → μ = f ε) ∧
      HasDerivAt f (share (P e) v w) 0 :=
  deriv_core A (P e) lam v w hv hw hwv hs

/-- The entry's statement: the sum clause and the derivative clause together. -/
theorem statement :
    (∀ (N E : ℕ) (P : Fin E → Matrix (Fin N) (Fin N) ℂ) (A : Matrix (Fin N) (Fin N) ℂ),
      A = ∑ e, P e → ∀ (lam : ℂ) (v w : Fin N → ℂ), A *ᵥ v = lam • v → star w ᵥ* A = lam • star w →
        star w ⬝ᵥ v ≠ 0 → ∑ e, share (P e) v w = lam) ∧
    (∀ (N E : ℕ) (P : Fin E → Matrix (Fin N) (Fin N) ℂ) (A : Matrix (Fin N) (Fin N) ℂ),
      A = ∑ e, P e → ∀ (lam : ℂ) (v w : Fin N → ℂ), A *ᵥ v = lam • v → star w ᵥ* A = lam • star w →
        star w ⬝ᵥ v ≠ 0 → A.charpoly.rootMultiplicity lam = 1 → ∀ e : Fin E,
        ∃ r > 0, ∃ δ > 0, ∃ f : ℂ → ℂ, f 0 = lam ∧
          (∀ ε : ℂ, ‖ε‖ < δ → (∃ x ≠ 0, (A + ε • P e) *ᵥ x = f ε • x) ∧ ‖f ε - lam‖ < r ∧
            ∀ μ : ℂ, ‖μ - lam‖ < r → (∃ x ≠ 0, (A + ε • P e) *ᵥ x = μ • x) → μ = f ε) ∧
          HasDerivAt f (share (P e) v w) 0) :=
  ⟨fun N E P A hA lam v w hv hw hwv => statement_sum N E P A hA lam v w hv hw hwv,
   fun N E P A hA lam v w hv hw hwv hs e => statement_deriv N E P A hA lam v w hv hw hwv hs e⟩

end MathDept.MD_0073
