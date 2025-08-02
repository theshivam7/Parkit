import math
from datetime import datetime
from zoneinfo import ZoneInfo

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

IST = ZoneInfo('Asia/Kolkata')


def get_ist_now():
    # SQLite drops tzinfo, so all timestamps are stored as naive IST.
    return datetime.now(IST).replace(tzinfo=None)


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=get_ist_now)

    reservations = db.relationship('Reservation', backref='user', lazy=True, cascade='all, delete-orphan')

    @staticmethod
    def create(name, email, password, role='user'):
        if User.get_by_email(email):
            return False
        db.session.add(User(name=name, email=email, password_hash=generate_password_hash(password), role=role))
        db.session.commit()
        return True

    @staticmethod
    def get_by_email(email):
        return User.query.filter_by(email=email).first()

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

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

    parking_spots = db.relationship('ParkingSpot', backref='parking_lot', lazy=True,
                                    cascade='all, delete-orphan', order_by='ParkingSpot.spot_number')
    reservations = db.relationship('Reservation', backref='parking_lot', lazy=True, cascade='all, delete-orphan')

    @staticmethod
    def create(prime_location_name, address, pin_code, price, max_number_of_spots):
        lot = ParkingLot(
            prime_location_name=prime_location_name,
            address=address,
            pin_code=pin_code,
            price=float(price),
            max_number_of_spots=int(max_number_of_spots),
        )
        db.session.add(lot)
        db.session.flush()
        for i in range(1, lot.max_number_of_spots + 1):
            db.session.add(ParkingSpot(lot_id=lot.id, spot_number=i))
        db.session.commit()
        return lot.id

    @staticmethod
    def get_all():
        return ParkingLot.query.order_by(ParkingLot.created_at.desc()).all()

    @staticmethod
    def get_by_id(lot_id):
        return db.session.get(ParkingLot, lot_id)

    @staticmethod
    def update(lot_id, prime_location_name, address, pin_code, price, max_number_of_spots):
        """Returns (ok, error_message)."""
        lot = ParkingLot.get_by_id(lot_id)
        if not lot:
            return False, 'Parking lot not found.'

        old_max = lot.max_number_of_spots
        new_max = int(max_number_of_spots)

        if new_max < old_max:
            excess = ParkingSpot.query.filter(ParkingSpot.lot_id == lot_id,
                                              ParkingSpot.spot_number > new_max).all()
            if any(spot.status == 'O' for spot in excess):
                return False, f'Cannot reduce to {new_max} spots while a spot above #{new_max} is occupied.'
            for spot in excess:
                db.session.delete(spot)
        else:
            for i in range(old_max + 1, new_max + 1):
                db.session.add(ParkingSpot(lot_id=lot.id, spot_number=i))

        lot.prime_location_name = prime_location_name
        lot.address = address
        lot.pin_code = pin_code
        lot.price = float(price)
        lot.max_number_of_spots = new_max
        db.session.commit()
        return True, None

    @staticmethod
    def delete(lot_id):
        lot = ParkingLot.get_by_id(lot_id)
        if not lot:
            return False
        if Reservation.query.filter_by(lot_id=lot_id, status='active').count():
            return False
        db.session.delete(lot)
        db.session.commit()
        return True


class ParkingSpot(db.Model):
    __tablename__ = 'parking_spots'

    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lots.id'), nullable=False)
    spot_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(1), default='A')  # A = available, O = occupied

    reservations = db.relationship('Reservation', backref='parking_spot', lazy=True)

    __table_args__ = (db.UniqueConstraint('lot_id', 'spot_number', name='unique_lot_spot'),)

    @staticmethod
    def get_lot_stats(lot_id):
        total = ParkingSpot.query.filter_by(lot_id=lot_id).count()
        occupied = ParkingSpot.query.filter_by(lot_id=lot_id, status='O').count()
        return {'total': total, 'occupied': occupied, 'available': total - occupied}

    @staticmethod
    def get_available_spot(lot_id):
        return (ParkingSpot.query.filter_by(lot_id=lot_id, status='A')
                .order_by(ParkingSpot.spot_number).first())

    @staticmethod
    def release_spot(spot_id):
        spot = db.session.get(ParkingSpot, spot_id)
        if spot:
            spot.status = 'A'

    def active_reservation(self):
        return Reservation.query.filter_by(spot_id=self.id, status='active').first()


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
        if Reservation.get_active_by_user(user_id):
            return None
        spot = db.session.get(ParkingSpot, spot_id)
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
            parking_timestamp=get_ist_now(),
        )
        db.session.add(reservation)
        db.session.commit()
        return reservation.id

    @staticmethod
    def get_active_by_user(user_id):
        return Reservation.query.filter_by(user_id=user_id, status='active').first()

    @staticmethod
    def get_user_history(user_id):
        return (Reservation.query.filter_by(user_id=user_id)
                .order_by(Reservation.parking_timestamp.desc()).all())

    @staticmethod
    def get_all():
        return Reservation.query.order_by(Reservation.parking_timestamp.desc()).all()

    def billable_hours(self, end=None):
        """Booked hours, or actual hours (rounded up) if the user stayed longer."""
        end = end or self.leaving_timestamp or get_ist_now()
        seconds = max(0, (end - self.parking_timestamp).total_seconds())
        return max(self.booking_duration, math.ceil(seconds / 3600))

    def complete(self):
        now = get_ist_now()
        self.total_cost = self.billable_hours(now) * float(self.cost_per_unit)
        self.leaving_timestamp = now
        self.status = 'completed'
        ParkingSpot.release_spot(self.spot_id)
        db.session.commit()
        return float(self.total_cost)
