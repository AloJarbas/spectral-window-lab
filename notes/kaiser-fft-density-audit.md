# Kaiser sweep FFT-density audit

The Kaiser sweep already made one good point: `beta` is a real design knob instead of a folklore label. This follow-up asks the next honest numerical question: **how much of that sweep is the window itself, and how much depends on how densely the spectrum is sampled?**

This pass keeps the same `129`-sample Kaiser family and compares a coarse `512`-point spectral probe against a denser `4096`-point probe.

## Main read

- at `beta = 4.0`, the coarse probe is already a little noisy but still close: `|Δ sidelobe| = 0.55 dB`, `|Δ width| = 0.25` bins
- at the repo's named checkpoint `beta = 8.6`, the coarse probe overstates the peak-sidelobe suppression by `4.93 dB` and overstates the main-lobe width by `1.20` bins
- the worst sidelobe mismatch lands at `beta = 14.0`: the coarse probe claims `-115.09 dB`, while the denser probe says `-105.81 dB`
- the worst width mismatch also lands at `beta = 14.0`: the coarse probe says `11.09` bins, while the denser probe says `9.20` bins

## Why this changes the repo

- the first `beta` with at least `1 dB` sidelobe error is `5.0`
- the first `beta` with at least `0.5` bin width error is `7.5`
- that means a coarse FFT grid can invent a fake high-`beta` windfall: the window can look cleaner and broader than the denser read really supports
- ENBW and scalloping do **not** move across this audit because they are direct sums, not sampled-spectrum estimates
- the right lesson is not that Kaiser changed its mind. The lesson is that some spectral metrics need enough zero padding before a plotted tradeoff is numerically honest

## Caveat

This is still a bounded audit of one window length and two FFT sizes. It is enough to expose the measurement failure mode without claiming one universal minimum FFT ratio for every possible window family.

Open `art/window-kaiser-fft-density-audit.png`, `art/window-kaiser-fft-density-audit.csv`, and `notebooks/kaiser_fft_density_audit.ipynb` together next.
