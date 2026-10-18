import sys
import unittest
from pathlib import Path

EXPERIMENTS_ROOT = Path(__file__).resolve().parents[1]
if str(EXPERIMENTS_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS_ROOT))

from discrete_noise_accounting.centered_binomial_accountant import ComposedPrivacyProfile, account
from discrete_noise_accounting.fixed_norm_pattern_accounting import (
    account_full_envelope,
    account_pattern,
    compose_profiles,
    feasible_patterns,
)


class FixedNormPatternTests(unittest.TestCase):
    def test_feasible_patterns_follow_the_fixed_bound(self) -> None:
        patterns = feasible_patterns()
        self.assertIn((4, 0), patterns)
        self.assertIn((0, 8), patterns)
        self.assertIn((2, 4), patterns)
        self.assertNotIn((5, 0), patterns)
        self.assertNotIn((4, 1), patterns)
        self.assertNotIn((0, 0), patterns)
        for a, b in patterns:
            self.assertLessEqual(a, 4)
            self.assertLessEqual(2 * a + b, 8)
        self.assertEqual(len(patterns), sum(8 - 2 * a + 1 for a in range(5)) - 1)

    def test_composing_two_profiles_matches_one_profile_with_summed_compositions(self) -> None:
        left = ComposedPrivacyProfile(k=16, shift=2, compositions=3)
        right = ComposedPrivacyProfile(k=16, shift=2, compositions=5)
        direct = ComposedPrivacyProfile(k=16, shift=2, compositions=8)
        composed = compose_profiles(left, right)
        for epsilon in (1.0, 4.0, 8.0):
            self.assertAlmostEqual(composed.delta_upper(epsilon), direct.delta_upper(epsilon), places=9)
        # The two factors are rounded to the grid separately, so agreement is to grid precision, not bit-exact.
        self.assertLess(abs(composed.epsilon_for_delta(1e-5) - direct.epsilon_for_delta(1e-5)), 1e-4)

    def test_all_shift2_pattern_reproduces_primary_accountant(self) -> None:
        primary = account(k=16, integer_shift=2, dimension=4, rounds=10, target_delta=1e-5, grid_step=0.002, numerical_guard=1e-10)
        pattern = account_pattern(a=4, b=0, rounds=10, k=16, target_delta=1e-5, grid_step=0.002, numerical_guard=1e-10)
        self.assertAlmostEqual(pattern.epsilon_upper, primary.epsilon_upper, places=6)

    def test_all_shift2_pattern_is_the_worst_case_for_one_round(self) -> None:
        results = [
            account_pattern(a=a, b=b, rounds=1, k=16, target_delta=1e-5, grid_step=0.002, numerical_guard=1e-10)
            for a, b in feasible_patterns()
        ]
        self.assertTrue(all(r.finite_epsilon_available for r in results))
        worst = max(results, key=lambda r: r.epsilon_upper)
        self.assertEqual((worst.shift2_coordinates, worst.shift1_coordinates), (4, 0))

    def test_full_displacement_envelope_loses_finite_epsilon_in_high_dimension(self) -> None:
        low = account_full_envelope(dimension=4, rounds=10, k=16, target_delta=1e-5)
        high = account_full_envelope(dimension=1991, rounds=20, k=16, target_delta=1e-5)
        self.assertTrue(low.finite_epsilon_available)
        self.assertFalse(high.finite_epsilon_available)
        self.assertGreater(high.unavoidable_delta_floor, 1e-5)


if __name__ == "__main__":
    unittest.main()
