import cv2
import mediapipe as mp

from mediapipe.tasks.python import vision
from mediapipe.tasks.python import BaseOptions


class HandTracker:

    def __init__(self):

        options = vision.HandLandmarkerOptions(

            base_options=BaseOptions(
                model_asset_path="models/hand_landmarker.task"
            ),

            num_hands=1,

            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.6,
            min_tracking_confidence=0.6,

            running_mode=vision.RunningMode.IMAGE

        )

        self.detector = vision.HandLandmarker.create_from_options(options)

    def detect(self, frame):

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb
        )

        result = self.detector.detect(image)

        if len(result.hand_landmarks) == 0:
            return None

        return result.hand_landmarks[0]