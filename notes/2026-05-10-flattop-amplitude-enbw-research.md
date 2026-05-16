# Flat-top window research pass — amplitude honesty, ENBW cost, and where it belongs in this repo

## Why this was the right next pass

The active `spectral-window-lab` queue already landed the two missing foundations:

- a practical Kaiser family entry,
- an off-bin leakage / scalloping-loss story.

The next real question is not "which other window names exist?"
It is: **when is it actually worth paying a huge ENBW and resolution bill to get near-perfect amplitude accuracy between bins?**

That is the flat-top window story.

## What survived source review

- Flat-top exists mainly for **accurate amplitude measurement in the frequency domain**, not as a general default window.
- Its core trick is a deliberately flattened main-lobe peak, which drives scalloping loss close to zero.
- The bill is large: much wider main lobe, much higher ENBW, and much lower coherent gain than the repo's current defaults.
- That tradeoff means flat-top belongs in this repo only if the prose says plainly that it is an **amplitude specialist**, not a universally better window.
- The best way to add it is probably through the existing amplitude-vs-offset and half-bin framing, not by pretending it belongs in every comparison equally.

## Flat-top definition worth keeping

For the common 5-term flat-top window of length `N`:

```text
w[n] = a0
     - a1 cos(2πn/(N-1))
     + a2 cos(4πn/(N-1))
     - a3 cos(6πn/(N-1))
     + a4 cos(8πn/(N-1))
```

with coefficients

```text
a0 = 0.21557895
a1 = 0.41663158
a2 = 0.277263158
a3 = 0.083578947
a4 = 0.006947368
```

This is the same coefficient set used by SciPy, MathWorks, and RecordingBlogs.

## Local metric snapshot at length 129

Computed locally with the repo's current metric code plus a temporary pure-Python flat-top helper.

| window | coherent gain | ENBW (bins) | peak sidelobe (dB) | main-lobe width | scalloping loss (dB) |
|---|---:|---:|---:|---:|---:|
| rectangular | 1.0000 | 1.0000 | -13.26 | 0.0156 | -3.9222 |
| hamming | 0.5364 | 1.3705 | -42.62 | 0.0315 | -1.7339 |
| hann | 0.4961 | 1.5117 | -31.47 | 0.0312 | -1.4013 |
| blackman | 0.4167 | 1.7402 | -58.11 | 0.0469 | -1.0818 |
| kaiser-8.6 | 0.4175 | 1.7347 | -62.99 | 0.0454 | -1.0922 |
| flattop | 0.2139 | 3.7998 | -91.33 | 0.0791 | -0.0091 |

A few offset checkpoints make the tradeoff feel more physical:

| window | loss at 0.10 bin | loss at 0.25 bin | loss at 0.50 bin |
|---|---:|---:|---:|
| rectangular | -0.1433 dB | -0.9120 dB | -3.9222 dB |
| hamming | -0.0683 dB | -0.4282 dB | -1.7339 dB |
| hann | -0.0552 dB | -0.3461 dB | -1.4013 dB |
| blackman | -0.0429 dB | -0.2689 dB | -1.0818 dB |
| kaiser-8.6 | -0.0434 dB | -0.2716 dB | -1.0922 dB |
| flattop | +0.0006 dB | +0.0023 dB | -0.0091 dB |

## What those numbers mean

- Flat-top really does earn its reputation: half-bin amplitude loss is basically gone.
- But the price is severe:
  - ENBW is about **3.80 bins**,
  - about **2.5× Hann**,
  - about **2.2× Blackman / Kaiser-8.6**,
  - and the main lobe is similarly much wider.
- Its coherent gain is only about **0.214**, so amplitude correction is not a side detail.
- If the repo adds flat-top without a warning label, it will teach the wrong instinct.

The honest one-line summary is:

> flat-top is what you choose when single-tone amplitude accuracy matters more than frequency resolution, leakage compactness, or FFT noise-floor efficiency.

## Where flat-top fits in this repo

The repo now has a good narrative order:

1. baseline windows and tradeoff metrics,
2. Kaiser as a tunable practical family,
3. off-bin leakage and scalloping loss,
4. **flat-top as the deliberate amplitude-measurement specialist**.

That sequence is better than adding flat-top early, because now the repo can explain *why* its near-zero scalloping loss is unusual and expensive.

## Best next artifact shape

Best next public improvement is probably **not** to just tack flat-top onto every existing plot.

A better move:

1. add `flattop(length)` to the code and metrics CSV,
2. extend the amplitude-vs-bin-offset figure to include flat-top,
3. add one compact comparison note or artifact that explicitly pairs
   - scalloping loss,
   - ENBW,
   - main-lobe width,
   - and the "amplitude specialist" framing.

That keeps the repo readable while making the tradeoff unmistakable.

## Implementation guidance for the next code pass

- add `flattop(length: int)` to `windowlab/windows.py`
- keep the implementation pure Python standard library using the fixed 5-term cosine coefficients
- include flat-top in metrics reporting
- prefer adding flat-top first to the **offset-loss** and **half-bin** story, where it actually shines
- be careful about crowding the existing spectrum figure; a dedicated sidecar artifact may teach better than a busier all-in-one chart
- add tests that anchor the real point:
  - flat-top scalloping loss is much closer to 0 dB than Blackman/Kaiser,
  - flat-top ENBW is much larger than Hann/Blackman,
  - flat-top main-lobe width is much larger than Hann/Blackman,
  - flat-top should not accidentally be framed as the default recommendation

## Accepted sources

### Accepted for primary claims

1. **SciPy `signal.windows.flattop` docs**  
   https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.windows.flattop.html  
   Accepted because it states the core purpose cleanly: accurate frequency-domain amplitude measurement with minimal scalloping error, and identifies the window as a 5th-order cosine design with a maximally flat main lobe.

2. **RecordingBlogs flat-top window page**  
   https://www.recordingblogs.com/wiki/flat-top-window  
   Accepted because it gives the exact coefficient set plus concrete figures of merit, including ENBW, scalloping loss, sidelobe level, and main-lobe width.

3. **RecordingBlogs scalloping loss page**  
   https://www.recordingblogs.com/wiki/scalloping-loss  
   Accepted because it gives the compact half-bin formula and the crucial comparison point: flat-top's scalloping loss is essentially zero while common general-purpose windows are not.

4. **GaussianWaves figure-of-merits note**  
   https://www.gaussianwaves.com/2020/09/window-function-figure-of-merits/  
   Accepted because it cleanly ties ENBW, coherent gain, and scalloping loss together in one place, which is exactly the framing this repo needs.

5. **Daqarta FFT windowing note**  
   https://www.daqarta.com/ww00wndo.htm  
   Accepted because it gives the best plain-language practical framing found in this pass: flat-top has the widest peak but the flattest top, making it the most accurate for level readings when frequency shifts.

### Accepted as secondary context only

6. **MathWorks `flattopwin` docs**  
   https://www.mathworks.com/help/signal/ref/flattopwin.html  
   Accepted as a secondary cross-check because it confirms the same coefficient set and adds a useful practical rule of thumb: the bandwidth is about 2.5× wider than Hann.

## Rejected sources

1. **Siemens community article candidate**  
   https://community.sw.siemens.com/s/article/window-types-hanning-flattop-uniform-tukey-and-exponential  
   Rejected because the fetch path only returned a JavaScript-heavy loading shell, not durable readable content.

2. **MSU `Understanding FFT Windows` PDF candidate**  
   https://www.egr.msu.edu/classes/me451/me451_labs/Fall_2013/Understanding_FFT_Windows.pdf  
   Rejected because the in-tool fetch returned raw PDF bytes instead of readable extracted text, so it was annoying to verify precisely.

## Best next move

Turn this straight into one repo improvement:

- implement `flattop(length)`,
- add flat-top to the offset-loss story and metrics CSV,
- keep the README language explicit that flat-top is the amplitude-measurement specialist,
- and only then consider whether it deserves a place in the repo's broader comparison gallery.
