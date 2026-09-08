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
- PortAudio-visible input and output endpoints;
- a host API and driver capable of opening the selected endpoints for simultaneous capture and playback;
- matching framework configuration for the selected host API and channel layout.

The input and output may be exposed as either:

- one shared PortAudio device supporting both directions; or
- separate PortAudio input and output endpoints.

Legacy configurations using only `device` continue to resolve one shared duplex device.

Platforms or host APIs that expose separate input-only and output-only endpoints can instead configure `input_device` and `output_device` independently.

---

## Duplex Endpoint Selection

Loopback validation supports both shared-device and split-endpoint configurations.

### Shared Device

Existing configurations remain supported:

```yaml
device:
  name_contains: "Scarlett"
  minimum_input_channels: 2
  minimum_output_channels: 2

stream:
  sample_rate: 48000
  input_channels: 2
  output_channels: 2
  block_size: 128
  dtype: float32
```

When neither `input_device` nor `output_device` is configured, the framework resolves `device` exactly once and requires that matched device to provide the configured input and output channel counts.

This preserves the original single-device duplex workflow.

### Separate Input and Output Endpoints

A host API may expose the same physical interface through separate PortAudio endpoints.

For example, a Windows audio interface may appear as:

```text
Input:
Analogue 1 + 2 (Focusrite USB Audio)

Output:
Speakers (Focusrite USB Audio)
```

A split-endpoint loopback configuration can select them independently:

```yaml
device:
  name_contains: "Focusrite USB Audio"

input_device:
  exact_name: "Analogue 1 + 2 (Focusrite USB Audio)"
  host_api_contains: "WASAPI"
  minimum_input_channels: 2

output_device:
  exact_name: "Speakers (Focusrite USB Audio)"
  host_api_contains: "WASAPI"
  minimum_output_channels: 2

stream:
  sample_rate: 48000
  input_channels: 2
  output_channels: 2
  block_size: 128
  dtype: float32
```

The framework resolves the input and output selectors independently and passes their distinct PortAudio device indexes to the duplex backend.

Device indexes are runtime values and should not be stored directly in configuration. Use device names, host API matching and channel requirements to select endpoints deterministically.

### Selector Fallback

`device` remains mandatory for backward compatibility and also acts as the fallback selector.

The effective selectors are:

```text
input  = input_device  if configured, otherwise device
output = output_device if configured, otherwise device
```

This permits configurations that override only one direction.

For example:

```yaml
device:
  exact_name: "Shared Duplex Device"

output_device:
  exact_name: "Separate Output Device"
```

uses `device` for input selection and `output_device` for output selection.

As soon as either directional selector is configured, input and output resolution is performed independently.

### Direction and Channel Validation

Endpoint resolution validates the configured direction before duplex execution.

The selected input endpoint must provide at least:

```text
stream.input_channels
```

input channels.

The selected output endpoint must provide at least:

```text
stream.output_channels
```

output channels.

An output-only endpoint cannot therefore be selected as the input endpoint, and an input-only endpoint cannot be selected as the output endpoint.

Ambiguous selectors and selectors that match no usable endpoint are rejected before audio execution begins.

Host API matching can be used to distinguish otherwise similar endpoint names.

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
- whether the loopback uses one shared device;
- input device name and index;
- input host API;
- output device name and index;
- output host API;
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
endpoints
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
- resolved input and output endpoint metadata;
- endpoint-reported default sample rates;
- configured stream settings;
- channel routing;
- audio dimensions;
- measured frequency;
- validation metrics;
- structured failures;
- evidence file paths.

Evidence is saved for both passing and failing validations.

A validation failure therefore does not discard the captured audio that produced the failure.

### Endpoint Reporting

Loopback results report the resolved input and output endpoints separately.

Human-readable output includes:

```text
Shared device       False
Input device        Analogue 1 + 2 (Focusrite USB Audio)
Input device index  3
Input host API      WASAPI
Output device       Speakers (Focusrite USB Audio)
Output device index 7
Output host API     WASAPI
```

For a legacy shared-device configuration, both endpoint entries identify the same resolved device and `Shared device` is `True`.

JSON and saved evidence use an `endpoints` object, for example:

```json
{
  "endpoints": {
    "uses_shared_device": false,
    "input": {
      "index": 3,
      "name": "Analogue 1 + 2 (Focusrite USB Audio)",
      "host_api_name": "WASAPI"
    },
    "output": {
      "index": 7,
      "name": "Speakers (Focusrite USB Audio)",
      "host_api_name": "WASAPI"
    }
  }
}
```

The complete endpoint objects also include the PortAudio-reported channel capabilities, default sample rate and default-device flags.

Recording the exact resolved endpoints is important because PortAudio device indexes and host API exposure can change between systems, driver versions and reboots.

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

### Split Endpoints and Clock Domains

Support for separate PortAudio input and output endpoints means that the framework can attempt duplex execution using different PortAudio device indexes.

It does **not** mean that arbitrary physical audio devices are guaranteed to share a sample clock.

When the selected endpoints belong to the same physical interface and driver, the driver or host API may provide the synchronization required for stable duplex operation even though PortAudio exposes separate input and output entries.

When the endpoints belong to different physical devices, each device may run from an independent hardware clock.

Independent clocks can drift relative to one another during capture and playback. Depending on the host API, driver and hardware, this may result in:

- PortAudio rejecting the endpoint pair;
- stream-opening failure;
- input overflow or output underflow;
- gradual timing drift;
- changing alignment over longer captures;
- dropped or repeated samples;
- unstable long-duration loopback behaviour.

The framework does not currently perform clock synchronization, sample-rate conversion or drift compensation between independent devices.

For physical validation, prefer input and output endpoints belonging to the same physical interface, driver and host API unless the hardware is externally synchronized or the platform audio stack explicitly provides synchronization.

A successful loopback run demonstrates that the selected endpoint pair worked for that validation run. It should not be interpreted as proof that arbitrary endpoint combinations are clock-compatible or stable for unlimited duration.

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

Loopback validation can resolve those input and output endpoints independently and pass their distinct PortAudio device indexes to the duplex backend.

Whether a particular endpoint pair can be opened simultaneously remains dependent on PortAudio, the selected Windows host API, the installed driver and the hardware topology.

The Scarlett split-endpoint workflow has automated test coverage but should not be treated as Windows hardware-validated until the corresponding physical loopback test has been completed and recorded.

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
