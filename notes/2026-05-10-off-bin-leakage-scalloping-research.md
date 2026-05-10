# Off-bin leakage research pass — scalloping loss, amplitude honesty, and the right next demo

## Why this was the right follow-up

The active `spectral-window-lab` queue already has a clear Kaiser pass. The next research gap is not another window name. It is the thing users actually feel when a tone does **not** land exactly on a DFT bin:

- leakage spreads energy away from the true tone,
- window choice decides whether that energy stays nearby or pollutes far bins,
- amplitude readings sag between bins, and that sag has a name: **scalloping loss**.

That makes off-bin tone behavior the cleanest next deepening pass after Kaiser.

## What survived source review

- Spectral leakage is not just a beginner mistake or a plotting artifact. For non-analysis frequencies, it is the normal DFT outcome.
- Windowing does not eliminate leakage. It **redistributes** it: usually less far-out leakage, more main-lobe spreading.
- The missing metric for this repo is scalloping loss: worst-case amplitude loss for a tone halfway between bins, after coherent-gain normalization.
- Among the repo's current baseline windows, Blackman gives the best half-bin amplitude honesty, rectangular gives the worst, and Hann/Hamming sit in the middle.
- Flat-top windows matter mainly as amplitude-measurement specialists. They belong in the repo only if the note explicitly says why their very low scalloping error costs ENBW and resolution.

## Local metric snapshot at length 129

Computed locally with the repo's current window builders plus a temporary half-bin-response script.

| window | ENBW (bins) | peak sidelobe (dB) | main-lobe width | scalloping loss (dB) |
|---|---:|---:|---:|---:|
| rectangular | 1.0000 | -13.26 | 0.01550 | -3.92 |
| hamming | 1.3705 | -42.62 | 0.03149 | -1.73 |
| hann | 1.5117 | -31.47 | 0.03125 | -1.40 |
| blackman | 1.7402 | -58.11 | 0.04688 | -1.08 |

A few intermediate offsets make the shape clearer:

| window | loss at 0.1 bin | loss at 0.25 bin | loss at 0.5 bin |
|---|---:|---:|---:|
| rectangular | -0.14 dB | -0.91 dB | -3.92 dB |
| hamming | -0.07 dB | -0.43 dB | -1.73 dB |
| hann | -0.06 dB | -0.35 dB | -1.40 dB |
| blackman | -0.04 dB | -0.27 dB | -1.08 dB |

## What those numbers mean

- **Rectangular** keeps the narrowest main lobe, but its half-bin amplitude miss is brutal and its sidelobes are high. Good when exact bin alignment exists; risky when it does not.
- **Hann** is still a strong default because it suppresses distant leakage well enough without exploding ENBW.
- **Hamming** beats Hann on peak sidelobes here but gives slightly worse scalloping loss.
- **Blackman** is the cleanest current choice when amplitude honesty between bins matters more than resolution.

The repo should say this plainly: there is no free lunch. Better off-bin amplitude behavior costs either ENBW, main-lobe width, or both.

## The formula worth keeping

For a window `w[n]` of length `N`, coherent-gain-normalized half-bin response is:

```text
SL = |sum_{n=0}^{N-1} w[n] * exp(-j * pi * n / N)| / sum_{n=0}^{N-1} w[n]
```

and scalloping loss in dB is:

```text
20 * log10(SL)
```

That is the cleanest compact metric to pair with ENBW, peak sidelobe level, and main-lobe width.

## Best artifact to build next

Do **not** bury this in prose alone. The repo wants a visible comparison.

Best next artifact pair:

1. **Amplitude-vs-bin-offset curve**  
   For each window, plot normalized amplitude error from offset `0.0` to `0.5` bins.

2. **Half-bin leakage spectrum**  
   Generate one tone intentionally placed halfway between bins and show the normalized spectrum under rectangular, Hann, Hamming, and Blackman.

That combination would make two different truths visible at once:

- scalloping loss is a main-lobe shape problem,
- leakage suppression is a sidelobe problem.

## Flat-top: where it fits honestly

The source review keeps pointing to the same framing:

> flat-top is not the "best" general-purpose window; it is the amplitude-measurement specialist.

That means flat-top should be a **second** move, not the first one.
A better sequence is:

1. add the off-bin leakage + scalloping demo using the current windows,
2. then add flat-top as the deliberate amplitude-accuracy counterexample,
3. show that flatter peak response buys lower scalloping loss by paying a heavy ENBW / resolution bill.

That keeps the repo thesis coherent.

## Implementation guidance for the next code pass

- add `scalloping_loss_db(window)` to `windowlab/metrics.py`
- add a small helper for coherent-gain-normalized response versus fractional bin offset
- keep the first pass standard-library only; direct complex sums are fine
- avoid folding this into the existing shape/spectrum SVG if that makes the plots cramped
- prefer a dedicated artifact, e.g. `art/window-offset-loss.svg` and/or `art/window-half-bin-leakage.svg`
- first pass should stay with the existing four baseline windows; let Kaiser join this comparison only after the Kaiser code lands

## Accepted sources

### Accepted for primary claims

1. **Brian McFee, Digital Signals Theory — spectral leakage and windowing**  
   https://brianmcfee.net/dstbook-site/content/ch06-dft-properties/Leakage.html  
   Accepted because it explains the core truth cleanly: non-analysis frequencies leak, and windowing redistributes rather than magically removes the problem.

2. **Julius O. Smith / DSPRelated, _Spectrum Analysis Windows_**  
   https://www.dsprelated.com/freebooks/sasp/Spectrum_Analysis_Windows.html  
   Accepted because it gives the sharpest framing of window tradeoffs in terms of sidelobes, cross-talk, and short-time spectral analysis.

3. **GaussianWaves — FFT and spectral leakage**  
   https://www.gaussianwaves.com/2011/01/fft-and-spectral-leakage-2/  
   Accepted because the worked examples separate two different causes people conflate: bin-grid mismatch and time-limited observation.

4. **RecordingBlogs — scalloping loss**  
   https://www.recordingblogs.com/wiki/scalloping-loss  
   Accepted because it gives the compact half-bin formula and rough common-window values that matched the local calculations closely enough for cross-checking.

### Accepted as secondary context only

5. **SciPy `signal.windows.flattop` docs**  
   https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.windows.flattop.html  
   Accepted as context because it states the practical reason to care about flat-top here: minimal scalloping error for amplitude measurement.

## Rejected sources

1. **Harris PDF mirror (`windows.pdf`)**  
   https://web.mit.edu/xiphmont/Public/windows.pdf  
   Rejected for this pass because the fetch path returned raw PDF bytes instead of usable extracted text, so it was annoying to verify precisely in-tool.

2. **NI documentation page candidate**  
   https://www.ni.com/docs/en-US/bundle/labwindows-cvi/page/advancedanalysisconcepts/lvac_side_lobes.html  
   Rejected because the fetch result was basically empty boilerplate and not usable as a durable citation.

## Best next move

After the Kaiser code lands, turn this directly into one visible repo improvement:

- add `scalloping_loss_db`,
- generate an amplitude-vs-offset artifact for the four current windows,
- generate one half-bin leakage spectrum figure,
- only then decide whether flat-top deserves to join as the amplitude-accuracy specialist.
