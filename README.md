# Audio Hardware Automation Framework

[![CI](https://github.com/rubiksfood/audio-hardware-automation-framework/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/rubiksfood/audio-hardware-automation-framework/actions/workflows/ci.yml)

A Python-based framework for automated audio hardware testing and validation.

This project demonstrates QA automation, hardware testing, configuration-driven validation, CI-friendly test design, and cross-platform audio device discovery. It is being developed as a portfolio project targeting Audio QA Engineer, Hardware QA Engineer, Embedded QA Engineer, and Software QA Engineer roles within the audio technology industry.

---

## Project Status

**Phase 2 complete — configuration-driven stream validation**

Completed capabilities include:

- Cross-platform audio device discovery
- Host API-aware device matching
- Input-only, output-only, and duplex stream validation
- PortAudio capability checks
- Safe stream construction and closure
- Rich CLI and structured JSON reporting
- Windows and Linux hardware validation

**Current development:** Phase 3 — recording and playback foundations.

See the [Roadmap](#roadmap) for planned development.

---

## Project Goals

The framework aims to provide a reusable foundation for automated testing of audio hardware such as:

- Audio interfaces
- USB audio devices
- Embedded audio hardware
- Audio drivers
- Recording and playback systems

The current focus is reliable device discovery, configuration management, hardware identification, stream-capability validation, and safe stream-opening checks.

Future releases will add playback, recording, loopback testing, measured sample-rate verification, audio quality analysis, latency observation, and stability testing.

---

## Current Features

### Device Discovery

Enumerate audio devices through PortAudio using Python's `sounddevice` package.

The framework collects:

- Device name
- Host API name
- Host API index
- Input channel count
- Output channel count
- Default sample rate

Example:

```text
Index  Device                                Host API  Inputs  Outputs  Default Rate
0      Analogue 1 + 2 (Focusrite USB Audio)  WASAPI    2       0        48000 Hz
1      Speakers (Focusrite USB Audio)        WASAPI    0       2        48000 Hz
...
```

Example output shortened for readability.

Supported matching rules:

- Exact device name
- Partial device name
- Host API matching
- Minimum input channels
- Minimum output channels

Example:

```yaml
device:
  name_contains: "Focusrite USB Audio"
  host_api_contains: "WASAPI"
  minimum_input_channels: 2
```

This allows the framework to distinguish between multiple entries representing the same physical audio interface across different host APIs.

---

### Command-Line Interface

Inspect available audio devices:

```bash
audio-hw inspect-devices
```

Inspect devices using a configuration:

```bash
audio-hw inspect-devices --config configs/scarlett_windows_wasapi_input.yaml
```

Output JSON:

```bash
audio-hw inspect-devices --json
```

Validate a configured stream:

```bash
audio-hw validate-stream --config configs/example_duplex_device.yaml
```

Output validation results as JSON:

```bash
audio-hw validate-stream \
  --config configs/example_duplex_device.yaml \
  --json
```

The validation command requires exactly one matching device. It checks whether PortAudio accepts the requested stream settings and whether the requested stream can be constructed and closed safely.

---

### Stream Validation

Configuration-driven validation supports:

- Input-only streams
- Output-only streams
- Duplex streams
- Sample-rate capability checks
- Input and output channel checks
- Strongly typed sample formats
- Configurable or backend-selected block sizes
- Safe stream construction and closure
- Human-readable and JSON results

Validation is implemented through a backend-independent application service. This separates workflow orchestration from PortAudio-specific behaviour and allows deterministic hardware-independent testing.

A successful stream-opening result does not start recording or playback and does not yet prove end-to-end audio signal quality.

See [`docs/stream-validation.md`](docs/stream-validation.md) for validation scope, limitations, exit codes and the hardware test procedure.

---

### Structured Device Models

The framework uses strongly typed Pydantic models for:

- Audio devices
- Device matching rules
- Stream configuration
- Framework configuration

This provides validation and predictable configuration handling.

---

### Cross-Platform Design

Current development targets:

- Windows 11
- Ubuntu Linux

Audio backends are abstracted to support future expansion.

---

### Automated Testing

The project includes:

- Unit tests
- Device matching tests
- Configuration validation tests
- Backend abstraction tests
- PortAudio capability-validation tests
- Stream-opening tests
- Validation-service orchestration tests
- CLI tests

GitHub Actions runs hardware-independent tests, linting, formatting checks, type checking, and coverage reporting on Ubuntu.

Current coverage target:

95%+

---

### Host API Awareness

The framework resolves host API information reported by PortAudio.

Examples:

- WASAPI
- MME
- DirectSound
- Windows WDM-KS
- ALSA
- JACK
- PulseAudio

This enables more reliable device matching on systems where the same physical interface appears multiple times through different audio subsystems.

---

## Current Architecture

```text
audio-hardware-automation-framework/
│
├── configs/
│   ├── example_duplex_device.yaml
│   │
│   ├── scarlett_windows_mme_input.yaml
│   ├── scarlett_windows_mme_output.yaml
│   │
│   ├── scarlett_windows_directsound_input.yaml
│   ├── scarlett_windows_directsound_output.yaml
│   │
│   ├── scarlett_windows_wasapi_input.yaml
│   ├── scarlett_windows_wasapi_output.yaml
│   │
│   ├── scarlett_windows_wdmks_input.yaml
│   ├── scarlett_windows_wdmks_output.yaml
│   │
│   ├── scarlett_linux_alsa.yaml
│   │
│   ├── scarlett_linux_jack.yaml
│   │
│   ├── scarlett_linux_pulseaudio_input1.yaml
│   ├── scarlett_linux_pulseaudio_input2.yaml
│   └── scarlett_linux_pulseaudio_output.yaml
│
├── docs/
│   ├── discovery.md
│   ├── platform-support.md
│   ├── stream-validation.md
│   └── images/
│       ├── phase-1-github-actions-passing.png
│       ├── phase-1-linux-device-discovery.png
│       ├── phase-1-pytest-coverage.png
│       ├── phase-1-wdmks-hotplug-verification.png
│       ├── phase-1-windows-device-discovery.png
│       ├── phase-2-linux-duplex-validation.png
│       ├── phase-2-negative-validation.png
│       └── phase-2-stream-validation.png
│
├── src/
│   └── audio_hw_framework/
│       ├── backend/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── fake_backend.py
│       │   └── sounddevice_backend.py
│       │
│       ├── configuration/
│       │   ├── __init__.py
│       │   └── loader.py
│       │
│       ├── device/
│       │   ├── __init__.py
│       │   ├── matcher.py
│       │   └── models.py
│       │
│       ├── validation/
│       │   ├── __init__.py
│       │   └── service.py
│       │
│       ├── __init__.py
│       ├── __main__.py
│       └── cli.py
│
├── tests/
│   └── unit/
│       ├── test_backend.py
│       ├── test_cli.py
│       ├── test_configuration.py
│       ├── test_device_matching.py
│       ├── test_models.py
│       ├── test_package.py
│       ├── test_sounddevice_backend.py
│       └── test_validation_service.py
│
├── pyproject.toml
├── README.md
└── LICENSE
```

---

## Installation

Clone the repository:

```bash
git clone <repository-url>
cd audio-hardware-automation-framework
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

Windows:

```bash
.venv\Scripts\activate
```

Linux:

```bash
source .venv/bin/activate
```

Install the project:

```bash
pip install -e ".[dev]"
```

---

## Usage

### List Devices

```bash
audio-hw inspect-devices
```

### Match Devices Using Configuration

```bash
audio-hw inspect-devices \
    --config configs/scarlett_windows_wasapi_input.yaml
```

### JSON Output

```bash
audio-hw inspect-devices --json
```

---

### No Devices Found

When no audio devices are detected:

#### Table Output

```bash
audio-hw inspect-devices
```

The command displays:

```text
No audio devices detected.
```

and exits with code `1`.

#### JSON Output

```bash
audio-hw inspect-devices --json
```

The command returns:

```json
{
  "backend": {
    "name": "portaudio",
    "library": "sounddevice",
    "library_version": "..."
  },
  "devices": []
}
```

and exits successfully.

This behaviour allows automated tooling to distinguish between command failures and valid enumeration results containing no devices.

---

## Example Configuration

```yaml
device:
  name_contains: "Focusrite USB Audio"
  host_api_contains: "WASAPI"
  minimum_input_channels: 2
  minimum_output_channels: 0

stream:
  sample_rate: 48000
  input_channels: 2
  output_channels: 0
  block_size: null
  dtype: "float32"
```

---

## Tested Hardware

### Focusrite Scarlett 2i2 (3rd Gen)

Current validation:

- Device enumeration
- Host API discovery
- Host API filtering
- Device matching
- CLI inspection
- Configuration loading
- Cross-platform discovery
- Windows host API validation (MME, DirectSound, WASAPI, WDM-KS)
- Linux host API validation (ALSA, JACK, PulseAudio)
- Audio-stack-specific device matching
- Configuration-driven unique device selection
- PortAudio input/output capability validation
- Input-only, output-only or duplex stream construction
- Configured block-size application during stream construction
- Safe stream closure without recording or playback
- Structured CLI and JSON validation reporting

Platforms tested:

- Windows 11 25H2
- Ubuntu Linux 26.04 LTS

---

## Documentation

Additional documentation is available in:

### Discovery

```text
docs/discovery.md
```

Explains:

- What device discovery does
- What it does not prove
- Device matching behaviour
- PortAudio limitations

### Platform Support

```text
docs/platform-support.md
```

Explains:

- Supported operating systems
- Host APIs
- CI limitations
- Hardware validation scope

### Stream Validation

```text
docs/stream-validation.md
```

Explains:

* Validation workflow
* Supported stream directions
* CLI and JSON output
* Exit codes
* Validation scope and limitations
* Focusrite hardware-validation procedure

## Evidence

### Windows device discovery

![Windows device discovery](docs/images/phase-1-windows-device-discovery.png)

### Linux device discovery

![Linux device discovery](docs/images/phase-1-linux-device-discovery.png)

### GitHub Actions

![GitHub Actions passing](docs/images/phase-1-github-actions-passing.png)

### pytest coverage

![pytest coverage](docs/images/phase-1-pytest-coverage.png)

### WDM-KS hotplug verification

![WDM-KS hotplug verification](docs/images/phase-1-wdmks-hotplug-verification.png)

---

## Roadmap

### Phase 1 — Device discovery and configuration

**Complete**

- Backend abstraction
- PortAudio device enumeration
- Typed YAML configuration
- Host API-aware device matching
- Rich and JSON device inspection
- Cross-platform hardware discovery

### Phase 2 — Stream capability and opening validation

**Complete**

- Strongly typed stream configuration
- Input-only, output-only, and duplex validation
- PortAudio capability checks
- Stream construction and safe closure
- Validation orchestration service
- `validate-stream` CLI command
- Structured validation reporting
- Windows and Linux hardware validation

### Phase 3 — Recording and playback foundations

**Planned**

- Finite-duration recording
- Finite-duration playback
- Audio buffer result models
- WAV import and export
- Execution services and CLI commands

### Later phases

- Signal generation and analysis
- Loopback validation
- Latency and stream-health measurement
- Stability and recovery testing
- Validation profiles and report generation

---

## Technologies

- Python 3.13
- Pydantic
- PyYAML
- sounddevice
- PortAudio
- pytest
- mypy
- Ruff
- Typer
- Rich

---

## QA Engineering Skills Demonstrated

This project demonstrates:

- Test automation design
- Configuration-driven testing
- Hardware abstraction
- Audio subsystem awareness (WASAPI, ALSA, JACK)
- Configuration-driven hardware selection
- API design
- Defensive programming
- Cross-platform testing considerations
- CI-friendly test strategies
- Structured logging and reporting preparation
- Python QA tooling
- Automated validation framework development
- Layered application architecture
- Backend-independent workflow orchestration
- Framework-owned exception translation
- Deterministic test doubles
- Stream lifecycle validation
- Human-readable and machine-readable reporting

---

## License

MIT License
