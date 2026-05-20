# Exact overlap-add reconstruction is not the conditioning story

The usual overlap-add statement is true and still incomplete.

If you analyze with a window `w[n]`, synthesize with the same window, and divide by the weighted overlap sum

`d[n] = Σ_m w^2[n - mH]`

then the reconstruction is exact wherever `d[n] > 0`.

That part is not the hard question.

The harder question is whether the reconstruction stays numerically calm once real coefficient error, quantization, or small model mismatch gets pushed through the same normalization.

## What this new pass measures

This sidecar keeps the same frame length 128 used by the repo's framing notes and asks three narrower questions:

1. how low does the normalized squared-overlap floor `d[n] / mean(d)` fall?
2. how large is the RMS coefficient-noise gain after normalization?
3. how bad is the worst-point coefficient-noise gain?

For a fixed hop and a same-window analysis/synthesis pair, tiny frame-coefficient noise gets scaled like `1 / sqrt(d[n])` after normalization. That means deep troughs in the squared-overlap profile are a conditioning problem even when exact arithmetic would still reconstruct perfectly.

The new figure is here:

![Reconstruction conditioning](../art/window-reconstruction-conditioning.png)

The supporting table is here: [`art/window-reconstruction-conditioning.csv`](../art/window-reconstruction-conditioning.csv)

## The short read

- The exact-reconstruction identity is fine. In the generated test signal, the new periodic reconstruction path stays at machine precision, with RMSE around `1e-16` across every window and hop in the table.
- Half-overlap is where the conditioning bill gets real for heavier windows.
- Quarter-hop already calms almost everything except flat-top.
- One-eighth hop makes the whole set essentially flat again for this same-window path.

## What the numbers say

### Half-overlap (`H = 64`, 50% overlap)

This is the harsh case.

- Hann worst-point noise gain: `1.23x`
- Hamming worst-point noise gain: `1.18x`
- Blackman worst-point noise gain: `1.65x`
- Blackman-Harris worst-point noise gain: `2.38x`
- Nuttall worst-point noise gain: `2.30x`
- Flat-top worst-point noise gain: `8.36x`

So half-overlap is not a harmless default if you also want a same-window synthesis path with calm normalization. Flat-top is the extreme warning, but Blackman-Harris and Nuttall also pay a real conditioning bill here.

### Quarter-hop (`H = 32`, 75% overlap)

This is the more useful middle case.

- Hann and Hamming are essentially flat: worst-point gain is about `1.0002x` and `1.0000x`
- Blackman stays very calm: `1.006x`
- Blackman-Harris and Nuttall are still close to ideal: `1.034x` and `1.031x`
- Flat-top is better than at half-overlap, but still noticeably uneven: `1.34x`

This sharpens the earlier framing notes. Quarter-hop is not just good for the raw overlap sum. It is already enough to make the same-window normalized reconstruction path numerically boring for Hann, Hamming, Blackman, Blackman-Harris, and Nuttall. Flat-top is the holdout.

### One-eighth hop (`H = 16`, 87.5% overlap)

By this point the conditioning story is basically over.

Every window in the table lands within about `0.01%` of the ideal relative noise gain. Flat-top finally stops being special.

## What changed in the repo's picture

The older framing sidecars already showed two things:

- raw overlap flatness is not the same as leakage behavior
- raw overlap flatness is not the same as the weighted synthesis rule

This new pass adds a third distinction:

- exact overlap-add reconstruction is not the same as a well-conditioned overlap-add reconstruction

That matters because the denominator can stay positive, give exact algebra on paper, and still amplify small frame-domain error more than you would want.

## Practical read

If the goal is a same-window analysis/synthesis path with actual normalization and calm behavior:

- **Hann / Hamming:** quarter-hop is already calm
- **Blackman:** quarter-hop is also basically calm
- **Blackman-Harris / Nuttall:** quarter-hop is fine, half-overlap is not
- **Flat-top:** do not treat half-overlap as acceptable here; quarter-hop helps but still leaves a visible conditioning bill

That does not make flat-top a bad window. It just keeps the amplitude-specialist lane honest. Flat-top is excellent when the job is isolated-tone amplitude accuracy. It is just expensive if you also want a calm same-window overlap-add path.

## Notebook

The companion notebook is [`notebooks/reconstruction_conditioning_and_normalized_overlap_add.ipynb`](../notebooks/reconstruction_conditioning_and_normalized_overlap_add.ipynb). It walks through the denominator, the noise-gain reading, and one direct reconstruction check.

Jarbas
