import Mathlib.Logic.Function.Iterate
import Mathlib.Algebra.Group.Nat.Even
import Mathlib.Tactic.Ring

/-!
# MD_0101: one internal node cannot condition robustly, two can

## Informal statement

Boolean networks, synchronous update, the two inputs `(u₁, u₂)` as source nodes, readout one
internal node. `(F, r)` passes at `(W, G)` when some fixed point `x*` of `F(·, (0,0))` gives
associative conditioning at `(T₁, T₂, T₃) = (W, G, W)`: the pretest `(0,1)` from `x*` does not
evoke; `(1,0)` from `x*` evokes; after training `(1,1)` for `W`, gap `(0,0)` for `G`, the test
`(0,1)` for `W` evokes; after training `(1,0)` or `(0,1)` instead, the test does not evoke.
(a) With one internal node, nothing passes at odd `W` with `G ≥ 1`, and nothing passes at both
`W` and `W+1` with the same `G ≥ 1`. (b) With two internal nodes, the network
`M' = M ∨ (u₁ ∧ u₂)`, `R' = u₁ ∨ (u₂ ∧ M)` with readout `R` and rest state `(0,0)` passes at
every `(W, G)` with `W, G ≥ 1`.

## Encoding

* Inputs are `Bool × Bool`. A network on state type `α` is `F : α → Bool × Bool → α` with a
  readout `ρ : α → Bool`. One internal node: `α = Bool`, `ρ = id`. Two internal nodes:
  `α = Bool × Bool` (`(M, R)`), `ρ = Prod.snd`.
* `step F u = fun y => F y u`. Step-indexing convention: a window of length `T` under constant
  input `u` applies `T` synchronous updates, `window F u T x = (step F u)^[T] x`, and the
  readout is read on the states after each update, steps `1..T` (H3):
  `evokes F ρ u T x ↔ ∃ t < T, ρ ((step F u)^[t+1] x) = true`.
* `assocCond F ρ x* T₁ T₂ T₃` is the four protocol conditions (five clauses);
  `passes F ρ W G = ∃ x*, F x* (0,0) = x* ∧ assocCond F ρ x* W G W`.
* `k = 0` has no internal node to read out, so it is excluded by the encoding, as in the entry.

## Proof recipe

(a) 1. Every `g : Bool → Bool` satisfies `g^[3] = g` (it is the identity, a constant or
   negation), so `g^[n+2] = g^[n]` for `n ≥ 1` and `g^[n + 2k] = g^[n]`.
2. Hence a window of length `n + 2k` (`n ≥ 1`) ends where one of length `n` does, and for
   `n ≥ 2` a readout over `n + 2k` steps evokes iff one over `n` steps does (steps `n+1, n+2`
   repeat steps `n-1, n`). The gap `G = G₀ + 2k` (`G₀ ≥ 1`) acts like `G₀`.
3. So `passes F id W G` depends on `W` odd only through `W ∈ {1, 3}` and on `G ≥ 1` only
   through `G ∈ {1, 2}`. The finite residue is the four statements
   `∀ F, ¬ passes F id W G` for `(W, G) ∈ {1, 3} × {1, 2}`, decided by `decide` after writing
   `F` as its truth table of 8 bits (`tbl`): 256 tables times 2 candidate rest states.
4. (a2) follows from (a1): one of `W`, `W + 1` is odd.
(b) Each of the four constant-input maps of the witness is idempotent (16 cases by `rfl`), so every window of length `n + 1` ends at `g x`, and every readout over
   `n + 1` steps evokes iff `ρ (g x)`. With `W = w + 1`, `G = g + 1` the five clauses become
   single-step facts, closed by `decide`.

The reduction is sound because it is proved, not assumed: lemmas `iter_add_two_mul`,
`evokes_add_two_mul`, `passes_W_reduce`, `passes_G_reduce` rewrite the predicate for arbitrary
`W, G` to the residue before `decide` runs.

## Attempt notes (S4, 2026-10-25)

Closed in full: no `sorry`, no `native_decide`, no `maxHeartbeats` or `maxRecDepth` change.
The S1 finite reduction (classes `W = 1`, odd `W ≥ 3`, even `W ≥ 2`; `G` immaterial) is used
in the slightly weaker form "G modulo 2", which suffices.
-/

namespace MathDept.MD_0101

open Function

/-! ## Protocol -/

/-- One synchronous update under constant input `u`. -/
def step {α : Type} (F : α → Bool × Bool → α) (u : Bool × Bool) : α → α := fun y => F y u

/-- The state after a window of `T` updates under constant input `u`. -/
def window {α : Type} (F : α → Bool × Bool → α) (u : Bool × Bool) (T : ℕ) (x : α) : α :=
  (step F u)^[T] x

/-- The readout equals `1` at some step `1..T` of a window under `u` from `x`. -/
def evokes {α : Type} (F : α → Bool × Bool → α) (ρ : α → Bool) (u : Bool × Bool) (T : ℕ)
    (x : α) : Prop :=
  ∃ t, t < T ∧ ρ ((step F u)^[t+1] x) = true

/-- Associative conditioning at `(T₁, T₂, T₃)` from the rest state `xs`. -/
def assocCond {α : Type} (F : α → Bool × Bool → α) (ρ : α → Bool) (xs : α)
    (T1 T2 T3 : ℕ) : Prop :=
  ¬ evokes F ρ (false, true) T3 xs ∧
  evokes F ρ (true, false) T3 xs ∧
  evokes F ρ (false, true) T3 (window F (false, false) T2 (window F (true, true) T1 xs)) ∧
  ¬ evokes F ρ (false, true) T3 (window F (false, false) T2 (window F (true, false) T1 xs)) ∧
  ¬ evokes F ρ (false, true) T3 (window F (false, false) T2 (window F (false, true) T1 xs))

/-- `(F, ρ)` passes at `(W, G)`. -/
def passes {α : Type} (F : α → Bool × Bool → α) (ρ : α → Bool) (W G : ℕ) : Prop :=
  ∃ xs, F xs (false, false) = xs ∧ assocCond F ρ xs W G W

/-! ## Part (a): one internal node -/

theorem iter_three (g : Bool → Bool) : g^[3] = g := by
  funext x
  simp only [iterate_succ, iterate_zero, comp_apply, id]
  cases x <;> cases h1 : g true <;> cases h2 : g false <;> simp [h1, h2]

theorem iter_add_two (g : Bool → Bool) (n : ℕ) (hn : 1 ≤ n) : g^[n + 2] = g^[n] := by
  obtain ⟨m, rfl⟩ : ∃ m, n = m + 1 := ⟨n - 1, by omega⟩
  rw [show m + 1 + 2 = m + 3 by omega, iterate_add, iter_three, ← iterate_succ]

theorem iter_add_two_mul (g : Bool → Bool) (n k : ℕ) (hn : 1 ≤ n) :
    g^[n + 2 * k] = g^[n] := by
  induction k with
  | zero => simp
  | succ k ih =>
    rw [show n + 2 * (k + 1) = n + 2 * k + 2 by ring, iter_add_two _ _ (by omega), ih]

theorem evokes_add_two (F : Bool → Bool × Bool → Bool) (u : Bool × Bool) (n : ℕ)
    (hn : 2 ≤ n) (x : Bool) : evokes F id u (n + 2) x ↔ evokes F id u n x := by
  obtain ⟨m, rfl⟩ : ∃ m, n = m + 2 := ⟨n - 2, by omega⟩
  constructor
  · rintro ⟨t, ht, h⟩
    by_cases h1 : t < m + 2
    · exact ⟨t, h1, h⟩
    · by_cases h2 : t = m + 2
      · subst h2
        refine ⟨m, by omega, ?_⟩
        rwa [show m + 2 + 1 = (m + 1) + 2 by omega, iter_add_two _ _ (by omega)] at h
      · have h3 : t = m + 3 := by omega
        subst h3
        refine ⟨m + 1, by omega, ?_⟩
        rwa [show m + 3 + 1 = (m + 2) + 2 by omega, iter_add_two _ _ (by omega)] at h
  · rintro ⟨t, ht, h⟩
    exact ⟨t, by omega, h⟩

theorem evokes_add_two_mul (F : Bool → Bool × Bool → Bool) (u : Bool × Bool) (n k : ℕ)
    (hn : 2 ≤ n) (x : Bool) : evokes F id u (n + 2 * k) x ↔ evokes F id u n x := by
  induction k with
  | zero => simp
  | succ k ih =>
    rw [show n + 2 * (k + 1) = n + 2 * k + 2 by ring, evokes_add_two _ _ _ (by omega), ih]

theorem window_add_two_mul (F : Bool → Bool × Bool → Bool) (u : Bool × Bool) (n k : ℕ)
    (hn : 1 ≤ n) (x : Bool) : window F u (n + 2 * k) x = window F u n x := by
  simp only [window, iter_add_two_mul _ _ _ hn]

theorem passes_W_reduce (F : Bool → Bool × Bool → Bool) (n k G : ℕ) (hn : 2 ≤ n) :
    passes F id (n + 2 * k) G ↔ passes F id n G := by
  simp only [passes, assocCond, window_add_two_mul _ _ _ _ (show 1 ≤ n by omega),
    evokes_add_two_mul _ _ _ _ hn]

theorem passes_G_reduce (F : Bool → Bool × Bool → Bool) (W n k : ℕ) (hn : 1 ≤ n) :
    passes F id W (n + 2 * k) ↔ passes F id W n := by
  simp only [passes, assocCond, window_add_two_mul _ _ _ _ hn]

/-- A one-node network as its truth table. -/
def tbl (a b c d e f g h : Bool) : Bool → Bool × Bool → Bool
  | false, (false, false) => a
  | false, (false, true) => b
  | false, (true, false) => c
  | false, (true, true) => d
  | true, (false, false) => e
  | true, (false, true) => f
  | true, (true, false) => g
  | true, (true, true) => h

theorem eq_tbl (F : Bool → Bool × Bool → Bool) :
    F = tbl (F false (false, false)) (F false (false, true)) (F false (true, false))
      (F false (true, true)) (F true (false, false)) (F true (false, true))
      (F true (true, false)) (F true (true, true)) := by
  funext x u
  obtain ⟨u1, u2⟩ := u
  cases x <;> cases u1 <;> cases u2 <;> rfl

instance (F : Bool → Bool × Bool → Bool) (W G : ℕ) : Decidable (passes F id W G) := by
  unfold passes assocCond evokes window; infer_instance

theorem residue_1_1 : ∀ a b c d e f g h : Bool, ¬ passes (tbl a b c d e f g h) id 1 1 := by
  decide
theorem residue_1_2 : ∀ a b c d e f g h : Bool, ¬ passes (tbl a b c d e f g h) id 1 2 := by
  decide
theorem residue_3_1 : ∀ a b c d e f g h : Bool, ¬ passes (tbl a b c d e f g h) id 3 1 := by
  decide
theorem residue_3_2 : ∀ a b c d e f g h : Bool, ¬ passes (tbl a b c d e f g h) id 3 2 := by
  decide

theorem not_passes_residue (F : Bool → Bool × Bool → Bool) (W G : ℕ)
    (hW : W = 1 ∨ W = 3) (hG : G = 1 ∨ G = 2) : ¬ passes F id W G := by
  rw [eq_tbl F]
  rcases hW with rfl | rfl <;> rcases hG with rfl | rfl
  · exact residue_1_1 _ _ _ _ _ _ _ _
  · exact residue_1_2 _ _ _ _ _ _ _ _
  · exact residue_3_1 _ _ _ _ _ _ _ _
  · exact residue_3_2 _ _ _ _ _ _ _ _

/-- (a1) One internal node: no pass at odd `W` with `G ≥ 1`. -/
theorem part_a1 : ∀ (F : Bool → Bool × Bool → Bool) (W G : ℕ), Odd W → 1 ≤ G →
    ¬ passes F id W G := by
  intro F W G hW hG
  obtain ⟨j, rfl⟩ := hW
  obtain ⟨G', rfl⟩ : ∃ G', G = G' + 1 := ⟨G - 1, by omega⟩
  have hGr : ∃ G₀ k, G' + 1 = G₀ + 2 * k ∧ (G₀ = 1 ∨ G₀ = 2) := by
    rcases Nat.even_or_odd G' with ⟨k, hk⟩ | ⟨k, hk⟩
    · exact ⟨1, k, by omega, Or.inl rfl⟩
    · exact ⟨2, k, by omega, Or.inr rfl⟩
  obtain ⟨G₀, k, hk, hG₀⟩ := hGr
  rw [hk, passes_G_reduce _ _ _ _ (by omega)]
  rcases j with _ | j
  · exact not_passes_residue F 1 G₀ (Or.inl rfl) hG₀
  · rw [show 2 * (j + 1) + 1 = 3 + 2 * j by ring, passes_W_reduce _ _ _ _ (by omega)]
    exact not_passes_residue F 3 G₀ (Or.inr rfl) hG₀

/-- (a2) One internal node: no pass at both `W` and `W + 1` with the same `G ≥ 1`. -/
theorem part_a2 : ∀ (F : Bool → Bool × Bool → Bool) (W G : ℕ), 1 ≤ W → 1 ≤ G →
    ¬ (passes F id W G ∧ passes F id (W + 1) G) := by
  intro F W G _ hG ⟨h1, h2⟩
  rcases Nat.even_or_odd W with hW | hW
  · exact part_a1 F (W + 1) G hW.add_one hG h2
  · exact part_a1 F W G hW hG h1

/-! ## Part (b): the two-node witness -/

/-- `M' = M ∨ (u₁ ∧ u₂)`, `R' = u₁ ∨ (u₂ ∧ M)`; state `(M, R)`. -/
def F₂ : Bool × Bool → Bool × Bool → Bool × Bool :=
  fun x u => (x.1 || (u.1 && u.2), u.1 || (u.2 && x.1))

theorem iter_idem {β : Type} (g : β → β) (hg : ∀ y, g (g y) = g y) (n : ℕ) (x : β) :
    g^[n + 1] x = g x := by
  induction n with
  | zero => rfl
  | succ n ih => rw [iterate_succ_apply', ih, hg]

theorem step_idem (u : Bool × Bool) (y : Bool × Bool) :
    step F₂ u (step F₂ u y) = step F₂ u y := by
  obtain ⟨_ | _, _ | _⟩ := u <;> obtain ⟨_ | _, _ | _⟩ := y <;> rfl

theorem window_F₂ (u : Bool × Bool) (n : ℕ) (x : Bool × Bool) :
    window F₂ u (n + 1) x = F₂ x u :=
  iter_idem _ (step_idem u) n x

theorem evokes_F₂ (u : Bool × Bool) (n : ℕ) (x : Bool × Bool) :
    evokes F₂ Prod.snd u (n + 1) x ↔ (F₂ x u).2 = true := by
  unfold evokes
  simp only [iter_idem _ (step_idem u)]
  exact ⟨fun ⟨_, _, h⟩ => h, fun h => ⟨0, by omega, h⟩⟩

/-- (b) The two-node witness passes at every `(W, G)` with `W, G ≥ 1`, rest state `(0,0)`. -/
theorem part_b : ∀ W G : ℕ, 1 ≤ W → 1 ≤ G → passes F₂ Prod.snd W G := by
  intro W G hW hG
  obtain ⟨w, rfl⟩ : ∃ w, W = w + 1 := ⟨W - 1, by omega⟩
  obtain ⟨g, rfl⟩ : ∃ g, G = g + 1 := ⟨G - 1, by omega⟩
  refine ⟨(false, false), by decide, ?_⟩
  simp only [assocCond, evokes_F₂, window_F₂]
  decide

/-- The entry's four-node sentence, as the conjunction of (a1), (a2) and (b). -/
theorem statement :
    (∀ (F : Bool → Bool × Bool → Bool) (W G : ℕ), Odd W → 1 ≤ G → ¬ passes F id W G) ∧
    (∀ (F : Bool → Bool × Bool → Bool) (W G : ℕ), 1 ≤ W → 1 ≤ G →
      ¬ (passes F id W G ∧ passes F id (W + 1) G)) ∧
    (∀ W G : ℕ, 1 ≤ W → 1 ≤ G → passes F₂ Prod.snd W G) :=
  ⟨part_a1, part_a2, part_b⟩

end MathDept.MD_0101
