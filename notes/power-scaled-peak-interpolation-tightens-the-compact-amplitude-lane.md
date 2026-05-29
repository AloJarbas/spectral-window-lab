# Power-scaled peak interpolation tightens the compact amplitude lane

The previous sidecar already showed that a tiny 3-point log parabola changes the amplitude ranking. The next honest question was whether window-tuned power scaling changes it again, or only replays the same result with fancier notation.

It changes it again — but only for the compact windows.

## External source triage that survived this pass

### Accepted

1. **DSPRelated / Spectral Audio Signal Processing — Quadratic Interpolation of Spectral Peaks**
   Accepted because it gives the clean three-sample parabola formulas and the right local-shape justification without forcing this repo to depend on a dead fetch path.
2. **DAFx 2021 companion page for Caetano & Depalle**
   Accepted because it exposes usable optimum power-scale tables and error comparisons for Blackman and Blackman-Harris instead of vague “power scaling can help” prose.
3. **MathWorks `flattopwin` docs**
   Accepted because they keep the flat-top role honest: amplitude-calibration use, explicit coefficients, and the bandwidth bill.
4. **SciPy `signal.windows.flattop` docs**
   Accepted as a secondary implementation check because they independently repeat the amplitude-measurement framing and fifth-order cosine form.

### Rejected

1. **MDPI direct fetch of Werner & Germain 2016**
   Rejected for direct use in this pass because the extractor did not return readable content.
2. **CCRMA direct fetch path**
   Rejected as the working fetch target because it failed live; the DSPRelated mirror carried the same teaching point cleanly enough.
3. **ResearchGate / secondary PDF mirrors**
   Rejected as primary sources because the companion page and direct implementation checks were cleaner and more stable.

## What the fitted power scale actually does

- at `256` points, **Blackman** goes from `0.273 dB` raw to `0.0050 dB` with the log parabola and then to `0.000010 dB` with fitted power scaling at `p ≈ 0.126`
- **Blackman-Harris** goes from `0.206 dB` raw to `0.0019 dB` log and then to `0.000002 dB` at `p ≈ 0.084`
- **flat-top** stays the odd one out: the raw sampled peak is already inside `0.0023 dB`, while the fitted search runs to `p ≈ 1.000` and still lands worse at `0.0134 dB`

So the new split is sharper than I expected:

- power scaling really does collapse the remaining bounded amplitude error for Blackman and Blackman-Harris
- flat-top does not join that win; its amplitude-specialist lane is still the zero-extra-work sampled peak
- the power-scaled family behaves like a calibration step for compact windows, not a universal upgrade for every window

## Literature cross-check

The cleanest external sanity check available in this pass was the DAFx 2021 companion table of optimum `p` values.

- for matched `M=N=512`, the brute-force reproduction here lands at `p ≈ 0.131` for **Blackman** against the companion value `0.13058`
- for matched `M=N=512`, it lands at `p ≈ 0.0855` for **Blackman-Harris** against `0.08553`

That does not prove every detail of the literature, but it is a strong enough match to trust the local implementation and to treat the 129-point repo values as the same family story rather than a coding accident.

## Practical rule for this repo now

1. Keep **flat-top** for the no-extra-processing amplitude lane.
2. Keep **Blackman-Harris + 3-point log interpolation** as the compact default when you want most of the gain with almost no tuning burden.
3. Add **Blackman-Harris + fitted power scaling** as the calibrated high-precision compact lane when a window-specific `p` is acceptable.
4. Do not bother power-scaling flat-top in this bounded isolated-tone setup; the raw sampled peak is already the better answer.

## Next honest experiment

Stop the noiseless-estimator race here. The next move that could actually change the practical rule is not another local fit. It is a sensitivity pass: how much amplitude accuracy survives when `p` is slightly wrong, the tone is noisy, or a nearby weak line is present.
