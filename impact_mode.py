"""A small, deterministic demo challenge for live hackathon presentations."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic


@dataclass(frozen=True)
class ChallengeStep:
    title: str
    prompt: str
    actions: tuple[str, ...]


class ImpactMode:
    """Turns ordinary gesture events into a visible, repeatable demo story."""

    steps = (
        ChallengeStep("CONTROL", "Move your hand into view", ("TRACKING",)),
        ChallengeStep("CLICK", "Pinch once to select", ("LEFT CLICK",)),
        ChallengeStep("ACCESS", "Pinch and hold to begin", ("DRAG START",)),
        ChallengeStep("RELEASE", "Release to finish the drag", ("DRAG END",)),
    )

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.step_index = 0
        self.completed_actions = 0
        self.started_at = monotonic()
        self.last_event = "READY"
        self._last_counted_action = ""
        self._last_counted_at = 0.0

    @property
    def complete(self) -> bool:
        return self.step_index >= len(self.steps)

    @property
    def current_step(self) -> ChallengeStep | None:
        return None if self.complete else self.steps[self.step_index]

    @property
    def score(self) -> int:
        return round(self.completed_actions / len(self.steps) * 100)

    def observe(self, action: str) -> bool:
        """Consume a gesture action once and return whether the challenge advanced."""

        if self.complete or not action:
            return False

        now = monotonic()
        if action == self._last_counted_action and now - self._last_counted_at < 0.45:
            return False

        self.last_event = action
        step = self.current_step
        if step is None or action not in step.actions:
            return False

        self._last_counted_action = action
        self._last_counted_at = now
        self.completed_actions += 1
        self.step_index += 1
        return True

    def snapshot(self) -> dict[str, object]:
        step = self.current_step
        return {
            "complete": self.complete,
            "score": self.score,
            "step": self.step_index + 1 if step else len(self.steps),
            "total": len(self.steps),
            "title": step.title if step else "PROOF COMPLETE",
            "prompt": step.prompt if step else "Hands-free control demonstrated",
            "last_event": self.last_event,
        }