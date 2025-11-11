# admin/routes.py
import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os

admin_bp = Blueprint(
    'admin_bp', 
    __name__, 
    template_folder='templates',
    static_folder='static',
    static_url_path='/admin_static'
)

# Database path
DB = os.path.join(os.path.dirname(__file__), '../dermasoul.db')
print(f"Admin DB path: {os.path.abspath(DB)}")

# Get database connection
def get_db_connection():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# Decorators
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            flash("Please log in first.")
            return redirect(url_for('admin_bp.login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash("Admin access required.")
            return redirect(url_for('admin_bp.dashboard'))
        return f(*args, **kwargs)
    return decorated

def staff_or_admin_required(f):
    """Allow both staff and admin to access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') not in ['admin', 'staff']:
            flash("Access denied.")
            return redirect(url_for('admin_bp.login'))
        return f(*args, **kwargs)
    return decorated

# Routes
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        # Check for both admin AND staff users
        user = conn.execute(
            'SELECT * FROM User WHERE username=? AND role IN ("admin", "staff")',
            (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['username'] = user['username']
            session['role'] = user['role']
            session['user_id'] = user['user_id']
            return redirect(url_for('admin_bp.dashboard'))
        else:
            flash("Invalid credentials")

    return render_template('admin_login.html')


def staff_or_admin_required(f):
    """Allow both staff and admin to access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') not in ['admin', 'staff']:
            flash("Access denied.")
            return redirect(url_for('admin_bp.login'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin_bp.login'))


@admin_bp.route('/dashboard')
@staff_or_admin_required  # Changed to allow staff
def dashboard():
    conn = get_db_connection()
    users_count = conn.execute('SELECT COUNT(*) FROM User WHERE role="staff"').fetchone()[0]
    preds_count = conn.execute('SELECT COUNT(*) FROM predictions').fetchone()[0]
    customers_count = conn.execute('SELECT COUNT(*) FROM Customer').fetchone()[0]
    analyses_count = conn.execute('SELECT COUNT(*) FROM Skin_Analysis').fetchone()[0]
    conn.close()
    
    return render_template('dashboard.html', 
                         users=users_count, 
                         preds=preds_count,
                         customers=customers_count,
                         analyses=analyses_count)


@admin_bp.route('/users')
@staff_or_admin_required  # Changed to allow staff
def users():
    conn = get_db_connection()
    # Get all users (staff and admin)
    all_users = conn.execute('SELECT * FROM User ORDER BY role, username').fetchall()
    conn.close()
    return render_template('users.html', users=all_users)


@admin_bp.route('/delete/<int:user_id>')
@admin_required  # Keep admin only
def delete_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM User WHERE user_id = ?', (user_id,)).fetchone()
    
    if user and user['role'] != 'admin':
        # Delete related data first (to maintain referential integrity)
        # Delete feedback
        conn.execute('DELETE FROM feedback WHERE user_id = ?', (user_id,))
        # Delete predictions
        conn.execute('DELETE FROM predictions WHERE user_id = ?', (user_id,))
        # Delete quiz responses
        conn.execute('DELETE FROM Quiz_Response WHERE user_id = ?', (user_id,))
        
        # Delete customers and their related data
        customers = conn.execute('SELECT customer_id FROM Customer WHERE user_id = ?', (user_id,)).fetchall()
        for customer in customers:
            customer_id = customer['customer_id']
            # Delete suggestions for analyses of this customer
            conn.execute('''
                DELETE FROM Suggestion 
                WHERE analysis_id IN (
                    SELECT analysis_id FROM Skin_Analysis WHERE customer_id = ?
                )
            ''', (customer_id,))
            # Delete skin analyses
            conn.execute('DELETE FROM Skin_Analysis WHERE customer_id = ?', (customer_id,))
            # Delete quiz responses for this customer
            conn.execute('DELETE FROM Quiz_Response WHERE customer_id = ?', (customer_id,))
        
        # Delete customers
        conn.execute('DELETE FROM Customer WHERE user_id = ?', (user_id,))
        
        # Finally delete the user
        conn.execute('DELETE FROM User WHERE user_id = ?', (user_id,))
        conn.commit()
        flash(f"User {user['username']} and all related data deleted successfully.")
    elif user and user['role'] == 'admin':
        flash("Cannot delete admin user.")
    else:
        flash("User not found.")
    
    conn.close()
    return redirect(url_for('admin_bp.users'))


@admin_bp.route('/reset/<int:user_id>', methods=['GET', 'POST'])
@admin_required  # Keep admin only
def reset_user_password(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM User WHERE user_id = ?', (user_id,)).fetchone()
    
    if not user:
        flash("User not found.")
        conn.close()
        return redirect(url_for('admin_bp.users'))

    if request.method == 'POST':
        new_password = request.form.get('new_password', '').strip()
        if not new_password:
            flash("Password cannot be empty.")
            conn.close()
            return render_template('reset.html', user=user)
        
        # Hash the new password
        password_hash = generate_password_hash(new_password)
        conn.execute('UPDATE User SET password_hash = ? WHERE user_id = ?', (password_hash, user_id))
        conn.commit()
        conn.close()
        flash(f"Password for {user['username']} has been reset successfully.")
        return redirect(url_for('admin_bp.users'))

    conn.close()
    return render_template('reset.html', user=user)


@admin_bp.route('/feedback')
@staff_or_admin_required  # Changed to allow staff
def feedback():
    conn = get_db_connection()
    # Join with User table to get username, use 'Anonymous User' for NULL usernames
    fb = conn.execute('''
        SELECT 
            feedback.id,
            feedback.user_id,
            feedback.message,
            feedback.timestamp,
            COALESCE(User.username, 'Anonymous User') as username,
            User.parlour_name
        FROM feedback
        LEFT JOIN User ON feedback.user_id = User.user_id
        ORDER BY feedback.timestamp DESC
    ''').fetchall()
    conn.close()
    return render_template('feedback.html', feedback=fb)


@admin_bp.route('/predictions')
@staff_or_admin_required  # Changed to allow staff
def predictions():
    # Check if clear filter is requested
    if request.args.get('clear') == 'true':
        return redirect(url_for('admin_bp.predictions'))
    
    username = request.args.get('username', '').strip()
    result = request.args.get('result', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()

    query = '''
        SELECT predictions.id, User.username, predictions.image_name,
               predictions.result, predictions.confidence, predictions.timestamp,
               predictions.salon_name, User.parlour_name
        FROM predictions
        LEFT JOIN User ON predictions.user_id = User.user_id
        WHERE 1=1
    '''
    params = []

    if username:
        query += " AND User.username LIKE ?"
        params.append(f'%{username}%')

    if result:
        query += " AND predictions.result LIKE ?"
        params.append(f'%{result}%')

    if start_date:
        query += " AND date(predictions.timestamp) >= date(?)"
        params.append(start_date)

    if end_date:
        query += " AND date(predictions.timestamp) <= date(?)"
        params.append(end_date)

    query += " ORDER BY predictions.timestamp DESC"

    conn = get_db_connection()
    preds = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('predictions.html', 
                         preds=preds,
                         username=username, 
                         result=result,
                         start_date=start_date, 
                         end_date=end_date)


@admin_bp.route('/customers')
@staff_or_admin_required  # Changed to allow staff
def customers():
    """View all customers with their latest analysis"""
    conn = get_db_connection()
    customers_data = conn.execute('''
        SELECT 
            c.customer_id,
            c.customer_name,
            c.image_path,
            u.username as staff_username,
            u.parlour_name,
            sa.skin_type,
            sa.acne_level,
            sa.analysis_date,
            sa.analysis_id
        FROM Customer c
        LEFT JOIN User u ON c.user_id = u.user_id
        LEFT JOIN Skin_Analysis sa ON c.customer_id = sa.customer_id
        WHERE sa.analysis_id = (
            SELECT MAX(analysis_id) 
            FROM Skin_Analysis 
            WHERE customer_id = c.customer_id
        )
        ORDER BY sa.analysis_date DESC
    ''').fetchall()
    conn.close()
    
    return render_template('customers.html', customers=customers_data)


@admin_bp.route('/analyses')
@staff_or_admin_required  # Changed to allow staff
def analyses():
    """View all skin analyses"""
    conn = get_db_connection()
    analyses_data = conn.execute('''
        SELECT 
            sa.analysis_id,
            sa.skin_type,
            sa.acne_level,
            sa.skin_confidence,
            sa.acne_confidence,
            sa.face_detected,
            sa.analysis_date,
            c.customer_name,
            u.username as staff_username,
            u.parlour_name
        FROM Skin_Analysis sa
        JOIN Customer c ON sa.customer_id = c.customer_id
        JOIN User u ON c.user_id = u.user_id
        ORDER BY sa.analysis_date DESC
        LIMIT 100
    ''').fetchall()
    conn.close()
    
    return render_template('analyses.html', analyses=analyses_data)