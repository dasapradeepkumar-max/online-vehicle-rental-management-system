# 🚗 Online Vehicle Rental Management System (VehicleHub)

A full-stack, real-time web application for renting vehicles (cars and bikes). Built with **Python (Flask)**, **SQLAlchemy**, **Flask-SocketIO**, and custom modern UI styling with responsive dark/light theme support.

---

## 🌟 Features

### 👤 Customer Features
- **User Authentication**: Secure registration, login, and session management with password hashing.
- **Vehicle Catalog**: Browse a wide selection of luxury cars, SUVs, sedans, and bikes with location and price filters.
- **Instant Booking**: Select pickup/drop-off dates, preview total cost in real time, and place bookings instantly.
- **My Bookings Dashboard**: View active, completed, and canceled bookings with real-time status updates and cancellation support.

### 🛡️ Admin Dashboard
- **Vehicle Fleet Management**: Add, update, and manage vehicle listings, pricing, and locations.
- **Booking Overview**: Monitor all customer bookings across the platform.
- **Real-Time Online Activity**: Track live online users across the site via WebSocket connections.

### ⚡ Real-Time & Security Features
- **Live Websocket Integration**: Real-time user online tracking and status notifications via **Flask-SocketIO**.
- **OTP & Email Notifications**: OTP verification service and automated email notifications for bookings.
- **Clean Security Practices**: Environment variable secrets management (`.env`) and parameterized database queries.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+, Flask, Flask-SQLAlchemy, Flask-Login, Flask-SocketIO, PyJWT, Eventlet
- **Frontend**: HTML5, Vanilla CSS3 (Custom Glassmorphism UI & Modern Animations), JavaScript (ES6+)
- **Database**: SQLite (via Flask-SQLAlchemy)
- **Version Control**: Git & GitHub

---

## 📁 Project Structure

```text
online-vehicle-rental-management-system/
├── app.py                  # Main Flask application entry point & SocketIO server
├── config.py               # Configuration settings & environment loader
├── models.py               # Database schemas (User, Vehicle, Booking)
├── requirements.txt        # Python package dependencies
├── .env.example            # Environment variables template
├── .gitignore              # Git ignore rules for virtualenv, database, and secrets
├── GIT_CONFIG.md           # Documentation for Git repository configuration
├── AUTH_GUIDE.md           # Documentation for Authentication system
├── routes/                 # Modular Flask Blueprints
│   ├── admin.py            # Admin dashboard routes
│   ├── auth.py             # Login, register, logout, OTP verification
│   ├── bookings.py         # Booking creation & status updates
│   ├── public_routes.py    # Public pages & catalog view
│   └── vehicles.py         # Vehicle details & list APIs
├── services/               # Background services
│   ├── notification_service.py
│   └── otp_service.py
├── static/                 # Static assets
│   ├── css/                # Custom CSS stylesheets (themes, navbar, hero, cards)
│   └── js/                 # Client-side JavaScript (SocketIO, API integration)
└── templates/              # Jinja2 HTML templates
    ├── index.html          # Homepage
    ├── vehicles.html       # Vehicle catalog
    ├── booking.html        # Booking form
    ├── dashboard.html      # User dashboard
    ├── mybookings.html     # User booking management
    ├── admin.html          # Admin panel
    ├── login.html          # Sign in page
    └── register.html       # Sign up page
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher installed on your system.
- Git installed.

### Installation & Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/dasapradeepkumar-max/online-vehicle-rental-management-system.git
   cd online-vehicle-rental-management-system
   ```

2. **Set Up Virtual Environment**
   ```bash
   python -m venv .venv
   
   # Windows (PowerShell)
   .\.venv\Scripts\activate

   # macOS / Linux
   source .venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**
   Create a `.env` file from `.env.example`:
   ```bash
   cp .env.example .env   # Linux/macOS
   copy .env.example .env # Windows
   ```

5. **Run the Application**
   ```bash
   python app.py
   ```
   Open your browser and navigate to `http://127.0.0.1:5000`.

---

## 🔑 Default Credentials

- **Admin Account**: `admin@vehiclehub.local`
- **Default Database**: Auto-initialized on first run with sample vehicles in `instance/site.db`.

---

## 📝 License

This project is open-source and available under the [MIT License](LICENSE).