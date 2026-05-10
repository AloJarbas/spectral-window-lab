# Repo-ready prompt: add a Kaiser window pass without bloating the repo

## Goal

Add one real Kaiser-based improvement to `spectral-window-lab` while keeping the repo small, standard-library only, and honest.

## Constraints

- keep the repo pure Python standard library
- do not add NumPy or SciPy
- do not turn the simple API into a generic parameter parser on the first pass
- preserve the repo's current readable shape: code, generated artifacts, tests, and a short note

## What to build

1. Add a local `_i0(x: float) -> float` helper in `windowlab/windows.py` using the convergent power series for the modified Bessel function of the first kind, order zero.
2. Add `kaiser(length: int, beta: float) -> list[float]`.
3. Keep `WINDOW_BUILDERS` for the fixed baseline windows.
4. Add a separate gallery spec layer for parameterized windows instead of trying to encode `beta` inside the existing `build_window(name, length)` string interface.
5. First gallery pass should add exactly one named Kaiser trace: `kaiser(beta=8.6)`.
6. Regenerate SVG and CSV artifacts.
7. Add one short explanatory note or README paragraph that says ENBW is the metric that explains why the FFT noise floor rises or falls when the window changes.

## Why `beta=8.6`

Use `beta=8.6` for the first visible comparison.

Reason:

- it is close to Blackman in coherent gain, ENBW, and main-lobe width,
- it makes the tradeoff curve visible without being as extreme as `beta=14`,
- SciPy's docs explicitly call out `beta=8.6` as Blackman-like.

## Suggested tests

Add tests that check at least the following:

1. `kaiser(length, 0.0)` is approximately equal to `rectangular(length)`.
2. For a fixed length, ENBW increases as beta increases over a small ordered set such as `0.0 < 5.0 < 8.6`.
3. For a fixed length, peak sidelobe level drops as beta increases over that same ordered set.
4. `kaiser(129, 8.6)` lands near Blackman on ENBW and main-lobe width within a reasonable tolerance, rather than exact equality.

## Implementation note

Do not rely on `math.i0` being present. On this host it is missing, so the local helper is required for portability.

## Acceptance criteria

- `python3 scripts/make_gallery.py` succeeds
- `python3 -m unittest discover -s tests` succeeds
- generated metrics CSV includes a Kaiser entry
- generated plots include one Kaiser line
- the prose explanation connects Kaiser, beta, and ENBW without pretending Kaiser is literally DPSS

## Optional second pass

If there is time after the first pass works, add a separate artifact that sweeps `beta = 0, 4, 6, 8.6, 14` and shows how coherent gain, ENBW, and sidelobe level move together.
