from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from facestudio.ai.models import FaceAnalysis, Point, Rect


class FaceAnalysisError(RuntimeError):
    pass


class FaceAnalyzer:
    def __init__(self) -> None:
        cascade_root = Path(cv2.data.haarcascades)
        self.face_detector = cv2.CascadeClassifier(
            str(cascade_root / "haarcascade_frontalface_default.xml")
        )
        self.eye_detector = cv2.CascadeClassifier(
            str(cascade_root / "haarcascade_eye_tree_eyeglasses.xml")
        )
        self.smile_detector = cv2.CascadeClassifier(
            str(cascade_root / "haarcascade_smile.xml")
        )
        if self.face_detector.empty():
            raise FaceAnalysisError("OpenCV face detector could not be loaded.")

    def analyze(self, image_path: Path) -> tuple[FaceAnalysis, np.ndarray]:
        image = cv2.imread(str(image_path))
        if image is None:
            raise FaceAnalysisError("The source photograph could not be read.")

        height, width = image.shape[:2]
        grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        grey = cv2.equalizeHist(grey)

        faces = self.face_detector.detectMultiScale(
            grey,
            scaleFactor=1.08,
            minNeighbors=5,
            minSize=(80, 80),
        )
        if len(faces) == 0:
            raise FaceAnalysisError(
                "No clear frontal face was detected. Use a well-lit, front-facing photograph."
            )

        x, y, face_width, face_height = max(
            faces,
            key=lambda box: int(box[2]) * int(box[3]),
        )
        face_box = Rect(int(x), int(y), int(face_width), int(face_height))
        face_grey = grey[y:y + face_height, x:x + face_width]

        landmarks: dict[str, Point] = {}
        notes: list[str] = []

        eyes = self.eye_detector.detectMultiScale(
            face_grey[: int(face_height * 0.65), :],
            scaleFactor=1.08,
            minNeighbors=6,
            minSize=(18, 18),
        )
        eye_candidates = sorted(
            eyes,
            key=lambda box: int(box[2]) * int(box[3]),
            reverse=True,
        )[:4]
        eye_centres = []
        for ex, ey, ew, eh in eye_candidates:
            centre = (x + ex + ew / 2, y + ey + eh / 2, ew * eh)
            eye_centres.append(centre)

        if len(eye_centres) >= 2:
            selected = sorted(eye_centres[:2], key=lambda item: item[0])
            left, right = selected
            landmarks["left_eye"] = Point(
                left[0] / width, left[1] / height, "detected", 0.82
            )
            landmarks["right_eye"] = Point(
                right[0] / width, right[1] / height, "detected", 0.82
            )
            eye_y = (left[1] + right[1]) / 2
            eye_distance = abs(right[0] - left[0])
        else:
            landmarks["left_eye"] = Point(
                (x + face_width * 0.34) / width,
                (y + face_height * 0.39) / height,
                "estimated",
                0.35,
            )
            landmarks["right_eye"] = Point(
                (x + face_width * 0.66) / width,
                (y + face_height * 0.39) / height,
                "estimated",
                0.35,
            )
            eye_y = y + face_height * 0.39
            eye_distance = face_width * 0.32
            notes.append("Eye centres were estimated from face proportions.")

        lower_face = face_grey[int(face_height * 0.48):, :]
        smiles = self.smile_detector.detectMultiScale(
            lower_face,
            scaleFactor=1.2,
            minNeighbors=20,
            minSize=(25, 12),
        )
        if len(smiles):
            sx, sy, sw, sh = max(
                smiles,
                key=lambda box: int(box[2]) * int(box[3]),
            )
            mouth_x = x + sx + sw / 2
            mouth_y = y + int(face_height * 0.48) + sy + sh / 2
            mouth_confidence = 0.62
            mouth_source = "detected"
        else:
            mouth_x = x + face_width * 0.50
            mouth_y = y + face_height * 0.76
            mouth_confidence = 0.32
            mouth_source = "estimated"
            notes.append("Mouth centre was estimated from face proportions.")

        landmarks["nose_tip"] = Point(
            (x + face_width * 0.50) / width,
            (y + face_height * 0.60) / height,
            "estimated",
            0.42,
        )
        landmarks["mouth_centre"] = Point(
            mouth_x / width,
            mouth_y / height,
            mouth_source,
            mouth_confidence,
        )
        landmarks["chin"] = Point(
            (x + face_width * 0.50) / width,
            (y + face_height * 0.94) / height,
            "estimated",
            0.38,
        )
        landmarks["forehead"] = Point(
            (x + face_width * 0.50) / width,
            (y + face_height * 0.10) / height,
            "estimated",
            0.38,
        )

        aspect = face_height / max(face_width, 1)
        eye_ratio = eye_distance / max(face_width, 1)
        upper_ratio = (eye_y - y) / max(face_height, 1)
        mouth_ratio = (mouth_y - y) / max(face_height, 1)

        if aspect >= 1.38:
            shape = "oblong"
        elif aspect <= 1.10:
            shape = "round"
        elif aspect <= 1.22:
            shape = "square / round"
        else:
            shape = "oval"

        detected_points = sum(
            1 for point in landmarks.values() if point.source == "detected"
        )
        confidence = min(
            0.95,
            0.48 + detected_points * 0.08 + min(face_width, face_height) / 2000,
        )

        analysis = FaceAnalysis(
            image_width=width,
            image_height=height,
            face_box=face_box,
            landmarks=landmarks,
            measurements={
                "face_height_width_ratio": round(aspect, 4),
                "inter_eye_face_width_ratio": round(eye_ratio, 4),
                "eye_line_face_height_ratio": round(upper_ratio, 4),
                "mouth_line_face_height_ratio": round(mouth_ratio, 4),
                "face_width_pixels": float(face_width),
                "face_height_pixels": float(face_height),
            },
            face_shape=shape,
            confidence=round(confidence, 3),
            notes=notes,
        )
        return analysis, self.draw_overlay(image, analysis)

    @staticmethod
    def draw_overlay(image: np.ndarray, analysis: FaceAnalysis) -> np.ndarray:
        overlay = image.copy()
        box = analysis.face_box
        cv2.rectangle(
            overlay,
            (box.x, box.y),
            (box.x + box.width, box.y + box.height),
            (0, 210, 255),
            2,
        )

        for name, point in analysis.landmarks.items():
            px = int(point.x * analysis.image_width)
            py = int(point.y * analysis.image_height)
            colour = (40, 220, 80) if point.source == "detected" else (0, 165, 255)
            cv2.circle(overlay, (px, py), 5, colour, -1)
            cv2.putText(
                overlay,
                name.replace("_", " "),
                (px + 7, py - 7),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                colour,
                1,
                cv2.LINE_AA,
            )

        cv2.putText(
            overlay,
            f"Shape: {analysis.face_shape}  Confidence: {analysis.confidence:.0%}",
            (box.x, max(25, box.y - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 210, 255),
            2,
            cv2.LINE_AA,
        )
        return overlay
