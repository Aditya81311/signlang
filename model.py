import cv2
import numpy as np
import pyttsx3
import speech_recognition as sr
import os
import time

# Initialize text-to-speech
engine = pyttsx3.init()

# Load Haar Cascade for hand detection (download from OpenCV GitHub or use provided path)
# Note: You need to download 'haarcascade_hand.xml' from OpenCV's Haar Cascade repository
# or use a similar pre-trained hand cascade. For simplicity, we'll use contour-based detection as fallback.
hand_cascade = None  # Set to path if you have a Haar Cascade file, e.g., 'haarcascade_hand.xml'
# Example: hand_cascade = cv2.CascadeClassifier('haarcascade_hand.xml')

# Gestures (ASL letters A-Z, space, delete)
gestures = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 
            'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'space', 'delete']

# Preprocess frame for hand detection
def preprocess_frame(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 100, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return thresh

# Extract features and map to ASL letters (rule-based)
def recognize_gesture(frame):
    thresh = preprocess_frame(frame)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(contour) < 1000:  # Ignore small contours
        return None
    
    # Features: area, aspect ratio, defect count
    area = cv2.contourArea(contour)
    x, y, w, h = cv2.boundingRect(contour)
    aspect_ratio = w / h if h > 0 else 0
    hull = cv2.convexHull(contour, returnPoints=False)
    defects = cv2.convexityDefects(contour, hull)
    defect_count = len(defects) if defects is not None else 0
    
    # Simple rule-based mapping (approximate, for demo purposes)
    if area > 50000:
        return 'space'  # Large area for space
    if defect_count == 0:
        if 0.8 < aspect_ratio < 1.2:
            return 'A'  # Compact, square shape
        elif aspect_ratio > 1.5:
            return 'B'  # Wide shape
    elif defect_count == 1:
        if aspect_ratio < 0.7:
            return 'L'  # Tall shape with one defect
        return 'D'
    elif defect_count == 2:
        if aspect_ratio > 1:
            return 'W'  # Wide with two defects
        return 'V'
    elif defect_count >= 3:
        return 'Y'  # Multiple defects
    return 'C'  # Default fallback

# Sign Language to Speech Mode
def sign_to_speech():
    cap = cv2.VideoCapture(0)
    current_word = ""
    last_gesture = None
    gesture_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        thresh = preprocess_frame(frame)
        gesture = recognize_gesture(frame)
        if gesture:
            cv2.putText(frame, gesture, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Stabilize prediction
        if gesture == last_gesture:
            gesture_count += 1
        else:
            gesture_count = 0
        if gesture_count > 10:  # Stable for ~10 frames
            if gesture == 'space':
                current_word += ' '
            elif gesture == 'delete':
                current_word = current_word[:-1]
            elif gesture:
                current_word += gesture
            gesture_count = 0
            print(f"Current word: {current_word}")
        last_gesture = gesture
        
        # Speak on 's' key
        if cv2.waitKey(1) & 0xFF == ord('s'):
            if current_word:
                engine.say(current_word)
                engine.runAndWait()
                current_word = ""
        
        cv2.putText(frame, f"Word: {current_word}", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        cv2.imshow('Sign to Speech', frame)
        cv2.imshow('Threshold', thresh)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()

# Speech to Sign Language Mode
def speech_to_sign():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Speak something...")
        audio = r.listen(source)
        try:
            text = r.recognize_google(audio)
            print(f"Recognized: {text}")
            for char in text.lower():
                if char.isalpha() or char == ' ':
                    sign_file = f"signs/{char if char != ' ' else 'space'}.jpg"
                    if os.path.exists(sign_file):
                        img = cv2.imread(sign_file)
                        cv2.imshow('Sign', img)
                        cv2.waitKey(1000)
                    else:
                        print(f"Sign image for '{char}' not found.")
            cv2.destroyAllWindows()
        except sr.UnknownValueError:
            print("Could not understand audio")
        except sr.RequestError:
            print("Speech service error")

# Main Menu
if __name__ == "__main__":
    while True:
        print("\nSign Language Translator Menu:")
        print("1. Sign to Speech Mode")
        print("2. Speech to Sign Mode")
        print("3. Exit")
        choice = input("Enter choice: ")
        if choice == '1':
            sign_to_speech()
        elif choice == '2':
            speech_to_sign()
        elif choice == '3':
            break
        else:
            print("Invalid choice")