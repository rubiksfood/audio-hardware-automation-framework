# Focusrite Scarlett 2i2 Loopback Hardware Validation

## Overview

This document records the Phase 5 physical loopback validation performed with a Focusrite Scarlett 2i2 (3rd Gen).

The purpose of the validation was to verify that the framework could execute an end-to-end hardware signal path:

```text
generated reference
       │
       ▼
configured output channel
       │
       ▼
Focusrite Scarlett 2i2 DAC
       │
       ▼
physical line-level output
       │
       │ external loopback cable
       ▼
physical line-level input
       │
       ▼
Focusrite Scarlett 2i2 ADC
       │
       ▼
captured audio
       │
       ▼
signal alignment
       │
       ▼
frequency and sample-domain validation
```

The validation also compared the behaviour of different PortAudio host APIs.

The key verified Phase 5 result is that physical end-to-end loopback succeeds through the direct ALSA Scarlett endpoint at 48 kHz.

JACK was also investigated. A JACK software-routed loopback can pass validation, but the tested JACK routing to and from the Scarlett hardware did not return the physical loopback signal at a valid captured level. That behaviour remains a follow-up diagnostic item rather than a Phase 5 acceptance requirement.

---

## Test Hardware

Hardware:

```text
Focusrite Scarlett 2i2 (3rd Gen)
```

Physical signal path:

```text
Scarlett line output
        │
        │ line-level cable
        ▼
Scarlett line input
```

The input was configured for an appropriate line-level signal with conservative hardware gain.

Direct monitoring was disabled for the final validation and diagnostic runs.

Software monitoring paths that could create an unintended digital loopback or feedback path were also avoided when validating the physical signal path.

See [`loopback-validation.md`](loopback-validation.md) for the general physical setup and safety procedure.

---

## Software Environment

Framework:

```text
Audio Hardware Automation Framework
```

Audio backend:

```text
PortAudio
```

Python audio library:

```text
sounddevice 0.5.5
```

Primary Linux host APIs investigated:

```text
ALSA
JACK Audio Connection Kit
```

Device indexes are intentionally not recorded as stable identifiers.

PortAudio device indexes changed between discovery sessions, so validation uses device and host-API matching rather than assuming that a particular numeric index remains constant.

Some JACK device names also contained session-dependent suffixes.

The device name, host API and channel capabilities are therefore more useful validation evidence than a transient PortAudio index.

---

## Validation Configuration

The normal Phase 5 physical loopback validation used:

```yaml
stream:
  sample_rate: 48000
  input_channels: 2
  output_channels: 2
  block_size: 128
  dtype: float32

loopback:
  output_channel: 0
  input_channel: 0
  signal_duration_seconds: 1.0
  frequency_hz: 1000.0
  amplitude: 0.25
  frequency_tolerance_hz: 5.0
  padding_seconds: 0.1
```

Framework channel indexes are zero-based, so:

```text
output_channel: 0
input_channel: 0
```

represent physical Output 1 and Input 1.

The generated one-second signal contains:

```text
48,000 signal frames
```

and the configured 0.1-second padding adds:

```text
4,800 leading frames
4,800 trailing frames
```

for a total duplex playback and capture window of:

```text
57,600 frames
```

The aligned analysis window contains:

```text
48,000 frames
```

of test signal.

Dedicated host-API configurations are provided:

```text
configs/example_loopback_alsa.yaml
configs/example_loopback_jack.yaml
```

The ALSA configuration is the verified Phase 5 physical loopback path.

The JACK configuration is retained for host-API comparison and further routing diagnostics.

---

## Correction to Preliminary Testing

Some preliminary Linux loopback experiments were performed when the physical loopback connection was incomplete.

Those runs produced:

```text
ALSA
    → duplex execution completed
    → capture remained near the noise floor
    → validation failed
```

At the time, that behaviour was incorrectly interpreted as an ALSA host-API or routing problem.

Once the physical cable was correctly connected, direct ALSA at 48 kHz passed the complete physical loopback validation without issue.

The earlier ALSA failures therefore do not represent valid physical-loopback failures and are not included in the final acceptance matrix.

An earlier JACK pass was also investigated further.

That pass was produced by a software routing path inside the JACK graph rather than by the Scarlett analogue output-to-input path.

It is therefore classified as a software loopback result, not as physical hardware validation.

Correcting these interpretations is part of the final Phase 5 evidence review.

---

## Final Validation Matrix

| Environment | Stream rate | Execution result | Loopback result | Interpretation |
| --- | ---: | --- | --- | --- |
| ALSA physical loopback | 48 kHz | Executed | PASS | Verified Scarlett DAC → cable → ADC path |
| JACK software-routed loopback | 48 kHz | Executed | PASS | Digital/software signal path only |
| JACK Scarlett hardware routing | 48 kHz | Executed | FAIL | Expected 1 kHz return absent; capture remained near noise floor |
| JACK | 44.1 kHz | Rejected before duplex execution | Not run | PortAudio reported `Invalid sample rate` |
| ALSA | 44.1 kHz | Not retested after physical setup correction | Not run | Earlier unplugged-cable result is not valid physical-loopback evidence |
| Windows PortAudio endpoints | — | No suitable single duplex endpoint | Not run | Scarlett input and output were exposed separately |

The matrix distinguishes three different questions:

```text
Can the framework execute duplex audio?
Can a software-routed signal return through the selected host API?
Can the signal travel through the real hardware output and input path?
```

A successful answer to one does not automatically prove the others.

---

## ALSA at 48 kHz — Physical Loopback PASS

The primary Phase 5 hardware acceptance test used the direct ALSA Scarlett endpoint at 48,000 Hz with a physical line-level cable connecting the configured Scarlett output to the configured Scarlett input.

The device reported a default sample rate of 44,100 Hz but the configured 48 kHz duplex stream opened and executed successfully.

This demonstrates that the device-reported default rate is not equivalent to the only stream rate that can be used through PortAudio.

The duplex run completed with:

```text
playback frames: 57,600
captured frames: 57,600
analysed frames: 48,000
```

A representative final run produced approximately:

```text
expected frequency:  1000.000 Hz
measured frequency:  1000.000 Hz
frequency error:     < 0.001 Hz
tolerance:           ±5.000 Hz

RMS:                 0.014242
Peak:                0.021235
DC offset:           0.000005
Silence detected:    False
Clipping detected:   False
```

No validation failures were reported.

The lower captured amplitude relative to the generated digital signal is expected for a physical analogue path whose resulting level depends on hardware output level and input gain.

This run demonstrates that the framework successfully:

- generated the configured reference signal;
- routed it to the selected hardware output;
- executed simultaneous playback and capture;
- sent the signal through the Scarlett physical output;
- received it through the Scarlett physical input;
- aligned the captured signal against the generated reference;
- recovered the expected 1 kHz dominant frequency;
- calculated sample-domain metrics;
- applied configured validation thresholds;
- returned a passing structured validation result;
- retained WAV and JSON evidence.

This is the primary Phase 5 hardware acceptance result.

---

## JACK at 48 kHz — Software Loopback PASS

A JACK validation also produced a passing result at:

```text
48,000 Hz
```

when an explicit software connection returned the generated playback signal into the capture side of the JACK graph.

The result contained:

```text
expected frequency:  1000.000 Hz
measured frequency:  1000.000 Hz

RMS:                 0.176777
Peak:                0.250000
DC offset:           approximately 0
Silence detected:    False
Clipping detected:   False
```

The RMS value is effectively the theoretical RMS of a sine wave with amplitude `0.25`:

```text
0.25 / sqrt(2) ≈ 0.176777
```

Together with the exact peak and effectively zero DC offset, this is consistent with a digital/software-routed signal rather than an analogue Scarlett output-to-input capture.

This result is useful because it demonstrates that the framework can execute, capture, align and validate audio through the JACK backend.

It is not classified as physical Scarlett loopback evidence.

---

## JACK at 48 kHz — Physical Routing Attempt FAIL

JACK was tested with the physical loopback cable connected.

A longer diagnostic run was used so that the PortAudio client remained visible in QjackCtl while validation was executing.

The diagnostic configuration used:

```yaml
execution:
  timeout_seconds: 25.0

loopback:
  signal_duration_seconds: 20.0
```

The live JACK graph showed the PortAudio client connected to Scarlett playback and capture-side ports while the validation was running.

The framework therefore successfully:

- created the JACK duplex stream;
- generated the configured test signal;
- routed playback into the JACK graph;
- received capture frames from the JACK graph;
- retained playback and capture evidence.

However, the expected physical 1 kHz return was not present in the selected JACK capture path.

A final diagnostic run produced approximately:

```text
expected frequency:  1000.000 Hz
measured frequency:  49.970 Hz
frequency error:     950.030 Hz
tolerance:           ±5.000 Hz

RMS:                 0.000024
Peak:                0.000115
DC offset:           0.000008
Silence detected:    False
Clipping detected:   False
```

The validation failed on both:

```text
frequency outside configured tolerance
RMS below configured minimum
```

The reported `Silence detected: False` does not indicate that the intended test signal was successfully captured.

The returned signal contained enough low-level energy to exceed the configured silence threshold, but its RMS level remained close to the noise floor and its dominant frequency was unrelated to the expected 1 kHz reference.

The retained evidence further isolated the behaviour:

```text
playback.wav
    → contains the expected 1 kHz test signal

captured.wav
    → contains only very low-level returned audio

analysed.wav
    → does not contain the expected 1 kHz reference at a valid level
```

This provides stronger evidence that the intended physical loopback signal is not reaching the selected JACK capture path.

Because the same physical Scarlett output-to-input path passes through direct ALSA, the physical cable and analogue hardware path have been independently verified.

The precise JACK capture-routing or port-mapping cause has not yet been established.

Further JACK-specific investigation is deferred to a separate follow-up issue rather than blocking completion of Phase 5.

---

## JACK at 44.1 kHz — Stream Rejected

The JACK configuration was also tested at:

```text
44,100 Hz
```

PortAudio rejected the stream settings before duplex execution with:

```text
Invalid sample rate
```

The loopback validation therefore did not reach playback, capture or signal analysis.

This is an execution/configuration failure:

```text
JACK 44.1 kHz
    │
    └── stream rejected
        └── exit code 2
```

rather than a completed signal-validation failure:

```text
JACK 48 kHz physical-routing attempt
    │
    └── duplex execution completed
        └── captured signal below validation threshold
            └── exit code 1
```

No completed capture evidence bundle is expected when the stream is rejected before duplex execution.

---

## ALSA at 44.1 kHz

An earlier 44.1 kHz ALSA run was performed while the physical loopback connection was incomplete.

That run is therefore not valid evidence of physical loopback behaviour.

ALSA at 44.1 kHz was not required for the Phase 5 acceptance criteria and was not repeated after the physical setup was corrected.

No pass or fail claim is made for physical ALSA loopback at 44.1 kHz.

The verified physical configuration is:

```text
ALSA
48 kHz
physical output-to-input cable
PASS
```

---

## Windows Limitation

The Scarlett was also investigated through the PortAudio device topology exposed on Windows.

The usable Scarlett entries were exposed as separate input and output endpoints rather than one device index providing both directions.

The current Phase 5 duplex contract operates on one `AudioDevice` and therefore requires one selected PortAudio device with both:

```text
input channels > 0
output channels > 0
```

No suitable Scarlett endpoint was available for the current physical loopback workflow on the tested Windows configuration.

This does not mean that recording or playback is unsupported on Windows.

The framework's independent recording and playback workflows can use separate input-only and output-only device entries.

The limitation applies specifically to the current single-device duplex loopback architecture.

---

## Host API Comparison

The hardware investigation demonstrates why host API and routing topology are material parts of audio-hardware validation.

### Direct ALSA at 48 kHz

```text
stream opens
duplex executes
test tone leaves the Scarlett output
physical cable carries the signal
Scarlett input captures the signal
alignment succeeds
frequency validation passes
sample-domain validation passes
```

Result:

```text
PASS — verified physical hardware loopback
```

### JACK with explicit software loopback

```text
stream opens
duplex executes
playback signal is returned through software routing
alignment succeeds
frequency validation passes
sample-domain validation passes
```

Result:

```text
PASS — software loopback only
```

### JACK with Scarlett hardware routing

```text
stream opens
PortAudio JACK client appears
playback is routed toward Scarlett playback ports
Scarlett capture-side ports are routed toward PortAudio inputs
duplex executes
playback evidence contains the 1 kHz test tone
returned capture remains near the noise floor
measured dominant frequency does not match the reference
minimum-RMS validation fails
frequency validation fails
```

Result:

```text
FAIL — expected physical JACK return not present
```

These results demonstrate that:

```text
device discovered
+
stream opened
+
duplex execution completed
```

does not itself prove:

```text
physical output
→ cable
→ physical input
→ valid captured signal
```

The end-to-end signal validation layer is what provides that assertion.

---

## Interpretation

The final evidence supports the following conclusions:

1. The Phase 5 loopback implementation successfully performs end-to-end physical hardware validation.
2. Direct ALSA at 48 kHz is the verified physical loopback path for the tested Scarlett 2i2.
3. The Scarlett's reported 44.1 kHz ALSA default sample rate did not prevent a configured 48 kHz duplex stream from executing successfully.
4. JACK at 48 kHz can successfully validate a software-routed loopback.
5. A JACK software-loopback PASS must not be interpreted as proof that the signal travelled through the Scarlett analogue hardware path.
6. With the physical cable connected and the PortAudio JACK client routed through the Scarlett graph, the selected JACK capture path returned only very low-level audio and did not recover the expected 1 kHz reference.
7. The latest controlled JACK run measured approximately 49.97 Hz rather than 1 kHz and also failed the configured minimum-RMS requirement, providing stronger evidence that the intended physical return was absent from the selected capture path.
8. The exact JACK capture-routing or port-mapping cause remains unresolved.
9. The earlier ALSA failures were invalid as physical-loopback evidence because the physical loopback connection was incomplete.
10. The tested JACK endpoint rejected 44.1 kHz before duplex execution.
11. PortAudio device indexes are not stable enough to use as permanent hardware identifiers.
12. The tested Windows device topology does not currently provide the single duplex Scarlett endpoint required by the Phase 5 implementation.

The unresolved JACK hardware-routing behaviour will be investigated separately if required.

It does not invalidate the successful direct-ALSA physical acceptance result.

---

## Evidence Retention

Phase 5 supports retaining a complete validation evidence bundle.

For the verified physical ALSA path:

```bash
audio-hw validate-loopback \
  --config configs/example_loopback_alsa.yaml \
  --evidence-dir evidence/linux-alsa-48k
```

A completed validation bundle contains:

```text
playback.wav
captured.wav
analysed.wav
report.json
```

This applies to both successful validations and completed validation failures.

The evidence was also useful during the JACK investigation because it demonstrated that:

```text
playback.wav
```

contained the expected generated signal while:

```text
captured.wav
analysed.wav
```

contained only the near-silent returned capture.

Execution failures that occur before duplex capture, such as rejection of an unsupported sample rate, do not produce a completed loopback evidence bundle.

---

## Phase 5 Acceptance Criteria

Phase 5 required the framework to demonstrate that:

- a deterministic tone can be generated;
- the tone can be routed to a selected hardware output;
- playback and capture can execute through a duplex backend;
- the captured signal can be aligned against the known reference;
- dominant frequency can be measured;
- RMS and peak level can be measured;
- silence and clipping can be detected;
- validation failures identify the affected metric and channel;
- raw playback and captured audio can be retained as evidence;
- structured JSON evidence can be exported;
- the workflow can be validated against physical audio hardware.

These criteria were satisfied by the successful direct-ALSA 48 kHz Focusrite physical loopback run together with the hardware-independent automated regression suite.

The JACK investigation also demonstrated that the framework correctly distinguishes a valid captured signal from an effectively absent physical return.

Phase 5 is therefore complete.

---

## Follow-Up Investigation

A separate diagnostic issue may investigate the JACK Scarlett capture topology.

Potential investigation areas include:

- mapping JACK-visible Scarlett capture ports to the physical analogue inputs;
- determining the purpose of each exposed capture port;
- checking JACK bridge routing;
- testing JACK auto-connection behaviour;
- determining whether PortAudio selects the intended Scarlett capture ports;
- evaluating whether JACK-specific routing support belongs in the framework.

This work is deliberately outside the Phase 5 acceptance scope.

---

## Remaining Scope

The current loopback implementation does not yet provide:

- measured round-trip latency as a reported validation metric;
- calibrated analogue voltage measurements;
- frequency-response sweeps;
- total harmonic distortion;
- THD+N;
- signal-to-noise ratio;
- channel crosstalk measurements;
- long-duration stability testing;
- automatic recovery or hot-plug stress testing;
- separate-device input/output duplex execution.

These remain candidates for later phases.