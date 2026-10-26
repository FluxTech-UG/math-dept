import Mathlib.Analysis.Calculus.MeanValue
import Mathlib.Analysis.Calculus.ContDiff.Comp
import Mathlib.Analysis.Calculus.ContDiff.Operations
import Mathlib.Analysis.InnerProductSpace.PiL2

/-!
# MD_0045: the shooting residual lies in the deflated subspace

## Informal statement

Let `U ⊆ ℝ^d` be open and convex, `Φ : U → U` any map, and `G : U → ℝ` with
`G (Φ x) = G x` for every `x ∈ U`.
(i) If `G x = lᵀ x` for some `l ∈ ℝ^d`, then `lᵀ (Φ x − x) = 0` for every `x ∈ U`.
(ii) If `G ∈ C²(U)` and `B := sup_{y ∈ U} ‖∇²G(y)‖₂ < ∞`, then
`|∇G(x)ᵀ (Φ x − x)| ≤ ½ B ‖Φ x − x‖₂²` for every `x ∈ U`.

## Conventions used here

* `ℝ^d` is `EuclideanSpace ℝ (Fin d)`, so `‖·‖` is the Euclidean norm and `lᵀ x` is
  `⟪l, x⟫_ℝ`. Maps are total functions; `Φ : U → U` is `Set.MapsTo Φ U U`, and the
  hypotheses on `G` hold on `U` only.
* `∇G(x)ᵀ v` is `fderiv ℝ G x v`. The Hessian `∇²G(y)` is `fderiv ℝ (fderiv ℝ G) y`, a
  bounded bilinear map `E →L[ℝ] E →L[ℝ] ℝ`; its operator norm equals the spectral norm of
  the (symmetric) Hessian matrix. `C²(U)` is `ContDiffOn ℝ 2 G U`.
* "`B := sup ‖∇²G‖ < ∞`" is carried as any real `B` with `‖∇²G(y)‖ ≤ B` on `U`; the
  conclusion for every such bound is equivalent to the conclusion for the supremum.

## Proof recipe

1. (i): `lᵀ Φ x = G (Φ x) = G x = lᵀ x`, and the inner product is linear.
2. (ii): fix `x ∈ U`, `v = Φ x − x`; the segment `x + t v`, `t ∈ [0,1]`, lies in `U`.
3. Mean value on `fderiv G` (derivative bounded by `B` on convex `U`):
   `‖∇G(x + t v) − ∇G(x)‖ ≤ B t ‖v‖`.
4. `g t = G (x + t v) − G x − t ∇G(x) v` has `g 0 = 0` and `|g' t| ≤ B ‖v‖² t`; comparison
   with `B ‖v‖² t² / 2` (`image_norm_le_of_norm_deriv_right_le_deriv_boundary`) gives
   `|g 1| ≤ B ‖v‖² / 2`.
5. `g 1 = G (Φ x) − G x − ∇G(x) v = −∇G(x) v`.
-/

namespace MathDept.MD_0045

open Set Filter Topology

variable {d : ℕ}

local notation "E" => EuclideanSpace ℝ (Fin d)

/-- Steps 2 to 5: the second-order bound for a `C²` functional with Hessian bound `B`. -/
lemma second_order {U : Set E} (hUo : IsOpen U) (hUc : Convex ℝ U) {G : E → ℝ}
    (hG : ContDiffOn ℝ 2 G U) {B : ℝ} (hB : ∀ y ∈ U, ‖fderiv ℝ (fderiv ℝ G) y‖ ≤ B)
    {x y : E} (hx : x ∈ U) (hy : y ∈ U) :
    |fderiv ℝ G x (y - x) + (G x - G y)| ≤ 1 / 2 * B * ‖y - x‖ ^ 2 := by
  set v := y - x with hv
  have hseg : ∀ t ∈ Icc (0 : ℝ) 1, x + t • v ∈ U := by
    intro t ht
    have := hUc.add_smul_sub_mem hx hy ht
    simpa [hv] using this
  have hat : ∀ z ∈ U, ContDiffAt ℝ 2 G z := fun z hz => hG.contDiffAt (hUo.mem_nhds hz)
  have hdG : ∀ z ∈ U, DifferentiableAt ℝ G z := fun z hz =>
    (hat z hz).differentiableAt (by norm_num)
  have hdG2 : ∀ z ∈ U, DifferentiableAt ℝ (fderiv ℝ G) z := fun z hz =>
    ((hat z hz).fderiv_right (m := 1) (by norm_num)).differentiableAt (by norm_num)
  -- Step 3.
  have hlip : ∀ t ∈ Icc (0 : ℝ) 1, ‖fderiv ℝ G (x + t • v) - fderiv ℝ G x‖ ≤ B * (t * ‖v‖) := by
    intro t ht
    have h := hUc.norm_image_sub_le_of_norm_fderiv_le hdG2 hB hx (hseg t ht)
    have hn : ‖x + t • v - x‖ = t * ‖v‖ := by
      rw [add_sub_cancel_left, norm_smul, Real.norm_of_nonneg ht.1]
    rwa [hn] at h
  -- Step 4.
  set g : ℝ → ℝ := fun t => G (x + t • v) - G x - t * fderiv ℝ G x v with hg
  set g' : ℝ → ℝ := fun t => fderiv ℝ G (x + t • v) v - fderiv ℝ G x v with hg'
  have hderiv : ∀ t ∈ Icc (0 : ℝ) 1, HasDerivAt g (g' t) t := by
    intro t ht
    have hline : HasDerivAt (fun s : ℝ => x + s • v) v t := by
      simpa using ((hasDerivAt_id t).smul_const v).const_add x
    have h1 : HasDerivAt (fun s : ℝ => G (x + s • v)) (fderiv ℝ G (x + t • v) v) t :=
      (hdG _ (hseg t ht)).hasFDerivAt.comp_hasDerivAt t hline
    have h2 : HasDerivAt (fun s : ℝ => s * fderiv ℝ G x v) (fderiv ℝ G x v) t := by
      simpa using (hasDerivAt_id t).mul_const (fderiv ℝ G x v)
    exact (h1.sub_const (G x)).sub h2
  have hcont : ContinuousOn g (Icc 0 1) := fun t ht =>
    (hderiv t ht).continuousAt.continuousWithinAt
  have hbound : ∀ t ∈ Ico (0 : ℝ) 1, ‖g' t‖ ≤ B * ‖v‖ ^ 2 * t := by
    intro t ht
    have ht' : t ∈ Icc (0 : ℝ) 1 := Ico_subset_Icc_self ht
    have h := (fderiv ℝ G (x + t • v) - fderiv ℝ G x).le_opNorm v
    have h' := mul_le_mul_of_nonneg_right (hlip t ht') (norm_nonneg v)
    simp only [hg', Real.norm_eq_abs]
    rw [← sub_apply, ← Real.norm_eq_abs]
    nlinarith
  have hcomp := image_norm_le_of_norm_deriv_right_le_deriv_boundary (f := g) (f' := g')
    (B := fun t => 1 / 2 * B * ‖v‖ ^ 2 * t ^ 2) (B' := fun t => B * ‖v‖ ^ 2 * t)
    hcont (fun t ht => (hderiv t (Ico_subset_Icc_self ht)).hasDerivWithinAt)
    (by simp [hg]) (fun t => by
      have h2 : HasDerivAt (fun s : ℝ => 1 / 2 * B * ‖v‖ ^ 2 * (s * s))
          (1 / 2 * B * ‖v‖ ^ 2 * (1 * t + t * 1)) t :=
        ((hasDerivAt_id' t).mul (hasDerivAt_id' t)).const_mul _
      have e : (fun s : ℝ => 1 / 2 * B * ‖v‖ ^ 2 * s ^ 2)
          = fun s : ℝ => 1 / 2 * B * ‖v‖ ^ 2 * (s * s) := by
        funext s; ring
      rw [e]
      exact h2.congr_deriv (by ring)) hbound (x := 1) ⟨zero_le_one, le_refl _⟩
  -- Step 5.
  have hxy : x + (1 : ℝ) • v = y := by simp [hv]
  simp only [hg, hxy, one_mul, Real.norm_eq_abs, one_pow, mul_one] at hcomp
  have : fderiv ℝ G x v + (G x - G y) = -(G y - G x - fderiv ℝ G x v) := by ring
  rw [this, abs_neg]
  exact hcomp

/-- The statement: (i) a conserved linear functional annihilates the residual `Φ x − x`;
(ii) a conserved `C²` functional with Hessian bound `B` has `|∇G(x)ᵀ (Φ x − x)| ≤ ½ B ‖Φ x − x‖²`. -/
theorem statement {U : Set E} (hUo : IsOpen U) (hUc : Convex ℝ U) {Φ : E → E}
    (hmaps : MapsTo Φ U U) {G : E → ℝ} (hcons : ∀ x ∈ U, G (Φ x) = G x) :
    (∀ l : E, (∀ x ∈ U, G x = inner ℝ l x) → ∀ x ∈ U, inner ℝ l (Φ x - x) = (0 : ℝ)) ∧
    (ContDiffOn ℝ 2 G U → ∀ B : ℝ, (∀ y ∈ U, ‖fderiv ℝ (fderiv ℝ G) y‖ ≤ B) →
      ∀ x ∈ U, |fderiv ℝ G x (Φ x - x)| ≤ 1 / 2 * B * ‖Φ x - x‖ ^ 2) := by
  refine ⟨fun l hl x hx => ?_, fun hG B hB x hx => ?_⟩
  · rw [inner_sub_right, ← hl _ (hmaps hx), ← hl x hx, hcons x hx, sub_self]
  · have h := second_order hUo hUc hG hB hx (hmaps hx)
    rwa [hcons x hx, sub_self, add_zero] at h

end MathDept.MD_0045
