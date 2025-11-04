import cv2
import numpy as np
from keras.models import load_model
from keras.applications.mobilenet_v2 import preprocess_input
import os

# Load models
try:
    BASE_DIR = os.path.dirname(__file__)
    skin_model = load_model(os.path.join(BASE_DIR, 'model', 'my_skin_model.h5'))
    acne_model = load_model(os.path.join(BASE_DIR, 'model', 'my_acne_model.h5'))
    print("Models loaded successfully")
except Exception as e:
    print(f"Error loading models: {e}")
    skin_model = None
    acne_model = None

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

skin_classes = ['dry', 'normal', 'oil']
acne_classes = ['no_acne', 'mild', 'moderate', 'severe', 'very_severe']

def is_likely_skin_image(image_region):
    try:
        hsv = cv2.cvtColor(image_region, cv2.COLOR_RGB2HSV)
        lower_skin = np.array([0, 10, 60], dtype=np.uint8)
        upper_skin = np.array([40, 255, 255], dtype=np.uint8)
        skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)
        skin_pixels = np.sum(skin_mask > 0)
        total_pixels = skin_mask.shape[0] * skin_mask.shape[1]
        skin_percentage = skin_pixels / total_pixels
        return skin_percentage > 0.08
    except Exception:
        return False

def detect_animal_features(image):
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        return laplacian_var > 1000
    except:
        return False

def ai_predict(image_path):
    """
    Predict skin type and acne level from facial image.
    EMERGENCY FIX: Very conservative thresholds to avoid false positives
    """
    try:
        if skin_model is None or acne_model is None:
            return {"error": "Models not loaded properly"}

        # Read image
        image = cv2.imread(image_path)
        if image is None:
            return {"error": "Could not read image file"}

        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Detect faces
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.05,
            minNeighbors=3,
            minSize=(30, 30)
        )
        face_detected = len(faces) > 0

        # Select region of interest
        if face_detected:
            areas = [w * h for (x, y, w, h) in faces]
            x, y, w, h = faces[np.argmax(areas)]
            pad = int(0.2 * min(w, h))
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(image.shape[1], x + w + pad)
            y2 = min(image.shape[0], y + h + pad)
            region = image_rgb[y1:y2, x1:x2]
        else:
            h, w, _ = image.shape
            if h < 100 or w < 100:
                return {"error": "Image too small for analysis"}
            
            ch, cw = int(h * 0.6), int(w * 0.6)
            sh, sw = (h - ch) // 2, (w - cw) // 2
            region = image_rgb[sh:sh+ch, sw:sw+cw]
            
            if not is_likely_skin_image(region):
                if detect_animal_features(region):
                    return {"error": "Animal or non-human face detected. Please upload a human facial image."}
                
                return {
                    "skin_type": "unknown",
                    "skin_confidence": 0.0,
                    "acne_type": "unknown",
                    "acne_confidence": 0.0,
                    "face_detected": False,
                    "message": "No clear face detected. Please ensure your face is visible, well-lit, and looking at the camera."
                }

        # Preprocess region
        region_resized = cv2.resize(region, (224, 224))
        region_normalized = region_resized.astype(np.float32) / 255.0
        region_preprocessed = preprocess_input(region_normalized * 255.0)
        region_expanded = np.expand_dims(region_preprocessed, axis=0)

        # Make predictions
        skin_preds = skin_model.predict(region_expanded, verbose=0)[0]
        acne_preds = acne_model.predict(region_expanded, verbose=0)[0]

        # 🔥 EMERGENCY FIX: Print raw predictions for debugging
        print(f"\n🔍 Raw Model Predictions:")
        print(f"   Skin confidences: {dict(zip(skin_classes, [f'{p:.2%}' for p in skin_preds]))}")
        print(f"   Acne confidences: {dict(zip(acne_classes, [f'{p:.2%}' for p in acne_preds]))}")

        # Get initial predictions
        skin_conf = float(np.max(skin_preds))
        acne_conf = float(np.max(acne_preds))
        skin_type = skin_classes[np.argmax(skin_preds)]
        acne_type = acne_classes[np.argmax(acne_preds)]

        print(f"\n📊 Initial Predictions (before filtering):")
        print(f"   Skin: {skin_type} ({skin_conf:.2%})")
        print(f"   Acne: {acne_type} ({acne_conf:.2%})")

        # 🔥 CRITICAL FIX: Very conservative thresholds
        
        # Skin type threshold
        if skin_conf < 0.45:
            skin_type = "uncertain"
            print(f"   ⚠️ Skin confidence too low, marked as uncertain")

        # 🔥 ACNE FIX: Default to no_acne unless VERY confident
        no_acne_idx = acne_classes.index('no_acne')
        no_acne_confidence = acne_preds[no_acne_idx]
        
        print(f"\n🔍 Acne Analysis:")
        print(f"   Predicted class: {acne_type}")
        print(f"   Predicted confidence: {acne_conf:.2%}")
        print(f"   'no_acne' confidence: {no_acne_confidence:.2%}")
        
        # Strategy: Only predict acne if:
        # 1. Confidence is VERY high (>70%) AND
        # 2. no_acne confidence is low (<30%)
        
        if acne_type != 'no_acne':
            # Model thinks there's acne
            if acne_conf < 0.70:
                # Not confident enough
                print(f"   ⚠️ Acne confidence {acne_conf:.2%} < 70%, defaulting to no_acne")
                acne_type = 'no_acne'
                acne_conf = max(no_acne_confidence, 0.5)
            elif no_acne_confidence > 0.30:
                # Model is confused - no_acne also has decent score
                print(f"   ⚠️ Conflicting predictions (no_acne: {no_acne_confidence:.2%}), defaulting to no_acne")
                acne_type = 'no_acne'
                acne_conf = no_acne_confidence
            else:
                print(f"   ✅ High confidence acne detection: {acne_type} ({acne_conf:.2%})")
        else:
            # Model predicts no_acne
            if no_acne_confidence < 0.40:
                # Model is not confident about no_acne either
                # Check if any acne class has very high confidence (>75%)
                acne_only_preds = acne_preds[1:]  # Exclude no_acne
                max_acne_conf = np.max(acne_only_preds)
                if max_acne_conf > 0.75:
                    # There's a very confident acne prediction
                    acne_type = acne_classes[np.argmax(acne_only_preds) + 1]
                    acne_conf = max_acne_conf
                    print(f"   🔄 Overriding to {acne_type} ({acne_conf:.2%}) due to very high confidence")
                else:
                    print(f"   ⚠️ Low no_acne confidence but no strong acne signal, keeping no_acne")
                    acne_conf = 0.5
            else:
                print(f"   ✅ Clear skin detected: no_acne ({no_acne_confidence:.2%})")
                acne_conf = no_acne_confidence

        # 🔥 If no face detected, be EXTREMELY conservative
        if not face_detected:
            if acne_conf < 0.80:
                print(f"   ⚠️ No face detected + confidence {acne_conf:.2%} < 80%, forcing no_acne")
                acne_type = 'no_acne'
                acne_conf = 0.5

        print(f"\n✅ FINAL Predictions:")
        print(f"   Skin: {skin_type} ({skin_conf:.2%})")
        print(f"   Acne: {acne_type} ({acne_conf:.2%})")
        print(f"   Face detected: {face_detected}")

        return {
            "skin_type": skin_type,
            "skin_confidence": skin_conf,
            "acne_type": acne_type,
            "acne_confidence": acne_conf,
            "face_detected": face_detected
        }

    except Exception as e:
        print(f"❌ Prediction error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": f"Unexpected error during prediction: {str(e)}"}


def test_prediction(image_path):
    """Test function"""
    print(f"\n{'='*60}")
    print(f"Testing: {image_path}")
    print(f"{'='*60}")
    result = ai_predict(image_path)
    print(f"\n📋 Final Results:")
    for key, value in result.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.2%}" if value <= 1.0 else f"   {key}: {value}")
        else:
            print(f"   {key}: {value}")
    print(f"{'='*60}\n")
    return result