from flask import Flask
from ai.ai_routes import ai_bp
from admin.routes import admin_bp
from ai.database_setup import init_db, create_admin_user, create_sample_staff, insert_sample_quiz_questions
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_change_this_in_production'

# Configure upload folder
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'ai', 'uploads')

# Ensure uploads folder exists
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Initialize database (single source of truth from database_setup.py)
print("\n" + "="*60)
print("Starting DermaSoul Application...")
print("="*60)

init_db()
create_admin_user()
create_sample_staff()
insert_sample_quiz_questions()

print("="*60)
print("Application ready!")
print("="*60 + "\n")

# Register Blueprints
app.register_blueprint(ai_bp)  # user/parlour routes at root
app.register_blueprint(admin_bp, url_prefix='/admin')  # admin routes at /admin

if __name__ == '__main__':
    print("Starting Flask development server...")
    print("Access URLs:")
    print("  - User/Staff Login: http://127.0.0.1:5000/login")
    print("  - Admin Login: http://127.0.0.1:5000/admin/login")
    print("\n")
    app.run(debug=True)