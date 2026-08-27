# Physical Loopback Validation

## Overview

The framework supports end-to-end physical audio loopback validation.

A generated test signal is:

1. created as a deterministic mono sine wave;
2. routed to a configured hardware output channel;
3. padded with silence before and after the signal;
4. played and captured simultaneously through a duplex audio stream;
5. aligned against the known reference signal;
6. analysed for frequency and sample-domain metrics;
7. evaluated against configured validation thresholds.

The validation result can be displayed as human-readable CLI output or JSON.

Optional evidence export saves the exact playback, capture and analysed audio used during validation.

---

## Physical Signal Path

A physical loopback test requires an external cable connecting one output of the audio interface back to one of its inputs.

Example:

```text
Audio interface

Line Output 1
     │
     │ line-level cable
     ▼
Line Input 1
```

The configured output and input channels must correspond to the physical ports used by the cable.

Framework channel indexes are zero-based.

For example:

```yaml
loopback:
  output_channel: 0
  input_channel: 0
```

corresponds to physical Output 1 and Input 1.

The human-readable CLI displays these as physical one-based channel numbers.

---

## Hardware Requirements

Physical loopback validation requires:

- an audio interface with at least one input and one output;
- a suitable line-level cable;
- a PortAudio device exposing both input and output channels;
- a host API capable of opening the selected device as a duplex stream;
- matching framework configuration for the selected host API and channel layout.

The current duplex implementation uses one PortAudio device for both capture and playback.

A platform or host API that exposes the physical interface as separate input-only and output-only devices cannot currently be used for physical loopback validation.

This limitation is separate from recording and playback validation, which can operate through different input-only and output-only device entries.

---

## Safety

Physical loopback testing sends a generated signal through real audio hardware.

Use conservative levels when configuring the test.

Before running validation:

1. Turn monitor speakers down or disconnect them if they are not required.
2. Reduce the interface output level.
3. Set the selected input to line-level operation where applicable.
4. Start with low input gain.
5. Disable direct monitoring for the looped input where possible.
6. Disable DAW or software monitoring that routes the captured input back to the tested output.
7. Verify that the physical cable connects the configured output to the configured input.
8. Do not connect a speaker-level amplifier output to an audio-interface input.

Avoid creating an uncontrolled feedback path.

For example, this routing is unsafe:

```text
framework output
      │
      ▼
interface output
      │
      ▼
interface input
      │
      ▼
direct/software monitoring
      │
      └──────────────► same interface output
```

The framework's default loopback signal amplitude is deliberately below full scale, but software amplitude does not control analogue output level, input gain or downstream amplification.

Hardware gain and monitoring settings must still be configured safely.

On interfaces where a front-panel monitor/output control also controls the tested line outputs, that hardware control is part of the physical signal path.

During Scarlett testing, setting the analogue output control to minimum removed the usable physical return, while excessive output/input level could drive the captured signal to clipping.

Use a moderate repeatable hardware level for validation rather than treating software amplitude as the only gain control.

---

## Test Signal

Loopback validation uses a configurable sine wave.

Example:

```yaml
loopback:
  output_channel: 0
  input_channel: 0

  signal_duration_seconds: 1.0
  frequency_hz: 1000.0
  amplitude: 0.25

  frequency_tolerance_hz: 5.0
  padding_seconds: 0.1
```

The generated reference is mono.

Before playback, the signal is routed to the selected output channel while all other configured output channels contain silence.

Equal-duration silence is added before and after the signal.

For a 48 kHz stream with:

```yaml
signal_duration_seconds: 1.0
padding_seconds: 0.1
```

the playback window contains:

```text
4,800 frames   leading silence
48,000 frames  test signal
4,800 frames   trailing silence
--------------------------------
57,600 frames  total playback
```

The padding provides space for hardware and driver latency so the captured signal can be aligned before analysis.

---

## Host API Selection

The same physical audio interface can appear as multiple PortAudio devices through different host APIs.

These device entries are not assumed to behave identically.

Use device discovery before physical validation:

```bash
audio-hw inspect-devices
```

Then select the required host API through configuration.

For the current Linux Focusrite validation setup, dedicated example configurations are provided:

```text
configs/example_loopback_alsa.yaml
configs/example_loopback_jack.yaml
```

The direct ALSA configuration at 48 kHz is the known-good physical loopback path used for Phase 5 hardware acceptance.

The JACK configuration is retained for host-API comparison and routing diagnostics.

JACK requires additional care because it exposes an explicit software routing graph. A validation can pass through a software connection without the signal travelling through the physical audio-interface output and input.

A JACK PASS must therefore not automatically be interpreted as physical hardware-loopback evidence.

For the tested Scarlett configuration:

```text
ALSA / 48 kHz / physical cable
    → PASS
    → unattended physical path

JACK / 48 kHz / software or monitor route
    → PASS
    → software path only

JACK / 48 kHz / default physical routing
    → FAIL

JACK / 48 kHz / manually completed physical routing
    → PASS
    → physical path verified
    → requires per-run JACK graph modification
```

Post-Phase 5 diagnostic testing established a working physical JACK path, but the required physical-input connection must currently be added manually after the transient PortAudio JACK client appears.

JACK physical loopback is therefore possible on the tested system but is not currently an unattended framework-only workflow.

Detailed routing results are documented in [`jack-loopback-routing.md`](jack-loopback-routing.md).

Detailed observed hardware results are documented in [`focusrite-loopback-validation.md`](focusrite-loopback-validation.md) so that environment-specific findings remain separate from the general setup procedure and framework requirements.

---

## JACK Routing Considerations

JACK exposes an explicit routing graph, so selecting a PortAudio device does not by itself prove that the application's capture ports are connected to the intended physical hardware inputs.

On the tested Scarlett system, the PortAudio JACK client exposed temporary ports such as:

```text
PortAudio:in_0
PortAudio:in_1
PortAudio:out_0
PortAudio:out_1
```

These ports existed only while the framework's duplex stream was active.

The default JACK graph did not produce a valid physical loopback return.

A valid physical result was obtained only when the original capture routing was retained and the Scarlett physical Input 1 `capture_MONO` source was additionally connected to `PortAudio:in_0`.

The additional connection disappears when the framework closes the PortAudio stream because the PortAudio JACK client itself disappears.

The framework does not currently create or maintain JACK graph connections.

A JACK-based physical validation should therefore distinguish between `stream/device selection` and `JACK graph routing` as separate test preconditions.

Software `monitor_*` routes must also be treated carefully because they can return the generated playback signal digitally without traversing the external analogue loopback path.

---

## Running Physical Loopback Validation

For the verified ALSA configuration:

```bash
audio-hw validate-loopback \
  --config configs/example_loopback_alsa.yaml
```

Human-readable output reports:

- selected backend;
- device;
- host API;
- sample rate;
- input and output channels;
- expected frequency;
- measured frequency;
- frequency error and tolerance;
- RMS;
- peak level;
- DC offset;
- silence detection;
- clipping detection;
- playback, capture and analysed frame counts.

A passing validation exits with code `0`.

A completed validation that fails one or more checks exits with code `1`.

Configuration, device, backend, analysis or reporting errors exit with code `2`.

---

## JSON Output

Use:

```bash
audio-hw validate-loopback \
  --config configs/example_loopback_alsa.yaml \
  --json
```

The JSON result contains:

```text
status
backend
device
stream
routing
audio
frequency
metrics
failures
```

Channel indexes in JSON remain zero-based so they match the framework configuration and internal models.

---

## Saving Evidence

Use `--evidence-dir` to retain validation evidence:

```bash
audio-hw validate-loopback \
  --config configs/example_loopback_alsa.yaml \
  --evidence-dir evidence/linux-alsa
```

The directory contains:

```text
evidence/linux-alsa/
├── playback.wav
├── captured.wav
├── analysed.wav
└── report.json
```

### `playback.wav`

The complete multichannel signal supplied to the backend.

It includes:

- the selected output-channel routing;
- leading silence;
- generated sine wave;
- trailing silence.

### `captured.wav`

The complete multichannel audio returned by the duplex backend.

This is the raw hardware evidence and is retained unchanged for later investigation.

### `analysed.wav`

The aligned mono section extracted from the configured capture channel.

This is the exact audio used for frequency and sample-domain validation.

### `report.json`

Structured evidence containing:

- validation status;
- backend information;
- device metadata;
- device-reported default sample rate;
- configured stream settings;
- channel routing;
- audio dimensions;
- measured frequency;
- validation metrics;
- structured failures;
- evidence file paths.

Evidence is saved for both passing and failing validations.

A validation failure therefore does not discard the captured audio that produced the failure.

---

## Validation Checks

The aligned capture is evaluated using:

- dominant-frequency measurement;
- RMS level;
- peak level;
- DC offset;
- silence detection;
- clipping detection.

Frequency validation compares the measured dominant frequency with:

```yaml
frequency_hz: 1000.0
frequency_tolerance_hz: 5.0
```

For example:

```text
expected frequency: 1000 Hz
measured frequency: 1001 Hz
tolerance:          ±5 Hz
```

passes frequency validation.

Existing sample-domain thresholds are applied through the normal `thresholds` configuration.

Example:

```yaml
thresholds:
  minimum_rms: 0.01
  maximum_peak: 0.95
  maximum_abs_dc_offset: 0.02
  silence_threshold: 0.0001
  clipping_threshold: 1.0
  fail_on_silence: true
  fail_on_clipping: true
```

Failures identify both the metric and configured physical input channel.

---

## Captured-Signal Alignment

Hardware capture does not necessarily return the signal at the exact frame at which playback began.

Latency can be introduced by:

- USB transport;
- audio-interface buffering;
- host API buffering;
- PortAudio buffering;
- ADC and DAC conversion;
- device firmware.

The framework therefore aligns the selected captured input channel against the known generated reference before calculating validation metrics.

The configured leading padding establishes the expected signal location.

Normalized correlation is then used to locate the best matching capture window.

Alignment is insensitive to:

- signal gain differences;
- DC offset;
- polarity inversion.

Those properties are handled separately from signal location.

---

## Interpretation of Frequency Results

Frequency measurement should be interpreted together with captured signal level.

A real hardware capture normally contains some noise even when the intended test signal is absent.

In that situation an FFT can still identify one frequency bin as the largest component of the noise floor.

A reported dominant frequency therefore does not by itself prove that the intended test tone was captured.

For example, if validation also reports:

```text
RMS: very low
Peak: very low
Silence detected: True
```

the reported dominant frequency should be treated as a spectral property of the noise floor rather than a valid measurement of the intended test signal.

The structured validation result should be interpreted as a whole.

---

## Platform Considerations

Physical loopback support depends on the device topology presented by the operating system and host API.

### Linux

A physical interface may be exposed through ALSA, JACK, PulseAudio or other PortAudio-visible routes.

Different host APIs can expose different:

- device indexes;
- channel layouts;
- sample-rate capabilities;
- buffering behaviour;
- duplex behaviour;
- routing behaviour.

The framework therefore uses host-API-aware device matching and separate configurations where required.

The tested Focusrite Scarlett 2i2 successfully completed physical loopback validation through direct ALSA at 48 kHz.

JACK additionally exposes an explicit routing graph. Software routing can return an application's playback signal directly into its capture path, producing a valid software-loopback PASS without proving that the signal travelled through the audio interface's analogue output and input.

When JACK is used for physical hardware validation, inspect the active routing graph and verify that the intended application playback, hardware playback, hardware capture and application capture ports are connected as expected.

On the tested system, default JACK routing did not return the expected physical Scarlett loopback signal at a valid level.

Post-Phase 5 diagnostics demonstrated that physical JACK loopback succeeds when the existing PortAudio capture routing is retained and the physical Input 1 `capture_MONO` source is additionally connected to `PortAudio:in_0`.

Cable A/B/A testing confirmed that the passing result depended on the external physical connection.

Because the PortAudio JACK client is recreated for each validation stream, the additional connection must currently be established manually for every run.

Direct ALSA therefore remains the preferred unattended physical loopback path for the tested environment.

### Windows

Some Windows audio drivers expose the same physical interface as separate input and output PortAudio devices rather than one duplex device.

The current loopback backend requires a single PortAudio device index with both input and output channels.

Where no such endpoint exists, physical loopback validation cannot currently run through that host API even though separate recording and playback validation remain available.

---

## Scope

Phase 5 loopback validation proves that:

- the framework can generate a deterministic test signal;
- the signal can be routed to a configured output channel;
- duplex playback and capture can be executed;
- returned audio can be aligned with the known reference;
- dominant frequency can be measured;
- existing sample-domain metrics can be applied;
- failures can identify the affected metric and input channel;
- raw and analysed evidence can be retained.

It does not currently measure:

- absolute analogue voltage;
- calibrated sound-pressure level;
- total harmonic distortion;
- THD+N;
- frequency response;
- channel crosstalk;
- round-trip latency as a reported validation metric;
- long-duration stream stability.

Those are potential later-phase extensions.
