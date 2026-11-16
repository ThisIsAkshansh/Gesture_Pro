# GestureMouse Pro

## Project Overview
GestureMouse Pro is a macOS-native assistive input application for Apple Silicon devices. It uses computer vision and hand gesture recognition to control the mouse cursor and perform common system actions without a physical mouse or trackpad.

## Target Platform
- macOS on Apple Silicon (M-series)
- Python 3.13
- MediaPipe Tasks API
- Quartz native mouse events
- PySide6 for the desktop UI
- PyInstaller for packaging

## Core Features
- Cursor movement
- Left click
- Right click
- Double click
- Drag
- Scroll
- FPS counter
- Mirror camera view
- Sensitivity controls
- Gesture recognition
- Mission Control
- Launchpad
- Volume control
- Brightness control
- Media keys

## Architecture
The application is structured as a modular, object-oriented system with clear separation of concerns.

- app.py
  - Application entry point
  - Initializes services, UI, and event loop
- tracker.py
  - Handles hand tracking and frame processing
  - Interfaces with MediaPipe Tasks API
- mouse.py
  - Emits native macOS mouse events through Quartz
  - Responsible for cursor movement, clicks, drag, and scroll
- gesture_engine.py
  - Maps recognized hand gestures to high-level actions
  - Implements gesture-to-command routing
- camera.py
  - Manages camera input, frame capture, and mirroring options
- ui.py
  - PySide6 user interface components
  - Displays camera feed, status, and controls
- settings.py
  - Runtime settings and user preferences
  - Includes sensitivity tuning and feature toggles
- permissions.py
  - Handles macOS permission checks and prompts
  - Covers camera and accessibility permissions
- config.py
  - Global constants, paths, defaults, and configuration values
- utils.py
  - Shared helpers, logging utilities, timing utilities, and validation helpers

## Design Requirements
- Modular OOP architecture
- Production-ready implementation standards
- Type hints throughout the codebase
- Structured logging for debugging and diagnostics
- Robust error handling and graceful fallbacks
- Apple Silicon-optimized performance paths
- No deprecated MediaPipe APIs

## Implementation Notes
- Use MediaPipe Tasks API for hand detection and gesture recognition with current, supported interfaces only.
- Prefer Quartz-based native event injection for accurate macOS input control.
- Keep UI responsive by offloading heavy processing to worker threads or async execution where appropriate.
- Persist settings in a user-safe config file and validate values before use.
- Ensure the app handles missing permissions, unavailable cameras, and dropped frames gracefully.
- Use dataclasses and typed interfaces for core models where practical.

## Development Plan
1. Project scaffolding and dependency setup
2. Core application shell and PySide6 UI
3. Camera integration and frame processing
4. Hand tracking with MediaPipe Tasks API
5. Gesture engine and command mapping
6. Quartz mouse event integration
7. Settings, permissions, and configuration management
8. Packaging with PyInstaller and final validation

## Quality Bar
- Stable runtime on Apple Silicon Macs
- Low-latency gesture response
- Clear user feedback in the UI
- Safe defaults and fallback behavior
- Clean code structure suitable for future expansion
