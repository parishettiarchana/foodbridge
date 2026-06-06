from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3, os, math, json
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'foodbridge_secret_2024'
DATABASE = 'instance/foodbridge.db'

# ── DB helpers ────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs('instance', exist_ok=True)
    with get_db() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ("donor","receiver")),
                location TEXT,
                lat REAL,
                lng REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS food_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                donor_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                quantity TEXT NOT NULL,
                category TEXT,
                expiry_date TEXT,
                location TEXT,
                lat REAL,
                lng REAL,
                image_url TEXT,
                status TEXT DEFAULT "available",
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(donor_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                message TEXT,
                status TEXT DEFAULT "pending",
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(listing_id) REFERENCES food_listings(id),
                FOREIGN KEY(receiver_id) REFERENCES users(id)
            );
        ''')
        # seed demo data if empty
        cur = conn.execute('SELECT COUNT(*) FROM users')
        if cur.fetchone()[0] == 0:
            conn.executescript('''
                INSERT INTO users(name,email,password,role,location,lat,lng) VALUES
                  ("Ravi Kumar","ravi@demo.com","demo123","donor","Banjara Hills, Hyderabad",17.4239,78.4738),
                  ("Priya Sharma","priya@demo.com","demo123","receiver","Jubilee Hills, Hyderabad",17.4325,78.4071),
                  ("Ahmed Khan","ahmed@demo.com","demo123","donor","Secunderabad, Hyderabad",17.4399,78.4983),
                  ("Sneha Reddy","sneha@demo.com","demo123","receiver","Madhapur, Hyderabad",17.4481,78.3915);

                INSERT INTO food_listings(donor_id,title,description,quantity,category,expiry_date,location,lat,lng,status) VALUES
                  (1,"Fresh Biryani","Chicken biryani, cooked today","20 portions","Cooked Food","2025-01-15","Banjara Hills",17.4239,78.4738,"available"),
                  (1,"Surplus Bread Loaves","Whole wheat bread from bakery","15 loaves","Bakery","2025-01-14","Banjara Hills",17.4239,78.4738,"available"),
                  (3,"Mixed Vegetables","Assorted fresh vegetables","10 kg","Produce","2025-01-16","Secunderabad",17.4399,78.4983,"available"),
                  (3,"Dal & Rice","Home-cooked lentils and rice","10 portions","Cooked Food","2025-01-13","Secunderabad",17.4399,78.4983,"claimed"),
                  (1,"Packaged Snacks","Unopened biscuit packets","30 packets","Packaged","2025-01-20","Banjara Hills",17.4239,78.4738,"available");
            ''')

# ── Auth decorator ────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ── Haversine distance (km) ───────────────────────────────────────────────────
def haversine(lat1, lng1, lat2, lng2):
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLng = math.radians(lng2 - lng1)
    a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dLng/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET','POST'])
def register():
    error = None
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        role = request.form['role']
        location = request.form.get('location','').strip()
        lat = request.form.get('lat', 0.0) or 0.0
        lng = request.form.get('lng', 0.0) or 0.0
        try:
            with get_db() as conn:
                conn.execute('INSERT INTO users(name,email,password,role,location,lat,lng) VALUES(?,?,?,?,?,?,?)',
                             (name, email, password, role, location, float(lat), float(lng)))
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            error = 'Email already registered.'
    return render_template('register.html', error=error)

@app.route('/login', methods=['GET','POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE email=? AND password=?', (email, password)).fetchone()
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            return redirect(url_for('dashboard'))
        error = 'Invalid email or password.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    uid = session['user_id']
    role = session['user_role']
    with get_db() as conn:
        if role == 'donor':
            listings = conn.execute(
                'SELECT * FROM food_listings WHERE donor_id=? ORDER BY created_at DESC', (uid,)).fetchall()
            requests_ = conn.execute(
                '''SELECT r.*, fl.title, u.name as receiver_name
                   FROM requests r
                   JOIN food_listings fl ON r.listing_id=fl.id
                   JOIN users u ON r.receiver_id=u.id
                   WHERE fl.donor_id=? ORDER BY r.created_at DESC''', (uid,)).fetchall()
            stats = {
                'total': len(listings),
                'available': sum(1 for l in listings if l['status']=='available'),
                'claimed': sum(1 for l in listings if l['status']=='claimed'),
                'requests': len(requests_)
            }
            return render_template('dashboard_donor.html', listings=listings,
                                   requests=requests_, stats=stats)
        else:
            # receiver: show nearby available listings
            user = conn.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
            listings_raw = conn.execute(
                '''SELECT fl.*, u.name as donor_name, u.location as donor_location
                   FROM food_listings fl JOIN users u ON fl.donor_id=u.id
                   WHERE fl.status="available" ORDER BY fl.created_at DESC''').fetchall()
            listings = []
            for l in listings_raw:
                d = dict(l)
                if user['lat'] and l['lat']:
                    d['distance'] = round(haversine(user['lat'], user['lng'], l['lat'], l['lng']), 1)
                else:
                    d['distance'] = None
                listings.append(d)
            listings.sort(key=lambda x: (x['distance'] or 9999))
            my_requests = conn.execute(
                '''SELECT r.*, fl.title, u.name as donor_name
                   FROM requests r
                   JOIN food_listings fl ON r.listing_id=fl.id
                   JOIN users u ON fl.donor_id=u.id
                   WHERE r.receiver_id=? ORDER BY r.created_at DESC''', (uid,)).fetchall()
            stats = {
                'available': len(listings),
                'my_requests': len(my_requests),
                'approved': sum(1 for r in my_requests if r['status']=='approved')
            }
            return render_template('dashboard_receiver.html', listings=listings,
                                   my_requests=my_requests, stats=stats)

@app.route('/listings/new', methods=['GET','POST'])
@login_required
def new_listing():
    if session['user_role'] != 'donor':
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        with get_db() as conn:
            conn.execute('''INSERT INTO food_listings
                (donor_id,title,description,quantity,category,expiry_date,location,lat,lng,image_url)
                VALUES(?,?,?,?,?,?,?,?,?,?)''', (
                session['user_id'],
                request.form['title'],
                request.form['description'],
                request.form['quantity'],
                request.form['category'],
                request.form['expiry_date'],
                request.form['location'],
                float(request.form.get('lat') or 0),
                float(request.form.get('lng') or 0),
                request.form.get('image_url','')
            ))
        return redirect(url_for('dashboard'))
    return render_template('new_listing.html')

@app.route('/listings/<int:lid>/delete', methods=['POST'])
@login_required
def delete_listing(lid):
    with get_db() as conn:
        conn.execute('DELETE FROM food_listings WHERE id=? AND donor_id=?', (lid, session['user_id']))
    return redirect(url_for('dashboard'))

@app.route('/listings/<int:lid>/status', methods=['POST'])
@login_required
def update_status(lid):
    status = request.form['status']
    with get_db() as conn:
        conn.execute('UPDATE food_listings SET status=? WHERE id=? AND donor_id=?',
                     (status, lid, session['user_id']))
    return redirect(url_for('dashboard'))

@app.route('/request/<int:lid>', methods=['POST'])
@login_required
def make_request(lid):
    if session['user_role'] != 'receiver':
        return redirect(url_for('dashboard'))
    msg = request.form.get('message','')
    with get_db() as conn:
        existing = conn.execute('SELECT id FROM requests WHERE listing_id=? AND receiver_id=?',
                                (lid, session['user_id'])).fetchone()
        if not existing:
            conn.execute('INSERT INTO requests(listing_id,receiver_id,message) VALUES(?,?,?)',
                         (lid, session['user_id'], msg))
    return redirect(url_for('dashboard'))

@app.route('/request/<int:rid>/approve', methods=['POST'])
@login_required
def approve_request(rid):
    with get_db() as conn:
        req = conn.execute('SELECT r.*, fl.donor_id FROM requests r JOIN food_listings fl ON r.listing_id=fl.id WHERE r.id=?', (rid,)).fetchone()
        if req and req['donor_id'] == session['user_id']:
            conn.execute('UPDATE requests SET status="approved" WHERE id=?', (rid,))
            conn.execute('UPDATE food_listings SET status="claimed" WHERE id=?', (req['listing_id'],))
    return redirect(url_for('dashboard'))

# ── AI Chatbot API ────────────────────────────────────────────────────────────
@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json()
    user_msg = data.get('message','').strip().lower()
    role = session['user_role']

    # Rule-based + context-aware responses
    responses = {
        'hello': "Hello! 👋 I'm FoodBridge AI. I can help you navigate the platform, list food, find donations, or answer questions.",
        'hi': "Hi there! How can I assist you today on FoodBridge?",
        'help': f"Sure! As a **{role}**, here's what you can do:\n" + (
            "• **Add Listing** – Share surplus food\n• **Track Requests** – See who wants your food\n• **Approve Requests** – Confirm pickups" if role=='donor'
            else "• **Browse Listings** – Find food near you\n• **Request Food** – Send a pickup request\n• **Track Requests** – See status of your requests"),
        'how to list food': "To list food:\n1. Click **'+ Add Listing'** on your dashboard\n2. Fill in the food title, quantity, category, and expiry date\n3. Add your location for matching\n4. Click Submit — it goes live immediately!",
        'how to donate': "To donate food:\n1. Register as a **Donor**\n2. Click **'+ Add Listing'**\n3. Fill in the food details\n4. Approve receiver requests from your dashboard!",
        'how to request food': "To request food:\n1. Browse the **Available Listings** on your dashboard\n2. Click **'Request'** on any listing you need\n3. Add an optional message\n4. Wait for the donor to approve!",
        'location': "Location matching is automatic! Listings are sorted by **distance from your location** so you see the closest food first. You can set your location in your profile.",
        'expiry': "Always check the **expiry date** on listings before requesting. Food marked as expiring soon is highlighted in orange — act fast!",
        'categories': "Food categories include:\n🍛 Cooked Food\n🥦 Produce\n🍞 Bakery\n📦 Packaged\n🥛 Dairy\n🥩 Meat & Fish\n🍰 Desserts",
        'contact': "For support, email us at **support@foodbridge.ai** or use this chatbot anytime!",
        'thanks': "You're welcome! 😊 Together we can reduce food waste and feed more people.",
        'thank you': "You're welcome! Feel free to ask anything anytime.",
        'food waste': "Food waste is a global crisis. In India alone, about **68 million tonnes** of food is wasted every year. FoodBridge AI helps connect surplus food to those in need — every donation matters!",
        'how does it work': "FoodBridge AI works in 3 simple steps:\n1. **Donors** list surplus food with details & location\n2. **Receivers** browse & request nearby food\n3. **Donors** approve requests & arrange pickup\n\nIt's that simple! 🌱",
        'who can use': "Anyone can use FoodBridge!\n• **Donors**: Restaurants, households, caterers, grocery stores\n• **Receivers**: NGOs, individuals, community kitchens, food banks",
        'bye': "Goodbye! 👋 Remember, every meal shared matters. See you soon!",
        'goodbye': "Take care! Come back whenever you need help. 🌱",
    }

    # Check keyword matches
    reply = None
    for key, resp in responses.items():
        if key in user_msg:
            reply = resp
            break

    if not reply:
        if any(w in user_msg for w in ['status', 'request', 'pending']):
            reply = "You can check your request status on the **Dashboard**. Pending requests will update to 'Approved' once the donor confirms."
        elif any(w in user_msg for w in ['delete', 'remove', 'cancel']):
            reply = "Donors can delete their listings using the **Delete** button on the Dashboard. Receivers can cancel requests by contacting the donor."
        elif any(w in user_msg for w in ['profile', 'account', 'settings']):
            reply = "Profile management is coming soon! For now, your name, email, role, and location are set during registration."
        elif any(w in user_msg for w in ['near', 'nearby', 'close', 'distance']):
            reply = "Listings are **sorted by distance** from your location! The closest food donations appear first. Make sure your location is set correctly when you register."
        else:
            reply = f"I'm not sure about that, but I'm happy to help! Try asking:\n• 'How to list food'\n• 'How to request food'\n• 'How does it work'\n• 'Help'\n\nOr email us at support@foodbridge.ai 🌱"

    return jsonify({'reply': reply})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
