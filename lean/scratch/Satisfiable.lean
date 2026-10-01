import TrotterOpt

/-! Satisfiability certificates (outside the library; not imported by it).
For every theorem with hypotheses: a Lean-checked example showing those hypotheses can all be met
simultaneously by concrete values. Theorems whose conclusion is `False` assert that their hypotheses
are jointly impossible; for those we certify that every hypothesis but the last is satisfiable,
so the impossibility is not caused by a trivially inconsistent subset. -/

set_option linter.unusedVariables false
set_option linter.unnecessarySeqFocus false
set_option linter.style.longLine false

-- hypotheses of key_poly are satisfiable
example : ∃ (k : ℕ) (t : ℝ) (ht : 0 ≤ t), True :=
by
  refine ⟨0, 0, by norm_num, trivial⟩

-- hypotheses of key_ineq are satisfiable
example : ∃ (k : ℕ) (t : ℝ) (ht : 0 < t), True :=
by
  refine ⟨1, 2, by norm_num, trivial⟩

-- hypotheses of trotter_global_min are satisfiable
example : ∃ (A B x0 x : ℝ) (k : ℕ) (hk : 0 < k) (hB : 0 < B) (hx0 : 0 < x0) (hx : 0 < x) (hdef : x0 ^ (k + 1) = (k : ℝ) * A / B), True :=
by
  refine ⟨1, 1, 1, 1, 1, by norm_num, by norm_num, by norm_num, by norm_num, by norm_num, trivial⟩

-- hypotheses of trotter_opt_value are satisfiable
example : ∃ (A B x0 : ℝ) (k : ℕ) (hk : 0 < k) (hB : 0 < B) (hx0 : 0 < x0) (hdef : x0 ^ (k + 1) = (k : ℝ) * A / B), True :=
by
  refine ⟨1, 1, 1, 1, by norm_num, by norm_num, by norm_num, by norm_num, trivial⟩

-- hypotheses of hoeffding_shots are satisfiable
example : ∃ (S u δ M : ℝ) (hu : 0 < u) (hδ : 0 < δ) (hM : 0 < M) (hS : 4 * Real.log (2 * M / δ) / u ^ 2 ≤ S), True :=
by
  refine ⟨4 * Real.log 2, 1, 1, 1, by norm_num, by norm_num, by norm_num, by norm_num, trivial⟩
