# Three-point log peak interpolation opens a compact amplitude lane

The previous amplitude audit answered one narrow question: if you only read the largest sampled FFT peak, does flat-top hide a coarse-grid trap? It did not.

This follow-up asks the practical next question:

- keep the same windows,
- keep the same coarse FFT peak grid,
- but allow one tiny local estimator around the peak instead of stopping at the biggest sampled bin.

That changes the story more than I expected.

## The three bounded reads

1. **sampled peak**: just take the biggest sampled magnitude
2. **3-point parabola on magnitude**: fit a quadratic through the three local magnitudes
3. **3-point parabola on log magnitude**: fit the same parabola after taking `log |X[k]|`

The last one is still tiny. It only uses the peak bin and its two neighbors. But it bends the practical ranking.

## Main read at the coarsest probe

- at `256` points, **Blackman** falls from `0.273 dB` worst-case bias on the raw sampled peak to `0.031 dB` with a linear parabola and `0.0050 dB` with a log parabola
- **Blackman-Harris** falls from `0.206 dB` raw to `0.019 dB` linear and `0.0019 dB` log
- **flat-top** already sits inside `0.0023 dB` on the raw sampled peak, and its log parabola actually grows that bounded error to `0.0134 dB`

## What actually changed

The old task map was honest for the raw sampled-peak read: flat-top really was the amplitude specialist.

This new sidecar shows a more conditional statement:

- if you want amplitude honesty **with no extra processing**, keep flat-top
- if you can afford a **3-point log interpolation**, Blackman-Harris becomes a real compact amplitude option
- Blackman becomes much better too, but Blackman-Harris is the sharper compromise here because it lands at lower bounded bias than Blackman while still costing far less ENBW than flat-top

That is the new split: at `256` points, Blackman-Harris reaches `0.0019 dB` worst-case bias with ENBW `2.020` bins, while flat-top needs ENBW `3.800` bins to win the same job without interpolation.

## Why the linear parabola is not the same result

A generic "parabolic interpolation" summary is too mushy. The method matters.

- the **linear-magnitude** parabola helps a lot, but it still leaves Blackman-Harris at `0.019 dB`
- the **log-magnitude** parabola drops that to `0.0019 dB`
- so this is not just "do any interpolation"; it is a narrower point about which local fit actually matches the lobe shape well enough to matter

## Practical rule for this repo now

1. Keep flat-top as the default answer for raw sampled-peak amplitude reads.
2. Add a second amplitude lane: Blackman-Harris plus 3-point log interpolation when you want much lower ENBW and a narrower main lobe.
3. Do not over-credit linear-magnitude parabolas. They help, but they do not change the compact-window ranking as sharply.

## Scope boundary

This is still a bounded, noiseless, isolated-tone audit. It does not settle every peak estimator, every noise regime, or every instrument front end. It says something narrower and useful: a tiny local log fit can erase most of the coarse-grid amplitude penalty that made flat-top look uniquely necessary.
