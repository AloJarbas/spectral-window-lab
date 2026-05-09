from __future__ import annotations

import unittest

from windowlab.metrics import coherent_gain, equivalent_noise_bandwidth_bins, peak_sidelobe_level_db
from windowlab.windows import build_window


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


if __name__ == "__main__":
    unittest.main()
