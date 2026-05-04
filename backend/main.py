import os
import sqlite3
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai
import requests

load_dotenv()

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
DB_PATH = "../data/campus_events.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            image TEXT,
            venue_capacity INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            location TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rsvps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            user_email TEXT,
            status TEXT,
            FOREIGN KEY(event_id) REFERENCES events(id)
        )
    ''')
    
    # Seed data if empty
    cursor.execute("SELECT COUNT(*) FROM events")
    if cursor.fetchone()[0] == 0:
        events = [
            ("Tech Innovators Hackathon", "2026-05-15", "Tech", "https://images.unsplash.com/photo-1504384308090-c894fdcc538d", 100, "hackathon", "evening", "Main Hall"),
            ("Spring Cultural Fest", "2026-05-20", "Cultural", "https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3", 500, "cultural", "evening", "Open Grounds"),
            ("AI & Ethics Seminar", "2026-05-12", "Tech", "https://images.unsplash.com/photo-1591115765373-520b7a217267", 50, "seminar", "afternoon", "Room 101"),
            ("Inter-College Basketball", "2026-05-18", "Sports", "https://images.unsplash.com/photo-1546519638-68e109498ffc", 200, "cultural", "morning", "Sports Complex"),
            ("Web Dev Workshop", "2026-05-14", "Tech", "https://images.unsplash.com/photo-1517694712202-14dd9538aa97", 30, "workshop", "afternoon", "Lab 3"),
            ("Photography Masterclass", "2026-05-22", "Workshops", "https://images.unsplash.com/photo-1452587925148-ce544e77e70d", 40, "workshop", "morning", "Art Studio"),
            ("Startup Pitch Night", "2026-05-25", "Tech", "https://images.unsplash.com/photo-1475721027785-f74eccf877e2", 80, "seminar", "evening", "Auditorium"),
            ("Yoga & Wellness Session", "2026-05-10", "Sports", "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b", 60, "workshop", "morning", "Gym"),
            ("Music Concert: Indie Vibes", "2026-05-30", "Cultural", "https://images.unsplash.com/photo-1501281668745-f7f57925c3b4", 300, "cultural", "evening", "Amphitheater"),
            ("Chess Tournament", "2026-05-16", "Sports", "https://images.unsplash.com/photo-1529699211952-734e80c4d42b", 50, "workshop", "afternoon", "Library Hall")
        ]
        cursor.executemany("INSERT INTO events (title, date, category, image, venue_capacity, event_type, time_slot, location) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", events)
    
    conn.commit()
    conn.close()

init_db()

# Models
class RSVPCreate(BaseModel):
    event_id: int
    user_email: str
    status: str

class EventCreate(BaseModel):
    title: str
    date: str
    category: str
    image: str
    venue_capacity: int
    event_type: str
    time_slot: str
    location: str

# Helper for prediction
def calculate_prediction(attending, maybe, event_type, time_slot):
    type_multipliers = {"workshop": 1.1, "seminar": 0.8, "cultural": 1.3, "hackathon": 1.2}
    time_multipliers = {"morning": 0.8, "afternoon": 1.0, "evening": 1.2}
    
    tm = type_multipliers.get(event_type.lower(), 1.0)
    tsm = time_multipliers.get(time_slot.lower(), 1.0)
    
    predicted = (attending * 0.85 + maybe * 0.4) * tm * tsm
    return round(predicted)

@app.post("/events")
def create_event(event: EventCreate, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO events (title, date, category, image, venue_capacity, event_type, time_slot, location)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (event.title, event.date, event.category, event.image, event.venue_capacity, event.event_type, event.time_slot, event.location))
    db.commit()
    return {"message": "Event created successfully", "id": cursor.lastrowid}

@app.get("/events")
def get_events(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM events")
    events = [dict(row) for row in cursor.fetchall()]
    
    for event in events:
        cursor.execute("SELECT status, COUNT(*) as count FROM rsvps WHERE event_id = ? GROUP BY status", (event['id'],))
        counts = {row['status']: row['count'] for row in cursor.fetchall()}
        event['attending'] = counts.get('Attending', 0)
        event['maybe'] = counts.get('Maybe', 0)
        event['predicted'] = calculate_prediction(event['attending'], event['maybe'], event['event_type'], event['time_slot'])
        
        # Risk logic
        utilization = (event['predicted'] / event['venue_capacity']) * 100 if event['venue_capacity'] > 0 else 0
        if utilization < 80:
            event['risk'] = "Safe"
        elif utilization <= 100:
            event['risk'] = "Warning"
        else:
            event['risk'] = "High Risk"
            
    return events

@app.post("/rsvp")
def post_rsvp(rsvp: RSVPCreate, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    # Check if already RSVPed
    cursor.execute("SELECT id FROM rsvps WHERE event_id = ? AND user_email = ?", (rsvp.event_id, rsvp.user_email))
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute("UPDATE rsvps SET status = ? WHERE id = ?", (rsvp.status, existing['id']))
    else:
        cursor.execute("INSERT INTO rsvps (event_id, user_email, status) VALUES (?, ?, ?)", (rsvp.event_id, rsvp.user_email, rsvp.status))
    
    db.commit()
    
    # Optional: Send Email via Resend
    resend_key = os.getenv("RESEND_API_KEY")
    if resend_key and rsvp.status == "Attending":
        try:
            requests.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                json={
                    "from": "CampusEvents <onboarding@resend.dev>",
                    "to": rsvp.user_email,
                    "subject": "RSVP Confirmation",
                    "html": f"<p>You have successfully RSVP'd as <strong>{rsvp.status}</strong> for the event!</p>"
                },
                timeout=5
            )
        except Exception:
            pass # Skip if fails
            
    return {"message": "RSVP recorded"}

@app.get("/recommendations")
def get_recommendations(email: str, db: sqlite3.Connection = Depends(get_db)):
    # Rule-based fallback
    cursor = db.cursor()
    cursor.execute("SELECT category FROM rsvps JOIN events ON rsvps.event_id = events.id WHERE user_email = ?", (email,))
    user_interests = [row['category'] for row in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM events")
    all_events = [dict(row) for row in cursor.fetchall()]
    
    # Gemini logic
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and user_interests:
        try:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-pro')
            prompt = f"User interests: {', '.join(set(user_interests))}. Events: {[{'id': e['id'], 'title': e['title'], 'cat': e['category']} for e in all_events]}. Rank top 3 event IDs for this user. Return ONLY a comma-separated list of IDs."
            response = model.generate_content(prompt)
            ids = [int(i.strip()) for i in response.text.split(',') if i.strip().isdigit()]
            recommended = [e for e in all_events if e['id'] in ids]
            if recommended: return recommended
        except Exception:
            pass
            
    # Fallback: simple category match
    if user_interests:
        return [e for e in all_events if e['category'] in user_interests][:3]
    return all_events[:3]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
