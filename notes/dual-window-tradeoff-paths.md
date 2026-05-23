# Dual-window tradeoff paths

The last sidecar asked a binary question: canonical dual or closest constant-looking dual?

This follow-up asks the sharper one:

**if both endpoints reconstruct exactly, is there a useful middle lane between them, or does the noise bill turn ugly as soon as you start flattening the dual?**

## Bounded setup

- frame length `N = 128`
- windows: Hann, Blackman-Harris, flat-top
- hops: `H = 64` and `H = 32`
- mixes: `λ = 0, 0.25, 0.5, 0.75, 1`, where `λ = 0` is the canonical dual and `λ = 1` is the closest constant-looking dual

Because the dual constraint is linear, every convex mix along that path is still an exact dual. So exact reconstruction is not the story here. The story is how the flatness-versus-noise tradeoff bends between the two endpoints.

## Main read

- **Hann / 75% overlap:** the midpoint already closes about `60%` of the flatness gap while raising RMS noise gain by only about `6%`
- **Blackman-Harris / 75% overlap:** this is the strongest compromise lane in the set; the midpoint closes about `67%` of the flatness gap for only about `12%` more RMS noise
- **Flat-top / 50% overlap:** even the midpoint stays ugly in absolute terms (`flatness = 4.22`, `noise = 6.96`), because the whole path lives between two already-hostile endpoints

So the right lesson is not just “canonical calm, constant noisy.”

The sharper lesson is this:

- some windows really do have a usable middle lane between the two exact dual endpoints
- some windows do not, because the starting case is already too hostile for synthesis-window retuning to count as a rescue

## Midpoint table (`λ = 0.5`)

| case | gap closed | noise / canonical | energy / canonical | midpoint flatness | midpoint noise |
| --- | ---: | ---: | ---: | ---: | ---: |
| Hann / 50% overlap | 59% | 1.05× | 1.11× | 0.268 | 1.258 |
| Hann / 75% overlap | 60% | 1.06× | 1.13× | 0.285 | 0.871 |
| Blackman-Harris / 50% overlap | 71% | 1.07× | 1.14× | 0.420 | 2.038 |
| Blackman-Harris / 75% overlap | 67% | 1.12× | 1.25× | 0.334 | 1.108 |
| Flat-top / 50% overlap | 69% | 1.01× | 1.01× | 4.224 | 6.959 |
| Flat-top / 75% overlap | 78% | 1.27× | 1.61× | 0.352 | 1.611 |

## Practical read

If the analysis window and hop are already only mildly uncomfortable, there may be a real design lane between the calm minimum-energy dual and the flattest constant-looking dual.

If the starting case is already hostile, the path is still informative, but it stops being a rescue plan. In those cases the repo's older advice survives unchanged: shrink the hop, or stop insisting on a window that is fighting the framing job.

## Artifacts

- `art/window-dual-tradeoff-paths.svg`
- `art/window-dual-tradeoff-paths.png`
- `art/window-dual-tradeoff-paths.csv`
- `notes/dual-window-tradeoff-paths.md`
- `notebooks/dual_window_tradeoff_paths.ipynb`
