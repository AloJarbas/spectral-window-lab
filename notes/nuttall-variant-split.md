# Nuttall variants split one low-sidelobe story into two different jobs

The repo already had a good deep-sidelobe branch. What it did not have was an honest answer to one quieter naming problem:

- the current `nuttall` implementation is real,
- but it is **not** the only coefficient set people mean by `Nuttall`,
- and that difference becomes important as soon as the question shifts from **first sidelobe depth** to **far-out decay**.

This sidecar keeps the existing Blackman-Harris comparison and adds one explicit split inside the Nuttall family:

- **Blackman-Harris**
- **Nuttall minimum 4-term Blackman-Harris** (the repo's current `nuttall`)
- **Nuttall continuous-derivative variant**

All three are measured at length `129` with the repo's standard-library metric code and a dense `16384`-point sampled-spectrum read for peak-sidelobe and width values.

## Main read

- the repo's current `nuttall` still wins the **first-sidelobe** contest: `-96.83 dB` versus `-92.04 dB` for Blackman-Harris and `-93.32 dB` for the continuous variant
- in the near tail (`6–12` bins), that same variant also stays lowest: `-96.83 dB` versus `-92.91 dB` and `-93.33 dB`
- but the deeper tail flips the story: in the `24–48` bin band the continuous variant reaches `-117.35 dB`, while the minimum-4-term-BH variant stalls at `-98.36 dB`
- Blackman-Harris lands between those two stories: `-116.88 dB` in the same far-out band

## Why this matters

The old deep-sidelobe note is still fine. Blackman-Harris and the repo's current Nuttall implementation really are deep-sidelobe specialists instead of amplitude specialists.

What changes is the next sentence. Once the repo wants to talk about **weak spurs farther away from the carrier** or **sidelobe falloff**, the bare word `nuttall` stops being precise enough.

That is because the family split is real:

- the **minimum-4-term-BH** branch spends more of the cosine-sum degrees of freedom on crushing the first sidelobe
- the **continuous-derivative** branch gives some of that back and buys a cleaner far tail

So these are not two names for the same ranking. They are two different design bets.

## Local metric snapshot

| variant | coherent gain | ENBW (bins) | peak sidelobe (dB) | scalloping loss (dB) | max 6–12 bins (dB) | max 12–24 bins (dB) | max 24–48 bins (dB) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Blackman-Harris | `0.355969` | `2.0200` | `-92.04` | `-0.8128` | `-92.91` | `-103.93` | `-116.88` |
| Nuttall min-4-term BH | `0.360766` | `1.9915` | `-96.83` | `-0.8374` | `-96.83` | `-97.26` | `-98.36` |
| Nuttall continuous | `0.353010` | `2.0370` | `-93.32` | `-0.7992` | `-93.33` | `-101.30` | `-117.35` |

## Practical rule for this repo

1. Keep `nuttall` as a compatibility alias for the current minimum-4-term-BH implementation.
2. Expose the two explicit variants whenever the lesson cares about sidelobe falloff instead of only peak sidelobe depth.
3. Stop teaching the lazy sentence “Nuttall decays faster than Blackman-Harris” unless the coefficients are named explicitly.

## Companion files

- `windowlab/nuttall_variants.py`
- `art/window-nuttall-variant-split.svg`
- `art/window-nuttall-variant-split.png`
- `art/window-nuttall-variant-split.csv`
- `notebooks/nuttall_variant_split.ipynb`
- `notes/nuttall-is-not-one-window.md`

## Scope boundary

This is still a bounded three-window comparison at one length. It is strong enough to clean up the naming problem and split two different sidelobe jobs without pretending the whole cosine-sum family can be reduced to one fixed ranking.
