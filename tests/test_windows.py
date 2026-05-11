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


if __name__ == "__main__":
    unittest.main()
