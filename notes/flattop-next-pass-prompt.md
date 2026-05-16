# Repo-ready prompt: add flat-top honestly, as an amplitude specialist

## Goal

Deepen `spectral-window-lab` with a flat-top window pass that teaches something real instead of just adding another name.

The repo already shows baseline tradeoffs, Kaiser, and off-bin leakage / scalloping loss. This pass should make one sharper point:

**flat-top is the deliberate amplitude-measurement specialist, and it earns that by paying a large ENBW and resolution bill.**

## Constraints

- keep the repo pure Python standard library
- do not add NumPy, SciPy, or plotting dependencies
- do not let flat-top silently become the implied default window
- do not crowd the existing all-purpose comparison figures if a dedicated sidecar artifact teaches better
- keep the prose honest: near-zero scalloping loss is the feature, high ENBW / wide main lobe is the cost

## What to build

1. Add `flattop(length: int) -> list[float]` to `windowlab/windows.py` using the common 5-term cosine coefficients:
   - `a0 = 0.21557895`
   - `a1 = 0.41663158`
   - `a2 = 0.277263158`
   - `a3 = 0.083578947`
   - `a4 = 0.006947368`
2. Include flat-top in the metrics CSV.
3. Extend the amplitude-vs-bin-offset artifact so flat-top appears alongside the current windows.
4. Either extend the half-bin leakage artifact or add a compact dedicated sidecar artifact that compares:
   - scalloping loss,
   - ENBW,
   - main-lobe width,
   - and one short note about why flat-top is for amplitude measurement.
5. Update the README so it says plainly that flat-top is an amplitude-accuracy specialist, not a universal best choice.

## Recommended artifact shape

Best first pass:

- keep the existing offset-loss figure and add flat-top there,
- keep the metrics CSV honest,
- add one small sidecar figure or note if the main gallery gets visually crowded.

The important visual is that flat-top stays near 0 dB across bin offsets while the ENBW and main-lobe width numbers get dramatically worse.

## Useful ordering facts to test

Add tests that check at least the following at a fixed length such as 129:

1. flat-top has lower scalloping loss than Blackman and `kaiser-8.6`
2. flat-top scalloping loss is very close to 0 dB, e.g. better than `-0.05 dB`
3. flat-top ENBW is larger than Blackman and much larger than Hann
4. flat-top main-lobe width is larger than Blackman and Hann
5. flat-top coherent gain is lower than Blackman and Hann

## Design note

Do not present flat-top as if it improves everything.

The repo should explicitly say something like:

> Flat-top is what you choose when single-tone amplitude accuracy matters more than frequency resolution or FFT noise-floor efficiency.

That sentence is the point of the whole pass.

## Acceptance criteria

- `python3 scripts/make_gallery.py` succeeds
- `python3 -m unittest discover -s tests` succeeds
- generated metrics CSV includes a flat-top entry
- at least one artifact makes the flat-top amplitude-vs-cost tradeoff visually obvious
- README or note text explains flat-top as the amplitude-measurement specialist with a clear ENBW / resolution warning

## Optional second pass

If the first pass lands cleanly, add a compact comparison note or figure that places `blackman`, `kaiser-8.6`, and `flattop` side by side as three different answers to the same question:

- leakage suppression
- tunable compromise
- amplitude accuracy
