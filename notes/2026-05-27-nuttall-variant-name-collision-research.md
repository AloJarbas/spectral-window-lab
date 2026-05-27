# Nuttall variant name collision — why the repo should stop pretending `nuttall` names one exact sidelobe-decay story

## Research question

The current repo already treats Blackman-Harris and Nuttall as deep-sidelobe specialists.

That broad split still works.

But a sharper follow-up appeared once I checked far-out leakage more directly:

- why do common practical tables describe **Nuttall** as a steeper-decay window,
- while the repo's current `nuttall` implementation behaves more like **minimum-peak-sidelobe optimization** than a steep far-out-decay variant?

The answer is that **`Nuttall` is not one coefficient set in practice**.

## What survived source review

### 1. The repo's current coefficients match a real Nuttall-defined minimum-4-term Blackman-Harris variant

The repo currently uses:

- `a0 = 0.3635819`
- `a1 = 0.4891775`
- `a2 = 0.1365995`
- `a3 = 0.0106411`

That matches MathWorks `nuttallwin`, which explicitly calls this a **"Nuttall-defined minimum 4-term Blackman-Harris window"** and says it produces slightly lower sidelobes than `blackmanharris`.

So the current implementation is not wrong.
It is one legitimate named variant.

### 2. Several practical comparison tables use a different coefficient set under the name `Nuttall window`

A common alternative set is:

- `a0 = 0.355768`
- `a1 = 0.487396`
- `a2 = 0.144232`
- `a3 = 0.012604`

RecordingBlogs presents that version as **the** Nuttall window and reports noticeably steeper sidelobe falloff than Blackman-Harris.

That means a lot of practical "Nuttall vs Blackman-Harris" folklore is really about a **different member of the family** than the one the repo currently builds.

### 3. Julius O. Smith / CCRMA keeps the design tradeoff honest

The useful family-level framing from Smith is:

- some Blackman / Blackman-Harris-family designs spend degrees of freedom minimizing **peak sidelobe level**,
- others spend them increasing **roll-off rate** by improving endpoint smoothness.

That is exactly the split that resolves the apparent contradiction.

## Local comparison at length 129

I compared three windows with the repo's current metric code and direct offset-response checks:

1. **SciPy / standard 4-term Blackman-Harris**
2. **current repo `nuttall`** = Nuttall-defined minimum 4-term Blackman-Harris
3. **continuous-derivative Nuttall-style coefficients** from the practical table above

### Core metrics

| window | coherent gain | ENBW (bins) | peak sidelobe (dB) | scalloping loss (dB) |
|---|---:|---:|---:|---:|
| 4-term Blackman-Harris | `0.355969` | `2.0200` | `-92.04` | `-0.8128` |
| repo `nuttall` (min-4-term BH) | `0.360766` | `1.9915` | `-96.83` | `-0.8374` |
| continuous-derivative Nuttall | `0.353010` | `2.0370` | `-93.32` | `-0.7992` |

If the only question is **first/peak sidelobe depth**, the repo's current `nuttall` really does look best.

### Bounded far-out leakage check

I then looked at the worst leakage in three offset bands after the main lobe:

| window | max in `6–12` bins | max in `12–24` bins | max in `24–48` bins |
|---|---:|---:|---:|
| 4-term Blackman-Harris | `-92.90 dB` | `-103.92 dB` | `-116.87 dB` |
| repo `nuttall` (min-4-term BH) | `-96.83 dB` | `-97.25 dB` | `-98.35 dB` |
| continuous-derivative Nuttall | `-93.33 dB` | `-101.28 dB` | `-117.33 dB` |

That is the whole point of this pass.

The repo's current `nuttall` is the **lowest first-sidelobe** option in this small group.
It is **not** the same thing as the steeper-decay practical Nuttall variant.

So the name collision is real:

- one variant wins the **first sidelobe** contest,
- another wins the **far-out decay** story.

## What this changes in the repo

### What stays true

The existing deep-sidelobe note does **not** need to be treated as broken.
It only claims that Blackman-Harris and Nuttall are deep-sidelobe specialists rather than amplitude specialists.
That still holds.

### What no longer feels safe

The repo should **not** keep using the bare label `nuttall` if a future pass wants to teach:

- sidelobe falloff,
- far-out weak-spur hunting,
- endpoint smoothness,
- or any "Nuttall decays faster than Blackman-Harris" story.

Those claims depend on **which Nuttall coefficients are actually in play**.

## Repo decision

1. **Do not rewrite the current implementation yet.**
   The current coefficients are real, useful, and already wired into existing artifacts.

2. **Do stop pretending the name is unambiguous.**
   The repo should treat the current implementation as something like:
   - `nuttall-min4-bh`, or
   - `nuttall (minimum 4-term BH)`

3. **If the deep-sidelobe branch gets one more pass, the honest addition is a variant split.**
   Add the continuous-derivative Nuttall-style coefficients as a second explicit builder and compare:
   - lowest first sidelobe,
   - far-out decay,
   - ENBW,
   - scalloping,
   - and maybe one weak-spur-at-distance task card.

That would give the repo a genuinely new teaching artifact instead of another same-shape ranking chart.

## Accepted sources

### Accepted for primary framing

1. **MathWorks `nuttallwin` docs**  
   https://www.mathworks.com/help/signal/ref/nuttallwin.html  
   Accepted because it matches the repo's current coefficients exactly and names the implemented object clearly: a *Nuttall-defined minimum 4-term Blackman-Harris window*.

2. **SciPy `blackmanharris` docs**  
   https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.windows.blackmanharris.html  
   Accepted as the standard 4-term Blackman-Harris baseline used for comparison.

3. **Julius O. Smith / CCRMA — Three-Term Blackman-Harris Window**  
   https://ccrma.stanford.edu/~jos/sasp/Three_Term_Blackman_Harris_Window.html  
   Accepted because it states the key family tradeoff explicitly: spend degrees of freedom on peak sidelobe suppression or on roll-off behavior.

4. **Julius O. Smith / DSPRelated — Blackman-Harris Window Family**  
   https://www.dsprelated.com/freebooks/sasp/Blackman_Harris_Window_Family.html  
   Accepted because it makes the family-level optimization story reusable instead of collapsing all cosine-sum windows into one label.

### Accepted as practical cross-checks, not primary naming authority

5. **RecordingBlogs — Blackman window**  
   https://www.recordingblogs.com/wiki/blackman-window  
   Accepted as a practical metric cross-check for the classic higher-rolloff Blackman branch.

6. **RecordingBlogs — Blackman-Harris window**  
   https://www.recordingblogs.com/wiki/blackman-harris-window  
   Accepted as a practical metric cross-check for 4-term Blackman-Harris.

7. **RecordingBlogs — Nuttall window**  
   https://www.recordingblogs.com/wiki/nuttall-window  
   Accepted because it exposes the coefficient mismatch directly and therefore helps explain the name collision. Not accepted as sole naming authority.

## Rejected or downgraded sources

1. **Raindrop discovery hit: Jake VanderPlas, Understanding the FFT Algorithm**  
   Rejected for this pass because it is a good general FFT explainer, not a window-family naming or leakage-tradeoff source.

2. **Hacker News discovery pass**  
   Rejected as noise for this topic. The pass surfaced no window-specific material worth using.

3. **Generic `window function` overview pages**  
   Downgraded because they flatten multiple coefficient families into one broad taxonomy and are exactly where this ambiguity gets hidden.

## Best next move

Do **one** explicit variant split, not another generic window expansion:

- keep current `nuttall` behavior reproducible,
- add one continuous-derivative Nuttall variant under an explicit name,
- then build a single deep-sidelobe sidecar around **first-sidelobe depth versus far-out decay**.
