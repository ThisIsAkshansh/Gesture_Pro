import math
import time
import settings

from mouse import MouseController


class GestureEngine:

    def __init__(self):

        self.mouse = MouseController()

        self.xmin = 0.18
        self.xmax = 0.82

        self.ymin = 0.18
        self.ymax = 0.82

        self.last_click = 0
        self.click_delay = 0.30

        self.dragging = False

        self.scroll_last = 0

        self.eye_action_armed = True

    def clamp(self, value, mn, mx):
        return max(mn, min(value, mx))

    def dist(self, a, b):
        return math.hypot(
            a.x - b.x,
            a.y - b.y
        )

    def eye_ratio(self, face, points):
        left, top, right, bottom = [face[index] for index in points]
        return math.hypot(top.x - bottom.x, top.y - bottom.y) / max(
            math.hypot(left.x - right.x, left.y - right.y),
            1e-6
        )

    def process_eye(self, face):

        if face is None:
            self.eye_action_armed = True
            return None

        if len(face) <= 387:
            return None

        # MediaPipe Face Landmarker eye contours: right eye first, left eye second.
        right_eye = self.eye_ratio(face, (33, 159, 133, 145))
        left_eye = self.eye_ratio(face, (362, 386, 263, 374))

        right_closed = right_eye < 0.20
        left_closed = left_eye < 0.20
        both_closed = right_closed and left_closed
        wink = right_closed != left_closed

        if not both_closed and not wink:
            self.eye_action_armed = True
            return None

        if not self.eye_action_armed:
            return None

        now = time.time()
        if now - self.last_click <= self.click_delay:
            return None

        self.eye_action_armed = False

        if both_closed and settings.ENABLE_BLINK_CLICK and settings.ENABLE_LEFT_CLICK:
            self.mouse.left_click()
            self.last_click = now
            settings.LAST_ACTION = "LEFT CLICK"
            return "LEFT CLICK"

        if wink and settings.ENABLE_WINK_RIGHTCLICK and settings.ENABLE_RIGHT_CLICK:
            self.mouse.right_click()
            self.last_click = now
            settings.LAST_ACTION = "RIGHT CLICK"
            return "RIGHT CLICK"

        return None

    def process(self, hand):

        if hand is None:

            settings.LAST_ACTION = "NO HAND"

            if self.dragging:

                self.mouse.left_up()
                self.dragging = False

            return "NO HAND"

        index = hand[8]
        thumb = hand[4]
        middle = hand[12]
        ring = hand[16]

        x = self.clamp(index.x, self.xmin, self.xmax)
        y = self.clamp(index.y, self.ymin, self.ymax)

        x = (x - self.xmin) / (self.xmax - self.xmin)
        y = (y - self.ymin) / (self.ymax - self.ymin)

        self.mouse.move(x, y)

        pinch = self.dist(index, thumb)
        middle_pinch = self.dist(middle, thumb)
        ring_pinch = self.dist(ring, thumb)

        settings.LAST_ACTION = "TRACKING"

        now = time.time()

        # -------------------
        # LEFT CLICK
        # -------------------

        if pinch < 0.040:

            if now - self.last_click > self.click_delay:

                self.mouse.left_click()

                self.last_click = now

                settings.LAST_ACTION = "LEFT CLICK"

                return "LEFT CLICK"

        # -------------------
        # RIGHT CLICK
        # -------------------

        if middle_pinch < 0.040:

            if now - self.last_click > self.click_delay:

                self.mouse.right_click()

                self.last_click = now

                settings.LAST_ACTION = "RIGHT CLICK"

                return "RIGHT CLICK"

        # -------------------
        # DRAG
        # -------------------

        if pinch < 0.020:

            if not self.dragging:

                self.mouse.left_down()

                self.dragging = True

                settings.LAST_ACTION = "DRAG START"

        else:

            if self.dragging:

                self.mouse.left_up()

                self.dragging = False

                settings.LAST_ACTION = "DRAG END"

        # -------------------
        # SCROLL
        # -------------------

        if settings.ENABLE_SCROLL:

            if ring_pinch < 0.035:

                dy = middle.y - index.y

                if abs(dy) > 0.05:

                    amount = int(dy * 120)

                    self.mouse.scroll(amount)

                    settings.LAST_ACTION = "SCROLL"

                    return "SCROLL"

        return "TRACKING"