# Kaiser window research pass — beta, ENBW, and DPSS context

## Why this was the right pass

`spectral-window-lab` already has a clean baseline: a few canonical windows, honest metrics, generated artifacts, and tests. The highest-upside next move is not just adding more names. It is adding the one practical parametric family that makes the tradeoff curve itself visible.

That family is the Kaiser window.

## What survived source review

- The Kaiser window is a Bessel-based approximation to the DPSS/Slepian window.
- `beta` is the useful control knob: larger `beta` lowers sidelobes, widens the main lobe, and raises ENBW.
- ENBW belongs in the explanation because it predicts the visible FFT noise-floor penalty that comes with broader windows.
- DPSS is still the stronger optimality story, but Kaiser is the practical pure-Python story for this repo.

## Core formulas worth keeping

For a symmetric Kaiser window of length `N`:

```text
w[n] = I0(beta * sqrt(1 - ((2n)/(N-1) - 1)^2)) / I0(beta)
```

where `I0` is the modified Bessel function of the first kind, order zero.

Equivalent noise bandwidth in DFT bins:

```text
ENBW = N * sum(w[n]^2) / (sum(w[n]))^2
```

That ENBW formula is already exactly the one used in this repo.

For FIR-design context, the common Kaiser heuristics are still worth keeping nearby:

```text
beta(A) = 0.1102 * (A - 8.7)                         for A > 50 dB
beta(A) = 0.5842 * (A - 21)^0.4 + 0.07886 * (A - 21) for 21 <= A <= 50 dB
beta(A) = 0                                           for A < 21 dB

numtaps ~= (A - 7.95) / (2.285 * pi * width) + 1
```

Those formulas matter less for the current gallery than for later filter-design notes, but they make the `beta` parameter feel less arbitrary.

## Local metric snapshot at length 129

These numbers were computed locally with the repo's current metric code and a temporary pure-Python series prototype for `I0`, not with SciPy.

| window | coherent gain | ENBW (bins) | peak sidelobe (dB) | main-lobe width |
|---|---:|---:|---:|---:|
| rectangular | 1.0000 | 1.0000 | -13.27 | 0.01562 |
| hamming | 0.5364 | 1.3705 | -42.62 | 0.03174 |
| hann | 0.4961 | 1.5117 | -31.48 | 0.03125 |
| blackman | 0.4167 | 1.7402 | -58.12 | 0.04688 |
| kaiser beta=5.0 | 0.5409 | 1.3682 | -36.99 | 0.02930 |
| kaiser beta=6.0 | 0.4963 | 1.4776 | -43.92 | 0.03369 |
| kaiser beta=8.6 | 0.4175 | 1.7347 | -62.99 | 0.04541 |
| kaiser beta=14.0 | 0.3293 | 2.1780 | -105.81 | 0.07129 |

## What those numbers suggest

- `beta ~= 5` lands close to Hamming in coherent gain and ENBW.
- `beta ~= 6` lands close to Hann in coherent gain and ENBW, while pushing sidelobes noticeably lower.
- `beta ~= 8.6` tracks Blackman surprisingly well on coherent gain, ENBW, and main-lobe width. This makes it the best first Kaiser comparison to add to the gallery.
- `beta = 14` is useful as an extreme example, but it is probably too aggressive for the first default comparison because the ENBW penalty gets large quickly.

The practical punchline: if the repo wants one Kaiser line first, `beta=8.6` is the cleanest choice because it visibly demonstrates the tradeoff while staying close to an already familiar baseline.

## DPSS relationship: what to say honestly

The repo should not oversell this.

A good short explanation is:

> Kaiser is the practical Bessel-based approximation to the DPSS/Slepian window family. DPSS is the stronger concentration-optimal construction; Kaiser is the easier knob to expose in lightweight code.

More detail than that is probably unnecessary unless the repo later adds a separate note about multitaper spectral estimation.

Two useful nuances from source review:

- SciPy's docs explicitly describe Kaiser as a very good approximation to DPSS and use `beta = alpha * pi` in their comparison example.
- Smith's DSPRelated text notes that DPSS tends to have slightly narrower main lobes and slightly better overall concentration, while Kaiser often shows steeper sidelobe rolloff farther from the main lobe.

That is enough nuance for this repo.

## Implementation guidance for the next code pass

1. Add `kaiser(length: int, beta: float)` to `windowlab/windows.py`.
2. Keep the repo standard-library only by adding a tiny local `_i0(x)` helper based on the convergent power series.
3. Do **not** force arbitrary `beta` parsing into the current `build_window(name, length)` string API on the first pass.
4. Instead, keep the existing named baseline windows and add a small gallery-spec layer for parameterized entries.
5. First public artifact should probably add exactly one new gallery line: `kaiser(beta=8.6)`.
6. Second pass can add a dedicated beta sweep artifact or note (`beta = 0, 4, 6, 8.6, 14`) focused on ENBW and sidelobe tradeoffs.
7. Keep DPSS explanatory text-only unless the repo later accepts a dependency or precomputed reference data.

## Small but real implementation constraint

On this host, `python3` does **not** expose `math.i0`, so a pure-stdlib Kaiser implementation cannot rely on that function being present.

That makes the local-series helper the right design, not just a portability nicety.

## Accepted sources

### Accepted for primary claims

1. **SciPy `signal.windows.kaiser` docs**  
   https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.windows.kaiser.html  
   Accepted because it gives the definition, the DPSS approximation claim, and the practical beta mapping (`0`, `5`, `6`, `8.6`, `14`).

2. **SciPy `signal.windows.dpss` docs**  
   https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.windows.dpss.html  
   Accepted because it states what DPSS is optimizing, anchors the multitaper context, and shows the comparison convention `beta = alpha * pi`.

3. **SciPy FIR design source (`kaiser_beta`, `kaiser_atten`, `kaiserord`)**  
   https://raw.githubusercontent.com/scipy/scipy/v1.17.0/scipy/signal/_fir_filter_design.py  
   Accepted because it exposes the exact empirical beta/attenuation and tap-count heuristics in code, which is better than relying on paraphrase.

4. **Julius O. Smith / DSPRelated, _Spectral Audio Signal Processing_**  
   https://www.dsprelated.com/freebooks/sasp/Kaiser_Window.html  
   Accepted because it gives the strongest explanatory treatment here: beta as a continuous tradeoff knob, time-bandwidth interpretation, and a nuanced Kaiser-vs-DPSS comparison.

5. **GaussianWaves ENBW note**  
   https://www.gaussianwaves.com/2020/09/equivalent-noise-bandwidth-enbw-of-window-functions/  
   Accepted because it gives the cleanest short explanation of why ENBW changes the displayed FFT noise floor and states the same practical ENBW formula used in this repo.

### Accepted as secondary cross-check only

6. **RecordingBlogs Kaiser window page**  
   https://www.recordingblogs.com/wiki/kaiser-window  
   Accepted only as a rough cross-check table for coherent gain / ENBW / sidelobe trends at a few alpha values. Not the source to trust first for theory.

## Rejected sources

1. **Wikipedia Kaiser window page**  
   https://en.wikipedia.org/wiki/Kaiser_window  
   Rejected for final claims because it is secondary and redundant once SciPy + DSPRelated are in hand. Fine for orientation, not needed for the durable note.

2. **MathWorks Kaiser window help page (fetch extract)**  
   https://www.mathworks.com/help/signal/ug/kaiser-window.html  
   Rejected for this pass because the fetched extract contained wording that looked internally inconsistent about how sidelobe attenuation changes with `beta`, and it added no claim we could not ground more cleanly elsewhere.

## Best next move

Turn this research into one real repo improvement:

- implement `kaiser(length, beta)` with a local `_i0` helper,
- add `kaiser(beta=8.6)` to the generated gallery and metrics CSV,
- add one short note explaining that ENBW is the reason the FFT noise floor visibly shifts across windows.

That would convert this research pass directly into code, figures, and a clearer thesis.
