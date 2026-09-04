import MathDept
import Lean
open Lean Elab Command Meta

def allowedAxioms : List Name := [``propext, ``Classical.choice, ``Quot.sound]

def enforced (m : Name) : Bool :=
  (`MathDept.Results).isPrefixOf m || (`MathDept.Defs).isPrefixOf m || m == `MathDept.Smoke

def readAllowlist (path : System.FilePath) : IO (List (Name × Name)) := do
  let txt ← IO.FS.readFile path
  return txt.splitOn "\n" |>.filterMap fun l =>
    let l := l.trim
    if l.isEmpty || l.startsWith "#" then none else
    match l.splitOn " " |>.filter (· ≠ "") with
    | [d, a] => some (d.toName, a.toName)
    | _ => none

run_cmd do
  let env ← getEnv
  let allow ← readAllowlist "audit/axiom-allowlist.txt"
  let mut bad : Array String := #[]
  for i in [0:env.header.moduleNames.size] do
    let mod := env.header.moduleNames[i]!
    unless (`MathDept).isPrefixOf mod do continue
    for n in env.header.moduleData[i]!.constNames do
      if n.isInternalDetail then continue
      let axs ← collectAxioms n
      let ty ← liftTermElabM do
        let ci ← getConstInfo n
        return toString (← Meta.ppExpr ci.type)
      IO.println (Json.compress <| Json.mkObj
        [("decl", toString n), ("module", toString mod),
         ("axioms", toJson (axs.map toString)), ("type", ty)])
      if enforced mod then
        for a in axs do
          unless allowedAxioms.contains a || allow.contains (n, a) do
            bad := bad.push s!"{n} depends on {a} (module {mod})"
  unless bad.isEmpty do
    throwError s!"axiom audit FAILED:\n{"\n".intercalate bad.toList}"
