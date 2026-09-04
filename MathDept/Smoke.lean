import Mathlib

/-!
# Smoke test
Proves that Mathlib is wired, the cache applied, and the toolchain matches. If `lake build`
starts printing `Building Mathlib.…` on this file, the cache did not apply: stop and rerun
`lake exe cache get`.
-/

/-- Smoke test: a Mathlib theorem resolves by name. -/
theorem MathDept.smoke : Irrational (Real.sqrt 2) := irrational_sqrt_two

example (n : ℕ) : n + 0 = n := by simp
