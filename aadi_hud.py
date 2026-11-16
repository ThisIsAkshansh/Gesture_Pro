"""Aadi.ai's camera-overlay HUD.

This module deliberately has no dependency on the voice or gesture engines.  A
camera loop can keep rendering while those services start, stop, or fail, and
voice callbacks can update :class:`HUDController` safely from a worker thread.

Quick integration::

    from aadi_hud import AadiHUD, HUDController

    hud, hud_state = AadiHUD(), HUDController()
    hud_state.set_voice_state("listening")
    hud_state.set_transcript("open Spotify")
    frame = hud.render(frame, hud_state.snapshot())

OpenCV is imported only when a frame is actually rendered.  This keeps command
and voice-only runs importable on machines where the camera stack is absent.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from enum import Enum
import math
import threading
import time
from collections.abc import Mapping
from typing import Any


class AssistantStatus(str, Enum):
    """The visible lifecycle of Aadi.ai's command pipeline."""

    READY = "READY"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    EXECUTING = "EXECUTING"
    SPEAKING = "SPEAKING"
    PAUSED = "PAUSED"
    OFFLINE = "OFFLINE"
    ERROR = "ERROR"


class SafetyState(str, Enum):
    """Whether commands can run immediately or need a user confirmation."""

    SAFE = "SAFE"
    CONFIRM = "CONFIRM"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class HUDState:
    """A small, serialisable snapshot consumed by :class:`AadiHUD`.

    All values have intentionally useful defaults so a HUD can be displayed
    before microphone, vision, or automation services have initialised.
    """

    assistant_name: str = "AADI.AI"
    status: str = AssistantStatus.READY.value
    active_mode: str = "HYBRID CONTROL"
    transcript: str = "Say “Hey Aadi” or hold V to speak"
    intent: str = "Awaiting command"
    last_action: str = "Systems standing by"
    task: str = "No active task"
    safety: str = SafetyState.SAFE.value
    voice_online: bool = False
    camera_online: bool = True
    gesture_online: bool = True
    automation_online: bool = True
    mic_level: float = 0.0
    fps: float | None = None
    latency_ms: float | None = None
    cpu_percent: float | None = None
    memory_percent: float | None = None
    uptime_seconds: float | None = None
    command_history: tuple[str, ...] = ()
    notification: str = ""
    updated_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def coerce(cls, value: "HUDState | Mapping[str, Any] | None") -> "HUDState":
        """Return a valid HUD state from a state object or a mapping.

        Unknown mapping keys are ignored so callers can pass their broader
        runtime-status dictionary without coupling it to the renderer.
        """

        if value is None:
            return cls()
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            raise TypeError("HUD state must be HUDState, a mapping, or None")

        allowed = set(cls.__dataclass_fields__)
        data = {key: item for key, item in value.items() if key in allowed}
        if "command_history" in data and not isinstance(data["command_history"], tuple):
            history = data["command_history"]
            data["command_history"] = (str(history),) if isinstance(history, str) else tuple(str(item) for item in history)
        if "updated_at" in data and not isinstance(data["updated_at"], datetime):
            try:
                data["updated_at"] = datetime.fromisoformat(str(data["updated_at"]))
            except ValueError:
                data["updated_at"] = datetime.now()
        return cls(**data)

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly copy suitable for diagnostics or a web HUD."""

        data = asdict(self)
        data["updated_at"] = self.updated_at.isoformat(timespec="seconds")
        return data


class HUDController:
    """Thread-safe producer for HUD snapshots.

    The controller does not execute commands; it only mirrors their lifecycle
    for the user.  It can therefore be passed to a speech-recognition callback
    without giving that callback camera or desktop-control permissions.
    """

    def __init__(self, initial: HUDState | Mapping[str, Any] | None = None) -> None:
        self._lock = threading.RLock()
        self._state = HUDState.coerce(initial)

    def snapshot(self) -> HUDState:
        """Return an immutable, consistent state snapshot."""

        with self._lock:
            return self._state

    def update(self, **changes: Any) -> HUDState:
        """Atomically update supported fields and return the new snapshot."""

        valid = set(HUDState.__dataclass_fields__)
        unknown = set(changes) - valid
        if unknown:
            names = ", ".join(sorted(unknown))
            raise KeyError(f"Unknown HUD field(s): {names}")
        if "command_history" in changes:
            changes["command_history"] = tuple(str(item) for item in changes["command_history"])
        changes["updated_at"] = datetime.now()
        with self._lock:
            self._state = replace(self._state, **changes)
            return self._state

    def set_voice_state(
        self,
        status: AssistantStatus | str,
        *,
        transcript: str | None = None,
        intent: str | None = None,
        mic_level: float | None = None,
    ) -> HUDState:
        """Update the visible voice-pipeline state in one call."""

        changes: dict[str, Any] = {
            "status": _enum_text(status),
            "voice_online": _enum_text(status) not in {AssistantStatus.OFFLINE.value, AssistantStatus.ERROR.value},
        }
        if transcript is not None:
            changes["transcript"] = transcript
        if intent is not None:
            changes["intent"] = intent
        if mic_level is not None:
            changes["mic_level"] = _clamp(float(mic_level), 0.0, 1.0)
        return self.update(**changes)

    def set_transcript(self, transcript: str, *, mic_level: float | None = None) -> HUDState:
        """Publish partial or final speech-recognition text without a status change."""

        changes: dict[str, Any] = {"transcript": str(transcript)}
        if mic_level is not None:
            changes["mic_level"] = _clamp(float(mic_level), 0.0, 1.0)
        return self.update(**changes)

    def show_action(
        self,
        action: str,
        *,
        task: str | None = None,
        safety: SafetyState | str | None = None,
        notification: str | None = None,
    ) -> HUDState:
        """Record an action and retain a compact, newest-first history."""

        with self._lock:
            history = (str(action), *self._state.command_history)[:5]
        changes: dict[str, Any] = {"last_action": str(action), "command_history": history}
        if task is not None:
            changes["task"] = str(task)
        if safety is not None:
            changes["safety"] = _enum_text(safety)
        if notification is not None:
            changes["notification"] = str(notification)
        return self.update(**changes)

    def set_service_health(
        self,
        *,
        camera: bool | None = None,
        voice: bool | None = None,
        gestures: bool | None = None,
        automation: bool | None = None,
    ) -> HUDState:
        """Set service-link indicators without changing the active command."""

        changes: dict[str, bool] = {}
        if camera is not None:
            changes["camera_online"] = bool(camera)
        if voice is not None:
            changes["voice_online"] = bool(voice)
        if gestures is not None:
            changes["gesture_online"] = bool(gestures)
        if automation is not None:
            changes["automation_online"] = bool(automation)
        return self.update(**changes) if changes else self.snapshot()


class AadiHUD:
    """Responsive, cyan holographic HUD rendered over an OpenCV BGR frame.

    ``render`` returns a new frame and never mutates the camera frame passed by
    the caller.  The dimensions are calculated at render time, so it remains
    readable for 720p webcam previews through an ultrawide capture surface.
    """

    # BGR values, matching OpenCV's default channel order.
    CYAN = (255, 224, 65)
    CYAN_DIM = (145, 112, 28)
    BLUE = (255, 125, 24)
    MINT = (130, 255, 150)
    AMBER = (0, 200, 255)
    RED = (70, 80, 255)
    WHITE = (245, 250, 250)
    INK = (12, 17, 20)

    def __init__(self, *, opacity: float = 0.24, show_telemetry: bool = True) -> None:
        self.opacity = _clamp(float(opacity), 0.0, 0.85)
        self.show_telemetry = bool(show_telemetry)
        self._started_at = time.monotonic()

    def draw(self, frame: Any, state: HUDState | Mapping[str, Any] | None = None) -> Any:
        """Alias for :meth:`render`, compatible with existing renderer APIs."""

        return self.render(frame, state)

    def render(self, frame: Any, state: HUDState | Mapping[str, Any] | None = None) -> Any:
        """Draw Aadi.ai's HUD over one BGR frame.

        Raises:
            RuntimeError: when OpenCV is not installed.
            ValueError: if the supplied frame is not a colour image.
        """

        cv2 = _get_cv2()
        hud = HUDState.coerce(state)
        if not hasattr(frame, "shape") or len(frame.shape) < 3 or frame.shape[2] < 3:
            raise ValueError("AadiHUD.render expects a BGR colour frame")

        height, width = int(frame.shape[0]), int(frame.shape[1])
        if height < 120 or width < 220:
            # A HUD at this size would hide the source image; retain a safe copy.
            return frame.copy()

        scale = _clamp(min(width / 1280.0, height / 720.0), 0.54, 1.7)
        now = time.monotonic()
        canvas = frame.copy()
        overlay = canvas.copy()

        pad = int(18 * scale)
        left_w = min(int(384 * scale), max(160, width - (2 * pad)))
        top_h = min(int(174 * scale), max(92, height - (2 * pad)))
        right_w = min(int(238 * scale), max(0, width - left_w - (3 * pad)))
        command_h = min(int(88 * scale), max(58, height // 5))
        command_y = height - pad - command_h

        # Translucent fields are intentionally distinct from the crisp vectors
        # drawn later. It keeps the camera view useful while feeling like a HUD.
        self._filled_panel(cv2, overlay, (pad, pad), (pad + left_w, pad + top_h), self.INK)
        if right_w >= int(155 * scale):
            self._filled_panel(cv2, overlay, (width - pad - right_w, pad), (width - pad, pad + top_h), self.INK)
        self._filled_panel(cv2, overlay, (pad, command_y), (width - pad, height - pad), self.INK)
        canvas = cv2.addWeighted(overlay, self.opacity, canvas, 1.0 - self.opacity, 0)

        self._draw_corner_frame(cv2, canvas, width, height, pad, scale)
        self._draw_header(cv2, canvas, hud, pad, left_w, top_h, scale, now)
        if right_w >= int(155 * scale):
            self._draw_service_panel(cv2, canvas, hud, width - pad - right_w, pad, right_w, top_h, scale)
        self._draw_reactor(cv2, canvas, hud, width, height, pad, command_y, scale, now)
        self._draw_command_panel(cv2, canvas, hud, pad, command_y, width - (2 * pad), command_h, scale)
        self._draw_scanline(cv2, canvas, width, height, scale, now)
        self._draw_watermark(cv2, canvas, width, height, scale)
        return canvas

    def _draw_watermark(self, cv2: Any, image: Any, width: int, height: int, scale: float) -> None:
        label = "AKSHANSH  //  ORIGINAL AUTHOR"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = max(0.38, 0.48 * scale)
        thickness = max(1, int(scale))
        text_width = cv2.getTextSize(label, font, font_scale, thickness)[0][0]
        self._text(
            cv2,
            image,
            label,
            (max(int(12 * scale), width - text_width - int(18 * scale)), height - int(14 * scale)),
            font_scale,
            self.CYAN_DIM,
            thickness,
        )

    def _filled_panel(self, cv2: Any, image: Any, p1: tuple[int, int], p2: tuple[int, int], colour: tuple[int, int, int]) -> None:
        cv2.rectangle(image, p1, p2, colour, -1)

    def _line(self, cv2: Any, image: Any, p1: tuple[int, int], p2: tuple[int, int], colour: tuple[int, int, int], thickness: int = 1) -> None:
        cv2.line(image, p1, p2, colour, max(1, thickness), cv2.LINE_AA)

    def _text(
        self,
        cv2: Any,
        image: Any,
        text: Any,
        origin: tuple[int, int],
        scale: float,
        colour: tuple[int, int, int],
        thickness: int = 1,
        *,
        max_width: int | None = None,
        font: int | None = None,
    ) -> None:
        value = _trim_text(cv2, str(text), max_width, font or cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
        cv2.putText(
            image,
            value,
            (int(origin[0]), int(origin[1])),
            font or cv2.FONT_HERSHEY_SIMPLEX,
            max(0.28, scale),
            colour,
            max(1, thickness),
            cv2.LINE_AA,
        )

    def _draw_corner_frame(self, cv2: Any, image: Any, width: int, height: int, pad: int, scale: float) -> None:
        arm = int(32 * scale)
        thick = max(1, int(2 * scale))
        corners = (
            ((pad, pad), (pad + arm, pad), (pad, pad + arm)),
            ((width - pad, pad), (width - pad - arm, pad), (width - pad, pad + arm)),
            ((pad, height - pad), (pad + arm, height - pad), (pad, height - pad - arm)),
            ((width - pad, height - pad), (width - pad - arm, height - pad), (width - pad, height - pad - arm)),
        )
        for anchor, horizontal, vertical in corners:
            self._line(cv2, image, anchor, horizontal, self.CYAN, thick)
            self._line(cv2, image, anchor, vertical, self.CYAN, thick)

    def _draw_header(self, cv2: Any, image: Any, state: HUDState, x: int, width: int, height: int, scale: float, now: float) -> None:
        right = x + width
        panel_y = int(18 * scale)
        title_y = panel_y + int(28 * scale)
        self._line(cv2, image, (x, panel_y), (right, panel_y), self.CYAN, max(1, int(scale)))
        self._line(cv2, image, (x, panel_y), (x, panel_y + int(18 * scale)), self.CYAN, max(1, int(scale)))
        self._text(
            cv2,
            image,
            f"{state.assistant_name.upper()} // NEURAL COMMAND INTERFACE",
            (x + int(14 * scale), title_y),
            0.50 * scale,
            self.CYAN,
            max(1, int(1.2 * scale)),
            max_width=width - int(28 * scale),
            font=cv2.FONT_HERSHEY_DUPLEX,
        )

        status_colour = self._status_colour(state.status)
        pulse = 0.65 + (0.35 * math.sin(now * 5.0))
        radius = max(3, int((4.5 + pulse * 2.0) * scale))
        dot_x = x + int(19 * scale)
        status_y = panel_y + int(57 * scale)
        cv2.circle(image, (dot_x, status_y - int(4 * scale)), radius, status_colour, -1, cv2.LINE_AA)
        self._text(
            cv2,
            image,
            f"{_enum_text(state.status)}  |  {state.active_mode.upper()}",
            (x + int(32 * scale), status_y),
            0.43 * scale,
            status_colour,
            max(1, int(scale)),
            max_width=width - int(47 * scale),
        )

        self._line(cv2, image, (x + int(14 * scale), status_y + int(11 * scale)), (right - int(14 * scale), status_y + int(11 * scale)), self.CYAN_DIM)
        transcript_y = status_y + int(34 * scale)
        self._text(cv2, image, "VOICE INPUT", (x + int(14 * scale), transcript_y), 0.34 * scale, self.CYAN_DIM, max_width=width - int(28 * scale))
        self._text(
            cv2,
            image,
            state.transcript or "Listening for a command…",
            (x + int(14 * scale), transcript_y + int(19 * scale)),
            0.43 * scale,
            self.WHITE,
            max_width=width - int(28 * scale),
        )

        waveform_y = panel_y + height - int(20 * scale)
        self._draw_waveform(cv2, image, state.mic_level, x + int(14 * scale), waveform_y, width - int(28 * scale), scale, now)

    def _draw_waveform(self, cv2: Any, image: Any, mic_level: float, x: int, y: int, width: int, scale: float, now: float) -> None:
        bars = max(12, min(34, width // max(6, int(10 * scale))))
        step = max(4, width // bars)
        peak = _clamp(float(mic_level), 0.0, 1.0)
        for index in range(bars):
            phase = (index * 0.54) + (now * 5.2)
            wave = (math.sin(phase) + 1.0) / 2.0
            energy = 0.16 + peak * (0.36 + 0.64 * wave)
            bar_h = max(2, int((7 + 16 * energy) * scale))
            xx = x + index * step
            colour = self.CYAN if index % 3 else self.BLUE
            self._line(cv2, image, (xx, y - bar_h), (xx, y), colour, max(1, int(scale)))

    def _draw_service_panel(self, cv2: Any, image: Any, state: HUDState, x: int, y: int, width: int, height: int, scale: float) -> None:
        right = x + width
        self._line(cv2, image, (x, y), (right, y), self.CYAN, max(1, int(scale)))
        self._line(cv2, image, (right, y), (right, y + int(18 * scale)), self.CYAN, max(1, int(scale)))
        self._text(cv2, image, "SYSTEM LINK", (x + int(13 * scale), y + int(28 * scale)), 0.50 * scale, self.CYAN, max_width=width - int(26 * scale), font=cv2.FONT_HERSHEY_DUPLEX)

        links = (
            ("CAMERA", state.camera_online),
            ("VOICE", state.voice_online),
            ("GESTURES", state.gesture_online),
            ("AUTOMATION", state.automation_online),
        )
        row_y = y + int(52 * scale)
        for label, online in links:
            colour = self.MINT if online else self.RED
            cv2.circle(image, (x + int(16 * scale), row_y - int(4 * scale)), max(2, int(3 * scale)), colour, -1, cv2.LINE_AA)
            self._text(cv2, image, label, (x + int(27 * scale), row_y), 0.37 * scale, self.WHITE, max_width=int(92 * scale))
            self._text(cv2, image, "ONLINE" if online else "OFFLINE", (right - int(67 * scale), row_y), 0.31 * scale, colour, max_width=int(60 * scale))
            row_y += int(22 * scale)

        if self.show_telemetry:
            footer_y = y + height - int(14 * scale)
            latency = "--" if state.latency_ms is None else f"{max(0, int(state.latency_ms))}ms"
            fps = "--" if state.fps is None else f"{max(0, int(state.fps))}fps"
            cpu = "--" if state.cpu_percent is None else f"{max(0, int(state.cpu_percent))}%"
            memory = "--" if state.memory_percent is None else f"{max(0, int(state.memory_percent))}%"
            self._text(
                cv2,
                image,
                f"LINK {latency}  VISION {fps}  CPU {cpu}  MEM {memory}",
                (x + int(13 * scale), footer_y),
                0.30 * scale,
                self.CYAN_DIM,
                max_width=width - int(26 * scale),
            )

    def _draw_reactor(self, cv2: Any, image: Any, state: HUDState, width: int, height: int, pad: int, command_y: int, scale: float, now: float) -> None:
        # Keep the motif in the open middle/right area and above the command bar.
        radius = int(46 * scale)
        cx = max(pad + radius + int(10 * scale), width - pad - int(118 * scale))
        lower_limit = command_y - radius - int(14 * scale)
        cy = max(pad + radius + int(110 * scale), min(lower_limit, int(height * 0.58)))
        if cy <= pad + radius:
            return

        status_colour = self._status_colour(state.status)
        rotation = int(now * 80.0) % 360
        cv2.circle(image, (cx, cy), radius, self.CYAN_DIM, max(1, int(scale)), cv2.LINE_AA)
        cv2.circle(image, (cx, cy), int(radius * 0.72), self.CYAN, max(1, int(scale)), cv2.LINE_AA)
        cv2.circle(image, (cx, cy), max(5, int(radius * 0.24)), status_colour, -1, cv2.LINE_AA)
        cv2.circle(image, (cx, cy), max(8, int(radius * 0.39)), self.BLUE, max(1, int(scale)), cv2.LINE_AA)

        for offset, length in ((0, 0.96), (90, 0.85), (180, 0.96), (270, 0.85)):
            angle = math.radians(rotation + offset)
            start = int(radius * 0.82)
            end = int(radius * length)
            p1 = (int(cx + math.cos(angle) * start), int(cy + math.sin(angle) * start))
            p2 = (int(cx + math.cos(angle) * end), int(cy + math.sin(angle) * end))
            self._line(cv2, image, p1, p2, self.MINT, max(1, int(2 * scale)))

        label_y = cy + radius + int(19 * scale)
        self._text(cv2, image, "AADI CORE", (cx - int(34 * scale), label_y), 0.31 * scale, self.CYAN, max_width=int(70 * scale))
        safety_colour = self._safety_colour(state.safety)
        self._text(cv2, image, _enum_text(state.safety), (cx - int(24 * scale), label_y + int(14 * scale)), 0.26 * scale, safety_colour, max_width=int(52 * scale))

    def _draw_command_panel(self, cv2: Any, image: Any, state: HUDState, x: int, y: int, width: int, height: int, scale: float) -> None:
        right = x + width
        self._line(cv2, image, (x, y), (right, y), self.CYAN, max(1, int(scale)))
        self._line(cv2, image, (x, y), (x + int(20 * scale), y), self.MINT, max(1, int(2 * scale)))
        title_y = y + int(20 * scale)
        self._text(cv2, image, "ACTIVE INTENT", (x + int(13 * scale), title_y), 0.32 * scale, self.CYAN_DIM, max_width=int(102 * scale))
        self._text(
            cv2,
            image,
            state.intent or "Awaiting command",
            (x + int(13 * scale), title_y + int(18 * scale)),
            0.46 * scale,
            self.WHITE,
            max_width=int(width * 0.54),
        )

        action_x = x + int(width * 0.58)
        self._text(cv2, image, "LAST ACTION", (action_x, title_y), 0.32 * scale, self.CYAN_DIM, max_width=right - action_x - int(12 * scale))
        self._text(
            cv2,
            image,
            state.last_action or "Systems standing by",
            (action_x, title_y + int(18 * scale)),
            0.40 * scale,
            self.MINT,
            max_width=right - action_x - int(12 * scale),
        )

        footer_y = y + height - int(12 * scale)
        timestamp = state.updated_at.strftime("%H:%M:%S")
        uptime = _format_duration(state.uptime_seconds if state.uptime_seconds is not None else time.monotonic() - self._started_at)
        left_footer = f"{state.task.upper()}  //  UPTIME {uptime}"
        self._text(cv2, image, left_footer, (x + int(13 * scale), footer_y), 0.28 * scale, self.CYAN_DIM, max_width=int(width * 0.70))
        self._text(cv2, image, timestamp, (right - int(58 * scale), footer_y), 0.31 * scale, self.CYAN, max_width=int(52 * scale))

        # An explicit safety prompt stays visible even if a voice engine's
        # transcript is off-screen or a task is pending confirmation.
        if _enum_text(state.safety) != SafetyState.SAFE.value:
            prompt = "CONFIRM WITH VOICE" if _enum_text(state.safety) == SafetyState.CONFIRM.value else "AUTOMATION LOCKED"
            colour = self._safety_colour(state.safety)
            self._text(cv2, image, prompt, (right - int(165 * scale), y + int(height * 0.67)), 0.29 * scale, colour, max_width=int(155 * scale))

    def _draw_scanline(self, cv2: Any, image: Any, width: int, height: int, scale: float, now: float) -> None:
        # Very subtle motion gives the static camera view a live systems feel.
        y = int(((math.sin(now * 0.75) + 1.0) * 0.5) * max(1, height - 1))
        self._line(cv2, image, (int(width * 0.28), y), (int(width * 0.72), y), self.CYAN_DIM, max(1, int(scale)))

    def _status_colour(self, value: AssistantStatus | str) -> tuple[int, int, int]:
        status = _enum_text(value)
        if status in {AssistantStatus.ERROR.value, AssistantStatus.OFFLINE.value}:
            return self.RED
        if status in {AssistantStatus.LISTENING.value, AssistantStatus.SPEAKING.value}:
            return self.MINT
        if status in {AssistantStatus.THINKING.value, AssistantStatus.EXECUTING.value}:
            return self.AMBER
        if status == AssistantStatus.PAUSED.value:
            return self.CYAN_DIM
        return self.CYAN

    def _safety_colour(self, value: SafetyState | str) -> tuple[int, int, int]:
        safety = _enum_text(value)
        if safety == SafetyState.BLOCKED.value:
            return self.RED
        if safety == SafetyState.CONFIRM.value:
            return self.AMBER
        return self.MINT


def _get_cv2() -> Any:
    try:
        import cv2  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - depends on host install.
        raise RuntimeError("AadiHUD needs opencv-python to render a camera HUD") from exc
    return cv2


def _enum_text(value: AssistantStatus | SafetyState | str) -> str:
    return str(value.value if isinstance(value, Enum) else value).strip().upper() or AssistantStatus.READY.value


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _format_duration(seconds: float | None) -> str:
    if seconds is None or not math.isfinite(seconds) or seconds < 0:
        return "--:--"
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{secs:02}"


def _trim_text(cv2: Any, text: str, max_width: int | None, font: int, scale: float, thickness: int) -> str:
    """Trim text at character boundaries so narrow camera windows stay tidy."""

    if max_width is None or max_width <= 0:
        return text
    if cv2.getTextSize(text, font, scale, thickness)[0][0] <= max_width:
        return text
    suffix = "…"
    candidate = text
    while candidate:
        candidate = candidate[:-1]
        rendered = candidate.rstrip() + suffix
        if cv2.getTextSize(rendered, font, scale, thickness)[0][0] <= max_width:
            return rendered
    return ""


__all__ = ["AssistantStatus", "AadiHUD", "HUDController", "HUDState", "SafetyState"]
