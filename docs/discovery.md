# Device Discovery

## Overview

The Audio Hardware Automation Framework currently focuses on audio device discovery and identification.

Device discovery is the process of enumerating audio devices visible to the operating system through PortAudio and converting that information into framework-specific models.

The framework uses:

- PortAudio
- Python sounddevice
- Configuration-driven device matching

This functionality forms the foundation for future automated audio validation workflows.

---

## What Device Discovery Does

Device discovery confirms that:

- An audio device is visible to PortAudio.
- Device metadata can be retrieved.
- Input channel counts can be queried.
- Output channel counts can be queried.
- Default sample rates can be queried.
- Devices can be identified using configuration rules.

Example:

```text
Index  Device                                Host API  Inputs  Outputs  Default Rate
0      Analogue 1 + 2 (Focusrite USB Audio)  WASAPI    2       0        48000 Hz
1      Speakers (Focusrite USB Audio)        WASAPI    0       2        48000 Hz
...
```

Example output shortened for readability.

The framework can use this information to locate a target device and prepare it for future automated testing.

---

## What Device Discovery Does Not Prove

Discovery alone does not verify audio functionality.

Finding a device does not prove that:

- Recording works.
- Playback works.
- Loopback testing works.
- Drivers are functioning correctly.
- All advertised sample rates are supported.
- Buffer sizes are operating correctly.
- Low-latency operation is possible.
- Long-duration stability is acceptable.

Example:

A device may appear during enumeration while:

- The driver is partially installed.
- Inputs are unavailable.
- Outputs are unavailable.
- Recording fails.
- Playback fails.

Discovery should therefore be considered a prerequisite check rather than a validation result.

---

## Device Matching

The framework identifies devices using configuration rules rather than device indices.

Recommended:

```yaml
device:
  name_contains: "Scarlett"
```

Avoid:

```yaml
device:
  index: 4
```

Device indices can change between:

- Reboots
- Driver updates
- Operating system updates
- Hardware configuration changes

Matching by device characteristics is significantly more reliable.

---

## Multiple Matching Devices

A configuration may match more than one device.

Example:

```text
Focusrite Scarlett 2i2 USB
Focusrite Scarlett Solo USB
```

When unique device selection is requested, the framework raises an ambiguity error rather than selecting a device automatically.

This behaviour is intentional and prevents tests from running against unintended hardware.

---

## Device Name Variability

Device names are not standardized.

The same hardware may appear differently depending on:

- Operating system
- Driver version
- Host API
- Audio subsystem configuration

Examples:

```text
Scarlett 2i2 USB
Focusrite Scarlett 2i2 USB
Speakers (Focusrite USB Audio)
```

For this reason partial matching is generally preferred.

Example:

```yaml
device:
  name_contains: "Focusrite"
```

---

## Host API Differences

The same physical device may appear through multiple host APIs.

Examples include:

### Windows

- WASAPI
- MME
- DirectSound
- Windows WDM-KS

### Linux

- ALSA
- JACK
- PulseAudio

As a result, a single interface may appear multiple times during enumeration.

The framework supports host API filtering through the `host_api_contains` configuration field.

---

## Current Scope

Currently implemented:

- Audio device enumeration
- Device metadata collection
- Device matching
- CLI device inspection
- JSON reporting

Not yet implemented:

- Playback validation
- Recording validation
- Loopback testing
- Sample-rate testing
- Buffer-size testing
- Latency measurement
- Stability testing
- Driver validation

---

## Summary

Device discovery means that the framework can locate a device that matches the supplied configuration.

It does not mean that the device functions correctly.

Functional validation will be added in future releases.
