import Mathlib.Analysis.SpecialFunctions.Log.Basic
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring
import Mathlib.Tactic.Positivity
import Mathlib.Tactic.NormNum

/-!
# Noise-limited optimal Trotter depth — formal checks

Machine-checked versions of the two closed-form facts the tutorial relies on.

1. `key_ineq` / `trotter_global_min` / `trotter_opt_value`:
   for `E(x) = A / x^k + B x` with `A, B > 0`, `k ≥ 1` a natural number, the point
   `x0` with `x0^(k+1) = k A / B` is a GLOBAL minimiser over `x > 0`, and
   `E(x0) = ((k+1)/k) · B · x0`.

2. `hoeffding_shots`: the simultaneous difference-of-means budget algebra.
   If `S ≥ 4 log(2M/δ) / u^2`, then `2M exp(-S u^2 / 4) ≤ δ`.
   This checks only the algebra; Hoeffding's inequality and the probability
   union bound themselves are cited, not formalised here.
-/

open Real

/-- Core polynomial inequality: `(k+1) t^k ≤ 1 + k t^(k+1)` for `t ≥ 0`. -/
theorem key_poly (k : ℕ) (t : ℝ) (ht : 0 ≤ t) :
    ((k : ℝ) + 1) * t ^ k ≤ 1 + (k : ℝ) * t ^ (k + 1) := by
  induction k with
  | zero => simp
  | succ n ih =>
    -- (t - 1)(t^(n+1) - 1) ≥ 0 for t ≥ 0
    have hprod : 0 ≤ (t - 1) * (t ^ (n + 1) - 1) := by
      rcases le_total 1 t with h1 | h1
      · have : 1 ≤ t ^ (n + 1) := one_le_pow₀ h1
        exact mul_nonneg (by linarith) (by linarith)
      · have : t ^ (n + 1) ≤ 1 := pow_le_one₀ ht h1
        exact mul_nonneg_of_nonpos_of_nonpos (by linarith) (by linarith)
    have hih : 0 ≤ t * (1 + (n : ℝ) * t ^ (n + 1) - ((n : ℝ) + 1) * t ^ n) :=
      mul_nonneg ht (by linarith)
    push_cast
    have e1 : t ^ (n + 1 + 1) = t * t ^ (n + 1) := by ring
    have e2 : t ^ (n + 1) = t * t ^ n := by ring
    nlinarith [hprod, hih, e1, e2]

/-- Scaled form: `1 / t^k + k t ≥ 1 + k` for `t > 0`. -/
theorem key_ineq (k : ℕ) (t : ℝ) (ht : 0 < t) :
    1 + (k : ℝ) ≤ 1 / t ^ k + (k : ℝ) * t := by
  have htk : 0 < t ^ k := pow_pos ht k
  have h := key_poly k t ht.le
  rw [div_add' _ _ _ htk.ne', le_div_iff₀ htk]
  have e : t ^ (k + 1) = t ^ k * t := pow_succ t k
  nlinarith [h, e]

/-- The stationary point `x0` (with `x0^(k+1) = kA/B`) is a global minimiser of
`E(x) = A/x^k + B x` on `x > 0`. -/
theorem trotter_global_min (A B x0 x : ℝ) (k : ℕ) (hk : 0 < k)
    (hB : 0 < B) (hx0 : 0 < x0) (hx : 0 < x)
    (hdef : x0 ^ (k + 1) = (k : ℝ) * A / B) :
    A / x0 ^ k + B * x0 ≤ A / x ^ k + B * x := by
  have hkR : (0 : ℝ) < k := by exact_mod_cast hk
  have hx0k : 0 < x0 ^ k := pow_pos hx0 k
  -- A = B x0^(k+1) / k
  have hA : A = B * x0 ^ (k + 1) / k := by
    field_simp; rw [hdef]; field_simp
  set t := x / x0 with ht_def
  have ht : 0 < t := div_pos hx hx0
  have hxt : x = t * x0 := by rw [ht_def]; field_simp
  have key := key_ineq k t ht
  -- rewrite both sides in terms of c = B x0 / k
  have hL : A / x0 ^ k + B * x0 = (B * x0 / k) * (1 + k) := by
    rw [hA, pow_succ]; field_simp
  have hR : A / x ^ k + B * x = (B * x0 / k) * (1 / t ^ k + k * t) := by
    rw [hA, hxt, mul_pow, pow_succ]
    have htk : 0 < t ^ k := pow_pos ht k
    field_simp
  rw [hL, hR]
  have hc : 0 < B * x0 / k := div_pos (mul_pos hB hx0) hkR
  exact mul_le_mul_of_nonneg_left key hc.le

/-- Optimal value: `E(x0) = ((k+1)/k) · B · x0`. -/
theorem trotter_opt_value (A B x0 : ℝ) (k : ℕ) (hk : 0 < k)
    (hB : 0 < B) (hx0 : 0 < x0)
    (hdef : x0 ^ (k + 1) = (k : ℝ) * A / B) :
    A / x0 ^ k + B * x0 = ((k : ℝ) + 1) / k * B * x0 := by
  have hkR : (0 : ℝ) < k := by exact_mod_cast hk
  have hx0k : 0 < x0 ^ k := pow_pos hx0 k
  have hA : A = B * x0 ^ (k + 1) / k := by
    field_simp; rw [hdef]; field_simp
  rw [hA, pow_succ]; field_simp; ring

/-- Algebra for Theorem 2: the union-bound tail for M differences of means. -/
theorem hoeffding_shots (S u δ M : ℝ) (hu : 0 < u) (hδ : 0 < δ)
    (hM : 0 < M) (hS : 4 * Real.log (2 * M / δ) / u ^ 2 ≤ S) :
    2 * M * Real.exp (-(S * u ^ 2 / 4)) ≤ δ := by
  have hu2 : 0 < u ^ 2 := pow_pos hu 2
  have h1 : Real.log (2 * M / δ) ≤ S * u ^ 2 / 4 := by
    rw [div_le_iff₀ hu2] at hS; linarith
  have h2 : Real.exp (-(S * u ^ 2 / 4)) ≤ Real.exp (-(Real.log (2 * M / δ))) :=
    Real.exp_le_exp.mpr (by linarith)
  rw [Real.exp_neg (Real.log (2 * M / δ)), Real.exp_log (by positivity), inv_div] at h2
  calc
    2 * M * Real.exp (-(S * u ^ 2 / 4)) ≤ 2 * M * (δ / (2 * M)) :=
      mul_le_mul_of_nonneg_left h2 (by positivity)
    _ = δ := by field_simp

#print axioms key_poly
#print axioms key_ineq
#print axioms trotter_global_min
#print axioms trotter_opt_value
#print axioms hoeffding_shots
