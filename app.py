import csv
from datetime import timedelta
from functools import wraps
from io import StringIO

from flask import Flask, Response, flash, jsonify, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from flask_wtf.csrf import CSRFProtect

from config import Config
from forms import BookingForm, LoginForm, ParkingLotForm, ProfileForm, RegisterForm
from models import ParkingLot, ParkingSpot, Reservation, User, db, get_ist_now

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('user_dashboard'))
        return view(*args, **kwargs)
    return wrapper


def user_required(view):
    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        return view(*args, **kwargs)
    return wrapper


def seed_database():
    """Create tables, the admin, and demo data. Safe to run on every start."""
    db.create_all()

    if not User.get_by_email(Config.ADMIN_EMAIL):
        User.create('Admin', Config.ADMIN_EMAIL, Config.ADMIN_PASSWORD, 'admin')

    if ParkingLot.query.count() == 0:
        for lot in [
            ('Downtown Central Plaza', 'Connaught Place, New Delhi, Delhi 110001', '110001', 75.0, 25),
            ('Mall Parking Complex', 'Select Citywalk, Saket, New Delhi, Delhi 110017', '110017', 50.0, 40),
            ('Airport Terminal Parking', 'Indira Gandhi International Airport, New Delhi, Delhi 110037', '110037', 100.0, 50),
        ]:
            ParkingLot.create(*lot)

    if not User.get_by_email(Config.DEMO_EMAIL):
        User.create('Demo User', Config.DEMO_EMAIL, Config.DEMO_PASSWORD)
        demo = User.get_by_email(Config.DEMO_EMAIL)
        now = get_ist_now()
        # A few past bookings so the history and charts are not empty.
        for i, (lot, days_ago, hours) in enumerate(zip(ParkingLot.query.all() * 2, [9, 7, 5, 4, 2, 1], [2, 1, 3, 2, 4, 1])):
            start = now - timedelta(days=days_ago, hours=hours)
            db.session.add(Reservation(
                user_id=demo.id, lot_id=lot.id, spot_id=lot.parking_spots[i].id,
                vehicle_number='DL01AB1234', cost_per_unit=float(lot.price), booking_duration=hours,
                parking_timestamp=start, leaving_timestamp=start + timedelta(hours=hours),
                total_cost=hours * float(lot.price), status='completed',
            ))
        db.session.commit()


with app.app_context():
    seed_database()


def read_lot_form():
    """Returns (values, error) for the add/edit lot forms."""
    form = request.form
    try:
        values = {
            'prime_location_name': form.get('prime_location_name', '').strip(),
            'address': form.get('address', '').strip(),
            'pin_code': form.get('pin_code', '').strip(),
            'price': float(form.get('price', 0)),
            'max_number_of_spots': int(form.get('max_number_of_spots', 0)),
        }
    except ValueError:
        return None, 'Invalid input values. Please check your data.'
    if not (values['prime_location_name'] and values['address']) or values['price'] <= 0 or values['max_number_of_spots'] <= 0:
        return None, 'All fields are required and must be valid.'
    if len(values['pin_code']) != 6 or not values['pin_code'].isdigit():
        return None, 'PIN code must be exactly 6 digits.'
    return values, None


def lots_with_stats(lots):
    return [{'lot': lot, 'stats': ParkingSpot.get_lot_stats(lot.id)} for lot in lots]


def search_lots(q):
    query = ParkingLot.query
    if q:
        like = f'%{q}%'
        query = query.filter(db.or_(ParkingLot.prime_location_name.ilike(like),
                                    ParkingLot.address.ilike(like),
                                    ParkingLot.pin_code.ilike(like)))
    return query.order_by(ParkingLot.created_at.desc()).all()


def is_safe_next(url):
    return bool(url) and url.startswith('/') and not url.startswith('//')


@app.route('/')
def index():
    return render_template('index.html')


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
            if is_safe_next(next_page):
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        flash('Invalid email or password', 'error')

    return render_template('auth/login.html', form=form)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.get_by_email(form.email.data)
        if user and user.check_password(form.password.data):
            if user.role == 'admin':
                login_user(user)
                return redirect(url_for('admin_dashboard'))
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
        if User.create(form.name.data, form.email.data, form.password.data):
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        flash('Email already exists', 'error')

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
    return redirect(url_for('user_dashboard'))


# ---------- Admin ----------

@app.route('/admin')
@admin_required
def admin_dashboard():
    total_spots = ParkingSpot.query.count()
    occupied_spots = ParkingSpot.query.filter_by(status='O').count()
    revenue = (db.session.query(db.func.sum(Reservation.total_cost))
               .filter(Reservation.status == 'completed').scalar() or 0)
    stats = {
        'total_lots': ParkingLot.query.count(),
        'total_spots': total_spots,
        'occupied_spots': occupied_spots,
        'available_spots': total_spots - occupied_spots,
        'total_users': User.query.filter_by(role='user').count(),
        'active_reservations': Reservation.query.filter_by(status='active').count(),
        'total_revenue': float(revenue),
    }

    per_lot = []
    for lot in ParkingLot.get_all():
        done = [r for r in lot.reservations if r.status == 'completed']
        per_lot.append({
            'name': lot.prime_location_name,
            'bookings': len(lot.reservations),
            'revenue': float(sum(r.total_cost or 0 for r in done)),
        })
    chart_data = {'occupied': occupied_spots, 'available': total_spots - occupied_spots, 'lots': per_lot}

    return render_template('admin/dashboard.html', stats=stats, chart_data=chart_data)


@app.route('/admin/parking-lots')
@admin_required
def admin_parking_lots():
    q = request.args.get('q', '').strip()
    return render_template('admin/parking_lots.html', lots_with_stats=lots_with_stats(search_lots(q)), search_query=q)


@app.route('/admin/parking-lots/<int:lot_id>')
@admin_required
def admin_lot_detail(lot_id):
    lot = ParkingLot.get_by_id(lot_id)
    if not lot:
        flash('Parking lot not found', 'error')
        return redirect(url_for('admin_parking_lots'))
    active = {r.spot_id: r for r in Reservation.query.filter_by(lot_id=lot_id, status='active')}
    return render_template('admin/lot_detail.html', lot=lot, active=active,
                           stats=ParkingSpot.get_lot_stats(lot_id))


@app.route('/admin/parking-lots/add', methods=['POST'])
@admin_required
def add_parking_lot():
    values, error = read_lot_form()
    if error:
        flash(error, 'error')
    else:
        ParkingLot.create(**values)
        flash('Parking lot created successfully!', 'success')
    return redirect(url_for('admin_parking_lots'))


@app.route('/admin/parking-lots/edit/<int:lot_id>', methods=['GET', 'POST'])
@admin_required
def edit_parking_lot(lot_id):
    lot = ParkingLot.get_by_id(lot_id)
    if not lot:
        flash('Parking lot not found', 'error')
        return redirect(url_for('admin_parking_lots'))

    if request.method == 'POST':
        values, error = read_lot_form()
        if not error:
            ok, error = ParkingLot.update(lot_id, **values)
        flash(error or 'Parking lot updated successfully!', 'error' if error else 'success')
        return redirect(url_for('admin_parking_lots'))

    form = ParkingLotForm(obj=lot)
    form.price.data = float(lot.price)
    return render_template('admin/parking_lots.html', form=form, lots_with_stats=[], show_form=True, editing=True)


@app.route('/admin/parking-lots/delete/<int:lot_id>', methods=['POST'])
@admin_required
def delete_parking_lot(lot_id):
    if ParkingLot.delete(lot_id):
        flash('Parking lot deleted successfully!', 'success')
    else:
        flash('Cannot delete a parking lot while any of its spots are occupied.', 'error')
    return redirect(url_for('admin_parking_lots'))


@app.route('/admin/users')
@admin_required
def admin_users():
    q = request.args.get('q', '').strip()
    query = User.query.filter(User.role != 'admin')
    if q:
        query = query.filter(db.or_(User.email.ilike(f'%{q}%'), User.name.ilike(f'%{q}%')))
    users = query.all()
    for user in users:
        user.booking_count = len(user.reservations)
    return render_template('admin/users.html', users=users, search_query=q)


@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user or user.role == 'admin':
        flash('User not found.', 'error')
    elif Reservation.get_active_by_user(user_id):
        flash('Cannot delete user with active reservations.', 'error')
    else:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/reservations')
@admin_required
def admin_reservations():
    q = request.args.get('q', '').strip()
    query = Reservation.query
    if q:
        like = f'%{q}%'
        query = (query.join(User).join(ParkingLot)
                 .filter(db.or_(Reservation.vehicle_number.ilike(like), User.name.ilike(like),
                                User.email.ilike(like), ParkingLot.prime_location_name.ilike(like))))
    reservations = query.order_by(Reservation.parking_timestamp.desc()).all()
    return render_template('admin/stats.html', reservations=reservations, search_query=q)


@app.route('/admin/reservations/delete/<int:reservation_id>', methods=['POST'])
@admin_required
def delete_reservation(reservation_id):
    reservation = db.session.get(Reservation, reservation_id)
    if not reservation:
        flash('Reservation not found.', 'error')
        return redirect(url_for('admin_reservations'))

    lot_name = reservation.parking_lot.prime_location_name
    if reservation.status == 'active':
        ParkingSpot.release_spot(reservation.spot_id)
    db.session.delete(reservation)
    db.session.commit()
    flash(f'Reservation for {lot_name} deleted successfully.', 'success')
    return redirect(url_for('admin_reservations'))


@app.route('/admin/export-reservations')
@admin_required
def export_reservations():
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Reservation ID', 'User Name', 'User Email', 'Parking Lot', 'Address', 'Spot Number',
                     'Vehicle Number', 'Status', 'Start Time', 'End Time', 'Billed Hours',
                     'Cost Per Hour', 'Total Cost', 'Booked Hours'])
    fmt = '%Y-%m-%d %H:%M:%S'
    for r in Reservation.get_all():
        writer.writerow([
            r.id, r.user.name, r.user.email, r.parking_lot.prime_location_name, r.parking_lot.address,
            r.parking_spot.spot_number if r.parking_spot else 'N/A',
            r.vehicle_number or 'N/A', r.status,
            r.parking_timestamp.strftime(fmt),
            r.leaving_timestamp.strftime(fmt) if r.leaving_timestamp else 'N/A',
            r.billable_hours() if r.leaving_timestamp else 'N/A',
            float(r.cost_per_unit), float(r.total_cost or 0), r.booking_duration,
        ])
    filename = f'parkit_reservations_{get_ist_now():%Y%m%d_%H%M%S}.csv'
    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename={filename}'})


# ---------- User ----------

@app.route('/user')
@user_required
def user_dashboard():
    per_lot = {}
    for r in current_user.reservations:
        entry = per_lot.setdefault(r.parking_lot.prime_location_name, {'bookings': 0, 'spent': 0.0})
        entry['bookings'] += 1
        entry['spent'] += float(r.total_cost or 0)
    chart_data = [{'name': name, **values} for name, values in per_lot.items()]
    return render_template('user/dashboard.html',
                           active_reservation=Reservation.get_active_by_user(current_user.id),
                           chart_data=chart_data)


@app.route('/user/booking')
@user_required
def user_booking():
    if Reservation.get_active_by_user(current_user.id):
        flash('You already have an active parking reservation', 'info')
        return redirect(url_for('user_current'))

    q = request.args.get('q', '').strip()
    return render_template('user/booking.html', lots_with_stats=lots_with_stats(search_lots(q)), search_query=q)


@app.route('/user/book/<int:lot_id>', methods=['GET', 'POST'])
@user_required
def book_parking(lot_id):
    if Reservation.get_active_by_user(current_user.id):
        flash('You already have an active parking reservation', 'error')
        return redirect(url_for('user_current'))

    lot = ParkingLot.get_by_id(lot_id)
    if not lot:
        flash('Parking lot not found', 'error')
        return redirect(url_for('user_booking'))

    form = BookingForm()
    if request.method == 'GET':
        form.name.data = current_user.name

    if form.validate_on_submit():
        spot = ParkingSpot.get_available_spot(lot_id)
        if spot and Reservation.create(current_user.id, lot_id, spot.id, lot.price,
                                       form.hours.data, form.vehicle_number.data.strip().upper()):
            flash(f'Parking spot {spot.spot_number} booked successfully at {lot.prime_location_name} '
                  f'for {form.hours.data} hour(s)!', 'success')
            return redirect(url_for('user_current'))
        flash('No parking spots available at this location. Please try another location.', 'error')
        return redirect(url_for('user_booking'))
    if request.method == 'POST':
        flash('Please correct the errors in the form.', 'error')

    return render_template('user/book_now.html', lot=lot, form=form)


@app.route('/user/current')
@user_required
def user_current():
    return render_template('user/current.html',
                           active_reservation=Reservation.get_active_by_user(current_user.id))


@app.route('/user/release', methods=['POST'])
@user_required
def release_parking():
    reservation = Reservation.get_active_by_user(current_user.id)
    if not reservation:
        flash('No active parking reservation found', 'error')
        return redirect(url_for('user_dashboard'))

    total_cost = reservation.complete()
    flash(f'Parking spot released successfully! Total cost: ₹{total_cost:.2f}', 'success')
    return redirect(url_for('user_history'))


@app.route('/user/history')
@user_required
def user_history():
    return render_template('user/history.html', reservations=Reservation.get_user_history(current_user.id))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)

    if form.validate_on_submit():
        existing = User.get_by_email(form.email.data)
        if existing and existing.id != current_user.id:
            flash('Email already exists', 'error')
            return render_template('profile.html', form=form)

        current_user.name = form.name.data
        current_user.email = form.email.data
        if form.password.data:
            current_user.set_password(form.password.data)
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    return render_template('profile.html', form=form)


# ---------- JSON API ----------

@app.route('/api/stats')
@login_required
def api_stats():
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    return jsonify({
        'total_lots': ParkingLot.query.count(),
        'total_spots': ParkingSpot.query.count(),
        'occupied_spots': ParkingSpot.query.filter_by(status='O').count(),
        'total_users': User.query.filter_by(role='user').count(),
        'active_reservations': Reservation.query.filter_by(status='active').count(),
    })


@app.route('/api/current-booking')
@login_required
def api_current_booking():
    if current_user.role == 'admin':
        return jsonify({'error': 'Access denied'}), 403

    reservation = Reservation.get_active_by_user(current_user.id)
    if not reservation:
        return jsonify({'error': 'No active booking'}), 404

    now = get_ist_now()
    elapsed = max(0, int((now - reservation.parking_timestamp).total_seconds()))
    booking_end = reservation.parking_timestamp + timedelta(hours=reservation.booking_duration)
    return jsonify({
        'parking_timestamp': reservation.parking_timestamp.isoformat(),
        'booking_end_time': booking_end.isoformat(),
        'booking_duration': reservation.booking_duration,
        'elapsed_hours': elapsed // 3600,
        'elapsed_minutes': elapsed % 3600 // 60,
        'overtime': now > booking_end,
        'cost_per_unit': float(reservation.cost_per_unit),
        'current_cost': reservation.billable_hours(now) * float(reservation.cost_per_unit),
    })


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(debug=True, port=5001)
