# Nuttall is not one window

The repo's current `nuttall` implementation is a real thing.
It matches the **Nuttall-defined minimum 4-term Blackman-Harris** coefficients:

- `0.3635819`
- `0.4891775`
- `0.1365995`
- `0.0106411`

That variant drives the **first sidelobe** very low.

But some practical tables use a different coefficient set under the same `Nuttall` label:

- `0.355768`
- `0.487396`
- `0.144232`
- `0.012604`

That second branch gives up a little first-sidelobe depth and buys **faster far-out decay**.

So if the question is only:

- *which one has the lower peak sidelobe?*

then the repo's current `nuttall` is fine.

If the question becomes:

- *which one decays faster far away from the main lobe?*
- *which one is better for weak spurs far from the carrier?*
- *which one has the smoother endpoint story?*

then the bare name `nuttall` stops being honest enough.

## Practical rule for this repo

Keep the current implementation for continuity.

But if a later sidecar wants to talk about **sidelobe falloff** instead of only **peak sidelobe depth**, split the family explicitly:

- `nuttall (minimum 4-term BH)`
- `nuttall (continuous-derivative variant)`

Otherwise the repo will quietly teach a naming shortcut that hides the actual tradeoff.
