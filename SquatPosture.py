# --- START OF FILE SquatPosture.py ---

import cv2
import mediapipe as mp
import numpy as np

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

def calculate_angle(a, b, c):
    a = np.array(a)  # First
    b = np.array(b)  # Mid
    c = np.array(c)  # End

    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - \
              np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)

    if angle > 180.0:
        angle = 360 - angle

    return angle

def get_params(results):
    try:
        landmarks = results.pose_landmarks.landmark

        # Get coordinates for relevant joints
        # Left side
        L_hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x,
                 landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]
        L_knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x,
                  landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
        L_ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x,
                   landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
        L_heel = [landmarks[mp_pose.PoseLandmark.LEFT_HEEL.value].x,
                  landmarks[mp_pose.PoseLandmark.LEFT_HEEL.value].y]
        L_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                      landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
        L_elbow = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x,
                   landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
        L_wrist = [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x,
                   landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y]


        # Right side
        R_hip = [landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x,
                 landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y]
        R_knee = [landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].x,
                  landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y]
        R_ankle = [landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x,
                   landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y]
        R_heel = [landmarks[mp_pose.PoseLandmark.RIGHT_HEEL.value].x,
                  landmarks[mp_pose.PoseLandmark.RIGHT_HEEL.value].y]
        R_shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,
                      landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
        R_elbow = [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x,
                   landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
        R_wrist = [landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].x,
                   landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].y]

        # Calculate angles
        angle_L_knee = calculate_angle(L_hip, L_knee, L_ankle)
        angle_R_knee = calculate_angle(R_hip, R_knee, R_ankle)
        angle_L_hip = calculate_angle(L_shoulder, L_hip, L_knee)
        angle_R_hip = calculate_angle(R_shoulder, R_hip, R_knee)
        angle_L_ankle = calculate_angle(L_knee, L_ankle, L_heel)
        angle_R_ankle = calculate_angle(R_knee, R_ankle, R_heel)
        
        # Upper body
        angle_L_shoulder = calculate_angle(L_elbow, L_shoulder, L_hip)
        angle_R_shoulder = calculate_angle(R_elbow, R_shoulder, R_hip)
        angle_L_elbow = calculate_angle(L_wrist, L_elbow, L_shoulder)
        angle_R_elbow = calculate_angle(R_wrist, R_elbow, R_shoulder)


        # Parameters for Squat detection (e.g., averages of left and right)
        params = np.array([
            (angle_L_knee + angle_R_knee) / 2,
            (angle_L_hip + angle_R_hip) / 2,
            (angle_L_ankle + angle_R_ankle) / 2,
            (angle_L_shoulder + angle_R_shoulder) / 2,
            (angle_L_elbow + angle_R_elbow) / 2
        ])

        return params

    except Exception as e:
        # print(f"Error in get_params: {e}")
        return np.zeros(5) # Return array of zeros if landmarks are not detected

def get_params_and_angles(results):
    try:
        landmarks = results.pose_landmarks.landmark

        # Get coordinates for relevant joints
        L_hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x,
                 landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]
        L_knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x,
                  landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
        L_ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x,
                   landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
        L_heel = [landmarks[mp_pose.PoseLandmark.LEFT_HEEL.value].x,
                  landmarks[mp_pose.PoseLandmark.LEFT_HEEL.value].y]
        L_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                      landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
        L_elbow = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x,
                   landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
        L_wrist = [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x,
                   landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y]

        R_hip = [landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x,
                 landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y]
        R_knee = [landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].x,
                  landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y]
        R_ankle = [landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x,
                   landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y]
        R_heel = [landmarks[mp_pose.PoseLandmark.RIGHT_HEEL.value].x,
                  landmarks[mp_pose.PoseLandmark.RIGHT_HEEL.value].y]
        R_shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,
                      landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
        R_elbow = [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x,
                   landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
        R_wrist = [landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].x,
                   landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].y]

        # Calculate angles
        angle_L_knee = calculate_angle(L_hip, L_knee, L_ankle)
        angle_R_knee = calculate_angle(R_hip, R_knee, R_ankle)
        angle_L_hip = calculate_angle(L_shoulder, L_hip, L_knee)
        angle_R_hip = calculate_angle(R_shoulder, R_hip, R_knee)
        angle_L_ankle = calculate_angle(L_knee, L_ankle, L_heel)
        angle_R_ankle = calculate_angle(R_knee, R_ankle, R_heel)
        
        angle_L_shoulder = calculate_angle(L_elbow, L_shoulder, L_hip)
        angle_R_shoulder = calculate_angle(R_elbow, R_shoulder, R_hip)
        angle_L_elbow = calculate_angle(L_wrist, L_elbow, L_shoulder)
        angle_R_elbow = calculate_angle(R_wrist, R_elbow, R_shoulder)

        # Average angles for params for model input
        params = np.array([
            (angle_L_knee + angle_R_knee) / 2,
            (angle_L_hip + angle_R_hip) / 2,
            (angle_L_ankle + angle_R_ankle) / 2,
            (angle_L_shoulder + angle_R_shoulder) / 2,
            (angle_L_elbow + angle_R_elbow) / 2
        ])
        
        # Store all calculated angles
        current_angles = {
            'knee': (angle_L_knee + angle_R_knee) / 2,
            'hip': (angle_L_hip + angle_R_hip) / 2,
            'ankle': (angle_L_ankle + angle_R_ankle) / 2,
            'shoulder': (angle_L_shoulder + angle_R_shoulder) / 2,
            'elbow': (angle_L_elbow + angle_R_elbow) / 2,
            'wrist': (angle_L_wrist + angle_R_wrist) / 2 if 'angle_L_wrist' in locals() and 'angle_R_wrist' in locals() else None # Add wrist if calculated
        }
        
        return params, current_angles

    except Exception as e:
        # print(f"Error in get_params_and_angles: {e}")
        return np.zeros(5), {} # Return array of zeros and empty dict if landmarks are not detected