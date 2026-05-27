# Deep-sidelobe FFT-density family audit

The Kaiser audit left one honest loophole open: maybe every strong low-sidelobe window is this sensitive to FFT grid density. This follow-up checks that claim against **Blackman-Harris** and **Nuttall** instead of assuming one family story covers them all.

This pass keeps the same `129`-sample windows, uses a dense `16384`-point reference probe, and walks a smaller FFT ladder: `256, 512, 1024, 2048, 4096`.

## Main read

- **Kaiser β=8.6** is still the harsh anchor at `512` points: `|Δ sidelobe| = 4.93 dB`, `|Δ width| = 1.18` bins
- **Blackman-Harris** is almost grid-locked at the same probe: `|Δ sidelobe| = 0.01 dB`, `|Δ width| = 0.02` bins
- **Nuttall** is the useful middle case: at `512` points its sidelobe error is only `0.35 dB`, but its width error is still `0.43` bins
- by `2048` points, Nuttall closes most of that gap: `|Δ sidelobe| = 0.04 dB`, `|Δ width| = 0.05` bins

## Why the family read changes

- Blackman-Harris lands its first sidelobe peak within `0.008` bins of the dense reference even at `512` points, and its first null is off by only `0.008` bins
- Nuttall is different: the same `512`-point grid misses the first sidelobe peak by `0.094` bins and the first null by `0.213` bins
- that means “deep sidelobe” is not one FFT-density sensitivity class
- the Kaiser warning was real, but it was not universal in the lazy way. Blackman-Harris stays numerically calm; Nuttall stays visibly softer on width until the probe gets denser

## What stays fixed

- Blackman-Harris ENBW stays `2.020` bins and its half-bin loss stays `0.813 dB` across the whole audit
- Nuttall ENBW stays `1.992` bins and its half-bin loss stays `0.837 dB` across the whole audit
- those direct-sum metrics do not move; only the sampled-spectrum estimates do

## Caveat

This is still a bounded audit of one length and one reference FFT. It is strong enough to separate three different numerical behaviors without pretending the whole world of windows falls into exactly these three buckets.

Open `art/window-specialist-fft-density-audit.png`, `art/window-specialist-fft-density-audit.csv`, and `notebooks/specialist_fft_density_audit.ipynb` together next.
