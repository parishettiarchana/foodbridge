# 🌱 FoodBridge AI — Setup & Run Guide

## Quick Start (3 steps)

### 1. Install dependencies
```bash
cd food_bridge
pip install flask
```

### 2. Run the app
```bash
python app.py
```

### 3. Open in browser
```
http://localhost:5000
```

---

## Demo Login Accounts

| Role     | Email              | Password |
|----------|--------------------|----------|
| Donor    | ravi@demo.com      | demo123  |
| Donor    | ahmed@demo.com     | demo123  |
| Receiver | priya@demo.com     | demo123  |
| Receiver | sneha@demo.com     | demo123  |

---

## Project Structure

```
food_bridge/
├── app.py                  ← Flask backend + API routes + AI chatbot
├── requirements.txt
├── instance/
│   └── foodbridge.db       ← SQLite database (auto-created)
├── static/
│   ├── css/style.css       ← Full responsive UI styles
│   └── js/main.js          ← Chatbot JS logic
└── templates/
    ├── base.html            ← Navbar + chatbot widget
    ├── login.html
    ├── register.html
    ├── dashboard_donor.html
    ├── dashboard_receiver.html
    └── new_listing.html
```

---

## Features Implemented

- ✅ Authentication (Register/Login/Logout)
- ✅ Donor module: Create, view, update, delete listings
- ✅ Receiver module: Browse & request food donations
- ✅ Location-based matching (Haversine distance sorting)
- ✅ Dashboard UI with stats cards
- ✅ Card-based food listing grid
- ✅ Request management (Donor approves → listing marked claimed)
- ✅ AI Chatbot (rule-based, context-aware, supports markdown)
- ✅ Filter/search for receivers
- ✅ GPS location capture
- ✅ Fully responsive design
- ✅ SQLite database with seed data
