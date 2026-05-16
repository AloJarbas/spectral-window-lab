# Amplitude-specialist window family follow-up — flat-top first, Blackman-Harris/Nuttall later if at all

## Research question

After the repo's Kaiser and scalloping-loss passes, what is the right next amplitude-focused move?

More specifically:

- should `spectral-window-lab` stop at **flat-top** as the amplitude specialist,
- or should it immediately widen the comparison set to **Blackman-Harris** and **Nuttall** as well?

## Scope boundary

This pass is about **repo sequencing and teaching clarity**, not about building a giant window zoo.

The question is not which window family exists.
The question is which comparison teaches the next honest thing.

## What survived source review

- **Flat-top** is still the clearest amplitude-measurement specialist because its main-lobe peak is intentionally flattened and its scalloping loss is essentially zero.
- **Blackman-Harris** and **Nuttall** are impressive deep-sidelobe windows, but they do **not** buy the same amplitude honesty. They improve far-out leakage much more than they improve between-bin amplitude error.
- That means adding Blackman-Harris/Nuttall *before* flat-top would blur the repo thesis.
- The clean narrative remains:
  1. baseline tradeoffs,
  2. Kaiser as tunable compromise,
  3. scalloping-loss / off-bin behavior,
  4. flat-top as the deliberate amplitude specialist.
- Only after that story is visible does it make sense to ask whether a second deep-sidelobe family belongs in the gallery.

## Local metric snapshot at length 129

Computed locally with the repo's current metric code plus temporary pure-Python generalized-cosine helpers for Blackman-Harris, Nuttall, and flat-top.

| window | coherent gain | ENBW (bins) | peak sidelobe (dB) | main-lobe width | scalloping loss (dB) |
|---|---:|---:|---:|---:|---:|
| blackman | 0.4167 | 1.7402 | -58.11 | 0.04688 | -1.0818 |
| kaiser-8.6 | 0.4175 | 1.7347 | -62.99 | 0.04547 | -1.0922 |
| blackman-harris | 0.3560 | 2.0200 | -92.04 | 0.06256 | -0.8128 |
| nuttall | 0.3608 | 1.9915 | -96.83 | 0.06305 | -0.8374 |
| flattop | 0.2139 | 3.7998 | -91.33 | 0.07916 | -0.0091 |

A few offset checkpoints make the contrast sharper:

| window | loss at 0.10 bin | loss at 0.25 bin | loss at 0.50 bin |
|---|---:|---:|---:|
| blackman | -0.0429 dB | -0.2689 dB | -1.0818 dB |
| kaiser-8.6 | -0.0434 dB | -0.2716 dB | -1.0922 dB |
| blackman-harris | -0.0324 dB | -0.2026 dB | -0.8128 dB |
| nuttall | -0.0334 dB | -0.2088 dB | -0.8374 dB |
| flattop | +0.0006 dB | +0.0023 dB | -0.0091 dB |

## What those numbers mean

- **Blackman-Harris** and **Nuttall** are not fake improvements. They really do push sidelobes down dramatically.
- But they are still much closer to **Blackman / Kaiser** than to **flat-top** on the specific question of amplitude honesty between bins.
- Flat-top is the outlier by a mile:
  - half-bin loss is basically gone,
  - but ENBW jumps to about **3.80 bins**,
  - and the main lobe gets much wider.
- So the repo's next public lesson should still be:

> if you want accurate single-tone amplitude away from exact bin centers, flat-top is the specialist — and it charges a huge ENBW / resolution bill.

That is a cleaner next lesson than:

> here are even more windows with excellent sidelobe numbers.

## Adversarial check

I explicitly checked the tempting counter-argument:

> Maybe Blackman-Harris or Nuttall should come first because they also have deep sidelobes and somewhat better scalloping loss than Blackman.

The local numbers say no.

They improve half-bin loss from roughly **-1.08 dB** to about **-0.82 dB**, which is real but modest.
Flat-top moves that same quantity to about **-0.01 dB**, which is a qualitatively different regime.

So if the teaching goal is amplitude honesty, Blackman-Harris/Nuttall are side branches, not the spine.

## Repo sequencing decision

### What to do next

1. implement `flattop(length)` first,
2. add flat-top to the offset-loss figure and metrics CSV,
3. add one compact sidecar note or artifact that pairs:
   - scalloping loss,
   - ENBW,
   - main-lobe width,
   - and the sentence that flat-top is an amplitude specialist, not a default.

### What **not** to do yet

- do not add Blackman-Harris and Nuttall in the same pass,
- do not expand the gallery into a window encyclopedia,
- do not bury flat-top inside a crowded all-in-one plot.

## Best second pass after flat-top lands cleanly

If the repo wants one more family after flat-top, the strongest candidate is a **deep-sidelobe comparison sidecar**:

- Blackman
- Kaiser-8.6
- Blackman-Harris
- Nuttall

That sidecar would teach a different question:

- how much extra ENBW and main-lobe width you are paying for much deeper sidelobes,
- and why those windows are about leakage suppression, not amplitude flatness.

## Accepted sources

### Accepted for primary framing

1. **SciPy `signal.windows.flattop` docs**  
   https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.windows.flattop.html  
   Accepted because it states the core claim cleanly: accurate frequency-domain amplitude measurement with minimal scalloping error.

2. **Brian McFee, spectral leakage and windowing**  
   https://brianmcfee.net/dstbook-site/content/ch06-dft-properties/Leakage.html  
   Accepted because it explains the true tradeoff spine: sidelobe suppression versus main-lobe spreading.

3. **Keysight window shapefactor / ENBW table**  
   https://helpfiles.keysight.com/csg/89600B/Webhelp/Subsystems/gui/content/windows_shapefactor_and_equiv_noisebw.htm  
   Accepted because it gives a practical instrument-oriented comparison showing flat-top's very large ENBW and very low amplitude error relative to Blackman-Harris/Kaiser-class windows.

4. **Tektronix window-functions overview**  
   https://www.tek.com/en/blog/window-functions-spectrum-analyzers  
   Accepted because it states the practical measurement framing plainly: flat-top broadens the peak but preserves amplitude best, while Blackman-Harris/Kaiser are broader compromise windows.

5. **GaussianWaves figure-of-merits note**  
   https://www.gaussianwaves.com/2020/09/window-function-figure-of-merits/  
   Accepted because it keeps ENBW, coherent gain, and scalloping loss in one place and gives exact coefficient cross-checks for multiple generalized-cosine windows.

6. **RecordingBlogs scalloping-loss page**  
   https://www.recordingblogs.com/wiki/scalloping-loss  
   Accepted because it gives the compact half-bin formula and useful common-window comparison values.

7. **RecordingBlogs Blackman-Harris page**  
   https://www.recordingblogs.com/wiki/blackman-harris-window  
   Accepted as a practical metric cross-check for ENBW, sidelobes, and scalloping loss.

8. **RecordingBlogs Nuttall page**  
   https://www.recordingblogs.com/wiki/nuttall-window  
   Accepted as a practical metric cross-check for ENBW, sidelobes, and scalloping loss.

### Rejected as primary sources

1. **SciPy `signal.windows.blackmanharris` docs**  
   https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.windows.blackmanharris.html  
   Rejected as a primary source because it mostly defines the window and shows a plot, but does not explain the measurement tradeoff nearly well enough for the repo's teaching goal.

2. **Wikipedia window-function overview**  
   https://en.wikipedia.org/wiki/Window_function  
   Rejected as a final citation target because it is secondary and unnecessary once better primary/practical sources are in hand.

## Best next move

Convert this directly into one repo pass:

- add flat-top first,
- make the amplitude-vs-cost tradeoff unmistakable,
- only then decide whether Blackman-Harris/Nuttall deserve a separate deep-sidelobe sidecar.