import Mathlib.Data.Sym.Card
import Mathlib.Data.Fintype.BigOperators
import Mathlib.Data.List.OfFn
import Mathlib.Data.Set.Finite.List

/-!
# MD_0105: commuting holonomies give polynomial growth of the reachable set

## Informal statement

`C` is a finite set of configurations, `c0 ∈ C`, `U` a finite nonempty alphabet and
`{M_u}_{u ∈ U}` a family of self-maps of `C`. For `k ≥ 0` the set reachable in exactly `k`
turns is `R_k(c0) = {M_{u_k} ∘ ⋯ ∘ M_{u_1}(c0) : (u_1, …, u_k) ∈ U^k}` (so `R_0 = {c0}`).
(a) If the `M_u` commute pairwise, `|R_k(c0)| ≤ C(k + |U| - 1, |U| - 1)` for every `k`.
(b) With no commutation assumption, `|R_k(c0)| ≤ |U|^k` for every `k`.
(c) For every finite nonempty `U` and every `k` there are a finite `C`, maps `M_u` and `c0`
with `|R_k(c0)| = |U|^k`.

## Encoding

* `{C U : Type*} [Fintype C] [DecidableEq C] [Fintype U] [Nonempty U]`, `M : U → C → C`,
  `c0 : C` (H1; `C` nonempty is automatic from `c0`). `DecidableEq C` only lets `R` be a
  `Finset` built by `Finset.image`.
* A word of length `k` is `w : Fin k → U` (H3: exactly one letter per turn, `k` turns).
  `applyWord M c0 w` folds left over `List.ofFn w`, so `u_1 = w 0` is applied first.
* `R M c0 k` is the image of all `Fin k → U` under `applyWord M c0`, as a `Finset C`.
* (a) carries H2 as the premise `∀ u v, M u ∘ M v = M v ∘ M u`; the bound is written
  `(k + Fintype.card U - 1).choose (Fintype.card U - 1)`, the ordinary binomial because
  `Fintype.card U ≥ 1` (`[Nonempty U]`).
* (c) quantifies the witness configuration set `C'` in `Type` (universe 0), with its own
  `Fintype` and `DecidableEq` instances, whatever the universe of `U`. The witness is
  `Words n k`, lists over `Fin n` (`n = |U|`) of length at most `k`, with `M'_u` appending
  `e u` (`e = Fintype.equivFin U`) below length `k` and fixing length-`k` lists, and
  `c0'` the empty list.
* `statement` is the conjunction of (a), (b), (c), quantified over `k`.

## Proof recipe (informal proof: `proofs/MD_0105.md`)

1. `card_R_le_pow` (b): `R` is the image of `Finset.univ : Finset (Fin k → U)`, of card
   `|U|^k` (`Finset.card_image_le`, `Fintype.card_fun`).
2. `card_R_le_choose` (a): every `applyWord M c0 w` equals the fold over
   `(s.val.toList)` with `s` the multiset of `w`'s letters, a permutation of `List.ofFn w`,
   by core `List.Perm.foldl_eq'` with H2 as the swap condition. So `R ⊆` the image of
   `Finset.univ : Finset (Sym U k)`, of card `(|U| + k - 1).choose k`
   (`Sym.card_sym_eq_choose`), equal to the entry's form by `Nat.choose_symm_add`.
3. `foldl_append_words`: from `x` with `|x| + |L| ≤ k`, appending the letters of `L` one
   by one gives `x ++ L`. `exists_card_R_eq_pow` (c): hence the witness sends `w` to
   `List.ofFn (e ∘ w)`, which is injective (`List.ofFn_injective`, `e.injective`), so `R`
   has `|U|^k` elements (`Finset.card_image_of_injective`).

## Attempt notes (S4, 2026-10-25)

Every theorem is closed; no `sorry`, no `native_decide`. `[Nonempty U]` is used only in (a)
(the binomial glue); `[Fintype C]` is not used by any of the three proofs (only
`DecidableEq C` for the `Finset.image`), and is kept because the entry stipulates H1.
-/

namespace MathDept.MD_0105

variable {C U : Type*}

def applyWord (M : U → C → C) (c0 : C) {k : ℕ} (w : Fin k → U) : C :=
  (List.ofFn w).foldl (fun c u => M u c) c0

def R [Fintype U] [DecidableEq C] (M : U → C → C) (c0 : C) (k : ℕ) : Finset C :=
  Finset.univ.image (fun w : Fin k → U => applyWord M c0 w)

theorem card_R_le_pow [Fintype U] [DecidableEq C] (M : U → C → C) (c0 : C) (k : ℕ) :
    (R M c0 k).card ≤ Fintype.card U ^ k := by
  unfold R
  calc _ ≤ (Finset.univ : Finset (Fin k → U)).card := Finset.card_image_le
    _ = _ := by simp

theorem card_R_le_choose [Fintype U] [Nonempty U] [DecidableEq C] (M : U → C → C) (c0 : C)
    (hcomm : ∀ u v, M u ∘ M v = M v ∘ M u) (k : ℕ) :
    (R M c0 k).card ≤ (k + Fintype.card U - 1).choose (Fintype.card U - 1) := by
  classical
  let f : Sym U k → C := fun s => (s.val.toList).foldl (fun c u => M u c) c0
  have hsub : R M c0 k ⊆ Finset.univ.image f := by
    intro c hc
    simp only [R, Finset.mem_image, Finset.mem_univ, true_and] at hc ⊢
    obtain ⟨w, rfl⟩ := hc
    refine ⟨⟨(List.ofFn w : Multiset U), by simp⟩, ?_⟩
    simp only [f, applyWord]
    apply List.Perm.foldl_eq'
    · exact Multiset.coe_eq_coe.mp (by simp)
    · intro x _ y _ z
      exact (congrFun (hcomm y x) z)
  calc (R M c0 k).card ≤ (Finset.univ.image f).card := Finset.card_le_card hsub
    _ ≤ (Finset.univ : Finset (Sym U k)).card := Finset.card_image_le
    _ = (Fintype.card U + k - 1).choose k := by rw [Finset.card_univ, Sym.card_sym_eq_choose]
    _ = (k + Fintype.card U - 1).choose (Fintype.card U - 1) := by
      have h := Fintype.card_pos (α := U)
      obtain ⟨m, hm⟩ : ∃ m, Fintype.card U = m + 1 := ⟨_, (Nat.succ_pred_eq_of_pos h).symm⟩
      rw [hm]
      simp only [Nat.add_sub_cancel]
      rw [show m + 1 + k - 1 = k + m by omega, show k + (m + 1) - 1 = k + m by omega]
      exact Nat.choose_symm_add

/-- The witness state space: words over `Fin n` of length at most `k`. -/
abbrev Words (n k : ℕ) : Type := {l : List (Fin n) // l.length ≤ k}

noncomputable instance (n k : ℕ) : Fintype (Words n k) :=
  haveI : Finite (Words n k) := (List.finite_length_le (α := Fin n) (n := k)).to_subtype
  Fintype.ofFinite _

def append {n k : ℕ} (a : Fin n) (x : Words n k) : Words n k :=
  if h : x.1.length < k then ⟨x.1 ++ [a], by simp; omega⟩ else x

theorem foldl_append_words {n k : ℕ} (L : List (Fin n)) :
    ∀ (x : Words n k), x.1.length + L.length ≤ k →
      (L.foldl (fun c a => append a c) x).1 = x.1 ++ L := by
  induction L with
  | nil => intro x _; simp
  | cons a L ih =>
    intro x hx
    simp only [List.length_cons] at hx
    have hlt : x.1.length < k := by omega
    rw [List.foldl_cons, ih]
    · simp [append, hlt]
    · simp [append, hlt]; omega

theorem exists_card_R_eq_pow [Fintype U] (k : ℕ) :
    ∃ (C' : Type) (_ : Fintype C') (_ : DecidableEq C') (M' : U → C' → C') (c0' : C'),
      (R M' c0' k).card = Fintype.card U ^ k := by
  classical
  let e := Fintype.equivFin U
  refine ⟨Words (Fintype.card U) k, inferInstance, inferInstance,
    fun u x => append (e u) x, ⟨[], by simp⟩, ?_⟩
  have hval : ∀ w : Fin k → U, (applyWord (fun u x => append (e u) x)
      (⟨[], by simp⟩ : Words (Fintype.card U) k) w).1 = List.ofFn (e ∘ w) := by
    intro w
    have h := foldl_append_words (k := k) (List.ofFn (e ∘ w)) ⟨[], by simp⟩ (by simp)
    simp only [List.nil_append] at h
    rw [← h, applyWord, ← List.map_ofFn, List.foldl_map]
  unfold R
  rw [Finset.card_image_of_injective]
  · simp
  · intro w w' hw
    have h1 := congrArg Subtype.val hw
    rw [hval, hval] at h1
    have h2 := List.ofFn_injective h1
    funext i
    exact e.injective (congrFun h2 i)

/-- MD_0105, (a), (b) and (c) for every `k`. -/
theorem statement {C U : Type*} [Fintype C] [DecidableEq C] [Fintype U] [Nonempty U]
    (M : U → C → C) (c0 : C) :
    ∀ k : ℕ,
      ((∀ u v, M u ∘ M v = M v ∘ M u) →
        (R M c0 k).card ≤ (k + Fintype.card U - 1).choose (Fintype.card U - 1)) ∧
      (R M c0 k).card ≤ Fintype.card U ^ k ∧
      (∃ (C' : Type) (_ : Fintype C') (_ : DecidableEq C') (M' : U → C' → C') (c0' : C'),
        (R M' c0' k).card = Fintype.card U ^ k) :=
  fun k => ⟨fun h => card_R_le_choose M c0 h k, card_R_le_pow M c0 k,
    exists_card_R_eq_pow (U := U) k⟩

end MathDept.MD_0105
