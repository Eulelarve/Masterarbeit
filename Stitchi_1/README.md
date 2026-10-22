# Stitchi 1.0 — Camera-Based Gesture Control

Stitchi 1.0 is a camera-based gesture-control application developed as part of a Master's thesis at Berliner Hochschule für Technik (BHT). It detects body and hand landmarks, estimates the user's pointing direction, and lets the user select and manipulate virtual instrument tiles in a graphical user interface (GUI).

The project also provides a communication interface for connecting the Python-based gesture-control system to an audio-system application implemented in MATLAB. The two applications exchange instrument information and control parameters using UDP datagrams with JSON payloads. The supplied MATLAB scripts are communication tests/diagnostics; connecting the received parameters to a working audio engine may require additional MATLAB-side integration.

The project was developed using **Visual Studio Code**.

## Documentation

- **User Manual:** Explains how to operate the gesture-control interface and use its gestures and controls.
- **Developer Manual:** `Developer_Guide_Stitchi1.0.docx` describes the software architecture, configuration, modules, and development details, including MATLAB/UDP integration.
- **MATLAB README:** `matlab-code/README.md` gives a short guide to starting the Python application and running the supplied MATLAB communication scripts. It is a brief start-up guide; consult the Developer Manual for further UDP configuration and troubleshooting.

## Project structure

```text
Stitchi1.0/
├── README.md
├── python-code/
│   ├── main.py                 # Main application entry point
│   ├── settings.py             # Camera, GUI, and UDP configuration
│   ├── requirements.txt        # Python package requirements
│   ├── communication.py        # UDP/JSON communication
│   ├── GUI.py                  # Instrument GUI
│   ├── MediaPipe_handler.py    # Body and hand landmark detection
│   ├── frame_handler.py        # Camera/video input
│   ├── coordinates_handler.py  # Coordinate conversion
│   ├── angle_handler.py        # Pointing direction estimation
│   ├── gesture_handler.py      # Gesture interpretation
│   ├── own_functions.py        # Shared helper functions
│   └── analyse.py              # Test and analysis support
└── matlab-code/
    ├── README.md
    ├── send_udp.m
    ├── receiv_udp.m
    ├── UDP_send_instruments_then_receiv_orders.m
    └── UDP_send_instruments_per_comandline_and_reseiv.m
```

## Requirements

- Windows is the documented development environment.
- Python **3.11.4** is the version used for the project.
- Python packages and pinned versions are listed in `python-code/requirements.txt`.
- For a standard webcam or video file, use a compatible camera/video source.
- For Intel RealSense depth-camera operation, install the compatible Intel RealSense SDK/driver and connect the camera before starting the application.
- MATLAB is required to run the supplied `.m` communication scripts. The scripts use MATLAB's UDP and JSON functionality.
- For communication between separate computers, both computers must be connected to a network that allows UDP traffic between them.

## Setup

Open PowerShell or the Visual Studio Code terminal in the project folder, then move into `python-code`:

```powershell
cd python-code
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the listed dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell prevents activation of the virtual environment, use the Python interpreter from `.venv` directly or follow your organisation's approved PowerShell policy. If installation fails, check that Python 3.11.4 is selected and review the package versions in `requirements.txt`.

## Run the gesture-control application

From the `python-code` directory, run:

```powershell
python main.py
```

The application uses the input source configured in `settings.py`. Check `video_source` before starting:

- An integer such as `0` or `1` selects a camera index.
- `'depth_cam'` selects the RealSense depth-camera path supported by the code.
- A video filename/path selects a recorded video; RealSense `.bag` recordings are also supported by the code.

The supplied `settings.py` currently sets `video_source = 1`. Change this value to match the camera or recording available on your computer. Other relevant settings include camera/room geometry, GUI options, and UDP addresses and port. Press **Esc** to exit the application.

## MATLAB and UDP communication

The Python application sends changed instrument/GUI state to the configured audio-system IP address and listens for incoming messages, including instrument names used to populate the GUI. Messages are JSON payloads sent over UDP.

1. Open `python-code/settings.py` and configure `IPv4_audiosystem`, `IPv4_videosystem`, `bind_ip`, and `port` for your setup. The supplied port is `5005`; the supplied IP addresses are examples and may need to be changed to the actual addresses of your computers.
2. Start the Python application on the video-system computer with `python main.py`.
3. On the MATLAB/audio-system computer, open the `matlab-code` folder and run `UDP_send_instruments_then_receiv_orders.m` for a basic send/receive test, or use `UDP_send_instruments_per_comandline_and_reseiv.m` to enter additional instrument names interactively.
4. Sent instrument names should appear in the Python GUI. When an instrument's state changes, the MATLAB script should display the received JSON data.

For a single-computer test, configure the addresses appropriately (for example, use `127.0.0.1` for loopback) and ensure that each local UDP listener port is owned by only one process. For two computers, use their actual reachable LAN IPv4 addresses. The destination and listener ports must match the configuration on both sides.

> **Firewall note:** Depending on the Windows/network firewall configuration, you may need to add an inbound rule allowing UDP traffic on the configured port (normally `5005`) on the relevant computer(s). Only open the required port on trusted networks. If communication fails, check the IP addresses, port settings, firewall rules, and whether another process is already using the local port.

The MATLAB README contains the basic start-up sequence. For more detail about IP addressing, port binding, message flow, diagnostics, and troubleshooting, see the UDP section of the Developer Manual.

## Notes

- UDP is connectionless and does not guarantee packet delivery or ordering. A successful send operation does not prove that the receiving application processed the message.
- The supplied MATLAB scripts are intended for communication testing and display decoded messages. They do not, by themselves, implement the complete audio synthesis/control system.
- Do not start multiple instances of the Python application that attempt to bind to the same local UDP address and port.

### This readme file was created with the help of ChatGPT.