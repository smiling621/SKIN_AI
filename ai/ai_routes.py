from flask import Blueprint, render_template, request, redirect, url_for, session, flash, get_flashed_messages
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import sqlite3
from .predict import ai_predict

ai_bp = Blueprint(
    'ai',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/ai_static'
)

# Path to main DB
ADMIN_DB = os.path.join(os.path.dirname(__file__), '../dermasoul.db')
print(f"AI ADMIN_DB path: {os.path.abspath(ADMIN_DB)}")

# Uploads folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ---------- DATABASE HELPER ----------
def get_db_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect(ADMIN_DB)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- ROUTES ----------

@ai_bp.route('/')
def home():
    if 'user_id' in session:
        return render_template('index.html', user=session['username'])
    return redirect(url_for('ai.login'))


@ai_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        salon_name = request.form['salonName']

        if not all([username, password, salon_name]):
            flash('All fields are required.', 'error')
            return render_template('register.html')

        # Hash the password
        password_hash = generate_password_hash(password)

        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO User (username, password_hash, parlour_name, role) VALUES (?, ?, ?, ?)",
                (username, password_hash, salon_name, 'staff')
            )
            conn.commit()
            
            # Auto-login after registration
            user = conn.execute("SELECT * FROM User WHERE username = ?", (username,)).fetchone()
            session['user_id'] = user['user_id']
            session['username'] = username
            session['salon_name'] = salon_name
            session['role'] = user['role']
            
            # Flash success message only, will be shown on home page
            flash('Registration successful! You are now logged in.', 'success')
            conn.close()
            return redirect(url_for('ai.home'))
            
        except sqlite3.IntegrityError:
            flash('Username already exists.', 'error')
            conn.close()
            return render_template('register.html')

    return render_template('register.html')


@ai_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username') or request.form.get('email')
        password = request.form['password']

        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('user_login.html')

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM User WHERE username = ? AND role = 'staff'",
            (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['salon_name'] = user['parlour_name']
            session['role'] = user['role']
            # Don't flash login success - it's obvious they logged in
            # flash('Login successful!', 'success')
            return redirect(url_for('ai.home'))
        else:
            flash('Invalid username or password.', 'error')
            return render_template('user_login.html')

    return render_template('user_login.html')


@ai_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('ai.login'))


@ai_bp.route('/analyzer', methods=['GET', 'POST'])
def analyzer():
    print("\n" + " "*30)
    print("ANALYZER ROUTE CALLED!")
    print(f"Method: {request.method}")
    print(f"URL: {request.url}")
    print(f"User in session: {'user_id' in session}")
    print(" "*30 + "\n")
    
    if 'user_id' not in session:
        print(" No user in session - redirecting to login")
        flash("Please login to access the analyzer.", "error")
        return redirect(url_for('ai.login'))

    # Clear error flags on GET request
    if request.method == 'GET':
        print("GET request - clearing error flags and rendering template")
        session.pop('show_face_error', None)
        session.pop('show_animal_error', None)
        session.pop('no_face_warning', None)
        return render_template('analyzer.html')

    # POST request - handle image upload
    print("\n" + "="*60)
    print("POST REQUEST - IMAGE UPLOAD")
    print("="*60)
    
    try:
        # Check if file part exists
        print(f"request.files keys: {list(request.files.keys())}")
        print(f"request.form keys: {list(request.form.keys())}")
        
        if 'image' not in request.files:
            print("No 'image' in request.files")
            flash("No image uploaded.", "error")
            return render_template('analyzer.html')

        file = request.files['image']
        print(f"File object: {file}")
        print(f"Filename: {file.filename}")
        
        if file.filename == '':
            print("Empty filename")
            flash("No image selected.", "error")
            return render_template('analyzer.html')

        # Get customer name
        customer_name = request.form.get('customerName', '').strip()
        print(f"Customer name: '{customer_name}'")
        
        if not customer_name:
            print("No customer name")
            flash("Please enter the customer's name.", "error")
            return render_template('analyzer.html')

        print(f"Customer: {customer_name}")
        print(f"File: {file.filename}")

        # Save the file
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        print(f"Saving to: {filepath}")
        file.save(filepath)
        
        print(f"   File saved successfully")
        print(f"   Exists: {os.path.exists(filepath)}")
        print(f"   Size: {os.path.getsize(filepath)} bytes")

        # Run prediction
        print("\n Calling ai_predict()...")
        prediction_result = ai_predict(filepath)
        
        print(f"\n Prediction completed!")
        print(f"   Result type: {type(prediction_result)}")
        print(f"   Result keys: {list(prediction_result.keys())}")
        
        for key, value in prediction_result.items():
            print(f"   {key}: {value}")

        #  Check for errors BEFORE saving to database
        if prediction_result.get("error"):
            error_msg = prediction_result.get("error")
            print(f"\n PREDICTION ERROR: {error_msg}")
            
            # Clean up file
            if os.path.exists(filepath):
                os.remove(filepath)
                print("   Cleaned up file")
            
            # Set error flags and redirect - NO DATABASE SAVE
            error_lower = error_msg.lower()
            if "animal" in error_lower or "fur" in error_lower or "non-human" in error_lower:
                print("   Setting show_animal_error = True")
                session['show_animal_error'] = True
                session.modified = True
                return redirect(url_for('ai.analyzer'))
            elif "face" in error_lower:
                print("   Setting show_face_error = True")
                session['show_face_error'] = True
                session.modified = True
                return redirect(url_for('ai.analyzer'))
            else:
                print("   Showing generic error")
                flash(f"Error: {error_msg}", "error")
                return render_template('analyzer.html')
        
        # check for "message" field (no face warning from predict.py)
        if prediction_result.get("message"):
            warning_msg = prediction_result.get("message")
            print(f"\n PREDICTION WARNING: {warning_msg}")
            
            # Clean up file
            if os.path.exists(filepath):
                os.remove(filepath)
                print("   Cleaned up file")
            
            # Show face detection error
            session['show_face_error'] = True
            session.modified = True
            return redirect(url_for('ai.analyzer'))
        
        # Validate required keys
        required_keys = ['skin_type', 'acne_type', 'skin_confidence', 'acne_confidence', 'face_detected']
        missing = [k for k in required_keys if k not in prediction_result]
        
        if missing:
            print(f" Missing keys: {missing}")
            flash(f"Invalid prediction: missing {', '.join(missing)}", "error")
            if os.path.exists(filepath):
                os.remove(filepath)
            return render_template('analyzer.html')

        # Check if results are "unknown" (from predict.py when no face detected)
        if prediction_result['skin_type'] == 'unknown' or prediction_result['acne_type'] == 'unknown':
            print(f" Unknown skin/acne type detected")
            if os.path.exists(filepath):
                os.remove(filepath)
            session['show_face_error'] = True
            session.modified = True
            return redirect(url_for('ai.analyzer'))

        print(" All required keys present and valid")

        #  ONLY SAVE TO DATABASE IF ALL CHECKS PASS
        print("\n Saving to database...")
        conn = get_db_connection()
        
        # Create/Get Customer
        customer = conn.execute(
            "SELECT * FROM Customer WHERE customer_name = ? AND user_id = ?",
            (customer_name, session['user_id'])
        ).fetchone()
        
        if not customer:
            cursor = conn.execute(
                "INSERT INTO Customer (customer_name, user_id, image_path) VALUES (?, ?, ?)",
                (customer_name, session['user_id'], filename)
            )
            customer_id = cursor.lastrowid
            print(f"   Created customer ID: {customer_id}")
        else:
            customer_id = customer['customer_id']
            conn.execute(
                "UPDATE Customer SET image_path = ? WHERE customer_id = ?",
                (filename, customer_id)
            )
            print(f"   Updated customer ID: {customer_id}")
        
        # Create Analysis
        cursor = conn.execute(
            '''INSERT INTO Skin_Analysis 
            (customer_id, skin_type, acne_level, skin_confidence, acne_confidence, face_detected)
            VALUES (?, ?, ?, ?, ?, ?)''',
            (customer_id, prediction_result['skin_type'], prediction_result['acne_type'],
             prediction_result['skin_confidence'], prediction_result['acne_confidence'],
             prediction_result['face_detected'])
        )
        analysis_id = cursor.lastrowid
        print(f"   Created analysis ID: {analysis_id}")
        
        # Save suggestions
        suggestions = generate_suggestions(
            prediction_result['skin_type'],
            prediction_result['acne_type']
        )
        
        for suggestion_text in suggestions:
            conn.execute(
                "INSERT INTO Suggestion (analysis_id, suggestion_text) VALUES (?, ?)",
                (analysis_id, suggestion_text)
            )
        print(f"   Saved {len(suggestions)} suggestions")
        
        # Save to predictions table
        db_result = f"Skin: {prediction_result['skin_type']}, Acne: {prediction_result['acne_type']}"
        confidence = max(prediction_result['skin_confidence'], prediction_result['acne_confidence'])
        
        conn.execute(
            "INSERT INTO predictions (user_id, image_name, result, confidence, salon_name) VALUES (?, ?, ?, ?, ?)",
            (session['user_id'], filename, db_result, confidence, session['salon_name'])
        )
        
        conn.commit()
        conn.close()
        print("    Database save complete")

        # Store in session
        print("\n Storing in session...")
        session['customer_id'] = customer_id
        session['customer_name'] = customer_name
        session['analysis_id'] = analysis_id
        session['skin_type'] = prediction_result['skin_type']
        session['acne'] = prediction_result['acne_type']
        session['skin_confidence'] = prediction_result['skin_confidence']
        session['acne_confidence'] = prediction_result['acne_confidence']
        session['face_detected'] = prediction_result['face_detected']
        session.modified = True
        
        print(f"   Session stored: {list(session.keys())}")

        # Clean up
        if os.path.exists(filepath):
            os.remove(filepath)
            print("   Cleaned up file")
        
        print("\n SUCCESS! Redirecting to result page...")
        print(f"   Redirect URL: {url_for('ai.result')}")
        print("="*60 + "\n")
        
        return redirect(url_for('ai.result'))

    except Exception as e:
        print(f"\n EXCEPTION in analyzer:")
        print(f"   Type: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        import traceback
        traceback.print_exc()
        
        flash(f"An error occurred: {str(e)}", "error")
        
        if 'filepath' in locals() and os.path.exists(locals()['filepath']):
            try:
                os.remove(locals()['filepath'])
                print("   Cleaned up file")
            except:
                pass
        
        return render_template('analyzer.html')

       

@ai_bp.route('/result')
def result():
    if 'user_id' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('ai.login'))

    if 'analysis_id' not in session:
        flash('Please analyze skin first.', 'error')
        return redirect(url_for('ai.analyzer'))

    return render_template('result.html',
                           customer_name=session.get('customer_name', 'Customer'),
                           skin_type=session['skin_type'],
                           acne=session['acne'],
                           face_detected='yes' if session.get('face_detected', False) else 'no',
                           skin_confidence=session.get('skin_confidence', 0),
                           acne_confidence=session.get('acne_confidence', 0))


@ai_bp.route('/suggestions')
def suggestions():
    if 'user_id' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('ai.login'))

    if 'analysis_id' not in session:
        flash('Please analyze skin first.', 'error')
        return redirect(url_for('ai.analyzer'))

    # Get suggestions from database (as per ER diagram)
    conn = get_db_connection()
    suggestions_list = conn.execute(
        "SELECT suggestion_text FROM Suggestion WHERE analysis_id = ?",
        (session['analysis_id'],)
    ).fetchall()
    conn.close()

    suggestions = [s['suggestion_text'] for s in suggestions_list]

    return render_template('suggestions.html',
                           customer_name=session.get('customer_name', 'Customer'),
                           skin_type=session['skin_type'],
                           acne=session['acne'],
                           suggestions=suggestions,
                           face_detected='yes' if session.get('face_detected', False) else 'no',
                           skin_confidence=session.get('skin_confidence', 0),
                           acne_confidence=session.get('acne_confidence', 0))


@ai_bp.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if 'user_id' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('ai.login'))

    if 'analysis_id' not in session:
        flash('Please analyze skin first.', 'error')
        return redirect(url_for('ai.analyzer'))

    conn = get_db_connection()

    if request.method == 'POST':
        # Save quiz responses to database (as per ER diagram)
        try:
            responses_saved = []
            for key, value in request.form.items():
                if key.startswith('question_'):
                    question_id = int(key.split('_')[1])
                    option_id = int(value)
                    
                    # Insert Quiz_Response as per ER diagram
                    conn.execute(
                        '''
                        INSERT INTO Quiz_Response 
                        (customer_id, question_id, option_id, analysis_id, user_id)
                        VALUES (?, ?, ?, ?, ?)
                        ''',
                        (
                            session['customer_id'],
                            question_id,
                            option_id,
                            session['analysis_id'],
                            session['user_id']
                        )
                    )
                    responses_saved.append(question_id)
            
            conn.commit()
            print(f"Saved quiz responses for customer {session['customer_id']}")
            
            # IMPORTANT: Mark quiz as completed in session
            session['quiz_completed'] = True
            session['quiz_responses'] = responses_saved
            
            # Don't flash - redirect silently
            # flash('Quiz completed successfully!', 'success')
            
        except Exception as e:
            print(f"Error saving quiz responses: {e}")
            flash('Error saving quiz responses', 'error')
        finally:
            conn.close()
            
        return redirect(url_for('ai.suggestions'))

    # GET request - load quiz questions (as per ER diagram)
    questions = conn.execute(
        "SELECT * FROM Quiz_Question ORDER BY question_id"
    ).fetchall()
    
    quiz_data = []
    for question in questions:
        options = conn.execute(
            "SELECT * FROM Quiz_Options WHERE question_id = ?",
            (question['question_id'],)
        ).fetchall()
        quiz_data.append({
            'question': question,
            'options': options
        })
    
    conn.close()

    return render_template('quiz.html',
                           quiz_data=quiz_data,
                           skin_type=session['skin_type'],
                           acne=session['acne'],
                           customer_name=session.get('customer_name', 'Customer'))


@ai_bp.route('/feedback', methods=['GET', 'POST'])
def user_feedback():
    if 'user_id' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('ai.login'))

    # Clear old flash messages
    if request.method == 'GET':
        get_flashed_messages()

    if request.method == 'POST':
        try:
            message = request.form.get('message', '').strip()
            
            if not message:
                flash('Please enter your feedback message.', 'error')
                return render_template('user_feedback.html')
            
            conn = get_db_connection()
            # Store NULL for user_id to make it truly anonymous
            conn.execute(
                "INSERT INTO feedback (user_id, message) VALUES (NULL, ?)",
                (message,)
            )
            conn.commit()
            conn.close()
            
            print(f"Saved anonymous feedback")
            flash('Thank you for your feedback!', 'success')
            return redirect(url_for('ai.user_feedback'))
            
        except Exception as e:
            print(f"Feedback error: {e}")
            flash('Error saving feedback. Please try again.', 'error')
            return render_template('user_feedback.html')
    
    return render_template('user_feedback.html')

@ai_bp.route('/history')
def history():
    """View customer analysis history"""
    if 'user_id' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('ai.login'))
    
    conn = get_db_connection()
    # Get all analyses for this staff member's customers (as per ER diagram)
    analyses = conn.execute(
        '''
        SELECT c.customer_name, c.image_path, sa.skin_type, sa.acne_level, 
               sa.analysis_date, sa.analysis_id, sa.skin_confidence, sa.acne_confidence
        FROM Skin_Analysis sa
        JOIN Customer c ON sa.customer_id = c.customer_id
        WHERE c.user_id = ?
        ORDER BY sa.analysis_date DESC
        LIMIT 50
        ''',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    
    return render_template('history.html', analyses=analyses, username=session['username'])


# ---------- HELPER FUNCTIONS ----------

def generate_suggestions(skin_type, acne_level):
    """Generate personalized suggestions based on analysis"""
    suggestions = []
    
    # Skin type suggestions (handle both lowercase and capitalized)
    skin_type_lower = skin_type.lower()
    
    if 'oil' in skin_type_lower:
        suggestions.extend([
            "Use oil-free, non-comedogenic moisturizers to avoid clogging pores",
            "Wash face twice daily with a gentle foaming cleanser",
            "Use products with salicylic acid to control excess oil",
            "Avoid heavy creams and opt for gel-based products"
        ])
    elif 'dry' in skin_type_lower:
        suggestions.extend([
            "Use rich, hydrating moisturizers with hyaluronic acid or ceramides",
            "Avoid harsh soaps and hot water that strip natural oils",
            "Apply moisturizer immediately after cleansing while skin is damp",
            "Use a gentle, cream-based cleanser"
        ])
    elif 'combination' in skin_type_lower:
        suggestions.extend([
            "Use different products for different zones (T-zone vs cheeks)",
            "Apply lightweight moisturizer on oily areas, richer cream on dry areas",
            "Consider using blotting papers for T-zone during the day",
            "Balance your routine with products suitable for mixed skin"
        ])
    else:  # Normal
        suggestions.extend([
            "Maintain your current routine with gentle, balanced products",
            "Use a mild cleanser and lightweight moisturizer",
            "Focus on protection with SPF 30+ sunscreen daily"
        ])
    
    # Acne suggestions
    acne_lower = acne_level.lower()
    if 'severe' in acne_lower or 'very_severe' in acne_lower:
        suggestions.extend([
            "Consult a dermatologist for professional treatment options",
            "Consider prescription treatments like retinoids or antibiotics",
            "Use benzoyl peroxide or salicylic acid spot treatments",
            "Avoid touching, picking, or squeezing acne lesions"
        ])
    elif 'moderate' in acne_lower:
        suggestions.extend([
            "Use over-the-counter acne treatments with benzoyl peroxide",
            "Keep skin clean with twice-daily gentle cleansing",
            "Consider consulting a dermatologist if condition worsens",
            "Use non-comedogenic makeup and skincare products"
        ])
    elif 'mild' in acne_lower:
        suggestions.extend([
            "Keep skin clean with twice-daily gentle cleansing",
            "Use over-the-counter acne spot treatments",
            "Exfoliate gently 1-2 times per week",
            "Use non-comedogenic makeup and skincare products"
        ])
    else:  # No acne or clear
        suggestions.extend([
            "Maintain clear skin with consistent gentle cleansing",
            "Continue using non-comedogenic products",
            "Keep up with sun protection to prevent damage"
        ])
    
    # General suggestions
    suggestions.extend([
        "Drink plenty of water (8+ glasses daily) for skin hydration",
        "Get 7-9 hours of quality sleep each night",
        "Eat a balanced diet rich in fruits, vegetables, and omega-3s",
        "Change pillowcases regularly to reduce bacteria exposure"
    ])
    
    return suggestions