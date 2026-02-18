import os
import pickle
import numpy as np
import cv2
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    face_recognition = None
    FACE_RECOGNITION_AVAILABLE = False
from flask import current_app


class FaceRecognitionSystem:
    """Handles face detection, encoding, and recognition for attendance."""

    def __init__(self, tolerance=None, model=None):
        self.tolerance = tolerance
        self.model = model
        self.known_encodings = []
        self.known_ids = []

    def _get_config(self):
        if self.tolerance is None:
            self.tolerance = current_app.config.get('FACE_RECOGNITION_TOLERANCE', 0.5)
        if self.model is None:
            self.model = current_app.config.get('FACE_RECOGNITION_MODEL', 'hog')

    def detect_faces(self, image):
        """Detect faces in an image and return locations."""
        if not FACE_RECOGNITION_AVAILABLE:
            current_app.logger.warning('face_recognition library not installed. Skipping detection.')
            return [], image
        if isinstance(image, str):
            image = cv2.imread(image)
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_image, model=self.model)
        return face_locations, rgb_image

    def encode_face(self, image_path):
        """Generate face encoding from an image file.
        Returns encoding bytes or None if no face found."""
        if not FACE_RECOGNITION_AVAILABLE:
            current_app.logger.warning('face_recognition library not installed. Skipping encoding.')
            return None
        image = face_recognition.load_image_file(image_path)
        self._get_config()
        face_locations = face_recognition.face_locations(image, model=self.model)

        if not face_locations:
            return None

        encodings = face_recognition.face_encodings(image, face_locations)
        if not encodings:
            return None

        return pickle.dumps(encodings[0])

    def load_known_faces(self, students):
        """Load known face encodings from student records."""
        self.known_encodings = []
        self.known_ids = []

        for student in students:
            if student.face_encoding:
                encoding = pickle.loads(student.face_encoding)
                self.known_encodings.append(encoding)
                self.known_ids.append(student.id)

    def recognize_faces(self, frame):
        """Recognize faces in a video frame.
        Returns list of (student_id, confidence, location) tuples."""
        if not FACE_RECOGNITION_AVAILABLE:
            return []
        self._get_config()
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Resize for faster processing
        small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.25, fy=0.25)
        face_locations = face_recognition.face_locations(small_frame, model=self.model)
        face_encodings = face_recognition.face_encodings(small_frame, face_locations)

        results = []

        for encoding, location in zip(face_encodings, face_locations):
            if not self.known_encodings:
                continue

            distances = face_recognition.face_distance(self.known_encodings, encoding)
            best_match_idx = np.argmin(distances)
            best_distance = distances[best_match_idx]

            if best_distance <= self.tolerance:
                student_id = self.known_ids[best_match_idx]
                confidence = round(1.0 - best_distance, 4)
                # Scale location back up
                top, right, bottom, left = [v * 4 for v in location]
                results.append((student_id, confidence, (top, right, bottom, left)))

        return results

    def recognize_from_image(self, image_data):
        """Recognize faces from uploaded image data (bytes).
        Returns list of (student_id, confidence) tuples."""
        if not FACE_RECOGNITION_AVAILABLE:
            return []
        self._get_config()
        nparr = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return []

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame, model=self.model)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        results = []
        for encoding in face_encodings:
            if not self.known_encodings:
                continue

            distances = face_recognition.face_distance(self.known_encodings, encoding)
            best_match_idx = np.argmin(distances)
            best_distance = distances[best_match_idx]

            if best_distance <= self.tolerance:
                student_id = self.known_ids[best_match_idx]
                confidence = round(1.0 - best_distance, 4)
                results.append((student_id, confidence))

        return results

    def annotate_frame(self, frame, recognitions, student_names):
        """Draw bounding boxes and names on frame."""
        for student_id, confidence, (top, right, bottom, left) in recognitions:
            name = student_names.get(student_id, 'Unknown')
            color = (0, 255, 0)  # Green for recognized
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            label = f'{name} ({confidence:.0%})'
            cv2.rectangle(frame, (left, bottom - 30), (right, bottom), color, cv2.FILLED)
            cv2.putText(frame, label, (left + 6, bottom - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        return frame


# Singleton instance
face_system = FaceRecognitionSystem()
