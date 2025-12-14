import cv2
import mediapipe as mp
import numpy as np
import plotly.graph_objects as go
from collections import deque
import time
import simpleaudio as sa
import threading
import queue
import datetime
import sqlite3
import pandas as pd

# Initialize MediaPipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

# Squat Counter Variables
counter = 0
stage = None
feedback = "Stand straight"
squat_start_time = None
squat_end_time = None
session_active = False
start_time = None
exercise_duration = 0 # In seconds

# Target variables (can be set by user later)
TARGET_REPS = 10
TARGET_SETS = 3
current_set = 0
reps_in_current_set = 0
set_rest_active = False
rest_start_time = None
REST_DURATION_SECONDS = 60

# Joint angle thresholds (example values, may need tuning)
MIN_KNEE_ANGLE_SQUAT = 70  # Angle at bottom of squat
MAX_KNEE_ANGLE_STAND = 160 # Angle when standing straight
MIN_HIP_ANGLE_SQUAT = 60   # Hip angle at bottom
MAX_HIP_ANGLE_STAND = 170  # Hip angle when standing

# Deque for smoothing angles (optional, but good for noisy data)
knee_angle_deque = deque(maxlen=5)
hip_angle_deque = deque(maxlen=5)

# Queue for inter-thread communication (video frames and data)
frame_queue = queue.Queue(maxsize=1)
data_queue = queue.Queue(maxsize=1) # For angles, reps, feedback

# Audio feedback
try:
    sound_squat_down = sa.WaveObject.from_file("audio/squat_down.wav")
    sound_squat_up = sa.WaveObject.from_file("audio/squat_up.wav")
    sound_good_job = sa.WaveObject.from_file("audio/good_job.wav")
    sound_keep_going = sa.WaveObject.from_file("audio/keep_going.wav")
    sound_rest = sa.WaveObject.from_file("audio/rest.wav")
    sound_set_complete = sa.WaveObject.from_file("audio/set_complete.wav")
    sound_workout_complete = sa.WaveObject.from_file("audio/workout_complete.wav")
    audio_loaded = True
except FileNotFoundError:
    print("Audio files not found. Audio feedback will be disabled.")
    audio_loaded = False

def play_sound(sound_obj):
    if audio_loaded:
        threading.Thread(target=sound_obj.play).start()

def calculate_angle(a, b, c):
    a = np.array(a)  # First
    b = np.array(b)  # Mid
    c = np.array(c)  # End

    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)

    if angle > 180.0:
        angle = 360 - angle
    return angle

def process_frame(frame):
    global counter, stage, feedback, squat_start_time, squat_end_time
    global reps_in_current_set, set_rest_active, rest_start_time, exercise_duration

    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image.flags.writeable = False
    results = pose.process(image)
    image.flags.writeable = True
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    current_knee_angle = None
    current_hip_angle = None

    if results.pose_landmarks:
        # Extract Landmarks
        landmarks = results.pose_landmarks.landmark
        
        # Get coordinates for key points
        try:
            shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
            hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]
            knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
            ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]

            # Calculate angles
            current_knee_angle = calculate_angle(hip, knee, ankle)
            current_hip_angle = calculate_angle(shoulder, hip, knee)

            knee_angle_deque.append(current_knee_angle)
            hip_angle_deque.append(current_hip_angle)

            smoothed_knee_angle = np.mean(knee_angle_deque)
            smoothed_hip_angle = np.mean(hip_angle_deque)

            # Squat Logic
            if session_active and not set_rest_active:
                if smoothed_knee_angle > MAX_KNEE_ANGLE_STAND: # Roughly standing straight
                    stage = "up"
                    feedback = "Stand straight"
                    squat_end_time = time.time() # Mark time when standing up
                if smoothed_knee_angle < MIN_KNEE_ANGLE_SQUAT and stage == 'up': # Squatting deep enough
                    stage = "down"
                    feedback = "Good depth"
                    squat_start_time = time.time() # Mark time when squatting down
                
                if stage == "down" and smoothed_knee_angle > MAX_KNEE_ANGLE_STAND: # Reached standing position after a squat
                    if squat_start_time and squat_end_time and (squat_end_time - squat_start_time) < 10: # Ensure reasonable squat duration
                        reps_in_current_set += 1
                        counter += 1
                        play_sound(sound_squat_up)
                        feedback = "Rep counted!"
                        print(f"Rep: {reps_in_current_set}, Total: {counter}")
                        stage = "up" # Reset stage for next rep
                        squat_start_time = None
                        squat_end_time = None
                        
                        if reps_in_current_set >= TARGET_REPS:
                            start_rest()
                            play_sound(sound_set_complete)
                            if current_set < TARGET_SETS:
                                feedback = f"Set {current_set+1} complete! Rest for {REST_DURATION_SECONDS} seconds."
                            else:
                                feedback = "Workout complete!"
                                play_sound(sound_workout_complete)
                                stop_session()
                    else:
                        # This handles cases where the "up" stage was missed or squat was too long
                        feedback = "Keep standing, or perform a controlled squat."


            # Visual feedback on angles
            cv2.putText(image, f"Knee: {int(smoothed_knee_angle)}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.putText(image, f"Hip: {int(smoothed_hip_angle)}", (10, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

            # Draw landmarks and connections
            mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                                    mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=2),
                                    mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2)
                                    )
        except Exception as e:
            # print(f"Error processing landmarks: {e}")
            feedback = "Adjust camera: ensure full body is visible."
            pass
    else:
        feedback = "No person detected. Adjust camera."

    # Update exercise duration
    if session_active and start_time:
        exercise_duration = int(time.time() - start_time)

    # Display squat counter
    cv2.putText(image, f"Reps: {reps_in_current_set}/{TARGET_REPS}", (image.shape[1] - 300, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
    cv2.putText(image, f"Sets: {current_set}/{TARGET_SETS}", (image.shape[1] - 300, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
    cv2.putText(image, f"Duration: {exercise_duration // 60:02d}:{(exercise_duration % 60):02d}", (image.shape[1] - 300, 110),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
    cv2.putText(image, feedback, (int(image.shape[1]/2) - 150, image.shape[0] - 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

    # Rest timer display
    if set_rest_active:
        remaining_rest_time = int(REST_DURATION_SECONDS - (time.time() - rest_start_time))
        if remaining_rest_time > 0:
            rest_feedback = f"Rest: {remaining_rest_time}s"
            cv2.putText(image, rest_feedback, (image.shape[1] // 2 - 100, image.shape[0] // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3, cv2.LINE_AA)
        else:
            end_rest()

    # Put data in queue for Plotly graph
    data_for_plot = {
        'time': time.time(),
        'knee_angle': smoothed_knee_angle if smoothed_knee_angle is not None else None,
        'hip_angle': smoothed_hip_angle if smoothed_hip_angle is not None else None,
        'reps': reps_in_current_set,
        'total_reps': counter,
        'feedback': feedback
    }
    if not data_queue.full():
        data_queue.put(data_for_plot)

    return image

def start_session():
    global session_active, counter, reps_in_current_set, current_set, stage, feedback, start_time, exercise_duration
    global set_rest_active, rest_start_time, squat_start_time, squat_end_time
    if not session_active:
        session_active = True
        counter = 0
        reps_in_current_set = 0
        current_set = 0
        stage = None
        feedback = "Get ready!"
        start_time = time.time()
        exercise_duration = 0
        set_rest_active = False
        rest_start_time = None
        squat_start_time = None
        squat_end_time = None
        play_sound(sound_keep_going)
        print("Session Started!")

def stop_session():
    global session_active, counter, reps_in_current_set, current_set, stage, feedback, start_time, exercise_duration
    global set_rest_active, rest_start_time
    if session_active:
        session_active = False
        print(f"Session Stopped! Total Reps: {counter}, Duration: {exercise_duration}s")
        # Save session data to DB here if needed
        feedback = "Session Ended."
        start_time = None
        current_set = 0 # Reset for next session
        reps_in_current_set = 0
        set_rest_active = False
        rest_start_time = None
        play_sound(sound_good_job)

def start_rest():
    global set_rest_active, rest_start_time, current_set, reps_in_current_set
    set_rest_active = True
    rest_start_time = time.time()
    current_set += 1 # Increment set after completing reps for the previous set
    print(f"Set {current_set} complete. Starting rest.")

def end_rest():
    global set_rest_active, reps_in_current_set, feedback
    set_rest_active = False
    reps_in_current_set = 0 # Reset reps for the new set
    feedback = "Rest Over! Start next set."
    play_sound(sound_squat_down)
    print("Rest ended. Starting next set.")

def generate_frames():
    cap = cv2.VideoCapture(0)  # Use default camera
    if not cap.isOpened():
        print("Error: Could not open video stream.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to grab frame.")
            break

        processed_frame = process_frame(frame)
        ret, buffer = cv2.imencode('.jpg', processed_frame)
        frame_bytes = buffer.tobytes()

        if not frame_queue.full():
            frame_queue.put(frame_bytes)
        else:
            # If queue is full, just replace the old frame with the new one
            try:
                frame_queue.get_nowait()
            except queue.Empty:
                pass
            frame_queue.put(frame_bytes)

        if not session_active and not set_rest_active: # If session ended or not started, stop streaming
            # Optionally, keep streaming a static frame or message
            time.sleep(0.1) # Reduce CPU usage
        
        # This part handles closing the stream if the app needs to stop
        # In a Dash app, this might be triggered by a specific event or when the app closes
        # For now, we'll assume the thread will run until the main app process terminates
        # or if a specific stop signal is implemented.
    cap.release()

# SQLite Database Integration
DATABASE_PATH = 'theralink.db'

def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            date TEXT NOT NULL,
            exercise_type TEXT NOT NULL,
            reps_achieved INTEGER,
            reps_target INTEGER,
            sets_achieved INTEGER,
            sets_target INTEGER,
            completion_status TEXT,
            feedback TEXT,
            joint_angles_json TEXT, -- Store as JSON string
            exercise_duration INTEGER,
            FOREIGN KEY (patient_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

def save_session_data(patient_id, reps_achieved, reps_target, sets_achieved, sets_target,
                       feedback_msg, joint_angles_data, duration):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Simple JSON serialization for joint_angles (example structure)
    import json
    joint_angles_json = json.dumps(joint_angles_data)

    cursor.execute('''
        INSERT INTO sessions (patient_id, date, exercise_type, reps_achieved, reps_target,
                              sets_achieved, sets_target, completion_status, feedback,
                              joint_angles_json, exercise_duration)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (patient_id, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Squats',
          reps_achieved, reps_target, sets_achieved, sets_target, 'Completed',
          feedback_msg, joint_angles_json, duration))
    conn.commit()
    conn.close()
    print("Session data saved to database.")

# Example usage for saving data (call this when a session ends)
# save_session_data(
#     patient_id=1, # Replace with actual patient ID
#     reps_achieved=counter,
#     reps_target=TARGET_REPS * TARGET_SETS,
#     sets_achieved=current_set,
#     sets_target=TARGET_SETS,
#     feedback_msg="Good workout!",
#     joint_angles_data={'knee_angles': list(knee_angle_deque), 'hip_angles': list(hip_angle_deque)},
#     duration=exercise_duration
# )

def get_patient_sessions(patient_id):
    conn = sqlite3.connect(DATABASE_PATH)
    df = pd.read_sql_query(f"SELECT * FROM sessions WHERE patient_id = {patient_id}", conn)
    conn.close()
    return df

# Initialize DB when this module is imported
init_db()