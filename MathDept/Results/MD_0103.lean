import Mathlib.Logic.Function.Iterate
import Mathlib.Data.Nat.Init

/-!
# MD_0103 (the Boolean form of MD_0100): an acyclic Boolean network settles, so it cannot condition

## Informal statement (Boolean form only)

Let a synchronous Boolean network `x_{t+1} = F(x_t, u_t)` on internal nodes `Fin k`, with the
two inputs as source nodes (H1), have an acyclic interaction graph on its internal nodes with
depth `d` (H2). Then `G = F(·,(0,0))` has a unique fixed point `x*`, every trajectory under
`(0,0)` reaches it within `d + 1` steps, and for every training input `v`, every `T1, T3` and
every gap `T2 ≥ d + 1`, the test readout equals the pretest readout, `φ_v(T2) = φ_0`. Hence
there is no associative conditioning at any gap `T2 ≥ d + 1`, and none persistent. The ODE form
of the entry (cascade of input-to-state stable nodes, reduced to MD_0096) is not formalized in
this file.

## Encoding

* Nodes `Fin k`, states `State k = Fin k → Bool`, inputs `Input = Bool × Bool` (the two source
  nodes; `(false, false)` is `(0,0)`). The network is `F : State k → Input → State k`, one
  synchronous update per application (H1). The input-free map is `G F x = F x (false, false)`.
* **Acyclicity with depth `d` (H2)** is encoded by a depth function `depth : Fin k → ℕ` with
  the locality hypothesis
  `hloc : ∀ i x y, (∀ j, depth j < depth i → x j = y j) → G F x i = G F y i`
  (node `i`'s update under `(0,0)` reads only nodes of strictly smaller depth; a depth-0 node's
  update is a constant) and the bound `hd : ∀ i, depth i ≤ d`.
  Justification of equivalence with H2. If the essential-dependence graph is acyclic with
  longest directed path of `d` edges, let `depth i` be the number of edges of the longest path
  ending at `i`. Every essential parent `j` of `i` has `depth j < depth i` (extend its longest
  path by the edge `j → i`), and `F_i` is determined by its essential arguments, so `hloc`
  holds (for every input, in particular `(0,0)`), and `depth i ≤ d`. The encoding constrains
  only the input-free slice of `F`, so it is implied by acyclicity of the full
  essential-dependence graph, and the theorem is at least as strong as the graph form. Mathlib has no directed-graph acyclicity or depth predicate
  (`SimpleGraph.IsAcyclic` is undirected; `Mathlib/Combinatorics/Digraph/` has none), which is
  why the depth-function form is used. The theorem needs `hloc` only at input `(0,0)`, which
  is weaker than H2 (H2 restricted to the `(0,0)` slice), so the result proven is at least as
  strong as the entry's.
* **Windows and step indexing.** A window of length `T` under constant input `u` from state `x`
  ends at `window F u T x = (fun y => F y u)^[T] x`. The readout trajectory on the window is
  `readout F r u T x : Fin T → Bool`, `t ↦ (window F u (t+1) x) r`: the readout node's value
  after `t + 1` updates, so the window's `T` samples are the states after updates `1, …, T`.
* **Protocol.** The rest state is any `xr` with `G F xr = xr` (a fixed point of the input-free
  dynamics). `testReadout F r xr v T1 T2 T3` is the readout under `(0,1) = (false, true)` for
  `T3` from `window F (0,0) T2 (window F v T1 xr)`; `pretestReadout F r xr T3` is the readout
  under `(0,1)` for `T3` from `xr`. `Evokes φ` is `∃ t, φ t = true`.
  `AssociativeConditioning F r xr T1 T2 T3` is the conjunction of the Protocol's four
  conditions: `φ_0` does not evoke; the readout under `(1,0)` for `T3` from `xr` evokes;
  `φ_(1,1)(T2)` evokes; neither `φ_(1,0)(T2)` nor `φ_(0,1)(T2)` evokes. `Persistent` is
  `∃ N, ∀ T2 ≥ N, AssociativeConditioning … T2 …`.
* The entry quantifies over `T1, T3 ≥ 1`; the theorems below hold for all `T1, T3 : ℕ`, which
  is stronger, so no positivity hypothesis appears.

## Proof recipe

1. `settle`: by strong induction on `depth i`, `(G^[n] x) i = (G^[n] y) i` for
   `n ≥ depth i + 1`: write `n = n' + 1`, `G^[n'+1] x = G (G^[n'] x)`, and apply `hloc`, whose
   premise is the induction hypothesis at the shallower nodes with `n' ≥ depth j + 1`.
   `settle_eq` restates it as `(G^[n] x) i = (G^[depth i + 1] x) i`.
2. `reach`: with `xs = G^[d+1] (fun _ => false)`, `G^[d+1] x = xs` for all `x` (`settle`
   pointwise, `hd`). `exists_unique_fixedPt`: `G xs = G^[d+1] (G 0) = xs`, and a fixed point
   `y` equals `G^[d+1] y = xs` (`Function.iterate_fixed`). `reach_of_le` extends `reach` to
   every `n ≥ d + 1`.
3. `readout_eq`: the gap ends at `G^[T2] w = xs`, and the rest state `xr` equals `xs` by
   uniqueness, so the test window starts at `xr` and the test readout is the pretest readout.
4. `no_conditioning`: condition one says `φ_0` does not evoke, and condition five says
   `φ_(0,1)(T2)` does not evoke, but condition three says `φ_(1,1)(T2)`, which equals `φ_0`,
   evokes. `not_persistent`: take `T2 = N + (d + 1)`.

`statement` is the hashed declaration: it conjoins `exists_unique_fixedPt`, `reach`,
`readout_eq`, `no_conditioning` and `not_persistent`.

## Attempt notes (S4, 2026-10-25)

Every theorem is closed; no `sorry` remains, and `exists_unique_fixedPt`, `readout_eq`,
`no_conditioning` and `not_persistent` depend only on `propext` and `Quot.sound`. Only the conditions "`φ_0` does not evoke" and
"`φ_(1,1)(T2)` evokes" are used by `no_conditioning`; the gap bound `d + 1` is the entry's,
the S1 refuter found the readout equality already holds at `T2 ≥ d` (not proven here).
-/

namespace MathDept.MD_0103

/-- States of a network on `k` internal nodes. -/
abbrev State (k : ℕ) := Fin k → Bool

/-- The two inputs, as source nodes; `(false, false)` is `(0,0)`. -/
abbrev Input := Bool × Bool

variable {k : ℕ}

/-- The input-free update `G = F(·,(0,0))`. -/
def G (F : State k → Input → State k) : State k → State k := fun y => F y (false, false)

/-- The state at the end of a window of length `T` under constant input `u` from `x`. -/
def window (F : State k → Input → State k) (u : Input) (T : ℕ) (x : State k) : State k :=
  (fun y => F y u)^[T] x

/-- The readout trajectory of node `r` on a window: the value after `t + 1` updates. -/
def readout (F : State k → Input → State k) (r : Fin k) (u : Input) (T : ℕ) (x : State k) :
    Fin T → Bool :=
  fun t => (window F u (t.val + 1) x) r

/-- Test readout `φ_v(T2)`: from rest state `xr`, train `v` for `T1`, gap `(0,0)` for `T2`,
test `(0,1)` for `T3`. -/
def testReadout (F : State k → Input → State k) (r : Fin k) (xr : State k) (v : Input)
    (T1 T2 T3 : ℕ) : Fin T3 → Bool :=
  readout F r (false, true) T3 (window F (false, false) T2 (window F v T1 xr))

/-- Pretest readout `φ_0`: the readout under `(0,1)` for `T3` from the rest state. -/
def pretestReadout (F : State k → Input → State k) (r : Fin k) (xr : State k) (T3 : ℕ) :
    Fin T3 → Bool :=
  readout F r (false, true) T3 xr

/-- A Boolean readout trajectory evokes when it equals `1` at some time of its window. -/
def Evokes {T : ℕ} (φ : Fin T → Bool) : Prop := ∃ t, φ t = true

/-- Associative conditioning at `(T1, T2, T3)`, the Protocol's four conditions. -/
def AssociativeConditioning (F : State k → Input → State k) (r : Fin k) (xr : State k)
    (T1 T2 T3 : ℕ) : Prop :=
  ¬ Evokes (pretestReadout F r xr T3) ∧
  Evokes (readout F r (true, false) T3 xr) ∧
  Evokes (testReadout F r xr (true, true) T1 T2 T3) ∧
  ¬ Evokes (testReadout F r xr (true, false) T1 T2 T3) ∧
  ¬ Evokes (testReadout F r xr (false, true) T1 T2 T3)

/-- Persistent associative conditioning: it holds for all sufficiently large gaps. -/
def Persistent (F : State k → Input → State k) (r : Fin k) (xr : State k) (T1 T3 : ℕ) : Prop :=
  ∃ N, ∀ T2, N ≤ T2 → AssociativeConditioning F r xr T1 T2 T3

section Settle

variable (F : State k → Input → State k) (depth : Fin k → ℕ)
  (hloc : ∀ i x y, (∀ j, depth j < depth i → x j = y j) → G F x i = G F y i)

include hloc

/-- Node `i`'s value is independent of the initial state from step `depth i + 1` on. -/
theorem settle : ∀ i x y n, depth i + 1 ≤ n → ((G F)^[n] x) i = ((G F)^[n] y) i := by
  intro i
  induction h : depth i using Nat.strong_induction_on generalizing i with
  | _ m ih =>
    intro x y n hn
    obtain ⟨n', rfl⟩ : ∃ n', n = n' + 1 := ⟨n - 1, by omega⟩
    rw [Function.iterate_succ_apply', Function.iterate_succ_apply']
    apply hloc
    intro j hj
    exact ih (depth j) (by omega) j rfl x y n' (by omega)

/-- Node `i` has settled to its value at step `depth i + 1`. -/
theorem settle_eq (i : Fin k) (x : State k) (n : ℕ) (hn : depth i + 1 ≤ n) :
    ((G F)^[n] x) i = ((G F)^[depth i + 1] x) i := by
  have e : n = (depth i + 1) + (n - (depth i + 1)) := by omega
  rw [e, Function.iterate_add_apply]
  exact settle F depth hloc i _ _ _ (Nat.le_refl _)

variable (d : ℕ) (hd : ∀ i, depth i ≤ d)

include hd

/-- Every trajectory under `(0,0)` reaches `G^[d+1] 0` within `d + 1` steps. -/
theorem reach (x : State k) :
    (G F)^[d + 1] x = (G F)^[d + 1] (fun _ => false) := by
  funext i
  exact settle F depth hloc i x _ (d + 1) (by have := hd i; omega)

/-- The settled state is reached at every step `n ≥ d + 1`. -/
theorem reach_of_le (x : State k) (n : ℕ) (hn : d + 1 ≤ n) :
    (G F)^[n] x = (G F)^[d + 1] (fun _ => false) := by
  have e : n = (d + 1) + (n - (d + 1)) := by omega
  rw [e, Function.iterate_add_apply]
  exact reach F depth hloc d hd _

/-- `G^[d+1] 0` is a fixed point of `G`. -/
theorem isFixed : G F ((G F)^[d + 1] (fun _ => false)) = (G F)^[d + 1] (fun _ => false) := by
  rw [← Function.iterate_succ_apply' (G F), Function.iterate_succ_apply]
  exact reach F depth hloc d hd _

/-- A fixed point of `G` is `G^[d+1] 0`. -/
theorem fixedPt_eq (y : State k) (hy : G F y = y) : y = (G F)^[d + 1] (fun _ => false) := by
  rw [← reach F depth hloc d hd y, Function.iterate_fixed hy]

/-- `G = F(·,(0,0))` has a unique fixed point. -/
theorem exists_unique_fixedPt : ∃! xs : State k, G F xs = xs :=
  ⟨_, isFixed F depth hloc d hd, fun y hy => fixedPt_eq F depth hloc d hd y hy⟩

/-- For every rest state, training input and gap `T2 ≥ d + 1`, `φ_v(T2) = φ_0`. -/
theorem readout_eq (r : Fin k) (xr : State k) (hrest : G F xr = xr) (v : Input)
    (T1 T2 T3 : ℕ) (hT2 : d + 1 ≤ T2) :
    testReadout F r xr v T1 T2 T3 = pretestReadout F r xr T3 := by
  have hgap : window F (false, false) T2 (window F v T1 xr) = xr := by
    rw [fixedPt_eq F depth hloc d hd xr hrest]
    exact reach_of_le F depth hloc d hd _ T2 hT2
  unfold testReadout pretestReadout
  rw [hgap]

/-- No associative conditioning at any gap `T2 ≥ d + 1`. -/
theorem no_conditioning (r : Fin k) (xr : State k) (hrest : G F xr = xr)
    (T1 T2 T3 : ℕ) (hT2 : d + 1 ≤ T2) :
    ¬ AssociativeConditioning F r xr T1 T2 T3 := by
  rintro ⟨h0, -, h11, -, -⟩
  rw [readout_eq F depth hloc d hd r xr hrest (true, true) T1 T2 T3 hT2] at h11
  exact h0 h11

/-- No persistent associative conditioning. -/
theorem not_persistent (r : Fin k) (xr : State k) (hrest : G F xr = xr) (T1 T3 : ℕ) :
    ¬ Persistent F r xr T1 T3 := by
  rintro ⟨N, hN⟩
  exact no_conditioning F depth hloc d hd r xr hrest T1 (N + (d + 1)) T3 (by omega)
    (hN _ (by omega))

/-- **MD_0103, the hashed statement.** Unique fixed point, settling within `d + 1` steps,
readout equality and no (persistent) associative conditioning at gaps `T2 ≥ d + 1`. -/
theorem statement :
    (∃! xs : State k, G F xs = xs) ∧
    (∀ x, (G F)^[d + 1] x = (G F)^[d + 1] (fun _ => false)) ∧
    (∀ r xr, G F xr = xr → ∀ v T1 T2 T3, d + 1 ≤ T2 →
      testReadout F r xr v T1 T2 T3 = pretestReadout F r xr T3) ∧
    (∀ r xr, G F xr = xr → ∀ T1 T2 T3, d + 1 ≤ T2 →
      ¬ AssociativeConditioning F r xr T1 T2 T3) ∧
    (∀ r xr, G F xr = xr → ∀ T1 T3, ¬ Persistent F r xr T1 T3) :=
  ⟨exists_unique_fixedPt F depth hloc d hd,
   reach F depth hloc d hd,
   fun r xr hrest v T1 T2 T3 hT2 => readout_eq F depth hloc d hd r xr hrest v T1 T2 T3 hT2,
   fun r xr hrest T1 T2 T3 hT2 => no_conditioning F depth hloc d hd r xr hrest T1 T2 T3 hT2,
   fun r xr hrest T1 T3 => not_persistent F depth hloc d hd r xr hrest T1 T3⟩

end Settle

end MathDept.MD_0103

