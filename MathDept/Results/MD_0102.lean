import Mathlib.Logic.Function.Iterate

/-!
# MD_0102 (the Boolean form of MD_0096): a globally attracting rest state erases every training input

## Informal statement (Boolean form only)

Let `x_{t+1} = F(x_t, u_t)` be a synchronous discrete network with inputs `u ∈ {0,1}²` and a
readout node. If every trajectory of `F(·,(0,0))` reaches a single fixed point `x*` within `m`
steps, then for every training input `v`, every `T1`, `T3` and every gap `T2 ≥ m`, the test
readout `φ_v(T2)` equals the pretest readout `φ_0` exactly. Consequently associative
conditioning fails at `(T1, T2, T3)` for every `T1`, `T3` and every `T2 ≥ m`.

The ODE form of the entry (uniform convergence of `φ_v(T2)` to `φ_0` under a globally
asymptotically stable equilibrium) is out of scope for this file.

## Conventions used here

* State space: an arbitrary type `α`. The proof uses nothing about it; the entry's
  `Fin k → Bool` is an instance, and finiteness of `k` (H4) is not needed once `m` is given.
* Inputs: `Bool × Bool`, with `(false, false)` the input-free `(0,0)` and `(false, true)` the
  test input `(0,1)`. Network: `F : α → Bool × Bool → α`, the synchronous update (the input
  source nodes are folded into the second argument). Readout: `ρ : α → β` for an arbitrary
  `β`; "evokes" (`evokes`) is stated for `β = Bool`, where the readout node equals `1` is
  `= true`.
* `step F u = fun y => F y u`, and a window of length `T` under constant input `u` from
  state `x` ends at `(step F u)^[T] x` (`Nat.iterate`).
* Step indexing: the readout trajectory on a window (`window F ρ u T x : Fin T → β`) reads the
  states produced during the window, after each update: entry `t` is
  `ρ ((step F u)^[t + 1] x)` for `t = 0, …, T - 1`.
* `gapEnd F v T1 T2 xs` is the state after `v` for `T1` from `xs`, then `(0,0)` for `T2`.
  `testReadout F ρ xs v T1 T2 T3 = window F ρ (false,true) T3 (gapEnd …)` is `φ_v(T2)`;
  `pretestReadout F ρ xs T3 = window F ρ (false,true) T3 xs` is `φ_0`. Both use the same
  window function, so the indexing convention cannot differ between them.
* Hypotheses: `hfix : F xs (false,false) = xs` (`x*` is a fixed point) and
  `hreach : ∀ x, (step F (false,false))^[m] x = xs` (every trajectory is at `x*` after `m`
  steps; "within `m` steps" plus the fixed point gives "at step `m`", which is how it is
  encoded). `hfix` is in fact derivable from `hreach`, but it is kept as the entry states it.
* `associativeConditioning F ρ xs T1 T2 T3` is the conjunction of the Protocol's four
  conditions: `φ_0` does not evoke; the `(1,0)` readout from `x*` for `T3` evokes;
  `φ_{(1,1)}(T2)` evokes; neither `φ_{(1,0)}(T2)` nor `φ_{(0,1)}(T2)` evokes.

## Proof recipe

1. `gapEnd_eq`: for `T2 ≥ m`, write `T2 = (T2 - m) + m`; by `Function.iterate_add_apply`,
   `g^[T2] y = g^[T2 - m] (g^[m] y) = g^[T2 - m] xs`, and `Function.iterate_fixed hfix` makes
   that `xs`. So the gap-end state is `xs` whatever `v`, `T1` were.
2. `readout_eq`: rewrite the test readout's start state by step 1; it is then literally the
   pretest readout.
3. `associativeConditioning_fails`: by step 2 `φ_{(1,1)}(T2) = φ_0`, so the third condition
   (it evokes) contradicts the first (`φ_0` does not evoke).

`statement` is the hashed declaration: it conjoins `readout_eq` and `associativeConditioning_fails`.

## Attempt notes (S4, 2026-10-25)

Every declaration is closed; no `sorry` remains. The proof is the recipe verbatim. Only the
`(1,1)` training input and the first and third conditions are used by the corollary.
-/

namespace MathDept.MD_0102

variable {α β : Type*}

/-- One synchronous update under the constant input `u`. -/
def step (F : α → Bool × Bool → α) (u : Bool × Bool) : α → α := fun y => F y u

/-- Readout trajectory on a window of length `T` under constant input `u` from state `x`:
entry `t` is the readout after the `(t+1)`-th update. -/
def window (F : α → Bool × Bool → α) (ρ : α → β) (u : Bool × Bool) (T : ℕ) (x : α) :
    Fin T → β :=
  fun t => ρ ((step F u)^[t.val + 1] x)

/-- State at the end of the gap: `v` for `T1` steps from `xs`, then `(0,0)` for `T2` steps. -/
def gapEnd (F : α → Bool × Bool → α) (v : Bool × Bool) (T1 T2 : ℕ) (xs : α) : α :=
  (step F (false, false))^[T2] ((step F v)^[T1] xs)

/-- The test readout `φ_v(T2)`: readout under `(0,1)` for `T3` from the gap-end state. -/
def testReadout (F : α → Bool × Bool → α) (ρ : α → β) (xs : α) (v : Bool × Bool)
    (T1 T2 T3 : ℕ) : Fin T3 → β :=
  window F ρ (false, true) T3 (gapEnd F v T1 T2 xs)

/-- The pretest readout `φ_0`: readout under `(0,1)` for `T3` from `xs`. -/
def pretestReadout (F : α → Bool × Bool → α) (ρ : α → β) (xs : α) (T3 : ℕ) : Fin T3 → β :=
  window F ρ (false, true) T3 xs

/-- A Boolean readout trajectory evokes when it is `true` at some time of its window. -/
def evokes {T : ℕ} (w : Fin T → Bool) : Prop := ∃ t, w t = true

/-- The Protocol's associative conditioning at `(T1, T2, T3)`, Boolean class. -/
def associativeConditioning (F : α → Bool × Bool → α) (ρ : α → Bool) (xs : α)
    (T1 T2 T3 : ℕ) : Prop :=
  ¬ evokes (pretestReadout F ρ xs T3) ∧
  evokes (window F ρ (true, false) T3 xs) ∧
  evokes (testReadout F ρ xs (true, true) T1 T2 T3) ∧
  ¬ evokes (testReadout F ρ xs (true, false) T1 T2 T3) ∧
  ¬ evokes (testReadout F ρ xs (false, true) T1 T2 T3)

theorem gapEnd_eq (F : α → Bool × Bool → α) (xs : α) (m : ℕ)
    (hfix : F xs (false, false) = xs)
    (hreach : ∀ x, (step F (false, false))^[m] x = xs)
    (v : Bool × Bool) (T1 T2 : ℕ) (hT2 : m ≤ T2) :
    gapEnd F v T1 T2 xs = xs := by
  unfold gapEnd
  obtain ⟨k, rfl⟩ := Nat.exists_eq_add_of_le' hT2
  rw [Function.iterate_add_apply, hreach]
  exact Function.iterate_fixed hfix k

/-- **MD_0102 (the Boolean form of MD_0096).** If every trajectory of `F(·,(0,0))` is at the fixed point `xs`
after `m` steps, then for every gap `T2 ≥ m` the test readout equals the pretest readout. -/
theorem readout_eq (F : α → Bool × Bool → α) (ρ : α → β) (xs : α) (m : ℕ)
    (hfix : F xs (false, false) = xs)
    (hreach : ∀ x, (step F (false, false))^[m] x = xs) :
    ∀ (v : Bool × Bool) (T1 T3 T2 : ℕ), m ≤ T2 →
      testReadout F ρ xs v T1 T2 T3 = pretestReadout F ρ xs T3 := by
  intro v T1 T3 T2 hT2
  unfold testReadout pretestReadout
  rw [gapEnd_eq F xs m hfix hreach v T1 T2 hT2]

/-- **MD_0102, corollary.** Under the same hypotheses associative conditioning fails at
`(T1, T2, T3)` for every `T1`, `T3` and every `T2 ≥ m`. -/
theorem associativeConditioning_fails (F : α → Bool × Bool → α) (ρ : α → Bool) (xs : α)
    (m : ℕ) (hfix : F xs (false, false) = xs)
    (hreach : ∀ x, (step F (false, false))^[m] x = xs) :
    ∀ (T1 T3 T2 : ℕ), m ≤ T2 → ¬ associativeConditioning F ρ xs T1 T2 T3 := by
  intro T1 T3 T2 hT2 h
  obtain ⟨h0, -, h11, -, -⟩ := h
  rw [readout_eq F ρ xs m hfix hreach (true, true) T1 T3 T2 hT2] at h11
  exact h0 h11

/-- **MD_0102, the hashed statement.** The readout equality and the failure of associative
conditioning, for a Boolean readout, at every gap `T2 ≥ m`. -/
theorem statement (F : α → Bool × Bool → α) (ρ : α → Bool) (xs : α) (m : ℕ)
    (hfix : F xs (false, false) = xs)
    (hreach : ∀ x, (step F (false, false))^[m] x = xs) :
    (∀ (v : Bool × Bool) (T1 T3 T2 : ℕ), m ≤ T2 →
      testReadout F ρ xs v T1 T2 T3 = pretestReadout F ρ xs T3) ∧
    (∀ (T1 T3 T2 : ℕ), m ≤ T2 → ¬ associativeConditioning F ρ xs T1 T2 T3) :=
  ⟨readout_eq F ρ xs m hfix hreach, associativeConditioning_fails F ρ xs m hfix hreach⟩

end MathDept.MD_0102
