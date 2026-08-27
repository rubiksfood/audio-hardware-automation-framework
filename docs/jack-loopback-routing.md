# JACK Loopback Routing Investigation

## Overview

This document records the post-Phase 5 investigation into physical loopback routing through the JACK host API on Linux using a Focusrite Scarlett 2i2 (3rd Gen).

Phase 5 had already established a successful unattended physical loopback path through direct ALSA at 48 kHz.

Initial JACK testing produced several different behaviours depending on the active JACK graph:

- software-routed loopback could pass;
- the default PortAudio JACK routing did not return the expected physical input signal;
- manually replacing the default capture route with a physical `capture_MONO` source also failed;
- retaining the default PortAudio capture routing and additionally connecting the physical `capture_MONO` source to `PortAudio:in_0` produced a valid physical loopback PASS.

The investigation therefore established that physical JACK loopback is possible on the tested system, but the required routing is not currently created automatically by the framework.

---

## Environment

Hardware:

```text
Focusrite Scarlett 2i2 (3rd Gen)
```

Audio backend:

```text
PortAudio
sounddevice
```

JACK environment:

```text
PipeWire-backed JACK graph
```

The tested PipeWire environment exposed the Scarlett through several JACK-visible nodes and ports rather than as one simple pair of physical capture and playback channels.

Observed Scarlett-related ports included names such as:

```text
capture_AUX0
capture_AUX1
capture_MONO
monitor_FL
monitor_FR
playback_FL
playback_FR
```

Numeric client suffixes associated with `capture_MONO` changed between sessions and are therefore not treated as stable identifiers.

---

## Physical Test Path

The physical loopback connection used:

```text
Scarlett Output L
        │
        │ physical line-level cable
        ▼
Scarlett Input 1
```

For the tested Scarlett output topology:

```text
playback_FL
```

corresponded to the left output used for the physical loopback.

The physical Input 1 source was exposed separately through a JACK-visible:

```text
capture_MONO
```

port.

Direct monitoring was disabled during the final controlled runs.

Input gain and analogue output level were set to moderate values to provide a valid captured level without clipping.

---

## PortAudio Client Lifetime

The framework creates the JACK-visible PortAudio client when the duplex stream is opened.

The client exposes temporary ports such as:

```text
PortAudio:in_0
PortAudio:in_1
PortAudio:out_0
PortAudio:out_1
```

When validation completes, the duplex stream closes and the PortAudio JACK client disappears.

Any manual connection involving those temporary ports therefore also disappears.

The required physical-input connection must currently be recreated after the PortAudio client appears during each validation run.

This prevents the tested JACK configuration from operating as an unattended framework workflow.

---

## Diagnostic Results

### Default JACK routing — FAIL

The automatically established PortAudio routing connected Scarlett capture-side ports to the PortAudio inputs and PortAudio outputs to Scarlett playback ports.

The expected physical 1 kHz return was not captured at a valid level.

Result:

```text
FAIL
```

The generated playback signal remained valid, but capture remained near the noise floor.

---

### `capture_MONO` as the only Input 1 route — FAIL

The default input connection to `PortAudio:in_0` was removed and the physical Input 1 `capture_MONO` source was connected directly instead.

Representative topology:

```text
capture_MONO
    │
    ▼
PortAudio:in_0

PortAudio:out_0
    │
    ▼
playback_FL
```

This configuration still failed.

A representative run produced approximately:

```text
expected frequency:  1000.000 Hz
measured frequency:  0.250 Hz

RMS:                 0.000002
Peak:                0.000082
Silence detected:    True
Clipping detected:   False
```

This demonstrates that simply replacing the default capture route with `capture_MONO` is not sufficient on the tested graph.

---

## Default routing plus `capture_MONO` — PASS

The successful physical JACK topology retained the original PortAudio capture routing and additionally connected the physical Input 1 `capture_MONO` source to:

```text
PortAudio:in_0
```

The resulting topology was approximately:

```text
default Scarlett capture route
        ─────────────► PortAudio inputs

physical Input 1 capture_MONO
        ─────────────► PortAudio:in_0

PortAudio:out_0
        ─────────────► playback_FL

PortAudio:out_1
        ─────────────► playback_FR
```

A representative controlled passing run produced approximately:

```text
expected frequency:  1000.000 Hz
measured frequency:  999.965 Hz
frequency error:     0.035 Hz
tolerance:           ±5.000 Hz

RMS:                 0.032995
Peak:                0.046741
DC offset:           0.000006
Silence detected:    False
Clipping detected:   False
```

Result:

```text
PASS
```

The retained playback, captured and analysed WAV evidence all contained the expected test tone.

---

## Physical-Path Verification

The passing JACK result was verified as a physical hardware path rather than a hidden software loopback.

### Cable A/B/A test

With the working JACK graph left otherwise unchanged:

```text
physical cable disconnected
    → FAIL

physical cable connected
    → PASS

physical cable disconnected
    → FAIL
```

The validation result therefore depended on the external physical connection.

### Input-gain response

Repeating the physical test with different Scarlett Input 1 gain settings changed the captured RMS and peak values while preserving the expected approximately 1 kHz frequency.

This is consistent with the signal passing through the Scarlett analogue input stage.

### Analogue output-level response

Direct ALSA testing also demonstrated that the Scarlett analogue output control materially affected the physical return:

```text
output level at minimum
    → physical return below validation threshold

moderate output level
    → physical loopback PASS

excessive output / input level
    → capture can reach clipping
```

These observations further support the conclusion that the successful loopback path traverses:

```text
Scarlett DAC
    ↓
physical output
    ↓
external cable
    ↓
physical input
    ↓
Scarlett ADC
```

---

## Software Monitor Routing

The Scarlett JACK graph also exposed:

```text
monitor_FL
monitor_FR
```

Routing one of these monitor ports into the PortAudio capture path can produce a passing validation.

A representative software-routed result closely matched the generated digital signal:

```text
RMS:   approximately 0.176777
Peak:  0.250000
```

For a sine wave with amplitude `0.25`:

```text
0.25 / sqrt(2) ≈ 0.176777
```

This behaviour is therefore classified separately as software/digital loopback evidence.

It must not be used as proof of the Scarlett physical analogue output-to-input path.

---

## Result Matrix

| JACK topology | Result | Interpretation |
| --- | --- | --- |
| Default PortAudio routing | FAIL | Expected physical return not captured at a valid level |
| `capture_MONO` replacing default Input 1 route | FAIL | Physical source alone was insufficient in the tested graph |
| Default routing + `capture_MONO → PortAudio:in_0` | PASS | Verified physical loopback, but requires manual runtime routing |
| `monitor_*` software route | PASS | Digital/software loopback only |

Direct ALSA remains the known-good unattended physical loopback path.

---

## Current Limitation

Physical JACK loopback has been demonstrated successfully, but it is not currently an unattended or repeatable framework-only workflow.

The required additional connection:

```text
capture_MONO
    ↓
PortAudio:in_0
```

must be created after the PortAudio JACK client appears.

When the validation stream closes:

```text
PortAudio client closes
    ↓
PortAudio JACK ports disappear
    ↓
manual connection disappears
```

The framework currently does not manage JACK graph connections.

---

## Remaining Investigation

The remaining question is no longer whether physical loopback through JACK is possible.

The unresolved engineering questions are:

- why the default capture route must remain alongside the additional `capture_MONO` connection;
- which component creates the default PortAudio JACK connections;
- whether the required connection can be applied automatically when the transient PortAudio client appears;
- whether routing policy should be owned by the framework or by the host audio environment;
- whether JACK-specific routing support belongs in the planned endpoint-topology work.

No JACK-specific production-code change was made as part of this diagnostic investigation.

---

## Conclusion

The investigation established four distinct behaviours:

```text
ALSA physical loopback
    → PASS
    → unattended and repeatable

JACK default physical routing
    → FAIL

JACK physical routing with manual runtime graph addition
    → PASS
    → verified physical path
    → not currently unattended

JACK monitor/software routing
    → PASS
    → digital path only
```

The direct ALSA result remains the primary Phase 5 physical hardware acceptance path.

The JACK result demonstrates that the hardware path can also operate through JACK when the required graph connection is established manually, while identifying a remaining routing-lifecycle limitation for future work.