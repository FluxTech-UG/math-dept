import Mathlib.Analysis.Complex.Exponential
import Mathlib.Data.Fintype.BigOperators
import Mathlib.Algebra.BigOperators.Ring.Finset
import Mathlib.Data.Fintype.Pi

/-!
# MD_0108: the orbit walk beats memoryless search only on a large orbit

## Informal statement

`C` is finite and nonempty with `N = |C|`, `M : C → C` one self-map, `c0 ∈ C`, and
`R(c0) = {M^k c0 : k ≥ 0}`. The orbit walk visits `M^0 c0, …, M^(N-1) c0`; memoryless search
draws `X_1, …, X_N` independent and uniform on `C`; the target `s` is drawn independently.
(a) For uniform `s`: `Pr[∃ k < N, M^k c0 = s] = |R|/N`, `Pr[∃ i, X_i = s] = 1 - (1 - 1/N)^N
≥ 1 - 1/e`, hence a strict gain of the orbit walk forces `|R| > (1 - 1/e) N`. (b) For any target
distribution `π`: the orbit probability is `π(R)`, the memoryless one is `1 - (1 - 1/N)^N`, and a
strict gain forces `π(R) > 1 - 1/e`.

## Encoding

* The probabilities are defined from the sample space, never stipulated as the closed form.
  For a target distribution `π : C → ℝ`:
  * `orbitHit M c0 π = ∑ s, π s * (if ∃ k < N, M^[k] c0 = s then 1 else 0)`: `M, c0` fixed
    (H2), the event is a deterministic function of `s`.
  * `memHit π = ∑ s, π s * (#{X : Fin N → C | ∃ i, X i = s} / N ^ N)`: the `N` draws are the
    uniform measure on `Fin N → C` (independent uniform coordinates), the target independent of
    them (H2), so the joint probability is the `π`-weighted average of the counted conditional.
  * `uniform C s = 1 / N`.
* `orbit M c0` is `R(c0) = Set.range (fun k => M^[k] c0)` as a `Finset` (filter of `univ` by
  membership in the range; `mem_orbit`).
* "Within `N` turns" is `k < N` (H3).

## Proof recipe

1. `exists_lt_card_iterate_eq` (this is MD_0104's lemma, the first `N` iterates exhaust the
   orbit, proved here so the file does not import MD_0104): pigeonhole on `Fin (N+1)` gives
   `i < j ≤ N` with `M^[i] c0 = M^[j] c0`; then `M^[m] c0 = M^[m - (j - i)] c0` for `m ≥ j`, and
   strong induction brings every index below `N`.
2. `orbitHit_eq`: by step 1 the indicator is that of `orbit M c0`, so the sum is `π(R)`.
3. `card_miss`: the tuples missing `s` are `piFinset (fun _ => univ.erase s)`, `(N-1)^N` of them;
   so the hitting tuples number `N^N - (N-1)^N` and the conditional is `1 - (1 - 1/N)^N`.
4. `Real.one_sub_div_pow_le_exp_neg` with `t = 1 ≤ N`.

## Attempt notes (S4, 2026-10-25)

Every lemma is closed; no `sorry` and no `native_decide`, and `statement` depends only on
`propext`, `Classical.choice` and `Quot.sound`. Hypotheses used: `Nonempty C` (`N ≥ 1`, for the
division by `N`, the cast of `N - 1` and `t = 1 ≤ N`), `∑ π = 1` in (b) (the memoryless
probability). The hypothesis `π ≥ 0` in (b) is unused: both identities and the implication hold
for any real weights summing to 1.
-/

namespace MathDept.MD_0108

open Finset

set_option linter.unusedSectionVars false

noncomputable section

variable {C : Type*} [Fintype C] [DecidableEq C] [Nonempty C] (M : C → C) (c0 : C)

/-- The orbit `R(c0) = Set.range (fun k => M^[k] c0)` as a `Finset`. -/
noncomputable def orbit : Finset C := by
  classical
  exact univ.filter (fun s => s ∈ Set.range (fun k => M^[k] c0))

lemma mem_orbit (s : C) : s ∈ orbit M c0 ↔ s ∈ Set.range (fun k => M^[k] c0) := by
  classical
  unfold orbit
  simp

/-- Orbit-walk hit probability for a target distribution `π`, defined from the sample space. -/
def orbitHit (π : C → ℝ) : ℝ :=
  ∑ s, π s * (if ∃ k < Fintype.card C, M^[k] c0 = s then 1 else 0)

variable (C) in
/-- Memoryless hit probability for a target distribution `π`: the `N` draws are uniform on
`Fin N → C`, counted. -/
def memHit (π : C → ℝ) : ℝ :=
  ∑ s, π s * (((univ.filter (fun X : Fin (Fintype.card C) → C => ∃ i, X i = s)).card : ℝ) /
    (Fintype.card C : ℝ) ^ (Fintype.card C))

variable (C) in
/-- The uniform target distribution. -/
noncomputable def uniform : C → ℝ := fun _ => 1 / (Fintype.card C : ℝ)

/-- MD_0104's lemma: the first `N` iterates of `c0` exhaust its orbit. -/
lemma exists_lt_card_iterate_eq (m : ℕ) : ∃ k < Fintype.card C, M^[k] c0 = M^[m] c0 := by
  obtain ⟨x, y, hxy, hfxy⟩ := Fintype.exists_ne_map_eq_of_card_lt
    (fun k : Fin (Fintype.card C + 1) => M^[k] c0) (by simp)
  -- WLOG i < j
  obtain ⟨i, j, hij, hjN, heq⟩ : ∃ i j : ℕ, i < j ∧ j ≤ Fintype.card C ∧ M^[i] c0 = M^[j] c0 := by
    rcases lt_or_gt_of_ne (Fin.val_ne_of_ne hxy) with h | h
    · exact ⟨x, y, h, by omega, hfxy⟩
    · exact ⟨y, x, h, by omega, hfxy.symm⟩
  have hstep : ∀ n, j ≤ n → M^[n] c0 = M^[n - (j - i)] c0 := by
    intro n hn
    have h1 : M^[n] c0 = M^[n - j] (M^[j] c0) := by
      rw [← Function.iterate_add_apply]; congr 1; omega
    have h2 : M^[n - (j - i)] c0 = M^[n - j] (M^[i] c0) := by
      rw [← Function.iterate_add_apply]; congr 1; omega
    rw [h1, h2, heq]
  induction m using Nat.strong_induction_on with
  | _ m ih =>
    by_cases hm : m < Fintype.card C
    · exact ⟨m, hm, rfl⟩
    · obtain ⟨k, hk, hk'⟩ := ih (m - (j - i)) (by omega)
      exact ⟨k, hk, by rw [hk', hstep m (by omega)]⟩

lemma hit_iff (s : C) : (∃ k < Fintype.card C, M^[k] c0 = s) ↔ s ∈ orbit M c0 := by
  rw [mem_orbit]
  constructor
  · rintro ⟨k, -, hk⟩; exact ⟨k, hk⟩
  · rintro ⟨m, rfl⟩; exact exists_lt_card_iterate_eq M c0 m

lemma orbitHit_eq (π : C → ℝ) : orbitHit M c0 π = ∑ s ∈ orbit M c0, π s := by
  classical
  unfold orbitHit
  simp_rw [mul_ite, mul_one, mul_zero, hit_iff]
  rw [Finset.sum_ite_mem, Finset.univ_inter]

lemma card_pos : 0 < Fintype.card C := Fintype.card_pos

/-- The tuples that miss `s`: `(N - 1)^N` of them. -/
lemma card_miss (s : C) :
    (univ.filter (fun X : Fin (Fintype.card C) → C => ¬ ∃ i, X i = s)).card =
      (Fintype.card C - 1) ^ Fintype.card C := by
  have : univ.filter (fun X : Fin (Fintype.card C) → C => ¬ ∃ i, X i = s) =
      Fintype.piFinset (fun _ => univ.erase s) := by
    ext X; simp [Fintype.mem_piFinset]
  rw [this, Fintype.card_piFinset, Finset.prod_const, Finset.card_erase_of_mem (mem_univ s),
    card_univ, card_univ, Fintype.card_fin]

/-- The counted conditional hit probability of memoryless search, for a fixed target. -/
lemma cond_eq (s : C) :
    ((univ.filter (fun X : Fin (Fintype.card C) → C => ∃ i, X i = s)).card : ℝ) /
      (Fintype.card C : ℝ) ^ (Fintype.card C) =
      1 - (1 - 1 / (Fintype.card C : ℝ)) ^ Fintype.card C := by
  have hN := card_pos (C := C)
  have hsum := Finset.card_filter_add_card_filter_not
    (s := (univ : Finset (Fin (Fintype.card C) → C))) (fun X => ∃ i, X i = s)
  rw [card_miss, card_univ, Fintype.card_fun, Fintype.card_fin] at hsum
  have hR : ((univ.filter (fun X : Fin (Fintype.card C) → C => ∃ i, X i = s)).card : ℝ) =
      (Fintype.card C : ℝ) ^ Fintype.card C - ((Fintype.card C : ℝ) - 1) ^ Fintype.card C := by
    have := congrArg (fun n : ℕ => (n : ℝ)) hsum
    push_cast [Nat.cast_sub (Nat.one_le_iff_ne_zero.mpr hN.ne')] at this
    linarith
  have hN0 : (Fintype.card C : ℝ) ≠ 0 := by exact_mod_cast hN.ne'
  rw [hR, one_sub_div hN0, div_pow]
  field_simp

lemma memHit_eq (π : C → ℝ) (hπ : ∑ s, π s = 1) :
    memHit C π = 1 - (1 - 1 / (Fintype.card C : ℝ)) ^ Fintype.card C := by
  unfold memHit
  simp_rw [cond_eq]
  rw [← Finset.sum_mul, hπ, one_mul]

lemma uniform_sum : ∑ s, uniform C s = 1 := by
  have hN0 : (Fintype.card C : ℝ) ≠ 0 := by exact_mod_cast (card_pos (C := C)).ne'
  simp [uniform, Finset.sum_const, card_univ]

lemma bound : 1 - (1 - 1 / (Fintype.card C : ℝ)) ^ Fintype.card C ≥ 1 - Real.exp (-1) := by
  have h := Real.one_sub_div_pow_le_exp_neg (n := Fintype.card C) (t := 1)
    (by exact_mod_cast (card_pos (C := C)))
  linarith

/-- **MD_0108, the hashed statement.** (a) uniform target, (b) arbitrary target distribution. -/
theorem statement :
    (orbitHit M c0 (uniform C) = ((orbit M c0).card : ℝ) / Fintype.card C ∧
      memHit C (uniform C) = 1 - (1 - 1 / (Fintype.card C : ℝ)) ^ Fintype.card C ∧
      1 - (1 - 1 / (Fintype.card C : ℝ)) ^ Fintype.card C ≥ 1 - Real.exp (-1) ∧
      (orbitHit M c0 (uniform C) > memHit C (uniform C) →
        ((orbit M c0).card : ℝ) > (1 - Real.exp (-1)) * Fintype.card C)) ∧
    (∀ π : C → ℝ, (∀ s, 0 ≤ π s) → ∑ s, π s = 1 →
      orbitHit M c0 π = ∑ s ∈ orbit M c0, π s ∧
      memHit C π = 1 - (1 - 1 / (Fintype.card C : ℝ)) ^ Fintype.card C ∧
      (orbitHit M c0 π > memHit C π → ∑ s ∈ orbit M c0, π s > 1 - Real.exp (-1))) := by
  have hNpos : (0 : ℝ) < Fintype.card C := by exact_mod_cast card_pos (C := C)
  have hunif : orbitHit M c0 (uniform C) = ((orbit M c0).card : ℝ) / Fintype.card C := by
    rw [orbitHit_eq]
    simp [uniform, Finset.sum_const]
    ring
  refine ⟨⟨hunif, memHit_eq (uniform C) uniform_sum, bound, fun h => ?_⟩, fun π _ hπ =>
    ⟨orbitHit_eq M c0 π, memHit_eq π hπ, fun h => ?_⟩⟩
  · rw [hunif, memHit_eq (uniform C) uniform_sum, gt_iff_lt, lt_div_iff₀ hNpos] at h
    have := bound (C := C)
    nlinarith
  · rw [orbitHit_eq, memHit_eq π hπ] at h
    have := bound (C := C)
    linarith

end

end MathDept.MD_0108
