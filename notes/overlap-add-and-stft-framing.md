# Overlap-add flatness is a second window bill

A window can look great in a one-shot FFT plot and still make STFT framing awkward.

That is the point of this sidecar.
Window choice does not stop at sidelobes, scalloping loss, and ENBW.
Once frames overlap, the receiver or analyzer also has to live with the **overlap-add sum**.

![Overlap-add flatness for common hops](../art/window-overlap-add-flatness.png)

## The compact equation

For a frame hop `H`, the periodic overlap-add profile is

```text
s[p] = Σ_k w[p + kH]
```

with `p` running over one hop period.
If `s[p]` stays constant, the raw overlap sum is flat.
If it ripples, the framing stage is quietly weighting some sample phases more than others.

## Scope and caveat

This pass uses the **symmetric** window tables already defined in this repo and measures them at frame length `N = 128`.

That caveat matters.
Some textbook COLA claims assume periodic STFT windows instead of endpoint-including symmetric tables.
So the numbers here are not trying to restate every textbook identity.
They are measuring what this repo’s actual window definitions do in a practical overlap-add experiment.

## What the measurements say

Representative results from `art/window-overlap-add-metrics.csv`:

### Half hop: `H = N/2`

- rectangular: exact flat sum, `0.0%` max deviation
- Hann: small ripple, `0.772%`
- Hamming: small ripple, `0.657%`
- Blackman: large ripple, `19.955%`
- Kaiser `β = 8.6`: large ripple, `19.926%`
- Blackman-Harris: very large ripple, `40.429%`
- Nuttall: very large ripple, `38.605%`
- flat-top: extreme ripple, `133.494%`, with the summed profile crossing below zero

So half-overlap is **not** a universal safe default just because the FFT window looked civilized in the frequency plot.

### Quarter hop: `H = N/4`

- Hann: `0.157%`
- Hamming: `0.133%`
- Blackman: `0.045%`
- Kaiser `β = 8.6`: `0.046%`
- Blackman-Harris: `0.0053%`
- Nuttall: `0.0078%`
- flat-top: still visibly wavy at `3.571%`

This is the useful middle panel in the figure.
Most windows are now effectively flat for many practical purposes, but flat-top still asks for a smaller hop if the raw overlap envelope matters.

### Eighth hop: `H = N/8`

By `87.5%` overlap, everything in the current set is close to flat.
Even flat-top drops to `0.0058%` max deviation.

That is the hidden cost.
It can be made well-behaved, but it asks for much heavier overlap than the lighter windows.

## The real reading

Three practical lessons survive this pass:

1. **Exact or near-exact overlap flatness is a different property from spectral leakage control.**
   Rectangular is perfect on raw overlap-add and still terrible on sidelobes.
2. **Blackman, Kaiser, Blackman-Harris, and Nuttall are not naturally half-hop windows in this symmetric-table experiment.**
   They calm down fast once the hop gets smaller.
3. **Flat-top is expensive twice.**
   It already pays extra ENBW, and it also wants heavier overlap before the raw overlap sum stops wavering.

That is why STFT framing belongs in this repo.
Window choice changes not just the spectrum you read, but the frame geometry that stays comfortable later.
