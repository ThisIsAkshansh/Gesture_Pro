# Aadi GestureMouse Pro

GestureMouse Pro is an original project by **AKSHANSH**.

The application includes an in-app `AKSHANSH // ORIGINAL AUTHOR` watermark as an attribution marker. Please preserve this attribution when redistributing or building on the project, and credit AKSHANSH in derivative work.

## Voice setup

Install the offline voice dependencies and download the small English Vosk model into `models/vosk-model-small-en-us-0.15`. Then run the app:

```bash
./.venv/bin/python app.py
```

The command center starts the camera, gesture controls, and microphone. On macOS, grant Camera, Microphone, and Accessibility permission to Python when prompted. Say `Hey Aadi` before a request, for example:

- `Hey Aadi, open Safari`
- `Hey Aadi, search for today's weather`
- `Hey Aadi, set volume to 40`
- `Hey Aadi, open Downloads`
- `Hey Aadi, write Hello, this is a dictated note` (then say `Hey Aadi, confirm`)
- `Hey Aadi, help me`

Aadi speaks its replies. Dictated text is pasted into the currently focused app after confirmation, so focus the intended text field first. Protected actions require a separate `Hey Aadi, confirm` or can be cancelled with `Hey Aadi, cancel`. Voice commands use an explicit allowlist; unrecognized requests are not executed as arbitrary computer or shell commands. Press `V` to pause/resume voice, `G` to pause/resume gestures, and `Esc` or `Q` to exit. Run `./.venv/bin/python -m aadi_ai --doctor` to check local dependencies and the Vosk model.

## Judge-ready demo

Start the camera app with `./.venv/bin/python app.py`. Impact Mode is enabled in
the HUD by default. Complete the visible proof sequence with your hand:
`TRACKING`, `LEFT CLICK`, `DRAG START`, and `DRAG END`. Press `D` to hide or show
the panel and `R` to reset it between demos. The 100% proof score makes the
accessibility value legible without a presenter narrating every step.
