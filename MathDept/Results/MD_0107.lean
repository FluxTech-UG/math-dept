import Mathlib.LinearAlgebra.Dual.Lemmas
import Mathlib.FieldTheory.Minpoly.Field
import Mathlib.RingTheory.IntegralClosure.Algebra.Basic
import Mathlib.LinearAlgebra.Dimension.Constructions

/-!
# MD_0107: the orbit of a linear map lies in its Krylov space and in the invariant affine slice

## Informal statement

Let `V` be a finite-dimensional vector space over a field `K` (H1), `M : V → V` linear (H2)
with minimal polynomial `μ_M`, `c₀ ∈ V`, and `R(c₀) = {M^k c₀ : k ≥ 0}`. Let
`𝒦(M, c₀) = span {M^k c₀ : k ≥ 0}` be the Krylov subspace. Then
(i) `R(c₀) ⊆ 𝒦(M, c₀)`;
(ii) `dim 𝒦(M, c₀) ≤ deg μ_M`;
(iii) every functional `ℓ ∈ V^*` with `ℓ ∘ M = ℓ` is constant on the orbit, `ℓ v = ℓ c₀`;
(iv) if `ℓ₁, …, ℓ_r ∈ V^*` are linearly independent and each is `M`-invariant, then
`R(c₀) ⊆ A = {v : ℓ_i v = ℓ_i c₀ ∀ i}`, `A = c₀ + ⋂ᵢ ker ℓ_i`, and the direction
`⋂ᵢ ker ℓ_i` has dimension `dim V - r`.

## Encoding

* `{K V : Type*} [Field K] [AddCommGroup V] [Module K V] [FiniteDimensional K V]` is H1;
  `M : Module.End K V` is H2 (a single map).
* The orbit is `Set.range (fun k : ℕ => (M ^ k) c0)` and the Krylov space is
  `Submodule.span K (orbit)`; `deg μ_M` is `(minpoly K M).natDegree`.
* "`A` is an affine subspace with direction `⋂ ker ℓ_i`" is encoded as the set identity
  `{v | ∀ i, ℓ i v = ℓ i c0} = {v | v - c0 ∈ ⨅ i, LinearMap.ker (ℓ i)}`, and its dimension
  claim as `Module.finrank K ↥(⨅ i, LinearMap.ker (ℓ i) : Submodule K V) = Module.finrank K V - r`.
* `statement` is the conjunction of (i)–(iv).

## Proof recipe

1. (i) is `Submodule.subset_span`.
2. (ii) Let `d = natDegree μ_M` and `W = span {M^i c₀ : i < d}`. Every `M^k c₀` equals
   `aeval M (X^k %ₘ μ_M) c₀` (`aeval_modByMonic_eq_self_of_root`), and a polynomial of degree
   `< d` evaluates into `W` (`aeval_eq_sum_range'`). So `𝒦 ≤ W` and `finrank W ≤ d`
   (`finrank_range_le_card`).
3. (iii) Induction on `k`: `ℓ (M^(k+1) c₀) = (ℓ ∘ M)(M^k c₀) = ℓ (M^k c₀)`.
4. (iv) The slice inclusion is (iii) per `i`; the set identity is `mem_iInf`, `map_sub`,
   `sub_eq_zero`; `⨅ ker ℓ_i` is the dual coannihilator of `span (range ℓ)`
   (`coe_dualCoannihilator_span`), whose finrank is `dim V - finrank span (range ℓ)`
   (`Subspace.finrank_add_finrank_dualCoannihilator_eq`) and `finrank span (range ℓ) = r`
   by independence (`finrank_span_eq_card`).
-/

namespace MathDept.MD_0107

open Polynomial

variable {K V : Type*} [Field K] [AddCommGroup V] [Module K V] [FiniteDimensional K V]

omit [FiniteDimensional K V] in
/-- Step 2, leaf: a polynomial of degree below `d` evaluates at `M` on `c0` into the span of the
first `d` orbit points. -/
lemma aeval_mem_span_lt (M : Module.End K V) (c0 : V) (d : ℕ) (p : K[X])
    (hp : p.degree < d) :
    aeval M p c0 ∈ Submodule.span K (Set.range (fun i : Fin d => (M ^ (i : ℕ)) c0)) := by
  by_cases h0 : p = 0
  · subst h0; simp
  have hn : p.natDegree < d := (natDegree_lt_iff_degree_lt h0).2 hp
  rw [aeval_eq_sum_range' hn, LinearMap.sum_apply]
  refine Submodule.sum_mem _ fun i hi => ?_
  rw [LinearMap.smul_apply]
  exact Submodule.smul_mem _ _
    (Submodule.subset_span ⟨⟨i, Finset.mem_range.1 hi⟩, rfl⟩)

/-- Step 2: the Krylov space has dimension at most the degree of the minimal polynomial. -/
lemma finrank_krylov_le (M : Module.End K V) (c0 : V) :
    Module.finrank K (Submodule.span K (Set.range (fun k : ℕ => (M ^ k) c0)))
      ≤ (minpoly K M).natDegree := by
  set d := (minpoly K M).natDegree
  have hint : IsIntegral K M := Algebra.IsIntegral.isIntegral M
  have hmon : (minpoly K M).Monic := minpoly.monic hint
  have hle : Submodule.span K (Set.range (fun k : ℕ => (M ^ k) c0))
      ≤ Submodule.span K (Set.range (fun i : Fin d => (M ^ (i : ℕ)) c0)) := by
    rw [Submodule.span_le]
    rintro _ ⟨k, rfl⟩
    show (M ^ k) c0 ∈ Submodule.span K (Set.range (fun i : Fin d => (M ^ (i : ℕ)) c0))
    have hk : (M ^ k) = aeval M (X ^ k %ₘ minpoly K M) := by
      rw [aeval_modByMonic_eq_self_of_root (minpoly.aeval K M)]
      simp
    rw [hk]
    refine aeval_mem_span_lt M c0 d _ ?_
    have := degree_modByMonic_lt (X ^ k) hmon
    rwa [degree_eq_natDegree (minpoly.ne_zero hint)] at this
  calc _ ≤ Module.finrank K (Submodule.span K (Set.range (fun i : Fin d => (M ^ (i : ℕ)) c0))) :=
        Submodule.finrank_mono hle
    _ ≤ Fintype.card (Fin d) := finrank_range_le_card _
    _ = d := Fintype.card_fin d

omit [FiniteDimensional K V] in
/-- Step 3: an `M`-invariant functional is constant on the orbit. -/
lemma invariant_const (M : Module.End K V) (c0 : V) (ℓ : Module.Dual K V)
    (hℓ : ℓ ∘ₗ M = ℓ) (k : ℕ) : ℓ ((M ^ k) c0) = ℓ c0 := by
  induction k with
  | zero => simp
  | succ k ih =>
    rw [pow_succ', Module.End.mul_apply, ← LinearMap.comp_apply, hℓ, ih]

/-- Step 4: the joint kernel of `r` independent functionals has codimension `r`. -/
lemma finrank_iInf_ker (r : ℕ) (ℓ : Fin r → Module.Dual K V) (hli : LinearIndependent K ℓ) :
    Module.finrank K ↥(⨅ i, LinearMap.ker (ℓ i) : Submodule K V) = Module.finrank K V - r := by
  have heq : (⨅ i, LinearMap.ker (ℓ i) : Submodule K V) = (Submodule.span K (Set.range ℓ)).dualCoannihilator := by
    apply SetLike.coe_injective
    rw [Submodule.coe_dualCoannihilator_span]
    ext x
    simp
  have h1 := Subspace.finrank_add_finrank_dualCoannihilator_eq (Submodule.span K (Set.range ℓ))
  rw [finrank_span_eq_card hli, Fintype.card_fin] at h1
  rw [heq]
  omega

theorem statement (M : Module.End K V) (c0 : V) :
    -- (i)
    Set.range (fun k : ℕ => (M ^ k) c0)
        ⊆ Submodule.span K (Set.range (fun k : ℕ => (M ^ k) c0)) ∧
    -- (ii)
    Module.finrank K (Submodule.span K (Set.range (fun k : ℕ => (M ^ k) c0)))
        ≤ (minpoly K M).natDegree ∧
    -- (iii)
    (∀ ℓ : Module.Dual K V, ℓ ∘ₗ M = ℓ →
        ∀ v ∈ Set.range (fun k : ℕ => (M ^ k) c0), ℓ v = ℓ c0) ∧
    -- (iv)
    (∀ (r : ℕ) (ℓ : Fin r → Module.Dual K V), LinearIndependent K ℓ →
        (∀ i, ℓ i ∘ₗ M = ℓ i) →
        Set.range (fun k : ℕ => (M ^ k) c0) ⊆ {v | ∀ i, ℓ i v = ℓ i c0} ∧
        {v | ∀ i, ℓ i v = ℓ i c0} = {v | v - c0 ∈ ⨅ i, LinearMap.ker (ℓ i)} ∧
        Module.finrank K ↥(⨅ i, LinearMap.ker (ℓ i) : Submodule K V) = Module.finrank K V - r) := by
  refine ⟨Submodule.subset_span, finrank_krylov_le M c0, ?_, ?_⟩
  · rintro ℓ hℓ _ ⟨k, rfl⟩
    exact invariant_const M c0 ℓ hℓ k
  · intro r ℓ hli hinv
    refine ⟨?_, ?_, finrank_iInf_ker r ℓ hli⟩
    · rintro _ ⟨k, rfl⟩ i
      exact invariant_const M c0 (ℓ i) (hinv i) k
    · ext v
      simp [Submodule.mem_iInf, sub_eq_zero]

end MathDept.MD_0107
