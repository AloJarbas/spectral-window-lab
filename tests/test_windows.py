from __future__ import annotations

import unittest

from windowlab.metrics import (
    coherent_gain,
    coherent_gain_normalized_response,
    equivalent_noise_bandwidth_bins,
    null_to_null_main_lobe_width,
    peak_sidelobe_level_db,
    scalloping_loss_db,
)
from windowlab.overlap import (
    normalized_synthesis_gain_profile,
    overlap_add_summary,
    periodic_overlap_add_profile,
    squared_overlap_add_summary,
)
from windowlab.recommend import TASK_PROFILES, build_task_metrics, rank_windows_for_task
from windowlab.windows import KAISER_BETA_86, build_window, kaiser


class WindowTests(unittest.TestCase):
    def test_hann_tapers_to_zero(self) -> None:
        window = build_window("hann", 33)
        self.assertAlmostEqual(window[0], 0.0, places=9)
        self.assertAlmostEqual(window[-1], 0.0, places=9)

    def test_hamming_edges_stay_positive(self) -> None:
        window = build_window("hamming", 33)
        self.assertGreater(window[0], 0.0)
        self.assertGreater(window[-1], 0.0)

    def test_coherent_gain_order(self) -> None:
        size = 129
        gains = {
            name: coherent_gain(build_window(name, size))
            for name in ["blackman", "hann", "hamming", "rectangular"]
        }
        self.assertLess(gains["blackman"], gains["hann"])
        self.assertLess(gains["hann"], gains["hamming"])
        self.assertLess(gains["hamming"], gains["rectangular"])

    def test_enbw_order(self) -> None:
        size = 129
        enbw = {
            name: equivalent_noise_bandwidth_bins(build_window(name, size))
            for name in ["rectangular", "hamming", "hann", "blackman"]
        }
        self.assertLess(enbw["rectangular"], enbw["hamming"])
        self.assertLess(enbw["hamming"], enbw["hann"])
        self.assertLess(enbw["hann"], enbw["blackman"])

    def test_sidelobe_order(self) -> None:
        size = 129
        sidelobes = {
            name: peak_sidelobe_level_db(build_window(name, size), fft_size=2048)
            for name in ["rectangular", "hann", "hamming", "blackman"]
        }
        self.assertLess(sidelobes["hann"], sidelobes["rectangular"])
        self.assertLess(sidelobes["hamming"], sidelobes["hann"])
        self.assertLess(sidelobes["blackman"], sidelobes["hamming"])

    def test_kaiser_matches_expected_shape(self) -> None:
        window = build_window("kaiser-8.6", 33)
        self.assertAlmostEqual(window[0], 0.0013325143, places=9)
        self.assertAlmostEqual(window[16], 1.0, places=9)
        self.assertAlmostEqual(window[-1], 0.0013325143, places=9)

    def test_kaiser_rejects_negative_beta(self) -> None:
        with self.assertRaises(ValueError):
            kaiser(33, -0.1)

    def test_kaiser_beta_zero_matches_rectangular(self) -> None:
        rectangular = build_window("rectangular", 33)
        beta_zero = kaiser(33, 0.0)
        for expected, actual in zip(rectangular, beta_zero):
            self.assertAlmostEqual(expected, actual, places=12)

    def test_kaiser_beta_86_has_blackman_like_enbw(self) -> None:
        size = 129
        kaiser_enbw = equivalent_noise_bandwidth_bins(build_window("kaiser-8.6", size))
        blackman_enbw = equivalent_noise_bandwidth_bins(build_window("blackman", size))
        self.assertGreater(kaiser_enbw, 1.6)
        self.assertLess(abs(kaiser_enbw - blackman_enbw), 0.08)
        self.assertEqual(KAISER_BETA_86, 8.6)

    def test_response_at_zero_offset_is_unity(self) -> None:
        response = coherent_gain_normalized_response(build_window("hann", 129), 0.0)
        self.assertAlmostEqual(response, 1.0, places=12)

    def test_scalloping_loss_order(self) -> None:
        size = 129
        losses = {
            name: scalloping_loss_db(build_window(name, size))
            for name in ["rectangular", "hamming", "hann", "blackman", "kaiser-8.6"]
        }
        self.assertLess(losses["rectangular"], losses["hamming"])
        self.assertLess(losses["hamming"], losses["hann"])
        self.assertLess(losses["hann"], losses["blackman"])
        self.assertLess(abs(losses["kaiser-8.6"] - losses["blackman"]), 0.05)

    def test_flattop_is_amplitude_specialist_not_default(self) -> None:
        size = 129
        flattop = build_window("flattop", size)
        blackman = build_window("blackman", size)

        self.assertLess(abs(scalloping_loss_db(flattop)), 0.05)
        self.assertGreater(
            equivalent_noise_bandwidth_bins(flattop),
            2.0 * equivalent_noise_bandwidth_bins(blackman),
        )
        self.assertGreater(
            null_to_null_main_lobe_width(flattop, fft_size=2048),
            1.5 * null_to_null_main_lobe_width(blackman, fft_size=2048),
        )
        self.assertLess(coherent_gain(flattop), coherent_gain(blackman))

    def test_blackman_harris_and_nuttall_are_deep_sidelobe_specialists(self) -> None:
        size = 129
        blackman = build_window("blackman", size)
        kaiser_86 = build_window("kaiser-8.6", size)
        blackman_harris = build_window("blackman-harris", size)
        nuttall = build_window("nuttall", size)
        flattop = build_window("flattop", size)

        self.assertAlmostEqual(blackman_harris[size // 2], 1.0, places=12)
        self.assertAlmostEqual(nuttall[size // 2], 1.0, places=12)

        self.assertLess(
            peak_sidelobe_level_db(blackman_harris, fft_size=2048),
            peak_sidelobe_level_db(blackman, fft_size=2048),
        )
        self.assertLess(
            peak_sidelobe_level_db(nuttall, fft_size=2048),
            peak_sidelobe_level_db(blackman_harris, fft_size=2048),
        )

        self.assertGreater(
            equivalent_noise_bandwidth_bins(blackman_harris),
            equivalent_noise_bandwidth_bins(blackman),
        )
        self.assertGreater(
            equivalent_noise_bandwidth_bins(nuttall),
            equivalent_noise_bandwidth_bins(kaiser_86),
        )

        self.assertLess(abs(scalloping_loss_db(blackman_harris)), abs(scalloping_loss_db(blackman)))
        self.assertLess(abs(scalloping_loss_db(nuttall)), abs(scalloping_loss_db(blackman)))
        self.assertGreater(abs(scalloping_loss_db(blackman_harris)), abs(scalloping_loss_db(flattop)))
        self.assertGreater(abs(scalloping_loss_db(nuttall)), abs(scalloping_loss_db(flattop)))

    def test_kaiser_tradeoffs_move_monotonically_with_beta(self) -> None:
        size = 129
        betas = [0.0, 5.0, 8.6, 14.0]
        windows = [kaiser(size, beta) for beta in betas]
        enbw = [equivalent_noise_bandwidth_bins(window) for window in windows]
        main_lobe = [null_to_null_main_lobe_width(window, fft_size=2048) for window in windows]
        sidelobes = [peak_sidelobe_level_db(window, fft_size=2048) for window in windows]

        self.assertEqual(enbw, sorted(enbw))
        self.assertEqual(main_lobe, sorted(main_lobe))
        self.assertEqual(sidelobes, sorted(sidelobes, reverse=True))

    def test_rectangular_overlap_add_is_exact_for_integer_hops(self) -> None:
        profile = periodic_overlap_add_profile(build_window("rectangular", 128), 64)
        self.assertTrue(all(value == profile[0] for value in profile))

    def test_blackman_needs_smaller_hop_than_half_overlap(self) -> None:
        half_overlap = overlap_add_summary(build_window("blackman", 128), 64)
        quarter_hop = overlap_add_summary(build_window("blackman", 128), 32)
        self.assertGreater(half_overlap.max_deviation_fraction, 0.15)
        self.assertLess(quarter_hop.max_deviation_fraction, 0.001)

    def test_flattop_stays_less_flat_than_hann_at_quarter_hop(self) -> None:
        flattop = overlap_add_summary(build_window("flattop", 128), 32)
        hann = overlap_add_summary(build_window("hann", 128), 32)
        self.assertGreater(flattop.max_deviation_fraction, 0.03)
        self.assertLess(hann.max_deviation_fraction, 0.002)

    def test_blackman_harris_quarter_hop_raw_sum_can_hide_weighted_ripple(self) -> None:
        raw = overlap_add_summary(build_window("blackman-harris", 128), 32)
        squared = squared_overlap_add_summary(build_window("blackman-harris", 128), 32)
        self.assertLess(raw.max_deviation_fraction, 0.001)
        self.assertGreater(squared.max_deviation_fraction, 0.05)

    def test_hann_quarter_hop_squared_sum_is_flatter_than_raw_sum(self) -> None:
        raw = overlap_add_summary(build_window("hann", 128), 32)
        squared = squared_overlap_add_summary(build_window("hann", 128), 32)
        self.assertLess(squared.max_deviation_fraction, raw.max_deviation_fraction)

    def test_flattop_quarter_hop_needs_large_synthesis_gain_swing(self) -> None:
        gain_profile = normalized_synthesis_gain_profile(build_window("flattop", 128), 32)
        gains = [value for _, value in gain_profile]
        self.assertGreater(max(gains), 1.4)
        self.assertLess(min(gains), 0.7)

    def test_task_map_picks_rectangular_for_close_equal_strength_tones(self) -> None:
        rows = build_task_metrics()
        task = next(task for task in TASK_PROFILES if task.key == "close_tones")
        rankings = rank_windows_for_task(rows, task)
        best = next(ranking for ranking in rankings if ranking.eligible)
        self.assertEqual(best.window, "rectangular")

    def test_task_map_picks_kaiser_for_compact_low_sidelobe_compromise(self) -> None:
        rows = build_task_metrics()
        task = next(task for task in TASK_PROFILES if task.key == "compact_compromise")
        rankings = rank_windows_for_task(rows, task)
        best = next(ranking for ranking in rankings if ranking.eligible)
        self.assertEqual(best.window, "kaiser-8.6")

    def test_task_map_picks_nuttall_for_weak_spur_next_to_strong_line(self) -> None:
        rows = build_task_metrics()
        task = next(task for task in TASK_PROFILES if task.key == "weak_near_strong")
        rankings = rank_windows_for_task(rows, task)
        best = next(ranking for ranking in rankings if ranking.eligible)
        self.assertEqual(best.window, "nuttall")

    def test_task_map_picks_flattop_for_isolated_tone_amplitude(self) -> None:
        rows = build_task_metrics()
        task = next(task for task in TASK_PROFILES if task.key == "amplitude")
        rankings = rank_windows_for_task(rows, task)
        best = next(ranking for ranking in rankings if ranking.eligible)
        self.assertEqual(best.window, "flattop")

    def test_task_map_picks_hamming_for_quarter_hop_stft_lane(self) -> None:
        rows = build_task_metrics()
        task = next(task for task in TASK_PROFILES if task.key == "stft_qhop")
        rankings = rank_windows_for_task(rows, task)
        best = next(ranking for ranking in rankings if ranking.eligible)
        self.assertEqual(best.window, "hamming")


if __name__ == "__main__":
    unittest.main()
