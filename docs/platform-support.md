# Platform Support

## Overview

The Audio Hardware Automation Framework is intended to support automated audio hardware testing across multiple operating systems.

Current functionality is based on PortAudio through the Python `sounddevice` package.

Development and validation are currently focused on Windows and Linux environments.

---

## Supported Platforms

### Windows

Tested on:

- Windows 11 25H2

Expected host APIs:

- WASAPI
- MME
- DirectSound
- Windows WDM-KS

Notes:

- The same physical device may appear multiple times.
- Device names can vary between host APIs.
- Driver naming conventions may differ.

Example:

```text
Analogue 1 + 2 (Focusrite USB Audio)
Speakers (Focusrite USB Audio)
```

### Windows Host API Behaviour

The Focusrite Scarlett 2i2 (3rd Gen) was detected through multiple Windows host APIs:

- MME
- Windows DirectSound
- Windows WASAPI
- Windows WDM-KS

Each host API exposed separate input and output endpoints.

Examples:

```text
Analogue 1 + 2 (Focusrite USB Audio)
Speakers (Focusrite USB Audio)
```

The same physical interface therefore appeared multiple times during enumeration.

Configuration files are provided per host API to ensure deterministic device selection during testing.

---

### Linux

Tested on:

- Ubuntu 26.04 LTS

Expected host APIs:

- ALSA
- JACK
- PulseAudio

Notes:

- Device naming differs significantly between distributions.
- Audio routing layers may expose virtual devices.
- Physical devices may appear multiple times.

Example:

```text
Scarlett 2i2 USB
hw:USB,0
```

### Linux Host API Behaviour

The Focusrite Scarlett 2i2 (3rd Gen) was detected through multiple Linux host APIs:

- ALSA
- JACK Audio Connection Kit
- PulseAudio

The same physical interface appeared differently depending on the host API.

Examples:

```text
ALSA
Scarlett 2i2 USB: Audio

JACK
Scarlett 2i2 USB-64

PulseAudio
alsa_input.usb-Focusrite_Scarlett_2i2_USB...
alsa_output.usb-Focusrite_Scarlett_2i2_USB...
```

Different host APIs exposed different channel counts and device structures.

Configuration files are therefore provided separately for each Linux host API.

---

## Current Functional Coverage

Currently implemented:

- Audio device enumeration
- Device metadata collection
- Device matching
- CLI device inspection
- JSON device reporting

Not yet implemented:

- Audio playback
- Audio recording
- Loopback testing
- Sample-rate validation
- Buffer-size validation
- Latency measurement
- Long-duration stability testing
- Driver validation

---

## Hardware Validated

### Focusrite Scarlett 2i2 (3rd Gen)

Validated areas:

- Device discovery
- Device matching
- CLI inspection
- Cross-platform enumeration

Operating systems tested:

- Windows 11 25H2
- Ubuntu 26.04 LTS

---

### Windows WDM-KS Verification

Two Windows WDM-KS endpoints were observed:

```text
Analogue 1 + 2 (wc4800_8210)
Speakers (wr4800_8210)
```

These endpoints were verified through device hot-plug testing.

Verification procedure:

1. Enumerate devices with the Scarlett connected.
2. Disconnect the Scarlett.
3. Enumerate devices again.
4. Reconnect the Scarlett.
5. Enumerate devices a third time.

The WDM-KS endpoints disappeared when the Scarlett was disconnected and reappeared when it was reconnected.

This confirms that the endpoints belong to the Scarlett 2i2 and are not generic system devices.

---

## CI/CD Considerations

Most CI environments do not provide access to physical audio hardware.

The following components are CI-safe:

- Configuration validation
- Device matching
- CLI behaviour
- Backend abstraction
- JSON reporting

Hardware-dependent testing should be separated and explicitly marked.

Example:

```python
@pytest.mark.hardware
def test_loopback_recording() -> None: ...
```

This allows CI pipelines to execute deterministic tests while reserving hardware validation for dedicated test environments.

GitHub Actions installs the PortAudio runtime so that `sounddevice` can be imported, but it does not provide access to physical audio hardware.

---

## Known Limitations

### Device Ordering

Audio device indices are not guaranteed to remain stable.

Device ordering can change after:

- Reboots
- Driver updates
- Hardware changes
- Operating system updates

Tests should rely on matching rules rather than indices.

---

### Host API Behaviour

Different host APIs may expose:

- Different device names
- Different channel counts
- Different capabilities

Framework users should verify behaviour on the specific platform and driver configuration being tested.

---

### Default Sample Rate Differences

The framework records the default sample rate reported by PortAudio.

This value represents the default operating mode exposed by the host API and should not be interpreted as the complete set of supported sample rates.

Observed values for the same Scarlett 2i2:

| Platform | Host API    | Reported Default Rate |
|----------|-------------|-----------------------|
| Windows  | WASAPI      | 48000 Hz              |
| Windows  | MME         | 44100 Hz              |
| Windows  | DirectSound | 44100 Hz              |
| Linux    | ALSA        | 44100 Hz              |
| Linux    | JACK        | 48000 Hz              |
| Linux    | PulseAudio  | 48000 Hz              |

These differences likely reflect operating-system and audio-subsystem configuration rather than hardware limitations.

Future framework versions will include explicit sample-rate capability validation.

---

### PulseAudio Device Structure

PulseAudio did not expose the Scarlett as a single duplex device.

Instead, separate logical endpoints were presented for:

- Playback
- Capture
- Monitor sources

Two separate capture endpoints were exposed, one for each input.

Examples:

```text
alsa_output.usb-Focusrite_Scarlett_2i2_USB...
alsa_input.usb-Focusrite_Scarlett_2i2_USB...Mic1...
alsa_input.usb-Focusrite_Scarlett_2i2_USB...Mic2...
```

Separate framework configuration files are therefore provided for:

- PulseAudio output validation
- PulseAudio input 1 validation
- PulseAudio input 2 validation

This behaviour differs from ALSA and JACK, which exposed the interface as a duplex device.

---

## Future Validation Targets

Future validation is planned against hardware from:

- Native Instruments
- RME
- Steinberg
- Arturia

Additional operating systems and host APIs may be evaluated as framework capabilities expand.

---

## Summary

Current platform support focuses on:

- Windows
- Linux
- PortAudio-compatible devices

The framework is designed to grow toward broader hardware validation while maintaining cross-platform compatibility.