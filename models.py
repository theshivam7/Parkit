from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import pytz
import math

db = SQLAlchemy()

IST = pytz.timezone('Asia/Kolkata')

def get_ist_now():
    """Get current time in IST timezone"""
    return datetime.now(IST)

def ensure_ist_timezone(dt):
    """Ensure datetime is in IST timezone"""
    if dt is None:
        return None
    
    if dt.tzinfo is None:
        return pytz.utc.localize(dt).astimezone(IST)
    elif dt.tzinfo != IST:
        return dt.astimezone(IST)
    
    return dt

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=get_ist_now)
    
    reservations = db.relationship('Reservation', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, name, email, password_hash, role='user'):
        self.name = name
        self.email = email
        self.password_hash = password_hash
        self.role = role
    
    @staticmethod
    def create(name, email, password, role='user'):
        """Create a new user"""
        try:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                return False
                
            password_hash = generate_password_hash(password)
            user = User(name=name, email=email, password_hash=password_hash, role=role)
            db.session.add(user)
            db.session.commit()
            return True
        except Exception as e:
            print(f"Error creating user: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get(user_id):
        return User.query.get(user_id)
    
    @staticmethod
    def get_by_email(email):
        return User.query.filter_by(email=email).first()
    
    @staticmethod
    def get_all_users():
        return User.query.filter_by(role='user').all()
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ParkingLot(db.Model):
    __tablename__ = 'parking_lots'
    
    id = db.Column(db.Integer, primary_key=True)
    prime_location_name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(500), nullable=False)
    pin_code = db.Column(db.String(10), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    max_number_of_spots = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=get_ist_now)
    
    parking_spots = db.relationship('ParkingSpot', backref='parking_lot', lazy=True, cascade='all, delete-orphan')
    reservations = db.relationship('Reservation', backref='parking_lot', lazy=True)
    
    @staticmethod
    def create(prime_location_name, address, pin_code, price, max_number_of_spots):
        """Create a new parking lot with spots"""
        try:
            parking_lot = ParkingLot(
                prime_location_name=prime_location_name,
                address=address,
                pin_code=pin_code,
                price=float(price),
                max_number_of_spots=int(max_number_of_spots)
            )
            db.session.add(parking_lot)
            db.session.flush()
            
            for i in range(1, int(max_number_of_spots) + 1):
                parking_spot = ParkingSpot(
                    lot_id=parking_lot.id,
                    spot_number=i
                )
                db.session.add(parking_spot)
            
            db.session.commit()
            return parking_lot.id
        except Exception as e:
            print(f"Error creating parking lot: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def get_all():
        return ParkingLot.query.order_by(ParkingLot.created_at.desc()).all()
    
    @staticmethod
    def get_by_id(lot_id):
        return ParkingLot.query.get(lot_id)
    
    @staticmethod
    def update(lot_id, prime_location_name, address, pin_code, price, max_number_of_spots):
        """Update parking lot details"""
        try:
            parking_lot = ParkingLot.query.get(lot_id)
            if not parking_lot:
                return False
                
            old_max_spots = parking_lot.max_number_of_spots
            new_max_spots = int(max_number_of_spots)
            
            parking_lot.prime_location_name = prime_location_name
            parking_lot.address = address
            parking_lot.pin_code = pin_code
            parking_lot.price = float(price)
            parking_lot.max_number_of_spots = new_max_spots
            
            if new_max_spots > old_max_spots:
                for i in range(old_max_spots + 1, new_max_spots + 1):
                    parking_spot = ParkingSpot(
                        lot_id=parking_lot.id,
                        spot_number=i
                    )
                    db.session.add(parking_spot)
            elif new_max_spots < old_max_spots:
                excess_spots = ParkingSpot.query.filter(
                    ParkingSpot.lot_id == lot_id,
                    ParkingSpot.spot_number > new_max_spots
                ).all()
                
                for spot in excess_spots:
                    if spot.status == 'O':
                        db.session.rollback()
                        return False
                    db.session.delete(spot)
            
            db.session.commit()
            return True
        except Exception as e:
            print(f"Error updating parking lot: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def delete(lot_id):
        """Delete parking lot if no active reservations"""
        try:
            parking_lot = ParkingLot.query.get(lot_id)
            if not parking_lot:
                return False
                
            active_reservations = Reservation.query.filter_by(
                lot_id=lot_id, 
                status='active'
            ).count()
            
            if active_reservations > 0:
                return False
            
            db.session.delete(parking_lot)
            db.session.commit()
            return True
        except Exception as e:
            print(f"Error deleting parking lot: {e}")
            db.session.rollback()
            return False

class ParkingSpot(db.Model):
    __tablename__ = 'parking_spots'
    
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lots.id'), nullable=False)
    spot_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(1), default='A')
    
    reservations = db.relationship('Reservation', backref='parking_spot', lazy=True)
    
    __table_args__ = (db.UniqueConstraint('lot_id', 'spot_number', name='unique_lot_spot'),)
    
    @staticmethod
    def get_lot_stats(lot_id):
        """Get parking lot statistics"""
        try:
            total = ParkingSpot.query.filter_by(lot_id=lot_id).count()
            occupied = ParkingSpot.query.filter_by(lot_id=lot_id, status='O').count()
            
            return {
                'total': total,
                'occupied': occupied,
                'available': total - occupied
            }
        except Exception as e:
            print(f"Error getting lot stats: {e}")
            return {
                'total': 0,
                'occupied': 0,
                'available': 0
            }
    
    @staticmethod
    def get_available_spot(lot_id):
        """Get first available spot in a lot"""
        return ParkingSpot.query.filter_by(lot_id=lot_id, status='A').first()
    
    @staticmethod
    def occupy_spot(spot_id):
        """Mark spot as occupied"""
        try:
            spot = ParkingSpot.query.get(spot_id)
            if spot and spot.status == 'A':
                spot.status = 'O'
                db.session.commit()
                return True
            return False
        except Exception as e:
            print(f"Error occupying spot: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def release_spot(spot_id):
        """Mark spot as available"""
        try:
            spot = ParkingSpot.query.get(spot_id)
            if spot and spot.status == 'O':
                spot.status = 'A'
                db.session.commit()
                return True
            return False
        except Exception as e:
            print(f"Error releasing spot: {e}")
            db.session.rollback()
            return False

class Reservation(db.Model):
    __tablename__ = 'reservations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lots.id'), nullable=False)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spots.id'), nullable=False)
    vehicle_number = db.Column(db.String(20))
    parking_timestamp = db.Column(db.DateTime, default=get_ist_now)
    leaving_timestamp = db.Column(db.DateTime)
    cost_per_unit = db.Column(db.Numeric(10, 2), nullable=False)
    total_cost = db.Column(db.Numeric(10, 2))
    booking_duration = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), default='active')
    
    @staticmethod
    def create(user_id, lot_id, spot_id, cost_per_unit, booking_duration=1, vehicle_number=None):
        """Create a new reservation"""
        try:
            existing_active = Reservation.query.filter_by(user_id=user_id, status='active').first()
            if existing_active:
                return None
            
            spot = ParkingSpot.query.get(spot_id)
            if not spot or spot.status != 'A':
                return None
            
            spot.status = 'O'
                
            reservation = Reservation(
                user_id=user_id,
                lot_id=lot_id,
                spot_id=spot_id,
                cost_per_unit=float(cost_per_unit),
                booking_duration=int(booking_duration),
                vehicle_number=vehicle_number,
                parking_timestamp=get_ist_now()
            )
            db.session.add(reservation)
            db.session.commit()
            return reservation.id
        except Exception as e:
            print(f"Error creating reservation: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def get_active_by_user(user_id):
        """Get active reservation for a user"""
        return Reservation.query.filter_by(user_id=user_id, status='active').first()
    
    @staticmethod
    def get_user_history(user_id):
        """Get all reservations for a user"""
        return Reservation.query.filter_by(user_id=user_id).order_by(
            Reservation.parking_timestamp.desc()
        ).all()
    
    @staticmethod
    def complete_reservation(reservation_id, total_cost):
        """Complete a reservation"""
        try:
            reservation = Reservation.query.get(reservation_id)
            if reservation and reservation.status == 'active':
                reservation.status = 'completed'
                reservation.total_cost = float(total_cost)
                reservation.leaving_timestamp = get_ist_now()
                db.session.commit()
                return True
            return False
        except Exception as e:
            print(f"Error completing reservation: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def cancel_reservation(reservation_id):
        """Cancel a reservation"""
        try:
            reservation = Reservation.query.get(reservation_id)
            if reservation and reservation.status == 'active':
                reservation.status = 'cancelled'
                reservation.leaving_timestamp = get_ist_now()
                db.session.commit()
                return True
            return False
        except Exception as e:
            print(f"Error cancelling reservation: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get_all():
        """Get all reservations"""
        return Reservation.query.order_by(Reservation.parking_timestamp.desc()).all()
    
    def get_duration_seconds(self):
        """Get actual parking duration in seconds"""
        if not self.parking_timestamp:
            return 0
            
        end_time = self.leaving_timestamp if self.leaving_timestamp else get_ist_now()
        
        start_time = ensure_ist_timezone(self.parking_timestamp)
        end_time = ensure_ist_timezone(end_time)
        
        if end_time < start_time:
            return 0
            
        duration = end_time - start_time
        return max(0, int(duration.total_seconds()))

    def get_duration_minutes(self):
        """Get actual parking duration in minutes"""
        return self.get_duration_seconds() // 60
    
    def get_duration_hours_minutes(self):
        """Get duration as hours and minutes tuple"""
        total_minutes = self.get_duration_minutes()
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return hours, minutes
    
    def calculate_current_cost(self):
        """Calculate current cost based on actual time spent with ceiling logic"""
        if not self.parking_timestamp:
            return 0.0
            
        duration_seconds = self.get_duration_seconds()
        
        if duration_seconds < 0:
            duration_seconds = 0
            
        billable_hours = max(1, math.ceil(duration_seconds / 3600))
        
        return float(billable_hours * self.cost_per_unit)
    
    def get_remaining_time_seconds(self):
        """Get remaining time in seconds"""
        if not self.parking_timestamp or self.status != 'active':
            return 0
            
        start_time = ensure_ist_timezone(self.parking_timestamp)
        current_time = get_ist_now()
        
        booking_end_time = start_time + timedelta(hours=self.booking_duration)
        
        remaining_seconds = (booking_end_time - current_time).total_seconds()
        return max(0, int(remaining_seconds))

def init_database():
    """Initialize the database and create all tables"""
    try:
        db.create_all()
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error initializing database: {e}")
