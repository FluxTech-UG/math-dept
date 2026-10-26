import Mathlib.Analysis.CStarAlgebra.Matrix
import Mathlib.Analysis.InnerProductSpace.PiL2

/-!
# MD_0051: A residual places the Ritz value in the pseudospectrum

Informal statement. Let `d ≥ 1`, `M ∈ ℂ^{d×d}`, `θ ∈ ℂ`, `u ∈ ℂ^d` with `‖u‖₂ = 1`, and
`ε ≥ 0` with `‖Mu − θu‖₂ ≤ ε`. Then `σ_min(θI − M) ≤ ε`, and `E := −(Mu − θu)u*` satisfies
`‖E‖₂ ≤ ε` and `(M + E)u = θu`.

Formalization notes.
* Vectors live in `EuclideanSpace ℂ (Fin d)`; a matrix acts through
  `Matrix.toEuclideanCLM`, whose operator norm is the matrix `ℓ²` operator norm
  (`Matrix.l2_opNorm_toEuclideanCLM`, scope `Matrix.Norms.L2Operator`).
* Mathlib has no matrix smallest singular value. For a square matrix `A`,
  `σ_min(A) = min_{‖v‖ = 1} ‖A v‖₂` (Courant–Fischer for `AᴴA`), so claim (a) is stated
  in two equivalent-to-the-ledger forms: a unit vector `v` with `‖(θI − M)v‖ ≤ ε`, and the
  infimum `⨅ v : {v // ‖v‖ = 1}, ‖(θI − M)v‖ ≤ ε`, which is `σ_min(θI − M)`.
* `u*` is the conjugate transpose, so `E = −vecMulVec r (star u)` with `r = Mu − θu`.

Proof recipe.
1. `(θI − M)u = −r`, so `u` itself is the unit vector of (a); the infimum is at most its
   value at `u`.
2. `E x = −⟪u, x⟫ r`, so `‖E x‖ = |⟪u, x⟫| ‖r‖ ≤ ‖x‖ ε` by Cauchy–Schwarz; the operator
   norm bound follows from `ContinuousLinearMap.opNorm_le_bound`.
3. `E u = −⟪u, u⟫ r = −r`, so `(M + E)u = Mu − r = θu`.
-/

open scoped Matrix.Norms.L2Operator

namespace MathDept.MD_0051

open Matrix

/-- `vecMulVec r (star u)` acts on `x` as `⟪u, x⟫ • r`. -/
lemma toEuclideanCLM_vecMulVec {d : ℕ} (r u x : EuclideanSpace ℂ (Fin d)) :
    toEuclideanCLM (n := Fin d) (𝕜 := ℂ) (vecMulVec (WithLp.ofLp r) (star (WithLp.ofLp u))) x
      = (inner ℂ u x) • r := by
  ext i
  simp only [ofLp_toEuclideanCLM, vecMulVec_mulVec, EuclideanSpace.inner_eq_star_dotProduct,
    PiLp.smul_apply, Pi.smul_apply, smul_eq_mul, MulOpposite.smul_eq_mul_unop,
    MulOpposite.unop_op]
  rw [dotProduct_comm]
  ring

theorem statement {d : ℕ} (_hd : 1 ≤ d) (M : Matrix (Fin d) (Fin d) ℂ) (θ : ℂ)
    (u : EuclideanSpace ℂ (Fin d)) (hu : ‖u‖ = 1) (ε : ℝ) (hε : 0 ≤ ε)
    (hres : ‖toEuclideanCLM (n := Fin d) (𝕜 := ℂ) M u - θ • u‖ ≤ ε) :
    -- (a), unit-vector form
    (∃ v : EuclideanSpace ℂ (Fin d), ‖v‖ = 1 ∧
      ‖toEuclideanCLM (n := Fin d) (𝕜 := ℂ) (θ • (1 : Matrix (Fin d) (Fin d) ℂ) - M) v‖ ≤ ε) ∧
    -- (a), infimum form: the left side is `σ_min(θI − M)`
    (⨅ v : {v : EuclideanSpace ℂ (Fin d) // ‖v‖ = 1},
      ‖toEuclideanCLM (n := Fin d) (𝕜 := ℂ) (θ • (1 : Matrix (Fin d) (Fin d) ℂ) - M) v‖) ≤ ε ∧
    -- (b)
    (let r := toEuclideanCLM (n := Fin d) (𝕜 := ℂ) M u - θ • u
     let E : Matrix (Fin d) (Fin d) ℂ := -vecMulVec (WithLp.ofLp r) (star (WithLp.ofLp u))
     ‖E‖ ≤ ε ∧ toEuclideanCLM (n := Fin d) (𝕜 := ℂ) (M + E) u = θ • u) := by
  set r := toEuclideanCLM (n := Fin d) (𝕜 := ℂ) M u - θ • u with hr
  have hA : ‖toEuclideanCLM (n := Fin d) (𝕜 := ℂ)
      (θ • (1 : Matrix (Fin d) (Fin d) ℂ) - M) u‖ ≤ ε := by
    rw [map_sub, map_smul, map_one, _root_.sub_apply,
      _root_.smul_apply, one_apply_eq_self, norm_sub_rev]
    exact hres
  refine ⟨⟨u, hu, hA⟩, ?_, ?_⟩
  · refine (ciInf_le ⟨0, ?_⟩ (⟨u, hu⟩ : {v : EuclideanSpace ℂ (Fin d) // ‖v‖ = 1})).trans hA
    rintro _ ⟨v, rfl⟩
    exact norm_nonneg _
  · simp only
    refine ⟨?_, ?_⟩
    · rw [← l2_opNorm_toEuclideanCLM]
      refine ContinuousLinearMap.opNorm_le_bound _ hε fun x => ?_
      rw [map_neg, _root_.neg_apply, toEuclideanCLM_vecMulVec, norm_neg,
        norm_smul]
      calc ‖inner ℂ u x‖ * ‖r‖ ≤ (‖u‖ * ‖x‖) * ε :=
            mul_le_mul (norm_inner_le_norm u x) hres (norm_nonneg _) (by positivity)
        _ = ε * ‖x‖ := by rw [hu]; ring
    · rw [map_add, _root_.add_apply, map_neg, _root_.neg_apply,
        toEuclideanCLM_vecMulVec, inner_self_eq_norm_sq_to_K, hu]
      simp [hr]

end MathDept.MD_0051

