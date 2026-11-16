import cv2
import mediapipe as mp

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision


class FaceTracker:

    def __init__(self):

        options = vision.FaceLandmarkerOptions(

            base_options=BaseOptions(
                model_asset_path="models/face_landmarker.task"
            ),

            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,

            num_faces=1,

            min_face_detection_confidence=0.6,
            min_face_presence_confidence=0.6,
            min_tracking_confidence=0.6,

            running_mode=vision.RunningMode.IMAGE

        )

        self.detector = vision.FaceLandmarker.create_from_options(options)

    def detect(self, frame):

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb
        )

        result = self.detector.detect(image)

        if len(result.face_landmarks) == 0:
            return None

        return result.face_landmarks[0]