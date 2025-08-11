# 🚗 Parkit - Smart Parking Management System

A modern, web-based parking management system built with Flask that allows users to book parking spots and administrators to manage parking lots efficiently.

## ✨ Features

### For Users
- **User Registration & Authentication**: Secure login and registration system
- **Parking Spot Booking**: Browse available parking lots and book spots
- **Real-time Availability**: Check real-time parking spot availability
- **Booking Management**: View current bookings, history, and cancel reservations
- **Profile Management**: Update personal information and view booking statistics
- **Responsive Design**: Modern, mobile-friendly interface

### For Administrators
- **Admin Dashboard**: Comprehensive overview of system statistics
- **Parking Lot Management**: Add, edit, and delete parking lots
- **User Management**: View and manage user accounts
- **Reservation Management**: Monitor and manage all bookings
- **Data Export**: Export reservation data for analysis
- **Real-time Statistics**: Live updates on system usage

## 🛠️ Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: Flask-Login
- **Forms**: Flask-WTF with WTForms
- **Frontend**: HTML, CSS, Bootstrap
- **Timezone**: pytz for Indian Standard Time (IST)

## 📋 Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

## 🚀 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/theshivam7/Parkit.git
   cd Parkit
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the database**
   ```bash
   python init_db.py
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   - Open your browser and go to `http://localhost:5000`
   - Admin login: Use the credentials configured in `config.py`

## 📁 Project Structure

```
Parkit/
├── app.py                 # Main Flask application
├── models.py             # Database models and ORM
├── forms.py              # Form definitions
├── config.py             # Configuration settings
├── init_db.py            # Database initialization script
├── requirements.txt      # Python dependencies
├── database.db           # SQLite database file
├── templates/            # HTML templates
│   ├── admin/           # Admin-specific templates
│   ├── auth/            # Authentication templates
│   ├── user/            # User-specific templates
│   └── base.html        # Base template
├── static/              # Static files (CSS, JS, images)
└── instance/            # Instance-specific files
```

## 🎯 Usage

### For Users
1. Register a new account or login
2. Browse available parking lots
3. Select a parking lot and book a spot
4. View your current bookings and history
5. Release parking spots when done

### For Administrators
1. Login with admin credentials
2. Access the admin dashboard
3. Manage parking lots, users, and reservations
4. Monitor system statistics
5. Export data as needed

## 🔒 Security Features

- Password hashing using Werkzeug
- CSRF protection with Flask-WTF
- Session management with Flask-Login
- Input validation and sanitization
- Role-based access control

## 📊 Database Schema

The system uses the following main entities:
- **Users**: User accounts and profiles
- **ParkingLots**: Parking lot information and pricing
- **ParkingSpots**: Individual parking spots within lots
- **Reservations**: Booking records and status

## 👨‍💻 Author

**Shivam** - [GitHub Profile](https://github.com/theshivam7)
