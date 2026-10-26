import Mathlib.LinearAlgebra.Charpoly.ToMatrix
import Mathlib.LinearAlgebra.Determinant
import Mathlib.LinearAlgebra.Matrix.Charpoly.Basic
import Mathlib.LinearAlgebra.Matrix.Rank
import Mathlib.Data.Complex.Basic

/-!
# MD_0044: deflating left unit eigenvectors removes exactly their multipliers

## Informal statement

Let `M ∈ ℂ^{d×d}` and let `l_1, …, l_r ∈ ℂ^d` be linearly independent with
`l_iᵀ M = l_iᵀ`. Let `W = {v : l_iᵀ v = 0 for all i}`. Then
(i) `M W ⊆ W`;
(ii) `χ_M = (X - 1)^r · χ_{M|_W}`;
(iii) for every `P` with `P² = P` and range `W`, `χ_{PMP} = X^r · χ_{M|_W}`.
Here `χ_A = det (X I - A)` and `χ_{M|_W}` is the characteristic polynomial of the
restriction `M|_W : W → W` (for `r = d`, `W = 0` and `χ_{M|_W} = 1`).

## Conventions used here

* Vectors are `Fin d → K`, the row functionals are `l : Fin r → Fin d → K`, and
  `l_iᵀ M = l_iᵀ` is `l i ᵥ* M = l i`. `W l` is the common kernel, defined literally.
* `M|_W` is `(Matrix.toLin' M).restrict h` for the invariance proof `h` of (i), and its
  characteristic polynomial is `LinearMap.charpoly` (the empty determinant `1` on `W = 0`).
* `P` is a matrix; "range `W`" is `LinearMap.range (Matrix.toLin' P) = W l`.
* `statement_field` proves the claim over any field `K`; `statement` is the `ℂ` case with
  the ledger's hypotheses `1 ≤ d`, `1 ≤ r ≤ d` carried (unused: the proof needs none of them).

## Proof recipe

1. `charpoly_eq_restrict_mul_mapQ`: for `e` preserving a subspace `W` of a finite-dimensional
   space, `χ_e = χ_{e|_W} · χ_{e mod W}` (block upper-triangular matrix in a basis of `W`
   joined to a lifted basis of `V ⧸ W`; mirrors `LinearMap.det_eq_det_mul_det`).
2. `finrank_quot`: `dim (Kᵈ ⧸ W) = r` (`W` is the kernel of `v ↦ (l_i ⬝ v)_i`, whose rank is
   the rank of the rows `l_i`, i.e. `r` by independence).
3. (i) and (ii): `l_i ⬝ (Mv - v) = (l_iᵀ M - l_iᵀ) v = 0`, so `M` preserves `W` and induces
   the identity on `Kᵈ ⧸ W`, whose characteristic polynomial is `(X - 1)^r`.
4. (iii): `P` fixes `W` pointwise (idempotent with range `W`), so `PMP` agrees with `M` on
   `W`; `PMP` maps everything into `W`, so it induces `0` on `Kᵈ ⧸ W`, with characteristic
   polynomial `X^r`.
-/

namespace MathDept.MD_0044

open Polynomial Matrix Module

variable {K : Type*} [Field K] {d r : ℕ}

/-- The common kernel `W = {v : l_i ⬝ v = 0 for all i}`. -/
def W (l : Fin r → Fin d → K) : Submodule K (Fin d → K) where
  carrier := {v | ∀ i, l i ⬝ᵥ v = 0}
  add_mem' := by
    intro a b ha hb i
    simp [dotProduct_add, ha i, hb i]
  zero_mem' := by
    intro i
    simp
  smul_mem' := by
    intro c v hv i
    simp [dotProduct_smul, hv i]

/-- Step 1: the characteristic polynomial of an endomorphism preserving `W` is that of the
restriction times that of the induced map on the quotient. -/
theorem charpoly_eq_restrict_mul_mapQ {V : Type*} [AddCommGroup V] [Module K V]
    [FiniteDimensional K V] (W : Submodule K V) (e : V →ₗ[K] V) (he : ∀ x ∈ W, e x ∈ W) :
    e.charpoly = (e.restrict he).charpoly * (W.mapQ W e he).charpoly := by
  classical
  let m := Module.Free.ChooseBasisIndex K W
  let bW : Basis m K W := Module.Free.chooseBasis K W
  let n := Module.Free.ChooseBasisIndex K (V ⧸ W)
  let bQ : Basis n K (V ⧸ W) := Module.Free.chooseBasis K (V ⧸ W)
  let b := bW.sumQuot bQ
  let A : Matrix m m K := LinearMap.toMatrix bW bW (e.restrict he)
  let B : Matrix m n K := Matrix.of fun i l ↦ (b.repr (e (b (Sum.inr l)))) (Sum.inl i)
  let D : Matrix n n K := LinearMap.toMatrix bQ bQ (W.mapQ W e he)
  suffices LinearMap.toMatrix b b e = Matrix.fromBlocks A B 0 D by
    rw [← LinearMap.charpoly_toMatrix e b, this, Matrix.charpoly_fromBlocks_zero₂₁,
      LinearMap.charpoly_toMatrix, LinearMap.charpoly_toMatrix]
  ext u v
  cases u with
  | inl i =>
    cases v with
    | inl k =>
      simp only [b, Basis.sumQuot_inl, Matrix.fromBlocks_apply₁₁, A, LinearMap.toMatrix_apply]
      apply Basis.sumQuot_repr_inl_of_mem
    | inr l => simp [b, LinearMap.toMatrix_apply, Matrix.fromBlocks_apply₁₂, B]
  | inr j =>
    cases v with
    | inl k =>
      suffices W.mkQ (e (bW k)) = 0 by simp [LinearMap.toMatrix_apply, b, this]
      rw [← LinearMap.mem_ker, Submodule.ker_mkQ]
      exact he _ (Submodule.coe_mem (bW k))
    | inr l =>
      simp only [LinearMap.toMatrix_apply, Basis.sumQuot_repr_inr,
        Matrix.fromBlocks_apply₂₂, b, D]
      rw [← Basis.sumQuot_inr bW bQ l, W.mapQ_apply]
      simp

theorem charpoly_id {V : Type*} [AddCommGroup V] [Module K V] [FiniteDimensional K V] :
    (LinearMap.id : V →ₗ[K] V).charpoly = (X - 1) ^ finrank K V := by
  classical
  rw [← LinearMap.charpoly_toMatrix _ (Module.Free.chooseBasis K V), LinearMap.toMatrix_id,
    Matrix.charpoly_one, ← Module.finrank_eq_card_chooseBasisIndex]

theorem charpoly_zero {V : Type*} [AddCommGroup V] [Module K V] [FiniteDimensional K V] :
    (0 : V →ₗ[K] V).charpoly = X ^ finrank K V := by
  classical
  rw [← LinearMap.charpoly_toMatrix _ (Module.Free.chooseBasis K V), map_zero,
    Matrix.charpoly_zero, ← Module.finrank_eq_card_chooseBasisIndex]

/-- Step 2: the quotient by the common kernel has dimension `r`. -/
theorem finrank_quot (l : Fin r → Fin d → K) (hl : LinearIndependent K l) :
    finrank K ((Fin d → K) ⧸ W l) = r := by
  let A : Matrix (Fin r) (Fin d) K := Matrix.of l
  have hker : W l = LinearMap.ker A.mulVecLin := by
    ext v
    simp only [W, Submodule.mem_mk, AddSubmonoid.mem_mk, AddSubsemigroup.mem_mk,
      Set.mem_ofPred_eq, LinearMap.mem_ker, Matrix.mulVecLin_apply, funext_iff, Pi.zero_apply]
    rfl
  rw [(Submodule.quotEquivOfEq _ _ hker).finrank_eq,
    (LinearMap.quotKerEquivRange A.mulVecLin).finrank_eq, ← Matrix.rank.eq_1,
    ← Matrix.rank_transpose, Matrix.rank.eq_1, Matrix.range_mulVecLin]
  have : Set.range Aᵀ.col = Set.range l := rfl
  rw [this, finrank_span_eq_card hl, Fintype.card_fin]

/-- MD_0044 over an arbitrary field. -/
theorem statement_field (M : Matrix (Fin d) (Fin d) K) (l : Fin r → Fin d → K)
    (hl : LinearIndependent K l) (hlM : ∀ i, l i ᵥ* M = l i) :
    (∀ v ∈ W l, M *ᵥ v ∈ W l) ∧
    ∃ hMW : ∀ v ∈ W l, Matrix.toLin' M v ∈ W l,
      M.charpoly = (X - 1) ^ r * ((Matrix.toLin' M).restrict hMW).charpoly ∧
      ∀ P : Matrix (Fin d) (Fin d) K, P * P = P → LinearMap.range (Matrix.toLin' P) = W l →
        (P * M * P).charpoly = X ^ r * ((Matrix.toLin' M).restrict hMW).charpoly := by
  -- `l_i ⬝ (M v) = l_i ⬝ v`
  have hdot : ∀ i v, l i ⬝ᵥ (M *ᵥ v) = l i ⬝ᵥ v := by
    intro i v
    rw [Matrix.dotProduct_mulVec, hlM i]
  have hinv : ∀ v ∈ W l, M *ᵥ v ∈ W l := by
    intro v hv i
    rw [hdot]
    exact hv i
  have hMW : ∀ v ∈ W l, Matrix.toLin' M v ∈ W l := by
    intro v hv
    rw [Matrix.toLin'_apply]
    exact hinv v hv
  refine ⟨hinv, hMW, ?_, ?_⟩
  · -- (ii)
    have hid : (W l).mapQ (W l) (Matrix.toLin' M) hMW = LinearMap.id := by
      refine LinearMap.ext fun x => ?_
      induction x using Submodule.Quotient.induction_on with
      | H v =>
        rw [Submodule.mapQ_apply, LinearMap.id_apply, Submodule.Quotient.eq,
          Matrix.toLin'_apply]
        intro i
        rw [dotProduct_sub, hdot, sub_self]
    rw [← Matrix.charpoly_toLin', charpoly_eq_restrict_mul_mapQ (W l) _ hMW, hid, charpoly_id,
      finrank_quot l hl, mul_comm]
  · -- (iii)
    intro P hPP hrange
    have hfix : ∀ w ∈ W l, P *ᵥ w = w := by
      intro w hw
      rw [← hrange] at hw
      obtain ⟨u, rfl⟩ := hw
      rw [Matrix.toLin'_apply, Matrix.mulVec_mulVec, hPP]
    have happ : ∀ v, Matrix.toLin' (P * M * P) v = P *ᵥ (M *ᵥ (P *ᵥ v)) := by
      intro v
      rw [Matrix.toLin'_apply, Matrix.mulVec_mulVec, Matrix.mulVec_mulVec]
    have hinto : ∀ v, Matrix.toLin' (P * M * P) v ∈ W l := by
      intro v
      rw [← hrange]
      exact ⟨M *ᵥ (P *ᵥ v), by rw [Matrix.toLin'_apply, happ]⟩
    have hPMPW : ∀ v ∈ W l, Matrix.toLin' (P * M * P) v ∈ W l := fun v _ => hinto v
    have hres : (Matrix.toLin' (P * M * P)).restrict hPMPW = (Matrix.toLin' M).restrict hMW := by
      ext ⟨w, hw⟩ : 2
      simp only [LinearMap.restrict_apply]
      rw [happ, hfix w hw, Matrix.toLin'_apply, hfix _ (hinv w hw)]
    have hzero : (W l).mapQ (W l) (Matrix.toLin' (P * M * P)) hPMPW = 0 := by
      refine LinearMap.ext fun x => ?_
      induction x using Submodule.Quotient.induction_on with
      | H v =>
        rw [Submodule.mapQ_apply, LinearMap.zero_apply, Submodule.Quotient.mk_eq_zero]
        exact hinto v
    rw [← Matrix.charpoly_toLin', charpoly_eq_restrict_mul_mapQ (W l) _ hPMPW, hres, hzero,
      charpoly_zero, finrank_quot l hl, mul_comm]

/-- MD_0044 (the ledger statement, over `ℂ`). -/
theorem statement (_hd : 1 ≤ d) (M : Matrix (Fin d) (Fin d) ℂ) (_hr1 : 1 ≤ r) (_hrd : r ≤ d)
    (l : Fin r → Fin d → ℂ) (hl : LinearIndependent ℂ l) (hlM : ∀ i, l i ᵥ* M = l i) :
    (∀ v ∈ W l, M *ᵥ v ∈ W l) ∧
    ∃ hMW : ∀ v ∈ W l, Matrix.toLin' M v ∈ W l,
      M.charpoly = (X - 1) ^ r * ((Matrix.toLin' M).restrict hMW).charpoly ∧
      ∀ P : Matrix (Fin d) (Fin d) ℂ, P * P = P → LinearMap.range (Matrix.toLin' P) = W l →
        (P * M * P).charpoly = X ^ r * ((Matrix.toLin' M).restrict hMW).charpoly :=
  statement_field M l hl hlM

end MathDept.MD_0044

