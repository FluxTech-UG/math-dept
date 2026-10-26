import Mathlib.Analysis.Calculus.FDeriv.Comp
import Mathlib.Analysis.Calculus.FDeriv.Congr
import Mathlib.Analysis.InnerProductSpace.PiL2
import Mathlib.LinearAlgebra.Dual.Lemmas

/-!
# MD_0043: a conserved differentiable functional is a left unit eigenvector of the monodromy

## Informal statement

Let `U ⊆ ℝ^d` be open, `Φ : U → U`, `x* ∈ U` with `Φ x* = x*`, `Φ` Fréchet differentiable
at `x*`. If `G : U → ℝ` is differentiable at `x*` and `G (Φ x) = G x` for every `x ∈ U`, then
`∇G(x*)ᵀ DΦ(x*) = ∇G(x*)ᵀ`. Moreover, if `G_1, …, G_r` are each such functionals with
linearly independent gradients at `x*`, then `dim ker (DΦ(x*)ᵀ − I) ≥ r`.

## Conventions used here

* `ℝ^d` is `EuclideanSpace ℝ (Fin d)`. Maps are total functions `E → E`, `E → ℝ`; `Φ : U → U`
  is `Set.MapsTo Φ U U`, and every hypothesis on `G` and `Φ` is used only on `U`.
* The derivative `DΦ(x*)` is `Φ' : E →L[ℝ] E` with `HasFDerivAt Φ Φ' x*`. The gradient
  row `∇G(x*)ᵀ` is the derivative `G' : E →L[ℝ] ℝ` with `HasFDerivAt G G' x*`, so
  `∇G(x*)ᵀ DΦ(x*)` is `G'.comp Φ'`.
* The transpose `DΦ(x*)ᵀ` acts on row vectors, i.e. on the dual `Module.Dual ℝ E`; it is
  the dual map `Φ'.toLinearMap.dualMap : ψ ↦ ψ ∘ Φ'`. "The gradients are linearly
  independent" is linear independence of the `G'_i` as elements of the dual (equivalent to
  linear independence of the gradient vectors under the Riesz isomorphism), and the
  second claim is `r ≤ finrank ℝ (ker (Φ'.dualMap − id))`.

## Proof recipe

1. `U ∈ 𝓝 x*`, so `G ∘ Φ = G` eventually near `x*`.
2. Chain rule (`HasFDerivAt.comp`, with `Φ x* = x*`): `G ∘ Φ` has derivative `G'.comp Φ'`
   at `x*`; by step 1 so does `G`, and uniqueness of the Fréchet derivative gives
   `G'.comp Φ' = G'`.
3. Each `G'_i` therefore lies in `ker (Φ'.dualMap − id)`; a linearly independent family of
   `r` vectors in a finite-dimensional space bounds its dimension from below.
-/

namespace MathDept.MD_0043

open Filter Topology Module

variable {d : ℕ}

local notation "E" => EuclideanSpace ℝ (Fin d)

/-- Steps 1 and 2: the conserved functional's derivative is fixed by precomposition. -/
lemma comp_eq_of_conserved {U : Set E} (hU : IsOpen U) {Φ : E → E} {xs : E}
    (hxs : xs ∈ U) (hfix : Φ xs = xs) {Φ' : E →L[ℝ] E} (hΦ : HasFDerivAt Φ Φ' xs)
    {G : E → ℝ} {G' : E →L[ℝ] ℝ} (hG : HasFDerivAt G G' xs)
    (hcons : ∀ x ∈ U, G (Φ x) = G x) : G'.comp Φ' = G' := by
  have hG' : HasFDerivAt G G' (Φ xs) := by rw [hfix]; exact hG
  have hcomp : HasFDerivAt (G ∘ Φ) (G'.comp Φ') xs := hG'.comp xs hΦ
  have hev : G =ᶠ[𝓝 xs] G ∘ Φ := by
    filter_upwards [hU.mem_nhds hxs] with x hx
    exact (hcons x hx).symm
  exact (hcomp.congr_of_eventuallyEq hev).unique hG

/-- The statement: (1) `∇G(x*)ᵀ DΦ(x*) = ∇G(x*)ᵀ` for one conserved `G`; (2) `r` conserved
functionals with linearly independent gradients give `dim ker (DΦ(x*)ᵀ − I) ≥ r`. -/
theorem statement {U : Set E} (hU : IsOpen U) {Φ : E → E} (_hmaps : Set.MapsTo Φ U U)
    {xs : E} (hxs : xs ∈ U) (hfix : Φ xs = xs) {Φ' : E →L[ℝ] E} (hΦ : HasFDerivAt Φ Φ' xs) :
    (∀ (G : E → ℝ) (G' : E →L[ℝ] ℝ), HasFDerivAt G G' xs →
        (∀ x ∈ U, G (Φ x) = G x) → G'.comp Φ' = G') ∧
    (∀ (r : ℕ) (G : Fin r → E → ℝ) (G' : Fin r → E →L[ℝ] ℝ),
        (∀ i, HasFDerivAt (G i) (G' i) xs) →
        (∀ i, ∀ x ∈ U, G i (Φ x) = G i x) →
        LinearIndependent ℝ (fun i => ((G' i : E →ₗ[ℝ] ℝ) : Module.Dual ℝ E)) →
        r ≤ finrank ℝ (LinearMap.ker (Φ'.toLinearMap.dualMap - LinearMap.id))) := by
  refine ⟨fun G G' hG hcons => comp_eq_of_conserved hU hxs hfix hΦ hG hcons, ?_⟩
  intro r G G' hG hcons hli
  set K := LinearMap.ker (Φ'.toLinearMap.dualMap - LinearMap.id)
  have hmem : ∀ i, ((G' i : E →ₗ[ℝ] ℝ) : Module.Dual ℝ E) ∈ K := by
    intro i
    have h := comp_eq_of_conserved hU hxs hfix hΦ (hG i) (hcons i)
    rw [LinearMap.mem_ker, LinearMap.sub_apply, LinearMap.id_apply, sub_eq_zero]
    ext v
    simp only [LinearMap.dualMap_apply, ContinuousLinearMap.coe_coe]
    exact congrArg (fun L : E →L[ℝ] ℝ => L v) h
  let b : Fin r → K := fun i => ⟨_, hmem i⟩
  have hb : LinearIndependent ℝ b := by
    apply LinearIndependent.of_comp K.subtype
    exact hli
  simpa using hb.fintype_card_le_finrank

end MathDept.MD_0043
