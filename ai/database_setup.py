import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

# Database file
DB_FILE = 'dermasoul.db'

def init_db():
    """Initialize all database tables according to ER diagram + feedback/predictions"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # User Table (with role field for admin/staff distinction)
    c.execute('''
        CREATE TABLE IF NOT EXISTS User (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            parlour_name TEXT NOT NULL,
            role TEXT DEFAULT 'staff'
        )
    ''')
    
    # Admin Table (as per ER diagram - can be used for separate admin management)
    c.execute('''
        CREATE TABLE IF NOT EXISTS Admin (
            admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_username TEXT NOT NULL UNIQUE,
            admin_password TEXT NOT NULL
        )
    ''')
    
    # Customer Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS Customer (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            image_path TEXT,
            FOREIGN KEY (user_id) REFERENCES User(user_id)
        )
    ''')
    
    # Skin_Analysis Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS Skin_Analysis (
            analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            skin_type TEXT NOT NULL,
            acne_level TEXT NOT NULL,
            skin_confidence REAL,
            acne_confidence REAL,
            face_detected BOOLEAN,
            analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES Customer(customer_id)
        )
    ''')
    
    # Suggestion Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS Suggestion (
            suggestion_id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id INTEGER NOT NULL,
            suggestion_text TEXT NOT NULL,
            FOREIGN KEY (analysis_id) REFERENCES Skin_Analysis(analysis_id)
        )
    ''')
    
    # Quiz_Question Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS Quiz_Question (
            question_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            question_text TEXT NOT NULL
        )
    ''')
    
    # Quiz_Options Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS Quiz_Options (
            option_id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL,
            option_text TEXT NOT NULL,
            FOREIGN KEY (question_id) REFERENCES Quiz_Question(question_id)
        )
    ''')
    
    # Quiz_Response Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS Quiz_Response (
            response_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            option_id INTEGER NOT NULL,
            analysis_id INTEGER,
            user_id INTEGER NOT NULL,
            response_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES Customer(customer_id),
            FOREIGN KEY (question_id) REFERENCES Quiz_Question(question_id),
            FOREIGN KEY (option_id) REFERENCES Quiz_Options(option_id),
            FOREIGN KEY (analysis_id) REFERENCES Skin_Analysis(analysis_id),
            FOREIGN KEY (user_id) REFERENCES User(user_id)
        )
    ''')
    
    # ===== (BONUS TABLES) =====
    
    # Feedback Table (for user feedback feature)
    c.execute('''
       CREATE TABLE IF NOT EXISTS feedback (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           user_id INTEGER NULL,  -- Explicitly allow NULL for anonymous feedback
           message TEXT NOT NULL,
           timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
           FOREIGN KEY(user_id) REFERENCES User(user_id) ON DELETE SET NULL
        )
    ''')
    
    # Predictions Table (for admin dashboard tracking)
    c.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            image_name TEXT,
            result TEXT,
            confidence REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            salon_name TEXT,
            FOREIGN KEY(user_id) REFERENCES User(user_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✓ Database initialized successfully!")


def insert_sample_quiz_questions():
    """Insert sample quiz questions and options"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Check if questions already exist
    c.execute("SELECT COUNT(*) FROM Quiz_Question")
    if c.fetchone()[0] > 0:
        print("✓ Quiz questions already exist.")
        conn.close()
        return
    
    # Sample questions
    questions = [
        ("Skin Type", "How does your skin feel after washing?"),
        ("Skin Type", "How often do you experience oily shine?"),
        ("Acne", "How often do you get breakouts?"),
        ("Acne", "What type of acne do you experience most?"),
        ("Lifestyle", "How many hours of sleep do you get per night?"),
        ("Lifestyle", "How much water do you drink daily?"),
    ]
    
    for category, question_text in questions:
        c.execute("INSERT INTO Quiz_Question (category, question_text) VALUES (?, ?)",
                 (category, question_text))
    
    # Sample options
    options = [
        (1, "Tight and dry"),
        (1, "Normal and comfortable"),
        (1, "Oily and greasy"),
        (2, "Never"),
        (2, "Occasionally"),
        (2, "Frequently"),
        (3, "Rarely"),
        (3, "Sometimes"),
        (3, "Often"),
        (4, "Whiteheads"),
        (4, "Blackheads"),
        (4, "Cystic acne"),
        (5, "Less than 6 hours"),
        (5, "6-8 hours"),
        (5, "More than 8 hours"),
        (6, "Less than 4 glasses"),
        (6, "4-8 glasses"),
        (6, "More than 8 glasses"),
    ]
    
    for question_id, option_text in options:
        c.execute("INSERT INTO Quiz_Options (question_id, option_text) VALUES (?, ?)",
                 (question_id, option_text))
    
    conn.commit()
    conn.close()
    print("✓ Sample quiz questions inserted!")


def create_admin_user():
    """Create default admin user in User table with role='admin'"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Check if admin exists
    c.execute("SELECT COUNT(*) FROM User WHERE username = 'admin' AND role = 'admin'")
    if c.fetchone()[0] > 0:
        print("✓ Admin user already exists.")
        conn.close()
        return
    
    # Create admin with hashed password
    admin_password_hash = generate_password_hash('admin123')
    c.execute(
        "INSERT INTO User (username, password_hash, parlour_name, role) VALUES (?, ?, ?, ?)",
        ('admin', admin_password_hash, 'DermaSoul Admin', 'admin')
    )
    
    conn.commit()
    conn.close()
    print("✓ Admin user created!")
    print("  Username: admin")
    print("  Password: admin123")


def create_sample_staff():
    """Create sample staff user for testing"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Check if staff exists
    c.execute("SELECT COUNT(*) FROM User WHERE username = 'staff1'")
    if c.fetchone()[0] > 0:
        print("✓ Sample staff already exists.")
        conn.close()
        return
    
    staff_password_hash = generate_password_hash('staff123')
    c.execute(
        "INSERT INTO User (username, password_hash, parlour_name, role) VALUES (?, ?, ?, ?)",
        ('staff1', staff_password_hash, 'Beauty Parlour 1', 'staff')
    )
    
    conn.commit()
    conn.close()
    print("✓ Sample staff created!")
    print("  Username: staff1")
    print("  Password: staff123")


def get_db_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


if __name__ == '__main__':
    print("=" * 50)
    print("Initializing DermaSoul Database...")
    print("=" * 50)
    
    init_db()
    create_admin_user()
    create_sample_staff()
    insert_sample_quiz_questions()
    
    print("\n" + "=" * 50)
    print("Database setup complete!")
    print("=" * 50)
    print(f"Database file: {os.path.abspath(DB_FILE)}")
    print("\nTables created (as per ER diagram):")
    print("  1. User")
    print("  2. Admin")
    print("  3. Customer")
    print("  4. Skin_Analysis")
    print("  5. Suggestion")
    print("  6. Quiz_Question")
    print("  7. Quiz_Options")
    print("  8. Quiz_Response")
    print("\nBonus tables (not in ER):")
    print("  9. feedback")
    print("  10. predictions")
    print("\nDefault Accounts:")
    print("  Admin: admin / admin123")
    print("  Staff: staff1 / staff123")
    print("=" * 50)