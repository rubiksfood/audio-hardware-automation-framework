# Recording and Playback Validation

Phase 3 adds finite recording and playback execution to the Audio Hardware Automation Framework.

The framework validates whether configured audio hardware can complete bounded recording and playback operations while preserving backend-independent application services and framework-owned result types.

## Recording Validation

Run recording validation with:

```bash
audio-hw validate-recording \
  --config configs/scarlett_windows_wasapi_input.yaml
```

JSON output is also available:

```bash
audio-hw validate-recording \
  --config configs/scarlett_windows_wasapi_input.yaml \
  --json
```

## Recording Workflow

The command performs the following steps:

1. Loads and validates the YAML configuration.
2. Verifies that the configured stream has at least one input channel.
3. Enumerates visible audio devices.
4. Finds exactly one device matching the configured rules.
5. Validates the configured input stream capability.
6. Converts the configured duration into an exact frame count.
7. Records the requested number of frames through the selected backend.
8. Verifies the returned frame count, sample rate, and channel count.
9. Optionally exports the recording as a WAV file.
10. Reports a successful result.

The recording operation fails if the backend does not return the requested number of frames.

## Recording Configuration

Example:

```yaml
device:
  name_contains: "Focusrite USB Audio"
  host_api_contains: "WASAPI"
  minimum_input_channels: 2

stream:
  sample_rate: 48000
  input_channels: 2
  output_channels: 0
  block_size: 128
  dtype: float32

execution:
  duration_seconds: 1.0
  timeout_seconds: 5.0
  output_file: recordings/capture.wav
```

### `duration_seconds`

Controls the requested finite recording duration.

The recording service converts the duration into a frame count using the configured sample rate.

For example:

```text
1.0 second × 48000 Hz = 48000 frames
```

### `timeout_seconds`

Defines the maximum execution period used by the audio backend.

A recording timeout is reported as an execution failure.

### `output_file`

Optional path used to export the captured audio as a WAV file.

When the value is `null`, the recording remains available through the framework-owned result but is not written to disk.

## Playback Validation

A simple end-to-end workflow is to first configure recording validation to export a WAV file:

```yaml
execution:
  output_file: recordings/capture.wav
```

Then run recording validation:

```bash
audio-hw validate-recording \
  --config configs/scarlett_windows_wasapi_input.yaml
```

Use the generated file for playback validation:

```bash
audio-hw validate-playback \
  --config configs/scarlett_windows_wasapi_output.yaml \
  --input recordings/capture.wav
```

The `--input` option can point to any compatible WAV file; the generated recording is simply the recommended self-contained validation workflow.

JSON output is also available:

```bash
audio-hw validate-playback \
  --config configs/scarlett_windows_wasapi_output.yaml \
  --input recordings/capture.wav \
  --json
```

## Playback Workflow

The command performs the following steps:

1. Loads and validates the YAML configuration.
2. Reads the input WAV file into a framework-owned `AudioBuffer`.
3. Verifies that the configured stream has at least one output channel.
4. Verifies that the buffer contains at least one frame.
5. Verifies that the WAV sample rate matches the configured stream.
6. Verifies that the WAV channel count matches the configured output channels.
7. Enumerates visible audio devices.
8. Finds exactly one device matching the configured rules.
9. Validates the configured output stream capability.
10. Plays the complete finite audio buffer through the selected backend.
11. Reports a successful result.

Playback duration is determined by the number of frames in the input `AudioBuffer`. The configured `duration_seconds` value does not truncate or extend playback.

## WAV Handling

The framework uses a two-dimensional audio representation:

```text
(frames, channels)
```

Mono audio is therefore represented as:

```text
(frames, 1)
```

rather than a one-dimensional array.

WAV files are read into float32 framework-owned audio buffers.

When integer samples are exported, they are normalized before writing to floating-point WAV format.

Recording export creates missing parent directories automatically.

## Backend Independence

Recording and playback application services depend on the `AudioBackend` abstraction rather than directly on PortAudio.

Both the deterministic fake backend and the PortAudio backend use the same framework-owned contracts.

This allows hardware-independent unit testing of execution workflows.

## Failure Handling

Recording validation can fail because of:

- Configuration errors
- No matching device
- Ambiguous device matching
- Unsupported stream settings
- PortAudio stream errors
- Recording timeout
- Input overflow
- Incorrect backend recording result
- WAV export failure

Playback validation can fail because of:

- Configuration errors
- Missing or invalid WAV input
- No matching device
- Ambiguous device matching
- Unsupported stream settings
- Sample-rate mismatch
- Channel-count mismatch
- PortAudio stream errors
- Playback timeout
- Output underflow

CLI validation failures exit with code `2`.

## Validation Boundaries

Recording and playback validation covers:

- Device selection
- Stream capability
- Finite recording execution
- Exact recording frame count
- Finite playback execution
- Audio-buffer shape and metadata
- WAV import and export
- Timeout handling
- Backend execution failures

Recording and playback validation does not by itself validate:

- Signal quality
- Frequency response
- Noise floor
- Distortion
- Clipping analysis
- Measured sample-rate accuracy
- Round-trip latency
- Loopback correctness
- Long-duration stability
