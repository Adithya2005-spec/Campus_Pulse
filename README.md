# 🎓 Smart Campus Event Finder + RSVP + Crowd Capacity Predictor

A full-stack web application designed for campus event management with smart crowd prediction and AI-powered recommendations.

## 🚀 Features

- **Event Discovery**: Browse events by category (Tech, Cultural, Sports, Workshops) with search and filtering.
- **Smart RSVP System**: Users can RSVP as 'Attending', 'Maybe', or 'Not Attending'.
- **Crowd Capacity Predictor**: Rule-based engine that predicts attendance based on RSVP status, event type, and time slot.
- **Risk Management**: Visual indicators (Safe, Warning, High Risk) based on predicted attendance vs. venue capacity.
- **AI Recommendations**: Personalized event suggestions using **Google Gemini API**.
- **Email Notifications**: Automated RSVP confirmations via **Resend API**.
- **Interactive Dashboard**: Real-time analytics using **Chart.js**.
- **Maps Integration**: Embedded Google Maps for event locations.

## 🛠️ Tech Stack

- **Frontend**: HTML5, Tailwind CSS, JavaScript (ES6+), Chart.js, Animate.css.
- **Backend**: FastAPI (Python), SQLite.
- **APIs**: Google Gemini (AI), Resend (Email), Firebase (Auth ready).

## 📦 Setup Instructions

### 1. Prerequisites
- Python 3.8+
- Node.js (optional, for serving frontend)

### 2. Backend Setup
1. Navigate to the `backend` folder:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the server:
   ```bash
   uvicorn main:app --reload
   ```
   The backend will be available at `http://localhost:8000`.

### 3. Frontend Setup
1. Open `frontend/index.html` in your browser.
2. Alternatively, serve it using a local server:
   ```bash
   # Using Python
   python -m http.server 8080
   ```
It is running locally on http://localhost:8080
### 4. Configuration
The `.env` file in the root directory contains the API keys. Ensure they are correct:
- `RESEND_API_KEY`
- `GEMINI_API_KEY`
- 'FIREBASE_API_KEY'

## 📊 Prediction Logic
The system uses a weighted formula:
`predicted = (attending * 0.85 + maybe * 0.4) * typeMultiplier * timeMultiplier`

- **Multipliers**:
  - Cultural: 1.3x | Hackathon: 1.2x | Workshop: 1.1x
  - Evening: 1.2x | Morning: 0.8x

## 📂 Project Structure
```text
smart-campus-app/
├── backend/
│   ├── main.py          # FastAPI logic & Database
│   └── requirements.txt # Python dependencies
├── frontend/
│   ├── index.html       # Main UI
│   └── app.js           # Frontend logic
├── data/
│   └── campus_events.db # SQLite Database (auto-generated)
├── .env                 # API Keys
└── README.md            # Documentation
```
