# SafeDrive AI 🛡️
> **Intelligent Real-Time Driver Attentiveness Monitoring & Emergency SOS Safety System**

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3119/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.21-teal.svg)](https://mediapipe.dev/)
[![NumPy](https://img.shields.io/badge/NumPy-1.26.4-informational.svg)](https://numpy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

SafeDrive AI is a real-time computer-vision safety system that actively monitors driver attentiveness, detects physiological indicators of drowsiness and fatigue, issues multi-tier audio/visual alarms, and orchestrates an emergency SOS workflow (capturing snapshots, acquiring device GPS coordinates, and dispatching simulated or SMS alerts) if a driver becomes unresponsive.

---

## 📑 Table of Contents
- [System Architecture](#-system-architecture)
- [Key Features](#-key-features)
- [How Detection Works](#-how-detection-works)
  - [Eye Aspect Ratio (EAR)](#1-eye-aspect-ratio-ear)
  - [Mouth Aspect Ratio (MAR)](#2-mouth-aspect-ratio-mar)
- [Emergency & SOS Workflow](#-emergency--sos-workflow)
- [Folder Structure](#-folder-structure)
- [Technology Stack](#-technology-stack)
- [Installation & Setup](#-installation--setup)
- [Running SafeDrive AI](#-running-safedrive-ai)
- [Keyboard Controls & Shortcuts](#-keyboard-controls--shortcuts)
- [Notifications Architecture](#-notifications-architecture)
- [Database Schema](#-database-schema)
- [Privacy & Security](#-privacy--security)
- [Troubleshooting](#-troubleshooting)
- [Testing](#-testing)
- [Limitations & Future Roadmap](#-limitations--future-roadmap)
- [Safety & Medical Disclaimer](#-safety--medical-disclaimer)

---

## 🏛️ System Architecture

SafeDrive AI follows a decoupled, modular architecture designed for high-frame-rate computer vision processing with non-blocking asynchronous subsystems:

```
                  ┌──────────────────────────────┐
                  │    Webcam Input Stream       │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │  MediaPipe FaceMesh (468 pts)│
                  │   Eye & Mouth Landmark Mesh  │
                  └──────────────┬───────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
       ┌────────────────────┐          ┌────────────────────┐
       │   EAR Calculation  │          │   MAR Calculation  │
       │ Prolonged Closure  │          │    Yawn Counter    │
       └─────────┬──────────┘          └─────────┬──────────┘
                 └───────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │ Emergency Safety Coordinator │
                  └──────────────┬───────────────┘
                                 │
         ┌───────────────────────┼──────────────────────┐
         ▼                       ▼                      ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ Pygame Audio     │   │ 10s Response     │   │ SQLite Telemetry │
│ Warning Alarm    │   │ Countdown Window │   │ Event Logging    │
└──────────────────┘   └─────────┬────────┘   └──────────────────┘
                                 │ Timeout (No Response)
                                 ▼
                  ┌──────────────────────────────┐
                  │  Emergency Mode Activated   │
                  └──────────────┬───────────────┘
                                 │
         ┌───────────────────────┼──────────────────────┐
         ▼                       ▼                      ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ Single Emergency │   │ Windows Device   │   │ Provider-Free    │
│ Snapshot Capture │   │ GPS Coordinates  │   │ Mock SMS / Twilio│
└──────────────────┘   └──────────────────┘   └──────────────────┘
```

---

## 🌟 Key Features

1. **Precision Facial Landmark Tracking**: Uses MediaPipe FaceMesh for sub-millisecond eye and mouth landmark tracking without full-face occlusion artifacts.
2. **Dynamic Attentiveness Metrics**:
   - Continuous **Eye Aspect Ratio (EAR)** calculation to detect microsleeps and prolonged closure.
   - **Mouth Aspect Ratio (MAR)** tracking with cooldown debouncing to detect sustained yawning.
3. **Audible & Visual Warning System**:
   - Instant continuous acoustic warning alarm via Pygame Mixer upon danger detection.
   - Prominent 10-second driver response countdown banner.
4. **Resilient Driver Response Mechanism**:
   - Single-key acknowledgement (`R`) resets alarm, countdown, and detector state without race conditions.
   - Opening eyes does **not** prematurely clear a 3-yawn hazard state before explicit acknowledgement.
5. **Autonomous Emergency SOS Orchestration**:
   - Subsystem fault isolation: If camera snapshot, GPS fix, or SMS dispatch fails, other subsystems continue uninterrupted.
   - **Emergency Snapshot**: Exactly one timestamped frame saved locally under `emergency_captures/`.
   - **Device GPS Location**: Native Windows `GeoCoordinateWatcher` coordinates with horizontal accuracy and Google Maps links.
   - **Zero-Cost Alert Dispatch**: Ships with `MockSMSProvider` (`SIMULATED` status) so no paid third-party SMS service is required. Optional Twilio integration is available.
6. **Premium Glassmorphic Desktop Dashboard**:
   - Dark obsidian UI built with CustomTkinter.
   - Real-time video canvas, live telemetry cards, system stats, and searchable event history audit log.

---

## 🔬 How Detection Works

### 1. Eye Aspect Ratio (EAR)
The eye landmarks correspond to 6 specific coordinate points on each eyelid:
$$EAR = \frac{||p_2 - p_6|| + ||p_3 - p_5||}{2 \times ||p_1 - p_4||}$$
- **Threshold**: `0.22`
- **Drowsiness Condition**: When `EAR < 0.22` for `45` consecutive frames (~1.5 seconds at 30 FPS), a **DROWSINESS** event is triggered.

### 2. Mouth Aspect Ratio (MAR)
Mouth landmarks measure the vertical lip separation relative to horizontal corner separation:
$$MAR = \frac{||p_{\text{top}} - p_{\text{bottom}}||}{||p_{\text{left}} - p_{\text{right}}||}$$
- **Threshold**: `0.50`
- **Yawn Condition**: When `MAR >= 0.50` for at least `8` consecutive frames, followed by closure, a yawn is counted.
- **Danger Threshold**: Reaching `3` yawns triggers the emergency countdown.

---

## ⏱️ Emergency & SOS Workflow

1. **Normal Monitoring**: Attentive driver; EAR and MAR normal; green indicators.
2. **Danger Detected**: Eyes closed $\ge 45$ frames OR yawn count $\ge 3$.
   - Audio alarm starts playing in a continuous loop.
   - Countdown timer activates: **RESPOND IN: 10s**.
3. **Driver Acknowledges**: Driver presses `R`.
   - Alarm stops immediately.
   - Countdown cancelled.
   - Detector counters reset to 0.
   - Normal monitoring resumes without re-triggering.
4. **No Response (Timeout)**: 10 seconds elapse without driver acknowledgement:
   - **Emergency Mode** activates.
   - **Hazard Status**: Set to ON.
   - **Single Photo**: Captured and saved locally to `emergency_captures/emergency_YYYYMMDD_HHMMSS.jpg`.
   - **GPS Fix**: Device location acquired (e.g., `Lat 16.9889, Lon 73.3065 ±50m`).
   - **Google Maps Link**: Generated automatically.
   - **SQLite Event**: Saved with `CRITICAL` severity and `NO_RESPONSE` status.
   - **SOS Notification**: Dispatched via `MockSMSProvider` (status: `SIMULATED`) or configured provider.
   - Audio alarm continues playing until driver presses `R`.

---

## 📁 Folder Structure

```
SafeDrive-AI/
├── app.py                  # Main application & GUI scheduler entry point
├── config.py               # Central thresholds, timings, and directory paths
├── detector.py             # MediaPipe FaceMesh detector & mouth-only mesh
├── eye.py                  # EAR, MAR, yawn, and drowsiness math calculations
├── alarm.py                # Pygame audio alarm manager with hardware fallbacks
├── location.py             # Windows GeoCoordinateWatcher location provider
├── camera_capture.py       # Verified local emergency snapshot capture
├── emergency.py            # Emergency coordinator & SOS fault-isolated pipeline
├── notifications.py        # Provider-independent notification subsystem (Mock & Twilio)
├── sms.py                  # Backward-compatible SMS wrapper
├── database.py             # SQLite database layer with non-destructive migrations
├── setup.py                # Driver and vehicle profile registration CLI
├── ui.py                   # CustomTkinter dark-mode desktop dashboard & event viewer
├── logger.py               # Structured console & rotating file logging
├── utils.py                # Geometry helpers and formatting utilities
├── requirements.txt        # Verified Python 3.11 dependencies
├── .env.example            # Environment variables template (no secrets)
├── .gitignore              # Ignores database, captures, logs, and secrets
├── README.md               # Complete system documentation
├── assets/
│   └── alarm.mp3           # Continuous alarm sound file
├── emergency_captures/     # Local sensitive emergency photos (git-ignored)
├── tests/                  # Comprehensive automated test suite
│   ├── __init__.py
│   ├── test_database.py
│   ├── test_detection.py
│   ├── test_location.py
│   ├── test_camera_capture.py
│   ├── test_notifications.py
│   ├── test_emergency.py
│   └── test_ui.py
└── safedrive.db            # Persistent SQLite database (git-ignored)
```

---

## 💻 Technology Stack

- **Platform**: Windows 10 / Windows 11
- **Python**: `3.11` (x64)
- **Computer Vision**:
  - `mediapipe==0.10.21` (FaceMesh 468 landmark model)
  - `numpy==1.26.4`
  - `opencv-python>=4.8.0`
- **Audio**: `pygame==2.6.1` (SDL Mixer)
- **Desktop GUI**: `customtkinter>=6.0.0` & `Pillow>=10.0.0`
- **Location**: Windows Native `System.Device.Location.GeoCoordinateWatcher`
- **Database**: SQLite 3 (with foreign key constraints and automatic schema migrations)
- **Notifications**: Internal Provider Interface (`MockSMSProvider` + optional `Twilio`)

---

## 🚀 Installation & Setup

### 1. Prerequisites
Ensure **Python 3.11** is installed on your Windows system. You can verify this by running:
```powershell
py -3.11 --version
```

### 2. Clone the Repository
```powershell
git clone https://github.com/parthDhanaba/SafeDrive-AI.git
cd SafeDrive-AI
```

### 3. Create & Activate Virtual Environment
```powershell
py -3.11 -m venv venv
.\venv\Scripts\activate
```

### 4. Install Dependencies
```powershell
py -3.11 -m pip install -r requirements.txt
```

### 5. Configure Driver & Vehicle Profile
Run the setup utility to register driver and emergency contact details:
```powershell
python setup.py
```
*(Or run `python setup.py --default` for quick non-interactive setup).*

---

## 🎬 Running SafeDrive AI

Ensure your webcam is connected, then launch the application:
```powershell
python app.py
```
To specify a secondary camera index:
```powershell
python app.py --camera 1
```

---

## ⌨️ Keyboard Controls & Shortcuts

| Key | Action | Description |
|:---:|:---|:---|
| **R** | **Reset Alarm & Detection** | Cancels warning countdown or active emergency, resets counters to 0, and stops audio alarm. |
| **Q** | **Quit Application** | Safely releases webcam, stops audio, and cleanly exits the dashboard. |

*(All keyboard actions are also accessible via buttons on the dashboard).*

---

## 📱 Notifications Architecture

SafeDrive AI does **not** force users into paid third-party SMS plans or restricted trial accounts.

### Mock SMS Provider (Default & Recommended)
- Automatically enabled when `USE_MOCK_SMS=true` (or by default).
- Formats the full emergency alert with driver name, vehicle plate, danger reason, GPS coordinates, Google Maps URL, and snapshot filename.
- Logs the simulated alert with status `SIMULATED` and persists it to SQLite.
- Fully free and self-contained.

### Optional Twilio SMS Provider
If you have an active Twilio account and want real SMS delivery:
1. Copy `.env.example` to `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Set `USE_MOCK_SMS=false` and configure your credentials:
   ```env
   USE_MOCK_SMS=false
   TWILIO_ACCOUNT_SID=your_account_sid_here
   TWILIO_AUTH_TOKEN=your_auth_token_here
   TWILIO_FROM_NUMBER=+1234567890
   EMERGENCY_PHONE_NUMBER=+0987654321
   ```
3. The system gracefully handles trial limitations and network errors without exposing tokens or halting the application.

---

## 🗄️ Database Schema

SafeDrive AI persists all telemetry, drivers, vehicles, and alert history in `safedrive.db`:

- `drivers`: Driver full name, phone number, emergency contact name, and emergency contact phone.
- `vehicles`: Vehicle registration plate number, vehicle class/type, and owner name.
- `safety_events`: Telemetry records of yawn limits, drowsiness instances, and emergency SOS triggers with EAR, MAR, location coordinates, accuracy, and snapshot paths.
- `emergency_alerts`: Outgoing dispatch records with recipient details, full message text, delivery status (`SIMULATED`, `SENT`, or `FAILED`), and timestamp.

---

## 🔒 Privacy & Security

- **Local Storage Only**: All emergency snapshots are saved exclusively on the local machine in `emergency_captures/`. Photos are **never** uploaded to public cloud hosting or third-party servers.
- **Secrets Protection**: `.env` and `safedrive.db` are strictly excluded from version control via `.gitignore`.
- **No Coordinate Fabrication**: The system queries real Windows device location. If location permissions or hardware are unavailable, it cleanly outputs `Unavailable` rather than fabricating coordinates.

---

## 🛠️ Troubleshooting

| Issue | Cause | Solution |
|:---|:---|:---|
| `Unable to access webcam` | Camera in use or missing permission | Close other video conferencing software and ensure webcam privacy permissions are enabled in Windows Settings. |
| `Audio initialization failed` | No audio output device connected | Plug in speakers or headphones. Visual alerts will continue to work normally even if audio is unavailable. |
| `Location shows 'Unavailable'` | Windows Location Services turned off | Enable Location in **Windows Settings > Privacy & security > Location**, and allow desktop apps access. |
| `Trial accounts can only use predefined SMS templates` | Twilio trial restriction | Keep `USE_MOCK_SMS=true` (default). Mock SMS provides complete simulation without paid accounts. |

---

## 🧪 Testing

Run the full automated test suite:
```powershell
py -3.11 -m unittest discover -s tests -p "test_*.py" -v
```
All 25 unit and integration tests validate database migrations, detection math, location providers, camera captures, notification handlers, emergency state transitions, and the UI dashboard.

---

## 🔮 Limitations & Future Roadmap

### Current Limitations
- Operates on 2D webcam video; performance in total darkness requires infrared (IR) driver-facing illumination.
- Relies on Windows Location Services; requires a device with GPS or Wi-Fi triangulation for location fix.

### Future Improvements
- Multi-camera support (cabin monitoring + road-facing lane detection).
- Night-vision / Near-Infrared (NIR) camera optimization.
- On-device lightweight wake-word voice acknowledgement ("SafeDrive Cancel").
- OBD-II telemetry integration (reading vehicle speed and steering wheel angle).

---

## ⚠️ Safety & Medical Disclaimer

> **IMPORTANT**: SafeDrive AI is an academic and developer prototype created for research and educational purposes. It is **NOT** a certified automotive safety system, an autonomous driving safety system, or an official emergency dispatch service. SafeDrive AI cannot guarantee the prevention of vehicular accidents. Drivers must always remain vigilant, take regular rest breaks, and adhere to traffic regulations.
