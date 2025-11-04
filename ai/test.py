
import os
import sys

# Make sure we're in the right directory
current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)

# Now import predict
from predict import ai_predict

print("="*60)
print("TESTING AI PREDICTION WITH IMAGE")
print("="*60)

# Get image path from user
image_path = input("\nEnter path to your test image (or full path): ").strip().strip('"').strip("'")

if not image_path:
    print("No image provided. Exiting.")
    sys.exit(0)

# If relative path, make it absolute
if not os.path.isabs(image_path):
    image_path = os.path.abspath(image_path)

if not os.path.exists(image_path):
    print(f"❌ File not found: {image_path}")
    print(f"\nTried looking at: {image_path}")
    print(f"Current directory: {os.getcwd()}")
    sys.exit(1)

print(f"\n✅ File found: {image_path}")
print(f"   Size: {os.path.getsize(image_path)} bytes")

print("\n" + "="*60)
print("RUNNING PREDICTION...")
print("="*60 + "\n")

# Run prediction
result = ai_predict(image_path)

print("\n" + "="*60)
print("FINAL RESULT:")
print("="*60)

for key, value in result.items():
    print(f"{key:20s}: {value}")

print("="*60)

# Analyze result
if "error" in result:
    print("\n❌ PREDICTION RETURNED ERROR")
    print(f"Error message: {result['error']}")
    
    if "animal" in result['error'].lower() or "fur" in result['error'].lower():
        print("\n-> This would set session['show_animal_error'] = True")
        print("-> User would see: 'Animal Image Detected' error card")
    elif "face" in result['error'].lower():
        print("\n-> This would set session['show_face_error'] = True")
        print("-> User would see: 'No Face Detected' error card")
    else:
        print("\n-> This would show as flash error message")
        print(f"-> Message: {result['error']}")
else:
    print("\n✅ PREDICTION SUCCESSFUL")
    print(f"\nSkin Type: {result.get('skin_type', 'N/A')}")
    print(f"Acne Level: {result.get('acne_type', 'N/A')}")
    print(f"Face Detected: {result.get('face_detected', False)}")
    print(f"Skin Confidence: {result.get('skin_confidence', 0):.2%}")
    print(f"Acne Confidence: {result.get('acne_confidence', 0):.2%}")
    
    if not result.get('face_detected', False):
        print("\n⚠️  WARNING: No face detected but results returned anyway")
        print("-> Web interface would show results with 'no face' warning")

print("\n" + "="*60)
print("WHAT THIS MEANS FOR YOUR WEB APP:")
print("="*60)

if "error" in result:
    print("\n1. User uploads image")
    print("2. ai_predict() returns error")
    print("3. Flask route should:")
    print("   - Delete uploaded file")
    print("   - Set session error flag")
    print("   - Redirect to analyzer page")
    print("4. Analyzer page should show error card")
    print("\nIf you're not seeing the error card, check:")
    print("   - Is session being set correctly?")
    print("   - Is the redirect happening?")
    print("   - Does analyzer.html check for session flags?")
else:
    print("\n1. User uploads image")
    print("2. ai_predict() returns successful result")
    print("3. Flask route should:")
    print("   - Save to database")
    print("   - Store in session")
    print("   - Delete uploaded file")
    print("   - Redirect to /result page")
    print("4. Result page should display findings")
    print("\nIf you're not seeing results, check:")
    print("   - Are database saves working?")
    print("   - Is session being stored?")
    print("   - Is redirect to /result happening?")
    print("   - Does result.html exist and work?")