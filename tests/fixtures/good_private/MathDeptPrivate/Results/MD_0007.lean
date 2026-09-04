import Mathlib.Data.Nat.Basic

/-!
# MD_0007: adding zero on the left changes nothing
-/

namespace MathDept.MD_0007

/-- Adding zero on the left is the identity on the naturals. -/
theorem statement (n : Nat) : 0 + n = n := by
  simp

end MathDept.MD_0007
