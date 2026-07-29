# Stream Validation

The `validate-stream` command validates whether a configured audio device can support and open a requested PortAudio stream.

```bash
audio-hw validate-stream --config configs/example_duplex_device.yaml
```

JSON output is also available:

```bash
audio-hw validate-stream \
  --config configs/example_duplex_device.yaml \
  --json
```

## Validation Workflow

The command performs the following steps in order:

1. Loads and validates the YAML configuration.
2. Enumerates audio devices through the configured backend.
3. Finds exactly one device matching the configured rules.
4. Checks the requested input and output settings with PortAudio.
5. Constructs the requested audio stream.
6. Closes the stream without starting recording or playback.
7. Reports a successful validation result.

Validation stops immediately when any step fails.

## Validated Settings

The capability check validates:

* Device index
* Sample rate
* Input channel count
* Output channel count
* Sample dtype

The stream-opening check additionally applies:

* Stream direction
* Configured block size
* PortAudio stream construction
* Host API and driver availability at the time of validation

When `block_size` is `null`, the framework passes `0` to PortAudio so the backend can select an appropriate block size.

## Supported Stream Directions

### Input-only

```yaml
stream:
  sample_rate: 48000
  input_channels: 2
  output_channels: 0
  block_size: null
  dtype: float32
```

The framework checks and opens an input stream only.

### Output-only

```yaml
stream:
  sample_rate: 48000
  input_channels: 0
  output_channels: 2
  block_size: null
  dtype: float32
```

The framework checks and opens an output stream only.

### Duplex

```yaml
stream:
  sample_rate: 48000
  input_channels: 2
  output_channels: 2
  block_size: 128
  dtype: float32
```

The framework checks both directions and opens a duplex stream.

A duplex configuration currently uses one matched PortAudio device index for both input and output. It therefore requires an endpoint that PortAudio reports as supporting both directions.

Some host APIs expose separate input and output endpoints for the same physical interface. Those endpoints must currently be validated using separate input-only and output-only configurations.

## Successful Output

Example table output:

```text
       Stream validation passed
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Setting         ┃ Value                        ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Backend         │ portaudio                    │
│ Library         │ sounddevice                  │
│ Device          │ Focusrite Scarlett 2i2 USB   │
│ Device index    │ 4                            │
│ Host API        │ WASAPI                       │
│ Sample rate     │ 48000 Hz                     │
│ Input channels  │ 2                            │
│ Output channels │ 0                            │
│ Block size      │ automatic                    │
│ Data type       │ float32                      │
└─────────────────┴──────────────────────────────┘
```

Device names and indexes depend on the operating system, driver and host API.

Example JSON structure:

```json
{
  "status": "passed",
  "backend": {
    "name": "portaudio",
    "library": "sounddevice",
    "library_version": "<installed-version>"
  },
  "device": {
    "index": 4,
    "name": "Focusrite Scarlett 2i2 USB",
    "host_api_index": 2,
    "host_api_name": "WASAPI",
    "max_input_channels": 2,
    "max_output_channels": 0,
    "default_sample_rate": 48000.0,
    "is_default_input": false,
    "is_default_output": false
  },
  "stream": {
    "sample_rate": 48000,
    "input_channels": 2,
    "output_channels": 0,
    "block_size": null,
    "dtype": "float32"
  },
  "checks": {
    "capability": "passed",
    "stream_opening": "passed"
  }
}
```

## Exit Codes

| Exit code | Meaning                                                                      |
| --------: | ---------------------------------------------------------------------------- |
|       `0` | Validation completed successfully                                            |
|       `2` | Configuration, device matching, backend capability or stream-opening failure |

Examples of exit-code `2` failures include:

* Configuration file not found
* Invalid YAML or configuration values
* No matching device
* More than one matching device
* Unsupported channel configuration
* Unsupported sample rate or dtype
* Device unavailable
* Stream construction rejected by PortAudio

## What Stream Validation Proves

A successful result demonstrates that, at the time of execution:

* The configuration is structurally valid.
* Exactly one PortAudio device matches the configured rules.
* PortAudio accepts the requested input and output settings.
* The requested stream object can be constructed.
* The stream can be closed safely without being started.

## What Stream Validation Does Not Prove

A successful result does not yet prove:

* Audio can be recorded successfully.
* Audio can be played successfully.
* The physical signal path is correct.
* The requested sample rate is used by the external hardware throughout the complete signal path.
* The effective callback block size equals the requested value.
* The stream remains stable over time.
* Audio is free from clipping, noise, dropouts or distortion.
* Input and output latency meet a target.
* Hot-plug recovery works while a stream is active.

Those behaviours require later recording, playback, loopback, measurement and stability phases.

## Hardware Validation Procedure

The following procedure should be run with the real audio interface connected.

### Preparation

1. Connect the Focusrite Scarlett 2i2.
2. Confirm that the expected driver or Linux audio service is active.
3. Close DAWs and other applications that may hold the device exclusively.
4. Inspect the available endpoints:

```bash
audio-hw inspect-devices
```

5. Confirm that the selected configuration matches exactly one endpoint:

```bash
audio-hw inspect-devices \
  --config configs/<configuration-file>.yaml
```

The output should report:

```text
Matched 1 device(s).
```

### Capability and Opening Validation

Run:

```bash
audio-hw validate-stream \
  --config configs/<configuration-file>.yaml
```

Then run the JSON form:

```bash
audio-hw validate-stream \
  --config configs/<configuration-file>.yaml \
  --json
```

Confirm that:

* The command exits with code `0`.
* The correct Focusrite endpoint is selected.
* The expected host API is reported.
* The requested sample rate is reported.
* The requested input and output channel counts are reported.
* `capability` is `passed`.
* `stream_opening` is `passed`.

### Negative Validation

Temporarily use a configuration that cannot match the connected endpoint, for example an invalid device name:

```yaml
device:
  exact_name: "Device That Does Not Exist"
  minimum_input_channels: 0
  minimum_output_channels: 0
```

Run:

```bash
audio-hw validate-stream --config configs/<negative-configuration>.yaml
```

Confirm that:

* The command exits with code `2`.
* The error reports that no device matched.
* No stream capability or opening validation is attempted.

Do not commit a temporary negative-test configuration unless it is intentionally retained as a documented test fixture.

## Phase 2 Hardware Validation Record

### System

* Date: 2026-07-29
* Operating system: Windows 11 Home
* Python: 3.13.x
* Interface: Focusrite Scarlett 2i2 (3rd Gen)
* Driver or audio stack: Focusrite USB driver
* Host API: Windows WASAPI
* Configuration (input): `configs/scarlett_windows_wasapi_input.yaml`
* Configuration (output): `configs/scarlett_windows_wasapi_output.yaml`

### Results

| Check                 | Expected                          | Actual                       | Result |
| --------------------- | --------------------------------- | ---------------------------- | ------ |
| Device enumeration    | Focusrite endpoint detected       | Correctly listed             | PASS   |
| Unique matching       | Exactly one device matched        | `Matched 1 device(s).`       | PASS   |
| Capability validation | Requested settings accepted       | `"capability": "passed"`     | PASS   |
| Stream opening        | Stream constructed and closed     | `"stream_opening": "passed"` | PASS   |
| JSON output           | Structured passed result returned | As expected                  | PASS   |
| Invalid device match  | Exit code `2` and clear error     | As expected                  | PASS   |

### Notes

Both input-only and output-only Windows configurations were tested successfully. A Linux ALSA duplex configuration was also validated successfully. Temporary configurations were used to confirm negative device matching and explicit `block_size: 128` stream construction; both checks passed.

### Evidence

![Phase 2 stream validation](images/phase-2-stream-validation.png)

![Phase 2 negative validation](images/phase-2-negative-validation.png)

![Phase 2 Linux duplex validation](images/phase-2-linux-duplex-validation.png)
