import Mathlib.Data.Fintype.Pigeonhole
import Mathlib.Data.Set.Card
import Mathlib.Logic.Function.Iterate

/-!
# MD_0104: the orbit of a self-map of a finite set is finite and eventually periodic

## Informal statement

Let `C` be a finite set of configurations with `|C| = N ≥ 1` (H1), `c₀ ∈ C`, and `M : C → C`
any self-map (H2). The reachable set is `R(c₀) = ⋃_{k ≥ 0} R_k(c₀)` with `R_k(c₀) = {M^k c₀}`.
Then (i) `R(c₀) = {M^k c₀ : k ≥ 0}`; (ii) `|R(c₀)| ≤ N`; (iii) there are `ρ ≥ 0` and `p ≥ 1`
with `ρ + p ≤ N` such that `M^{k+p} c₀ = M^k c₀` for every `k ≥ ρ` (some preperiod and
period, not necessarily the minimal ones).

## Encoding

* `C : Type*` with `[Fintype C]` and `[Nonempty C]` (H1); `N = Fintype.card C`. `M : C → C` is
  an arbitrary function (H2), `c0 : C`. `M^k` is `M^[k]` (`Nat.iterate`), with `M^[0] = id`.
* `reach M c0 : Set C` is `⋃ k : ℕ, {M^[k] c0}`, the union of the singletons `R_k(c₀)`,
  literally as the entry defines it; it is deliberately not `Set.range`, so that (i), the
  equality `reach M c0 = Set.range (fun k => M^[k] c0)`, is a stated conjunct and not a
  definitional triviality.
* (ii) is `(reach M c0).ncard ≤ Fintype.card C`.
* (iii) is `∃ ρ p, 1 ≤ p ∧ ρ + p ≤ Fintype.card C ∧ ∀ k ≥ ρ, M^[k + p] c0 = M^[k] c0`;
  `ρ, p : ℕ`, so `ρ ≥ 0` is automatic.
* `exists_lt_card_iterate_eq` (exported): every iterate is one of the first `N`,
  `∀ k, ∃ j < N, M^[j] c0 = M^[k] c0`. MD_0108 leans on this lemma.

## Proof recipe

1. `reach_eq_range`: membership in the union of singletons is `∃ k, M^[k] c0 = x`.
2. `ncard_reach_le`: `Set.ncard_le_card` gives `ncard ≤ Nat.card C = Fintype.card C`.
3. `eventually_periodic`: pigeonhole (`Fintype.exists_ne_map_eq_of_card_lt`) on
   `i : Fin (N + 1) ↦ M^[i] c0` gives `i < j ≤ N` with equal iterates; take `ρ = i`,
   `p = j - i`. For `k ≥ ρ`, `M^[k + p] c0 = M^[k - ρ] (M^[j] c0) = M^[k - ρ] (M^[i] c0)
   = M^[k] c0` by `Function.iterate_add_apply`.
4. `exists_lt_card_iterate_eq`: strong induction on `k`. If `k < N` take `j = k`; otherwise
   `k ≥ N ≥ ρ + p`, so `k - p ≥ ρ` and `M^[k] c0 = M^[k - p] c0` by step 3, and `k - p < k`.

## Attempt notes (S4, 2026-10-25)

Every theorem is closed; no `sorry` remains. `statement` and `exists_lt_card_iterate_eq`
depend on `propext`, `Classical.choice` and `Quot.sound` only. The `[Nonempty C]` half of H1
is unused by every proof (the `unusedSectionVars` linter reports it on `reach_eq_range`,
`ncard_reach_le` and `eventually_periodic`; it reaches `statement` through the section
variables, not through any proof step): pigeonhole on `Fin (N + 1)` needs no `N ≥ 1`, and
a `c0 : C` already makes `C` nonempty. `[Fintype C]` is unused by (i).
-/

namespace MathDept.MD_0104

variable {C : Type*} [Fintype C] [Nonempty C] (M : C → C) (c0 : C)

/-- The reachable set `R(c₀) = ⋃_{k ≥ 0} {M^k c₀}`. -/
def reach : Set C := ⋃ k : ℕ, {M^[k] c0}

/-- (i) The reachable set is the forward orbit. -/
theorem reach_eq_range : reach M c0 = Set.range (fun k : ℕ => M^[k] c0) := by
  ext x
  simp only [reach, Set.mem_iUnion, Set.mem_singleton_iff, Set.mem_range]
  exact ⟨fun ⟨k, hk⟩ => ⟨k, hk.symm⟩, fun ⟨k, hk⟩ => ⟨k, hk.symm⟩⟩

/-- (ii) The reachable set has at most `N` elements. -/
theorem ncard_reach_le : (reach M c0).ncard ≤ Fintype.card C := by
  have h := Set.ncard_le_card (reach M c0)
  rwa [Nat.card_eq_fintype_card] at h

/-- (iii) The orbit is eventually periodic with preperiod plus period at most `N`. -/
theorem eventually_periodic :
    ∃ ρ p : ℕ, 1 ≤ p ∧ ρ + p ≤ Fintype.card C ∧ ∀ k ≥ ρ, M^[k + p] c0 = M^[k] c0 := by
  obtain ⟨i, j, hij, heq⟩ := Fintype.exists_ne_map_eq_of_card_lt
    (fun i : Fin (Fintype.card C + 1) => M^[(i : ℕ)] c0) (by simp)
  -- order the pair: `a < b ≤ N` with `M^[a] c0 = M^[b] c0`
  obtain ⟨a, b, hab, hbN, habeq⟩ : ∃ a b : ℕ, a < b ∧ b ≤ Fintype.card C ∧
      M^[a] c0 = M^[b] c0 := by
    rcases lt_or_gt_of_ne (Fin.val_ne_of_ne hij) with h | h
    · exact ⟨i, j, h, Nat.lt_succ_iff.mp j.isLt, heq⟩
    · exact ⟨j, i, h, Nat.lt_succ_iff.mp i.isLt, heq.symm⟩
  refine ⟨a, b - a, by omega, by omega, fun k hk => ?_⟩
  have e1 : k + (b - a) = (k - a) + b := by omega
  have e2 : k = (k - a) + a := by omega
  rw [e1, Function.iterate_add_apply, ← habeq, ← Function.iterate_add_apply, ← e2]

/-- The first `N` iterates exhaust the orbit. MD_0108 leans on this lemma. -/
theorem exists_lt_card_iterate_eq (k : ℕ) : ∃ j < Fintype.card C, M^[j] c0 = M^[k] c0 := by
  obtain ⟨ρ, p, hp, hρp, hper⟩ := eventually_periodic M c0
  induction k using Nat.strong_induction_on with
  | _ k ih =>
    by_cases hk : k < Fintype.card C
    · exact ⟨k, hk, rfl⟩
    · obtain ⟨j, hj, hjeq⟩ := ih (k - p) (by omega)
      refine ⟨j, hj, ?_⟩
      rw [hjeq, ← hper (k - p) (by omega), Nat.sub_add_cancel (by omega)]

/-- **MD_0104, the hashed statement.** (i) the reachable set is the forward orbit, (ii) it has
at most `N = |C|` elements, (iii) the orbit is eventually periodic with `ρ + p ≤ N`. -/
theorem statement :
    reach M c0 = Set.range (fun k : ℕ => M^[k] c0) ∧
    (reach M c0).ncard ≤ Fintype.card C ∧
    ∃ ρ p : ℕ, 1 ≤ p ∧ ρ + p ≤ Fintype.card C ∧ ∀ k ≥ ρ, M^[k + p] c0 = M^[k] c0 :=
  ⟨reach_eq_range M c0, ncard_reach_le M c0, eventually_periodic M c0⟩

end MathDept.MD_0104
