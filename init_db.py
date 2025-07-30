"""
Database Initialization Script for Parkit
Shivam Sharma - 2025
"""

from models import init_database, User, ParkingLot
from config import Config

def main():
    print("Initializing Parkit Database...")
    
    init_database()
    print("Database schema created successfully!")
    
    admin_created = User.create(
        'Admin',
        'admin@parkit.com',
        Config.ADMIN_PASSWORD,
        'admin'
    )
    
    if admin_created:
        print(f"Admin user created: {Config.ADMIN_EMAIL}")
    else:
        print(f"Admin user already exists: {Config.ADMIN_EMAIL}")
    
    sample_users = [
        ('John Doe', 'john@gmail.com', 'user123'),
    ]
    print("\nCreating sample users...")
    for name, email, password in sample_users:
        if User.create(name, email, password, 'user'):
            print(f"Sample user created: {email}")
        else:
            print(f"User already exists: {email}")
    
    sample_lots = [
        {
            'prime_location_name': 'Downtown Central Plaza',
            'address': '123 Main Street, Central Business District',
            'pin_code': '110001',
            'price': 50.0,
            'max_number_of_spots': 25
        },
        {
            'prime_location_name': 'Mall Parking Complex',
            'address': '456 Shopping Avenue, Commercial Zone',
            'pin_code': '110002',
            'price': 30.0,
            'max_number_of_spots': 40
        },
        {
            'prime_location_name': 'Airport Terminal Parking',
            'address': '789 Airport Road, Terminal 1',
            'pin_code': '110037',
            'price': 75.0,
            'max_number_of_spots': 60
        },
        {
            'prime_location_name': 'University Campus Parking',
            'address': '321 Education Lane, University District',
            'pin_code': '110025',
            'price': 20.0,
            'max_number_of_spots': 50
        },
        {
            'prime_location_name': 'Business Park Parking',
            'address': '654 Corporate Drive, Business District',
            'pin_code': '110048',
            'price': 40.0,
            'max_number_of_spots': 35
        }
    ]
    
    print("\nCreating sample parking lots...")
    for lot_data in sample_lots:
        lot_id = ParkingLot.create(**lot_data)
        print(f"Parking lot created: {lot_data['prime_location_name']} (ID: {lot_id})")
    
    print("\nDatabase initialization completed successfully!")
    print("\nLogin Credentials:")
    print("Admin: admin / admin123")
    print("Users: john_doe / user123, alice_smith / alice123, bob_wilson / bob123")
    
    print("\nParkit is ready to use!")
    print("Run: python app.py")

if __name__ == "__main__":
    main()
