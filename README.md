# TheraLink 🏥

TheraLink is an AI-powered physiotherapy assistance system that uses real-time pose estimation and deep learning to analyze posture, evaluate exercise accuracy, and provide live corrective feedback. It enables remote rehabilitation with objective biomechanical insights and session-based analytics.

---

## 🚀 Features
- Real-time human pose detection using MediaPipe
- AI-based posture and movement classification (TensorFlow)
- Joint angle and biomechanical analysis
- Live visual feedback and corrective guidance
- Exercise accuracy and session performance tracking
- Scalable backend-ready architecture for reports and analytics

---

## 🧠 Tech Stack
- **Computer Vision:** MediaPipe Pose
- **Deep Learning:** TensorFlow / Keras
- **Frontend:** Dash (Python)
- **Backend:** Flask
- **Video Processing:** OpenCV
- **Data Handling:** NumPy

---

## 🏋️ Supported Exercises
- Squats (current implementation)
- Designed to extend for other physiotherapy exercises such as:
  - Knee rehabilitation
  - Shoulder mobility
  - Arm and leg raises

---

## 📂 Project Structure

TheraLink/
├── app.py
├── SquatPosture.py
├── utils.py
├── assets/
│ └── stylesheet.css
├── models/
│ └── working_model_1/
├── requirements.txt
└── README.md


---

## ⚙️ Installation & Setup

### 1️⃣ Clone the repository
```bash
git clone https://github.com/your-username/TheraLink.git
cd TheraLink

Install dependencies:
pip install -r requirements.txt

Run the application:
python app.py

The app will launch automatically in your browser at:
http://127.0.0.1:8050/
