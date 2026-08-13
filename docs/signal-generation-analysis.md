# Signal Generation and Sample-Domain Analysis

Phase 4 adds deterministic signal generation and basic sample-domain audio analysis to the Audio Hardware Automation Framework.

The implementation provides framework-owned synthetic signals, deterministic metric calculations, configurable validation thresholds, per-channel results, and structured validation failures.

All analysis operates on framework-owned `AudioBuffer` instances.

## Signal Generation

The framework can generate:

- Sine waves
- Silence

Generated signals are returned as `AudioBuffer` instances using the framework's standard two-dimensional sample representation:

```text
(frames, channels)
```

Generated samples use `float32`.

### Sine-Wave Generation

Sine-wave generation is configured using `SineWaveConfig`.

Example:

```python
from audio_hw_framework.signal import (
    SineWaveConfig,
    generate_sine_wave,
)

audio = generate_sine_wave(
    SineWaveConfig(
        sample_rate=48_000,
        duration_seconds=1.0,
        channel_count=2,
        frequency_hz=1_000.0,
        amplitude=0.5,
    )
)
```

The generated signal:

- Uses the configured sample rate.
- Uses the configured duration.
- Uses the configured channel count.
- Starts at zero phase.
- Generates the same waveform on every configured channel.
- Uses normalized amplitude values from `0.0` to `1.0`.
- Requires the sine frequency to remain below the Nyquist frequency.

The number of generated frames is calculated from:

```text
duration_seconds × sample_rate
```

and rounded to the nearest integer frame.

Configurations producing no audio frames are rejected.

### Silence Generation

Silence generation is configured using `SilenceConfig`.

Example:

```python
from audio_hw_framework.signal import (
    SilenceConfig,
    generate_silence,
)

audio = generate_silence(
    SilenceConfig(
        sample_rate=48_000,
        duration_seconds=1.0,
        channel_count=2,
    )
)
```

Every generated sample is exactly zero.

## Sample-Domain Analysis

Phase 4 implements:

- RMS level
- Peak level
- DC offset
- Silence detection
- Clipping detection

Numeric metrics return:

- An overall value
- One value per channel

Detection metrics return:

- An overall detection result
- One detection result per channel

Analysis rejects empty audio buffers.

### RMS Level

RMS is calculated as:

```text
sqrt(mean(samples²))
```

Per-channel RMS is calculated independently for each channel.

The overall RMS value is calculated across every sample in the complete buffer.

It is not calculated by averaging the per-channel RMS values.

### Peak Level

Peak level is the largest absolute sample magnitude:

```text
max(abs(samples))
```

Positive and negative sample excursions therefore contribute equally.

Per-channel peak values are calculated independently.

### DC Offset

DC offset is the arithmetic mean of the sample values:

```text
mean(samples)
```

A centred waveform should normally produce a value near zero.

Positive and negative offsets are preserved in the returned result.

### Silence Detection

A channel is considered silent when every absolute sample value is less than or equal to the configured silence threshold.

The default threshold is:

```text
0.0001
```

Overall silence is detected only when every channel is silent.

### Clipping Detection

A channel is considered clipped when any absolute sample value is greater than or equal to the configured clipping threshold.

The default threshold is:

```text
1.0
```

Overall clipping is detected when any channel contains a clipping sample.

## Configurable Thresholds

Sample-domain validation thresholds can be configured in YAML:

```yaml
thresholds:
  minimum_rms: 0.01
  maximum_rms: 0.8
  maximum_peak: 0.95
  maximum_abs_dc_offset: 0.02
  silence_threshold: 0.0001
  clipping_threshold: 1.0
  fail_on_silence: true
  fail_on_clipping: true
```

The available settings are:

### `minimum_rms`

Optional minimum permitted RMS level.

A channel fails when:

```text
actual RMS < minimum_rms
```

### `maximum_rms`

Optional maximum permitted RMS level.

A channel fails when:

```text
actual RMS > maximum_rms
```

### `maximum_peak`

Optional maximum permitted absolute peak level.

A channel fails when:

```text
actual peak > maximum_peak
```

### `maximum_abs_dc_offset`

Optional maximum permitted absolute DC offset.

A channel fails when:

```text
abs(actual DC offset) > maximum_abs_dc_offset
```

### `silence_threshold`

Controls sample-domain silence detection.

Default:

```text
0.0001
```

### `clipping_threshold`

Controls sample-domain clipping detection.

Default:

```text
1.0
```

### `fail_on_silence`

Controls whether detected silence produces a validation failure.

Default:

```text
true
```

### `fail_on_clipping`

Controls whether detected clipping produces a validation failure.

Default:

```text
true
```

Numeric thresholds are inclusive at their permitted boundary.

For example, when:

```yaml
maximum_peak: 0.95
```

a measured peak of exactly `0.95` passes, while a value greater than `0.95` fails.

Clipping detection is intentionally different: a sample exactly equal to the clipping threshold is considered clipped.

## Structured Validation Failures

Threshold validation is performed per channel.

A failure records:

- Metric name
- Channel index
- Actual value or detection state
- Configured threshold
- Human-readable reason

Conceptually:

```text
metric    = "rms"
channel   = 1
actual    = 0.01
threshold = 0.05
reason    = "RMS level is below the configured minimum"
```

Channel indexes in structured framework results are zero-based.
channel   = 1  # zero-based; second channel

This prevents a valid channel from masking a failure on another channel.

## CLI Audio Analysis

Analyse a WAV file using configured thresholds:

```bash
audio-hw analyse-audio \
  --config configs/<configuration-file>.yaml \
  --input recordings/capture.wav
```

Output structured JSON:

```bash
audio-hw analyse-audio \
  --config configs/<configuration-file>.yaml \
  --input recordings/capture.wav \
  --json
```

The command:

1. Loads and validates the YAML configuration.
2. Reads the WAV file into a framework-owned `AudioBuffer`.
3. Calculates RMS.
4. Calculates peak level.
5. Calculates DC offset.
6. Performs silence detection.
7. Performs clipping detection.
8. Applies configured thresholds per channel.
9. Reports the metric results and any structured failures.

`analyse-audio` does not enumerate, open or access physical audio hardware.

It analyses the supplied WAV file only.

## Exit Codes

| Exit code | Meaning |
| --------: | ------- |
| `0` | Analysis completed and all configured thresholds passed |
| `1` | Analysis completed successfully but one or more thresholds failed |
| `2` | Configuration or WAV input could not be processed |

A threshold failure is therefore distinguished from an operational CLI failure.

## Deterministic Testing

Signal generation and sample-domain analysis are hardware-independent.

The unit suite uses known synthetic inputs to verify:

- Exact silence generation
- Deterministic sine-wave generation
- Known sine-wave sample values
- Amplitude scaling
- Per-channel signal generation
- RMS calculations
- Peak calculations
- DC offset calculations
- Silence detection boundaries
- Clipping detection boundaries
- Per-channel threshold failures
- Structured validation reasons

This allows Phase 4 behaviour to run deterministically in CI without physical audio hardware.

## Analysis Limitations

Phase 4 analysis is intentionally limited to the samples already contained in an `AudioBuffer`.

It does not perform frequency-domain, psychoacoustic or hardware-path measurements.

### RMS Limitations

RMS measures the effective magnitude of the supplied samples.

It does not identify:

- Signal frequency
- Harmonic content
- Noise spectrum
- Frequency response
- Distortion components

RMS is also not currently expressed in dBFS.

### Peak Limitations

Peak analysis measures the largest stored sample magnitude.

It does not detect:

- Inter-sample peaks
- Analogue clipping
- Converter saturation
- Downstream hardware clipping

A sample value below the configured clipping threshold does not prove that the physical audio path did not clip.

### DC Offset Limitations

DC offset reports the mean of the supplied digital samples.

It does not directly measure analogue DC voltage at a hardware input or output.

### Silence Detection Limitations

Silence detection is threshold-based.

It does not distinguish between:

- Intended silence
- Muted hardware
- Disconnected inputs
- Extremely low-level signals
- Low-level noise below the configured threshold

The selected threshold therefore determines what the framework considers silent.

### Clipping Detection Limitations

Clipping detection checks whether stored sample magnitudes reach or exceed a configured threshold.

It does not prove the cause of clipping and does not detect clipping that occurred earlier in an analogue or digital signal path if the resulting captured samples remain below the configured threshold.

### Sample-Domain Scope

Phase 4 does not yet measure:

- Frequency response
- Total harmonic distortion
- THD+N
- Signal-to-noise ratio
- Frequency accuracy
- Phase response
- Crosstalk
- Inter-channel delay
- Latency
- Dropouts
- Long-duration stability
- Effective hardware sample rate
- End-to-end loopback correctness

Those require later signal-path, frequency-domain, latency and stability work.

## Phase 4 Scope

Phase 4 establishes deterministic signal generation and basic sample-domain measurement.

It provides the foundation for later loopback validation, where generated signals can be played through hardware, captured again, and compared or measured through the framework.

Phase 4 alone does not prove end-to-end audio hardware quality.