from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import math
import pytz

from config import Config
from models import db, init_database, User, ParkingLot, ParkingSpot, Reservation, get_ist_now, ensure_ist_timezone
from forms import LoginForm, RegisterForm, ParkingLotForm, ProfileForm, BookingForm

app = Flask(__name__)
app.config.from_object(Config)

app.config['WTF_CSRF_ENABLED'] = True

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

IST = pytz.timezone('Asia/Kolkata')

@login_manager.user_loader
def load_user(user_id):
    return User.get(int(user_id))

def create_admin_user():
    """Create admin user if not exists"""
    admin = User.get_by_email(Config.ADMIN_EMAIL)
    if not admin:
        User.create('Admin', Config.ADMIN_EMAIL, Config.ADMIN_PASSWORD, 'admin')
        print("Admin user created successfully!")

def create_sample_data():
    """Create sample parking lots for demo"""
    existing_lots = ParkingLot.query.count()
    
    if existing_lots == 0:

        sample_lots = [
            {
                'prime_location_name': 'Downtown Central Plaza',
                'address': 'Connaught Place, New Delhi, Delhi 110001',
                'pin_code': '110001',
                'price': 75.0,
                'max_number_of_spots': 25
            },
            {
                'prime_location_name': 'Mall Parking Complex',
                'address': 'Select Citywalk, Saket, New Delhi, Delhi 110017',
                'pin_code': '110017',
                'price': 50.0,
                'max_number_of_spots': 40
            },
            {
                'prime_location_name': 'Airport Terminal Parking',
                'address': 'Indira Gandhi International Airport, New Delhi, Delhi 110037',
                'pin_code': '110037',
                'price': 100.0,
                'max_number_of_spots': 50
            }
        ]
        
        for lot_data in sample_lots:
            try:
                ParkingLot.create(**lot_data)
                print(f"Created parking lot: {lot_data['prime_location_name']}")
            except Exception as e:
                print(f"Error creating parking lot {lot_data['prime_location_name']}: {e}")
        
        print("Sample parking lots created successfully!")

def ensure_parking_spots_exist():
    """Ensure all parking lots have their parking spots created"""
    try:
        lots = ParkingLot.query.all()
        for lot in lots:

            existing_spots = ParkingSpot.query.filter_by(lot_id=lot.id).count()
            if existing_spots == 0:
                print(f"Creating {lot.max_number_of_spots} parking spots for {lot.prime_location_name}")

                for i in range(1, lot.max_number_of_spots + 1):
                    parking_spot = ParkingSpot(
                        lot_id=lot.id,
                        spot_number=i
                    )
                    db.session.add(parking_spot)
                db.session.commit()
                print(f"Successfully created {lot.max_number_of_spots} spots for {lot.prime_location_name}")
            else:
                print(f"Lot {lot.prime_location_name} already has {existing_spots} spots")
    except Exception as e:
        print(f"Error ensuring parking spots exist: {e}")
        db.session.rollback()


with app.app_context():
    try:
        init_database()
        create_admin_user()
        create_sample_data()
        ensure_parking_spots_exist()
        print("Database initialization completed successfully!")
    except Exception as e:
        print(f"Database initialization error: {e}")
        import traceback
        traceback.print_exc()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test-db')
def test_db():
    """Test route to check database status"""
    try:
        lots_count = ParkingLot.query.count()
        spots_count = ParkingSpot.query.count()
        users_count = User.query.count()
        
        return jsonify({
            'status': 'success',
            'parking_lots': lots_count,
            'parking_spots': spots_count,
            'users': users_count,
            'sample_lots': [lot.prime_location_name for lot in ParkingLot.query.all()]
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/fix-parking-spots')
def fix_parking_spots():
    """Fix missing parking spots for existing lots"""
    try:
        ensure_parking_spots_exist()
        return jsonify({
            'status': 'success',
            'message': 'Parking spots have been created for all lots'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/fix-negative-costs')
def fix_negative_costs():
    """Fix any negative costs in the database"""
    try:
        negative_reservations = Reservation.query.filter(Reservation.total_cost < 0).all()
        
        fixed_count = 0
        for reservation in negative_reservations:
            if reservation.parking_timestamp and reservation.leaving_timestamp:
                parking_time = ensure_ist_timezone(reservation.parking_timestamp)
                leaving_time = ensure_ist_timezone(reservation.leaving_timestamp)
                
                if leaving_time >= parking_time:
                    duration_seconds = (leaving_time - parking_time).total_seconds()
                    duration_hours = max(1, math.ceil(duration_seconds / 3600))
                    new_cost = duration_hours * float(reservation.cost_per_unit)
                else:
                    new_cost = reservation.booking_duration * float(reservation.cost_per_unit)
            else:
                new_cost = reservation.booking_duration * float(reservation.cost_per_unit)
            
            reservation.total_cost = new_cost
            fixed_count += 1
        
        if fixed_count > 0:
            db.session.commit()
            return jsonify({
                'status': 'success',
                'message': f'Fixed {fixed_count} reservations with negative costs'
            })
        else:
            return jsonify({
                'status': 'success',
                'message': 'No negative costs found'
            })
            
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/admin/export-reservations')
@login_required
def export_reservations():
    """Export reservations data as CSV"""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('user_dashboard'))
    
    try:
        import csv
        from io import StringIO
        
        reservations = Reservation.query.all()
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Reservation ID',
            'User Name',
            'User Email',
            'Parking Lot',
            'Address',
            'Spot Number',
            'Vehicle Number',
            'Status',
            'Start Time',
            'End Time',
            'Duration (Hours)',
            'Cost Per Hour',
            'Total Cost',
            'Booking Duration',
            'Created Date'
        ])
        
        for reservation in reservations:
            user = User.query.get(reservation.user_id)
            user_name = user.name if user else 'Unknown'
            user_email = user.email if user else 'No email'
            
            parking_lot = ParkingLot.query.get(reservation.lot_id)
            lot_name = parking_lot.prime_location_name if parking_lot else 'Unknown Lot'
            lot_address = parking_lot.address if parking_lot else 'No address'
            
            parking_spot = ParkingSpot.query.get(reservation.spot_id)
            spot_number = parking_spot.spot_number if parking_spot else 'N/A'
            duration_hours = 0
            if reservation.parking_timestamp and reservation.leaving_timestamp:
                start_time = ensure_ist_timezone(reservation.parking_timestamp)
                end_time = ensure_ist_timezone(reservation.leaving_timestamp)
                if end_time >= start_time:
                    duration_seconds = (end_time - start_time).total_seconds()
                    if duration_seconds > (reservation.booking_duration * 3600):
                        duration_hours = math.ceil(duration_seconds / 3600)
                    else:
                        duration_hours = reservation.booking_duration
            
            start_time_str = reservation.parking_timestamp.strftime('%Y-%m-%d %H:%M:%S') if reservation.parking_timestamp else 'N/A'
            end_time_str = reservation.leaving_timestamp.strftime('%Y-%m-%d %H:%M:%S') if reservation.leaving_timestamp else 'N/A'
            
            writer.writerow([
                reservation.id,
                user_name,
                user_email,
                lot_name,
                lot_address,
                spot_number,
                reservation.vehicle_number or 'N/A',
                reservation.status,
                start_time_str,
                end_time_str,
                duration_hours,
                float(reservation.cost_per_unit),
                float(reservation.total_cost) if reservation.total_cost else 0,
                reservation.booking_duration,
                reservation.parking_timestamp.strftime('%Y-%m-%d %H:%M:%S') if reservation.parking_timestamp else 'N/A'
            ])
        

        output.seek(0)
        csv_data = output.getvalue()
        
        from flask import Response
        response = Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=parkit_reservations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
        )
        
        return response
        
    except Exception as e:
        print(f"Error exporting reservations: {e}")
        flash('Error exporting data. Please try again.', 'error')
        return redirect(url_for('admin_reservations'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.get_by_email(form.email.data)
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html', form=form)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.get_by_email(form.email.data)
        if user and user.check_password(form.password.data):
            if user.role == 'admin':
                login_user(user)
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Access denied. Admin privileges required.', 'error')
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('admin/login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            if User.create(form.name.data, form.email.data, form.password.data):
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
            flash('Email already exists', 'error')
        except Exception as e:
            flash('Registration failed. Please try again.', 'error')
            print(f"Registration error: {e}")
    
    return render_template('auth/register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('user_dashboard'))

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('user_dashboard'))
    
    try:
        total_lots = ParkingLot.query.count()
        total_spots = ParkingSpot.query.count()
        occupied_spots = ParkingSpot.query.filter_by(status='O').count()
        total_users = User.query.filter_by(role='user').count()
        active_reservations = Reservation.query.filter_by(status='active').count()
        total_revenue = Reservation.query.filter_by(status='completed').with_entities(db.func.sum(Reservation.total_cost)).scalar() or 0
        
        stats = {
            'total_lots': total_lots,
            'total_spots': total_spots,
            'occupied_spots': occupied_spots,
            'available_spots': total_spots - occupied_spots,
            'total_users': total_users,
            'active_reservations': active_reservations,
            'total_revenue': float(total_revenue)
        }
    except Exception as e:
        print(f"Dashboard stats error: {e}")
        stats = {
            'total_lots': 0,
            'total_spots': 0,
            'occupied_spots': 0,
            'available_spots': 0,
            'total_users': 0,
            'active_reservations': 0,
            'total_revenue': 0.0
        }
    
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/parking-lots')
@login_required
def admin_parking_lots():
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('user_dashboard'))
    
    try:
        lots = ParkingLot.get_all()
        lots_with_stats = []
        
        for lot in lots:
            stats = ParkingSpot.get_lot_stats(lot.id)
            lot.price = float(lot.price) if lot.price else 0.0
            lots_with_stats.append({
                'lot': lot,
                'stats': stats
            })
    except Exception as e:
        print(f"Error loading parking lots: {e}")
        lots_with_stats = []
        flash('Error loading parking lots. Please try again.', 'error')
    
    return render_template('admin/parking_lots.html', lots_with_stats=lots_with_stats)

@app.route('/admin/parking-lots/add', methods=['POST'])
@login_required
def add_parking_lot():
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('user_dashboard'))
    
    try:
        prime_location_name = request.form.get('prime_location_name', '').strip()
        address = request.form.get('address', '').strip()
        pin_code = request.form.get('pin_code', '').strip()
        price = float(request.form.get('price', 0))
        max_number_of_spots = int(request.form.get('max_number_of_spots', 0))
        
        if not all([prime_location_name, address, pin_code]) or price <= 0 or max_number_of_spots <= 0:
            flash('All fields are required and must be valid.', 'error')
            return redirect(url_for('admin_parking_lots'))
        
        if len(pin_code) != 6 or not pin_code.isdigit():
            flash('PIN code must be exactly 6 digits.', 'error')
            return redirect(url_for('admin_parking_lots'))
        
        lot_id = ParkingLot.create(
            prime_location_name,
            address,
            pin_code,
            price,
            max_number_of_spots
        )
        
        if lot_id:
            flash('Parking lot created successfully!', 'success')
        else:
            flash('Failed to create parking lot. Please try again.', 'error')
            
    except ValueError as e:
        flash('Invalid input values. Please check your data.', 'error')
    except Exception as e:
        flash('Error creating parking lot. Please try again.', 'error')
        print(f"Error creating parking lot: {e}")
    
    return redirect(url_for('admin_parking_lots'))

@app.route('/admin/parking-lots/edit/<int:lot_id>', methods=['GET', 'POST'])
@login_required
def edit_parking_lot(lot_id):
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('user_dashboard'))
    
    lot = ParkingLot.get_by_id(lot_id)
    if not lot:
        flash('Parking lot not found', 'error')
        return redirect(url_for('admin_parking_lots'))
    
    if request.method == 'POST':
        try:
            prime_location_name = request.form.get('prime_location_name', '').strip()
            address = request.form.get('address', '').strip()
            pin_code = request.form.get('pin_code', '').strip()
            price = float(request.form.get('price', 0))
            max_number_of_spots = int(request.form.get('max_number_of_spots', 0))
            
            if not all([prime_location_name, address, pin_code]) or price <= 0 or max_number_of_spots <= 0:
                flash('All fields are required and must be valid.', 'error')
                return redirect(url_for('admin_parking_lots'))
            
            if len(pin_code) != 6 or not pin_code.isdigit():
                flash('PIN code must be exactly 6 digits.', 'error')
                return redirect(url_for('admin_parking_lots'))
            
            success = ParkingLot.update(
                lot_id,
                prime_location_name,
                address,
                pin_code,
                price,
                max_number_of_spots
            )
            
            if success:
                flash('Parking lot updated successfully!', 'success')
            else:
                flash('Failed to update parking lot.', 'error')
                
        except ValueError:
            flash('Invalid input values. Please check your data.', 'error')
        except Exception as e:
            flash('Error updating parking lot. Please try again.', 'error')
            print(f"Error updating parking lot: {e}")
        
        return redirect(url_for('admin_parking_lots'))
    
    form = ParkingLotForm()
    form.prime_location_name.data = lot.prime_location_name
    form.address.data = lot.address
    form.pin_code.data = lot.pin_code
    form.price.data = float(lot.price) if lot.price else 0.0
    form.max_number_of_spots.data = lot.max_number_of_spots
    
    lots_with_stats = []
    return render_template('admin/parking_lots.html', form=form, lots_with_stats=lots_with_stats, show_form=True, editing=True)

@app.route('/admin/parking-lots/delete/<int:lot_id>')
@login_required
def delete_parking_lot(lot_id):
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('user_dashboard'))
    
    try:
        if ParkingLot.delete(lot_id):
            flash('Parking lot deleted successfully!', 'success')
        else:
            flash('Cannot delete parking lot with active reservations', 'error')
    except Exception as e:
        flash('Error deleting parking lot.', 'error')
        print(f"Error deleting parking lot: {e}")
    
    return redirect(url_for('admin_parking_lots'))

@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('user_dashboard'))
    
    try:
        q = request.args.get('q', '').strip()
        if q:
            users = User.query.filter(
                db.and_(
                    User.role != 'admin',
                    db.or_(
                        User.email.like(f'%{q}%'),
                        User.name.like(f'%{q}%')
                    )
                )
            ).all()
        else:
            users = User.query.filter(User.role != 'admin').all()
        
        for user in users:
            booking_count = Reservation.query.filter_by(user_id=user.id).count()
            user.booking_count = booking_count
            
    except Exception as e:
        print(f"Error loading users: {e}")
        users = []
        flash('Error loading users.', 'error')
    
    return render_template('admin/users.html', users=users, search_query=request.args.get('q', ''))

@app.route('/admin/reservations')
@login_required
def admin_reservations():
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('user_dashboard'))
    
    try:
        reservations = Reservation.get_all()
        
        for reservation in reservations:
            if reservation.parking_timestamp:
                reservation.parking_timestamp = ensure_ist_timezone(reservation.parking_timestamp)
            if reservation.leaving_timestamp:
                reservation.leaving_timestamp = ensure_ist_timezone(reservation.leaving_timestamp)
                    
    except Exception as e:
        print(f"Error loading reservations: {e}")
        reservations = []
        flash('Error loading reservations.', 'error')
    
    return render_template('admin/stats.html', reservations=reservations)

@app.route('/admin/reservations/delete/<int:reservation_id>')
@login_required
def delete_reservation(reservation_id):
    """Delete a reservation"""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('user_dashboard'))
    
    try:
        reservation = Reservation.query.get(reservation_id)
        if not reservation:
            flash('Reservation not found.', 'error')
            return redirect(url_for('admin_reservations'))
        
        parking_lot = ParkingLot.query.get(reservation.lot_id)
        lot_name = parking_lot.prime_location_name if parking_lot else 'Unknown Location'
        
        if reservation.status == 'active':
            ParkingSpot.release_spot(reservation.spot_id)
        
        db.session.delete(reservation)
        db.session.commit()
        
        flash(f'Reservation for {lot_name} deleted successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error deleting reservation.', 'error')
        print(f"Error deleting reservation: {e}")
    
    return redirect(url_for('admin_reservations'))

@app.route('/admin/users/delete/<int:user_id>')
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('user_dashboard'))
    
    if user_id == current_user.id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin_users'))
    
    try:
        active_reservations = Reservation.query.filter_by(user_id=user_id, status='active').count()
        
        if active_reservations > 0:
            flash('Cannot delete user with active reservations.', 'error')
            return redirect(url_for('admin_users'))
        
        Reservation.query.filter_by(user_id=user_id).delete()
        User.query.filter_by(id=user_id).delete()
        db.session.commit()
        
        flash('User deleted successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error deleting user.', 'error')
        print(f"Error deleting user: {e}")
    
    return redirect(url_for('admin_users'))

@app.route('/user')
@login_required
def user_dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    try:
        active_reservation = Reservation.get_active_by_user(current_user.id)
        
        if active_reservation and active_reservation.parking_timestamp:
            active_reservation.parking_timestamp = ensure_ist_timezone(active_reservation.parking_timestamp)
            
    except Exception as e:
        print(f"Error loading user dashboard: {e}")
        active_reservation = None
        flash('Error loading dashboard data.', 'error')
    
    return render_template('user/dashboard.html', active_reservation=active_reservation)

@app.route('/user/booking')
@login_required
def user_booking():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))

    try:
        active_reservation = Reservation.get_active_by_user(current_user.id)
        if active_reservation:
            flash('You already have an active parking reservation', 'info')
            return redirect(url_for('user_current'))
    except Exception as e:
        print(f"Error checking active reservation: {e}")
        active_reservation = None

    try:
        lots = ParkingLot.get_all()
        if not lots:
            flash('No parking lots available. Please contact administrator.', 'error')
            return redirect(url_for('user_dashboard'))
    except Exception as e:
        print(f"Error getting parking lots: {e}")
        flash('Error loading parking lots. Please try again.', 'error')
        return redirect(url_for('user_dashboard'))

    lots_with_stats = []
    for lot in lots:
        try:
            stats = ParkingSpot.get_lot_stats(lot.id)
            lot.price = float(lot.price) if lot.price else 0.0
            lots_with_stats.append({
                'lot': lot,
                'stats': stats
            })
        except Exception as e:
            print(f"Error processing lot {getattr(lot, 'id', 'unknown')}: {e}")
            import traceback
            traceback.print_exc()
            continue

    if not lots_with_stats:
        flash('No parking lots with available spots found. Please try again later.', 'error')
        return redirect(url_for('user_dashboard'))

    return render_template('user/booking.html', lots_with_stats=lots_with_stats)

@app.route('/user/book/<int:lot_id>', methods=['GET', 'POST'])
@login_required
def book_parking(lot_id):
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))

    try:
        active_reservation = Reservation.get_active_by_user(current_user.id)
        if active_reservation:
            flash('You already have an active parking reservation', 'error')
            return redirect(url_for('user_current'))

        lot = ParkingLot.get_by_id(lot_id)
        if not lot:
            flash('Parking lot not found', 'error')
            return redirect(url_for('user_booking'))

        lot.price = float(lot.price) if lot.price else 0.0

        form = BookingForm()
        if request.method == 'GET':
            form.name.data = current_user.name

        if request.method == 'POST':
            if form.validate_on_submit():
                try:
                    available_spot = ParkingSpot.get_available_spot(lot_id)
                    if not available_spot:
                        flash('No parking spots available at this location. Please try another location.', 'error')
                        return
                    hours = form.hours.data if form.hours.data else 1
                    vehicle_number = form.vehicle_number.data if form.vehicle_number.data else None

                    reservation_id = Reservation.create(
                        current_user.id,
                        lot_id,
                        available_spot.id,
                        lot.price,
                        hours,
                        vehicle_number
                    )

                    if reservation_id:
                        flash(f'Parking spot {available_spot.spot_number} booked successfully at {lot.prime_location_name} for {hours} hour(s)!', 'success')
                        return redirect(url_for('user_current'))
                    else:
                        flash('No parking spots available at this location. Please try another location.', 'error')
                except Exception as e:
                    print(f"Error in form submission: {e}")
                    import traceback
                    traceback.print_exc()
                    flash('Error processing booking. Please try again.', 'error')
            else:
                flash('Please correct the errors in the form.', 'error')

        return render_template('user/book_now.html', lot=lot, form=form)

    except Exception as e:
        print(f"Error in book_parking route: {e}")
        import traceback
        traceback.print_exc()
        flash('An error occurred while loading the booking page. Please try again.', 'error')
        return redirect(url_for('user_booking'))

@app.route('/user/current')
@login_required
def user_current():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    try:
        active_reservation = Reservation.get_active_by_user(current_user.id)
        
        if active_reservation and active_reservation.parking_timestamp:
            active_reservation.parking_timestamp = ensure_ist_timezone(active_reservation.parking_timestamp)
            
    except Exception as e:
        print(f"Error loading current reservation: {e}")
        active_reservation = None
        flash('Error loading current reservation.', 'error')
    
    return render_template('user/current.html', active_reservation=active_reservation)

@app.route('/user/release')
@login_required
def release_parking():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    try:
        active_reservation = Reservation.get_active_by_user(current_user.id)
        if not active_reservation:
            flash('No active parking reservation found', 'error')
            return redirect(url_for('user_dashboard'))
        
        parking_time = ensure_ist_timezone(active_reservation.parking_timestamp)
        current_time = get_ist_now()
        
        if current_time < parking_time:
            duration_hours = active_reservation.booking_duration
        else:
            actual_duration_seconds = (current_time - parking_time).total_seconds()
            
            if actual_duration_seconds > (active_reservation.booking_duration * 3600):
                duration_hours = math.ceil(actual_duration_seconds / 3600)
            else:
                duration_hours = active_reservation.booking_duration
        
        total_cost = duration_hours * float(active_reservation.cost_per_unit)
        
        Reservation.complete_reservation(active_reservation.id, total_cost)
        ParkingSpot.release_spot(active_reservation.spot_id)
        
        flash(f'Parking spot released successfully! Total cost: ₹{total_cost:.2f}', 'success')
        
    except Exception as e:
        print(f"Error releasing parking: {e}")
        flash('Error releasing parking spot. Please try again.', 'error')
        return redirect(url_for('user_current'))
    
    return redirect(url_for('user_history'))

@app.route('/user/history')
@login_required
def user_history():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    try:
        reservations = Reservation.get_user_history(current_user.id)
        
        for reservation in reservations:
            try:
                if reservation.parking_timestamp:
                    reservation.parking_timestamp = ensure_ist_timezone(reservation.parking_timestamp)
                if reservation.leaving_timestamp:
                    reservation.leaving_timestamp = ensure_ist_timezone(reservation.leaving_timestamp)
                
                if reservation.leaving_timestamp and reservation.parking_timestamp:
                    try:
                        actual_seconds = (reservation.leaving_timestamp - reservation.parking_timestamp).total_seconds()
                        actual_hours = int(actual_seconds // 3600)
                        booked_hours = reservation.booking_duration or 0
                        
                        if actual_seconds > (booked_hours * 3600):
                            reservation.duration_text = f"{actual_hours} hour{'s' if actual_hours != 1 else ''} (Booked: {booked_hours}h, Overtime)"
                        else:
                            reservation.duration_text = f"{booked_hours} hour{'s' if booked_hours != 1 else ''} (Booked: {booked_hours}h)"
                    except Exception as e:
                        print(f"Error calculating duration for reservation {reservation.id}: {e}")
                        reservation.duration_text = "Completed"
                else:
                    reservation.duration_text = f"Ongoing (Booked: {reservation.booking_duration or 0}h)"
                
                try:
                    if reservation.parking_timestamp:
                        reservation.parking_time_formatted = reservation.parking_timestamp.strftime('%I:%M %p')
                        reservation.parking_date_formatted = reservation.parking_timestamp.strftime('%b %d, %Y')
                    if reservation.leaving_timestamp:
                        reservation.leaving_time_formatted = reservation.leaving_timestamp.strftime('%I:%M %p')
                        reservation.leaving_date_formatted = reservation.leaving_timestamp.strftime('%b %d, %Y')
                except Exception as e:
                    print(f"Error formatting timestamps for reservation {reservation.id}: {e}")
                    
            except Exception as e:
                print(f"Error processing reservation {getattr(reservation, 'id', 'unknown')}: {e}")
                continue
                    
    except Exception as e:
        print(f"Error loading user history: {e}")
        import traceback
        traceback.print_exc()
        reservations = []
        flash('Error loading booking history.', 'error')
    
    return render_template('user/history.html', reservations=reservations)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        try:
            if form.email.data != current_user.email:
                existing = User.query.filter_by(email=form.email.data).first()
                if existing:
                    flash('Email already exists', 'error')
                    return render_template('profile.html', form=form)
            
            user = User.query.get(current_user.id)
            user.name = form.name.data
            user.email = form.email.data
            
            if form.password.data:
                user.password_hash = generate_password_hash(form.password.data)
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error updating profile. Please try again.', 'error')
            print(f"Profile update error: {e}")
    
    return render_template('profile.html', form=form)

@app.route('/user/cancel', methods=['POST'])
@login_required
def cancel_booking():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    try:
        active_reservation = Reservation.get_active_by_user(current_user.id)
        if not active_reservation:
            flash('No active booking to cancel.', 'error')
            return redirect(url_for('user_dashboard'))
        
        ParkingSpot.release_spot(active_reservation.spot_id)
        Reservation.query.filter_by(id=active_reservation.id).delete()
        db.session.commit()
        
        flash('Booking cancelled successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error cancelling booking.', 'error')
        print(f"Booking cancellation error: {e}")
    
    return redirect(url_for('user_dashboard'))

@app.route('/api/stats')
@login_required
def api_stats():
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        stats = {
            'total_lots': ParkingLot.query.count(),
            'total_spots': ParkingSpot.query.count(),
            'occupied_spots': ParkingSpot.query.filter_by(status='O').count(),
            'total_users': User.query.filter_by(role='user').count(),
            'active_reservations': Reservation.query.filter_by(status='active').count(),
        }
        return jsonify(stats)
    except Exception as e:
        print(f"API stats error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/current-booking')
@login_required
def api_current_booking():
    """API endpoint to get real-time current booking data"""
    if current_user.role == 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        active_reservation = Reservation.get_active_by_user(current_user.id)
        if not active_reservation:
            return jsonify({'error': 'No active booking'}), 404
        
        current_time = get_ist_now()
        
        parking_time = ensure_ist_timezone(active_reservation.parking_timestamp)
        
        booking_end_time = parking_time + timedelta(hours=active_reservation.booking_duration)
        
        duration_seconds = max(0, (current_time - parking_time).total_seconds())
        duration_hours = int(duration_seconds // 3600)
        duration_minutes = int((duration_seconds % 3600) // 60)
        
        remaining_seconds = max(0, (booking_end_time - current_time).total_seconds())
        remaining_hours = int(remaining_seconds // 3600)
        remaining_minutes = int((remaining_seconds % 3600) // 60)
        remaining_secs = int(remaining_seconds % 60)
        
        actual_hours_used = max(1, math.ceil(duration_seconds / 3600))
        current_cost = actual_hours_used * float(active_reservation.cost_per_unit)
        
        total_booking_seconds = active_reservation.booking_duration * 3600
        elapsed_seconds = min(duration_seconds, total_booking_seconds)
        progress_percent = max(0, min(100, (elapsed_seconds / total_booking_seconds) * 100)) if total_booking_seconds > 0 else 0
        
        return jsonify({
            'parking_timestamp': parking_time.isoformat(),
            'parking_date': parking_time.strftime('%B %d, %Y'),
            'duration_hours': duration_hours,
            'duration_minutes': duration_minutes,
            'current_cost': current_cost,
            'remaining_hours': remaining_hours,
            'remaining_minutes': remaining_minutes,
            'remaining_seconds': remaining_secs,
            'booking_duration': active_reservation.booking_duration,
            'cost_per_unit': float(active_reservation.cost_per_unit),
            'booking_end_time': booking_end_time.isoformat(),
            'progress_percent': progress_percent
        })
        
    except Exception as e:
        print(f"API current booking error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

@app.errorhandler(Exception)
def handle_exception(e):
    print(f"Unhandled exception: {e}")
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
