from Quartz import (
    CGEventCreateMouseEvent,
    CGEventCreateScrollWheelEvent,
    CGEventPost,
    CGDisplayBounds,

    kCGHIDEventTap,

    kCGEventMouseMoved,

    kCGEventLeftMouseDown,
    kCGEventLeftMouseUp,

    kCGEventRightMouseDown,
    kCGEventRightMouseUp,

    kCGMouseButtonLeft,
    kCGMouseButtonRight,

    kCGScrollEventUnitLine
)

import settings


class MouseController:

    def __init__(self):

        bounds = CGDisplayBounds(0)

        self.screen_width = int(bounds.size.width)
        self.screen_height = int(bounds.size.height)

        self.prev_x = self.screen_width // 2
        self.prev_y = self.screen_height // 2

        self.smoothing = settings.SMOOTHING
        self.sensitivity = settings.SENSITIVITY

    # ------------------------------------

    def move(self, x_norm, y_norm):

        x_norm = max(0.0, min(1.0, x_norm))
        y_norm = max(0.0, min(1.0, y_norm))

        x = int(
            x_norm *
            self.screen_width *
            self.sensitivity
        )

        y = int(
            y_norm *
            self.screen_height *
            self.sensitivity
        )

        x = min(x, self.screen_width - 1)
        y = min(y, self.screen_height - 1)

        x = self.prev_x + (x - self.prev_x) * self.smoothing
        y = self.prev_y + (y - self.prev_y) * self.smoothing

        self.prev_x = x
        self.prev_y = y

        event = CGEventCreateMouseEvent(

            None,
            kCGEventMouseMoved,
            (x, y),
            0

        )

        CGEventPost(
            kCGHIDEventTap,
            event
        )

    # ------------------------------------

    def left_click(self):

        self.left_down()
        self.left_up()

    # ------------------------------------

    def left_down(self):

        event = CGEventCreateMouseEvent(

            None,
            kCGEventLeftMouseDown,
            (self.prev_x, self.prev_y),
            kCGMouseButtonLeft

        )

        CGEventPost(
            kCGHIDEventTap,
            event
        )

    # ------------------------------------

    def left_up(self):

        event = CGEventCreateMouseEvent(

            None,
            kCGEventLeftMouseUp,
            (self.prev_x, self.prev_y),
            kCGMouseButtonLeft

        )

        CGEventPost(
            kCGHIDEventTap,
            event
        )

    # ------------------------------------

    def right_click(self):

        down = CGEventCreateMouseEvent(

            None,
            kCGEventRightMouseDown,
            (self.prev_x, self.prev_y),
            kCGMouseButtonRight

        )

        up = CGEventCreateMouseEvent(

            None,
            kCGEventRightMouseUp,
            (self.prev_x, self.prev_y),
            kCGMouseButtonRight

        )

        CGEventPost(
            kCGHIDEventTap,
            down
        )

        CGEventPost(
            kCGHIDEventTap,
            up
        )

    # ------------------------------------

    def double_click(self):

        self.left_click()
        self.left_click()

    # ------------------------------------

    def scroll(self, amount):

        event = CGEventCreateScrollWheelEvent(

            None,
            kCGScrollEventUnitLine,
            1,
            int(amount)

        )

        CGEventPost(
            kCGHIDEventTap,
            event
        )