# MagTag Weather Display

## Battery Analysis (2026-04-13)
Based on discharge data from two ~37-day cycles.

### Voltage to Percentage Mapping
To provide a more linear feel relative to time, use this piecewise approximation:

| Voltage | Percentage | Notes |
| :--- | :--- | :--- |
| **4.1V+** | **100%** | Full charge |
| **4.0V** | **90%** | ~4 days in |
| **3.8V** | **75%** | ~10 days in |
| **3.7V** | **60%** | Mid-point of the plateau |
| **3.6V** | **40%** | End of 3.6V plateau (~21 days in) |
| **3.5V** | **20%** | Approaching the "knee" (~27 days in) |
| **3.4V** | **10%** | ~4 days of life left |
| **3.3V** | **5%** | **Low Battery Warning** (~1 day left) |
| **3.2V** | **0%** | **Critical / Shutdown** |

### Critical Thresholds
* **3.3V**: Trigger "Please Charge" warning.
* **3.2V**: Trigger full-screen "Battery Critical" overlay.
