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
from windowlab.amplitude_density import study_amplitude_fft_density
from windowlab.dual_path import interpolate_dual_windows, study_dual_window_paths
from windowlab.kaiser_density import study_kaiser_fft_density
from windowlab.nuttall_variants import study_nuttall_variant_split
from windowlab.peak_interpolation import study_peak_interpolation
from windowlab.power_peak_interpolation import reproduce_reference_power_scales, study_power_peak_interpolation
from windowlab.overlap import (
    normalized_synthesis_gain_profile,
    overlap_add_summary,
    periodic_overlap_add_profile,
    squared_overlap_add_summary,
)
from windowlab.recommend import TASK_PROFILES, build_task_metrics, rank_windows_for_task
from windowlab.reconstruct import (
    build_reference_signal,
    canonical_dual_window,
    closest_scaled_constant_dual_window,
    compare_dual_windows,
    periodic_same_window_reconstruction,
    periodic_dual_window_reconstruction,
    reconstruction_condition_summary,
    simulated_relative_noise_gain,
)
from windowlab.specialist_density import study_specialist_fft_density
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

    def test_kaiser_fft_density_audit_shows_large_high_beta_error(self) -> None:
        study = study_kaiser_fft_density(length=129, coarse_fft=512, fine_fft=4096, betas=(0.0, 4.0, 8.6, 14.0))
        by_beta = {row.beta: row for row in study.rows}
        self.assertLess(by_beta[4.0].peak_sidelobe_error_db, 1.0)
        self.assertGreater(by_beta[8.6].peak_sidelobe_error_db, 4.0)
        self.assertGreater(by_beta[8.6].main_lobe_width_error_bins, 1.0)
        self.assertGreater(by_beta[14.0].peak_sidelobe_error_db, by_beta[8.6].peak_sidelobe_error_db)

    def test_kaiser_fft_density_audit_keeps_direct_sum_metrics_fixed(self) -> None:
        study = study_kaiser_fft_density(length=129, coarse_fft=512, fine_fft=4096, betas=(8.6,))
        row = study.rows[0]
        self.assertAlmostEqual(row.enbw_bins, equivalent_noise_bandwidth_bins(build_window("kaiser-8.6", 129)), places=12)
        self.assertAlmostEqual(row.scalloping_loss_db, abs(scalloping_loss_db(build_window("kaiser-8.6", 129))), places=12)

    def test_specialist_fft_density_audit_separates_blackman_harris_from_nuttall(self) -> None:
        study = study_specialist_fft_density(length=129, reference_fft=16384, probe_ffts=(512, 2048))
        by_key = {(row.window, row.fft_size): row for row in study.rows}
        blackman_harris_512 = by_key[("blackman-harris", 512)]
        nuttall_512 = by_key[("nuttall", 512)]
        kaiser_512 = by_key[("kaiser-8.6", 512)]
        self.assertLess(blackman_harris_512.peak_sidelobe_error_db, 0.02)
        self.assertLess(blackman_harris_512.main_lobe_width_error_bins, 0.02)
        self.assertGreater(nuttall_512.peak_sidelobe_error_db, 0.2)
        self.assertGreater(nuttall_512.main_lobe_width_error_bins, 0.4)
        self.assertGreater(kaiser_512.peak_sidelobe_error_db, nuttall_512.peak_sidelobe_error_db)

    def test_specialist_fft_density_audit_keeps_direct_sum_metrics_fixed(self) -> None:
        study = study_specialist_fft_density(length=129, reference_fft=16384, probe_ffts=(512,), windows=("blackman-harris", "nuttall"))
        by_key = {row.window: row for row in study.rows}
        self.assertAlmostEqual(
            by_key["blackman-harris"].enbw_bins,
            equivalent_noise_bandwidth_bins(build_window("blackman-harris", 129)),
            places=12,
        )
        self.assertAlmostEqual(
            by_key["nuttall"].scalloping_loss_db,
            abs(scalloping_loss_db(build_window("nuttall", 129))),
            places=12,
        )

    def test_amplitude_fft_density_audit_shows_flat_top_peak_read_is_already_honest(self) -> None:
        study = study_amplitude_fft_density(length=129, probe_ffts=(256, 512), highlight_fft=256)
        by_key = {(row.window, row.fft_size): row for row in study.rows}
        blackman_256 = by_key[("blackman", 256)]
        blackman_harris_256 = by_key[("blackman-harris", 256)]
        flattop_256 = by_key[("flattop", 256)]
        flattop_512 = by_key[("flattop", 512)]

        self.assertGreater(blackman_256.worst_underread_db, 0.25)
        self.assertGreater(blackman_harris_256.worst_underread_db, 0.20)
        self.assertLess(flattop_256.worst_underread_db, 1e-9)
        self.assertLess(flattop_256.worst_overread_db, 0.003)
        self.assertLess(flattop_512.worst_overread_db, flattop_256.worst_overread_db)

    def test_amplitude_fft_density_audit_keeps_window_metrics_fixed(self) -> None:
        study = study_amplitude_fft_density(length=129, probe_ffts=(256,), windows=("flattop",), highlight_fft=256)
        row = study.rows[0]
        self.assertAlmostEqual(row.enbw_bins, equivalent_noise_bandwidth_bins(build_window("flattop", 129)), places=12)
        self.assertAlmostEqual(row.scalloping_loss_db, abs(scalloping_loss_db(build_window("flattop", 129))), places=12)

    def test_peak_interpolation_opens_compact_amplitude_lane(self) -> None:
        study = study_peak_interpolation(length=129, probe_ffts=(256, 512), highlight_fft=256)
        by_key = {(row.window, row.estimator, row.fft_size): row for row in study.rows}
        blackman_sampled = by_key[("blackman", "sampled", 256)]
        blackman_linear = by_key[("blackman", "parabolic-linear", 256)]
        blackman_log = by_key[("blackman", "parabolic-log", 256)]
        blackman_harris_sampled = by_key[("blackman-harris", "sampled", 256)]
        blackman_harris_log = by_key[("blackman-harris", "parabolic-log", 256)]
        flattop_sampled = by_key[("flattop", "sampled", 256)]
        flattop_log = by_key[("flattop", "parabolic-log", 256)]

        self.assertGreater(blackman_sampled.worst_abs_bias_db, 0.25)
        self.assertLess(blackman_linear.worst_abs_bias_db, 0.04)
        self.assertLess(blackman_log.worst_abs_bias_db, 0.006)
        self.assertGreater(blackman_harris_sampled.worst_abs_bias_db, 0.20)
        self.assertLess(blackman_harris_log.worst_abs_bias_db, 0.0025)
        self.assertLess(flattop_sampled.worst_abs_bias_db, 0.003)
        self.assertGreater(flattop_log.worst_abs_bias_db, flattop_sampled.worst_abs_bias_db)
        self.assertLess(blackman_harris_log.enbw_bins, flattop_sampled.enbw_bins)

    def test_power_scaled_interpolation_tightens_compact_windows_without_helping_flattop(self) -> None:
        study = study_power_peak_interpolation(length=129, probe_ffts=(256,), highlight_fft=256)
        by_window = {row.window: row for row in study.rows}
        blackman = by_window["blackman"]
        blackman_harris = by_window["blackman-harris"]
        flattop = by_window["flattop"]

        self.assertLess(blackman.power_worst_abs_bias_db, blackman.log_worst_abs_bias_db)
        self.assertLess(blackman_harris.power_worst_abs_bias_db, blackman_harris.log_worst_abs_bias_db)
        self.assertLess(blackman.power_worst_abs_bias_db, 1e-4)
        self.assertLess(blackman_harris.power_worst_abs_bias_db, 5e-5)
        self.assertGreater(blackman.power_opt_p, 0.12)
        self.assertLess(blackman.power_opt_p, 0.13)
        self.assertGreater(blackman_harris.power_opt_p, 0.08)
        self.assertLess(blackman_harris.power_opt_p, 0.09)
        self.assertGreater(flattop.power_opt_p, 0.99)
        self.assertGreater(flattop.power_worst_abs_bias_db, flattop.sampled_worst_abs_bias_db)

    def test_power_scaled_interpolation_reproduces_reference_window_scales(self) -> None:
        reproduction = reproduce_reference_power_scales()
        by_window = {row.window: row for row in reproduction.rows}
        self.assertAlmostEqual(by_window["blackman"].fitted_p, 0.131, places=3)
        self.assertAlmostEqual(by_window["blackman-harris"].fitted_p, 0.0855, places=4)
        self.assertLess(by_window["blackman"].fitted_worst_abs_bias_db, 0.001)
        self.assertLess(by_window["blackman-harris"].fitted_worst_abs_bias_db, 0.001)

    def test_peak_interpolation_keeps_window_metrics_fixed(self) -> None:
        study = study_peak_interpolation(length=129, probe_ffts=(256,), windows=("blackman-harris",), estimators=("parabolic-log",), highlight_fft=256)
        row = study.rows[0]
        self.assertAlmostEqual(row.enbw_bins, equivalent_noise_bandwidth_bins(build_window("blackman-harris", 129)), places=12)
        self.assertAlmostEqual(row.scalloping_loss_db, abs(scalloping_loss_db(build_window("blackman-harris", 129))), places=12)

    def test_nuttall_alias_matches_min4_bh_variant(self) -> None:
        alias = build_window("nuttall", 129)
        explicit = build_window("nuttall-min4-bh", 129)
        continuous = build_window("nuttall-continuous", 129)
        for expected, actual in zip(alias, explicit):
            self.assertAlmostEqual(expected, actual, places=12)
        self.assertGreater(sum(abs(a - b) for a, b in zip(alias, continuous)), 1e-4)

    def test_nuttall_variant_split_separates_first_sidelobe_from_far_tail(self) -> None:
        study = study_nuttall_variant_split(length=129, fft_size=16384)
        rows = {row.window: row for row in study.rows}
        blackman_harris = rows["blackman-harris"]
        min4 = rows["nuttall-min4-bh"]
        continuous = rows["nuttall-continuous"]

        self.assertLess(min4.peak_sidelobe_db, blackman_harris.peak_sidelobe_db)
        self.assertLess(min4.peak_sidelobe_db, continuous.peak_sidelobe_db)
        self.assertLess(min4.max_6_12_db, continuous.max_6_12_db)
        self.assertLess(continuous.max_24_48_db, min4.max_24_48_db - 10.0)
        self.assertLess(continuous.max_24_48_db, blackman_harris.max_24_48_db)

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

    def test_task_map_picks_explicit_min4_nuttall_for_weak_spur_next_to_strong_line(self) -> None:
        rows = build_task_metrics()
        task = next(task for task in TASK_PROFILES if task.key == "weak_near_strong")
        rankings = rank_windows_for_task(rows, task)
        best = next(ranking for ranking in rankings if ranking.eligible)
        self.assertEqual(best.window, "nuttall-min4-bh")

    def test_task_map_picks_continuous_nuttall_for_farther_out_weak_spur(self) -> None:
        rows = build_task_metrics()
        task = next(task for task in TASK_PROFILES if task.key == "weak_far_strong")
        rankings = rank_windows_for_task(rows, task)
        best = next(ranking for ranking in rankings if ranking.eligible)
        self.assertEqual(best.window, "nuttall-continuous")

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

    def test_same_window_reconstruction_is_exact_when_denominator_stays_positive(self) -> None:
        signal = build_reference_signal(1024)
        run = periodic_same_window_reconstruction(signal, build_window("hann", 128), 32)
        self.assertLess(run.rmse, 1e-12)
        self.assertLess(run.max_abs_error, 1e-11)

    def test_rectangular_integer_hop_has_flat_conditioning(self) -> None:
        summary = reconstruction_condition_summary(build_window("rectangular", 128), 64)
        self.assertAlmostEqual(summary.min_denominator_fraction, 1.0, places=12)
        self.assertAlmostEqual(summary.rms_relative_noise_gain, 1.0, places=12)
        self.assertAlmostEqual(summary.worst_relative_noise_gain, 1.0, places=12)

    def test_flattop_quarter_hop_is_less_calm_than_hamming(self) -> None:
        flattop = reconstruction_condition_summary(build_window("flattop", 128), 32)
        hamming = reconstruction_condition_summary(build_window("hamming", 128), 32)
        self.assertGreater(flattop.worst_relative_noise_gain, 1.3)
        self.assertLess(hamming.worst_relative_noise_gain, 1.05)
        self.assertGreater(flattop.worst_relative_noise_gain, hamming.worst_relative_noise_gain)

    def test_flattop_becomes_calmer_at_eighth_hop(self) -> None:
        quarter = reconstruction_condition_summary(build_window("flattop", 128), 32)
        eighth = reconstruction_condition_summary(build_window("flattop", 128), 8)
        self.assertLess(eighth.rms_relative_noise_gain, quarter.rms_relative_noise_gain)
        self.assertLess(eighth.worst_relative_noise_gain, quarter.worst_relative_noise_gain)

    def test_simulated_noise_gain_matches_profile_prediction(self) -> None:
        summary = reconstruction_condition_summary(build_window("blackman-harris", 128), 32)
        simulated = simulated_relative_noise_gain(build_window("blackman-harris", 128), 32, periods=64, coefficient_noise_std=1e-6, seed=11)
        self.assertAlmostEqual(simulated, summary.rms_relative_noise_gain, delta=0.03)

    def test_canonical_dual_matches_same_window_normalized_reconstruction(self) -> None:
        signal = build_reference_signal(1024)
        analysis = build_window("hann", 128)
        canonical = canonical_dual_window(analysis, 32)
        normalized = periodic_same_window_reconstruction(signal, analysis, 32)
        dual = periodic_dual_window_reconstruction(signal, analysis, canonical, 32)
        self.assertLess(dual.rmse, 1e-12)
        self.assertLess(max(abs(left - right) for left, right in zip(normalized.reconstructed, dual.reconstructed)), 1e-12)

    def test_closest_scaled_constant_dual_reconstructs_exactly(self) -> None:
        signal = build_reference_signal(1024)
        analysis = build_window("blackman-harris", 128)
        dual, scale = closest_scaled_constant_dual_window(analysis, 32)
        self.assertGreater(scale, 0.0)
        run = periodic_dual_window_reconstruction(signal, analysis, dual, 32)
        self.assertLess(run.rmse, 1e-12)
        self.assertLess(max(abs(value - 1.0) for value in run.denominator), 1e-12)

    def test_closest_constant_dual_is_flatter_but_noisier_than_canonical(self) -> None:
        comparison = compare_dual_windows(build_window("flattop", 128), 32)
        self.assertLess(
            comparison.closest_constant.relative_constant_rmse,
            comparison.canonical.relative_constant_rmse,
        )
        self.assertGreater(
            comparison.closest_constant.rms_noise_gain,
            comparison.canonical.rms_noise_gain,
        )
        self.assertGreater(
            comparison.closest_constant.l2_energy,
            comparison.canonical.l2_energy,
        )

    def test_interpolated_dual_window_stays_exact(self) -> None:
        signal = build_reference_signal(1024)
        analysis = build_window("blackman-harris", 128)
        canonical = canonical_dual_window(analysis, 32)
        closest_constant, _ = closest_scaled_constant_dual_window(analysis, 32)
        midpoint = interpolate_dual_windows(canonical, closest_constant, 0.5)
        run = periodic_dual_window_reconstruction(signal, analysis, midpoint, 32)
        self.assertLess(run.rmse, 1e-12)
        self.assertLess(max(abs(value - 1.0) for value in run.denominator), 1e-12)

    def test_blackman_harris_quarter_hop_has_useful_midpoint_tradeoff(self) -> None:
        rows = study_dual_window_paths()
        midpoint = next(row for row in rows if row.name == "blackman-harris" and row.hop == 32 and row.mix == 0.5)
        self.assertLess(midpoint.flatness_gap_fraction, 0.35)
        self.assertLess(midpoint.noise_ratio_to_canonical, 1.15)

    def test_flattop_half_overlap_midpoint_stays_absolutely_bad(self) -> None:
        rows = study_dual_window_paths()
        midpoint = next(row for row in rows if row.name == "flattop" and row.hop == 64 and row.mix == 0.5)
        self.assertGreater(midpoint.relative_constant_rmse, 4.0)
        self.assertGreater(midpoint.rms_noise_gain, 6.9)


if __name__ == "__main__":
    unittest.main()
