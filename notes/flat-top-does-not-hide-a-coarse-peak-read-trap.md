# Flat-top does not hide a coarse FFT peak-read trap

The task map already gives flat-top the amplitude lane. The remaining honest numerical question was narrower:

- if a tone lands between FFT samples,
- and you only read the largest sampled peak after coherent-gain normalization,
- does flat-top hide a new coarse-grid amplitude error that the earlier scalloping note did not expose?

This sidecar says **no**. The amplitude-specialist lane is already very grid-stable on that specific read.

The study keeps symmetric length `129` windows and sweeps a sampled-peak ladder of `256, 512, 1024, 2048, 4096` points. For each FFT size, it measures the peak-read bias that survives when the tone can sit anywhere between two sampled FFT peaks.

## Main read

- at `256` points, **Blackman** still underreads by as much as `0.273 dB`
- at the same probe, **Blackman-Harris** still underreads by `0.206 dB`
- **flat-top** stays inside `+0.0023 / -0.0000 dB`
- even at `512` points, Blackman-Harris still carries `0.051 dB` of worst-case underread, while flat-top is down at only `+0.0009 dB`

## Why this matters

The earlier amplitude note already said flat-top earns its keep by keeping the main-lobe top very flat. This audit closes the numerical loophole inside that sentence.

A coarse FFT peak read could, in principle, have reopened a practical amplitude error even after the direct scalloping metric said the window was flat. That is **not** what happens here.

Instead the split is cleaner:

- compact windows still lose visible amplitude when the nearest sampled peak misses the true tone
- flat-top mostly does not underread at all on the same sampled peak ladder
- the only visible flat-top wrinkle is a tiny positive hump, not a hidden attenuation cliff

So the amplitude-specialist lane is paying for **ENBW** and **main-lobe width**, not for a second hidden coarse-grid amplitude tax.

## Direct metrics that do not move

- flat-top ENBW stays `3.800` bins and its half-bin scalloping stays `0.0091 dB`
- Blackman-Harris ENBW stays `2.020` bins and its half-bin scalloping stays `0.8128 dB`
- those are direct window properties; the moving part in this audit is only the sampled peak read

## Practical rule for this repo

1. Keep letting flat-top win the isolated-tone amplitude lane on purpose.
2. Do not invent a fake warning that flat-top needs heavy zero-padding before its peak read becomes trustworthy.
3. Keep the real warning attached to flat-top: wide main lobe, large ENBW, poor selectivity when nearby lines matter.

## Scope boundary

This is a bounded peak-reading audit, not a statement about every amplitude estimator, every interpolation method, or every FFT instrument. It only says something narrower and useful: with these windows, the flat-top peak itself is already very hard to fool by coarse sample spacing.
