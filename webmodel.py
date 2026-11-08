import cv2
import numpy as np
import pyttsx3
import speech_recognition as sr
import os
from flask import Flask, Response, render_template, request
import threading
import time

app = Flask(__name__)

# Initialize text-to-speech
engine = pyttsx3.init()

# Global state
current_mode = None
current_word = ""
last_gesture = None
gesture_count = 0
cap = None

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
    if cv2.contourArea(contour) < 1000:
        return None
    
    # Features: area, aspect ratio, defect count
    area = cv2.contourArea(contour)
    x, y, w, h = cv2.boundingRect(contour)
    aspect_ratio = w / h if h > 0 else 0
    hull = cv2.convexHull(contour, returnPoints=False)
    defects = cv2.convexityDefects(contour, hull)
    defect_count = len(defects) if defects is not None else 0
    
    # Simple rule-based mapping
    if area > 50000:
        return 'space'
    if defect_count == 0:
        if 0.8 < aspect_ratio < 1.2:
            return 'A'
        elif aspect_ratio > 1.5:
            return 'B'
    elif defect_count == 1:
        if aspect_ratio < 0.7:
            return 'L'
        return 'D'
    elif defect_count == 2:
        if aspect_ratio > 1:
            return 'W'
        return 'V'
    elif defect_count >= 3:
        return 'Y'
    return 'C'

# Video feed generator for sign-to-speech
def generate_frames():
    global current_word, last_gesture, gesture_count
    while current_mode == 'sign_to_speech' and cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        gesture = recognize_gesture(frame)
        if gesture:
            cv2.putText(frame, gesture, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            if gesture == last_gesture:
                gesture_count += 1
            else:
                gesture_count = 0
            if gesture_count > 10:
                if gesture == 'space':
                    current_word += ' '
                elif gesture == 'delete':
                    current_word = current_word[:-1]
                elif gesture:
                    current_word += gesture
                gesture_count = 0
        last_gesture = gesture
        cv2.putText(frame, f"Word: {current_word}", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        
        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# Main route for UI
@app.route('/')
def index():
    return render_template('index.html', current_word=current_word)

# HTML template
@app.route('/template')
def get_template():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sign Language Translator</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; }
            .container { margin: 20px; }
            video, img { width: 640px; height: 480px; }
            button { padding: 10px 20px; margin: 10px; font-size: 16px; }
            #output { font-size: 24px; margin: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Sign Language Translator</h1>
            <div>
                <button onclick="startMode('sign_to_speech')">Sign to Speech</button>
                <button onclick="startMode('speech_to_sign')">Speech to Sign</button>
                <button onclick="stopMode()">Stop</button>
                <button onclick="speakWord()">Speak Word</button>
            </div>
            <div id="video-feed">
                <img src="{{ url_for('video_feed') }}" alt="Video Feed" style="display:none;" id="video">
            </div>
            <div id="output">{{ current_word }}</div>
            <script>
                function startMode(mode) {
                    fetch('/start_mode?mode=' + mode).then(() => {
                        if (mode === 'sign_to_speech') {
                            document.getElementById('video').style.display = 'block';
                            updateWord();
                        } else {
                            document.getElementById('video').style.display = 'none';
                        }
                    });
                }
                function stopMode() {
                    fetch('/stop_mode').then(() => {
                        document.getElementById('video').style.display = 'none';
                    });
                }
                function speakWord() {
                    fetch('/speak_word');
                }
                function updateWord() {
                    fetch('/get_word').then(response => response.text()).then(word => {
                        document.getElementById('output').innerText = word;
                        if (document.getElementById('video').style.display === 'block') {
                            setTimeout(updateWord, 500);
                        }
                    });
                }
            </script>
        </div>
    </body>
    </html>
    """

# Video feed route
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Start mode route
@app.route('/start_mode')
def start_mode():
    global current_mode, cap, current_word
    current_mode = request.args.get('mode')
    current_word = ""
    if current_mode == 'sign_to_speech':
        if cap is None or not cap.isOpened():
            cap = cv2.VideoCapture(0)
    elif current_mode == 'speech_to_sign':
        if cap is not None:
            cap.release()
            cap = None
        threading.Thread(target=speech_to_sign).start()
    return "OK"

# Stop mode route
@app.route('/stop_mode')
def stop_mode():
    global current_mode, cap
    current_mode = None
    if cap is not None:
        cap.release()
        cap = None
    return "OK"

# Speak current word
@app.route('/speak_word')
def speak_word():
    global current_word
    if current_word:
        engine.say(current_word)
        engine.runAndWait()
        current_word = ""
    return "OK"

# Get current word
@app.route('/get_word')
def get_word():
    return current_word

# Speech to Sign Language
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
    global current_mode
    current_mode = None

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)