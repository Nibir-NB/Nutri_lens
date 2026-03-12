# -------- Import Libraries --------
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import pytesseract
from PIL import Image
import joblib
import numpy as np
from scipy.sparse import hstack
import re
import cv2


# -------- Load ML Model --------
model = joblib.load("model/food_health_model.pkl")
vectorizer = joblib.load("model/tfidf_vectorizer.pkl")


# -------- NutriScore Meaning --------
grade_meaning = {
    "a": "Very Healthy",
    "b": "Healthy",
    "c": "Moderate",
    "d": "Unhealthy",
    "e": "Very Unhealthy"
}


# -------- Prediction Function --------
def predict_food_health(ingredients, nutrition_values):

    ingredient_features = vectorizer.transform([ingredients])

    nutrition_array = np.array(nutrition_values).reshape(1, -1)

    combined_features = hstack([ingredient_features, nutrition_array])

    prediction = model.predict(combined_features)[0]

    meaning = grade_meaning[prediction]

    return prediction.upper(), meaning


# -------- Tesseract Path --------
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


# -------- Initialize Flask --------
app = Flask(__name__, template_folder='.')
CORS(app)


# -------- OCR with Image Preprocessing --------
def read_text_from_image(image_file):

    try:

        image = np.array(Image.open(image_file))

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)

        thresh = cv2.threshold(gray,150,255,cv2.THRESH_BINARY)[1]

        text = pytesseract.image_to_string(thresh)

        return text.lower()

    except Exception as e:

        print("OCR Error:", e)
        return ""


# -------- Ingredient Extraction --------
def format_ingredients(text):

    cleaned_text = text.lower()

    keyword = "ingredients"
    start_pos = cleaned_text.find(keyword)

    if start_pos != -1:
        ingredients_section = cleaned_text[start_pos + len(keyword):]
    else:
        ingredients_section = cleaned_text

    ingredient_list = ingredients_section.split(',')

    final_list = [
        item.strip().replace('.', '')
        for item in ingredient_list
        if item.strip()
    ]

    return final_list


# -------- Nutrition Extraction --------
def extract_nutrition_values(text):

    def find_value(keyword):
        match = re.search(rf"{keyword}\s*[:\-]?\s*(\d+\.?\d*)", text)
        return float(match.group(1)) if match else 0

    energy = find_value("energy")
    fat = find_value("fat")
    saturated_fat = find_value("saturated")
    carbs = find_value("carbohydrate")
    sugar = find_value("sugar")
    fiber = find_value("fiber")
    protein = find_value("protein")
    salt = find_value("salt")

    return [
        energy,
        fat,
        saturated_fat,
        carbs,
        sugar,
        fiber,
        protein,
        salt
    ]


# -------- Home Page --------
@app.route('/')
def home():
    return render_template("index.html")


# -------- Main API Endpoint --------
@app.route('/analyze', methods=['POST'])
def analyze_ingredients():

    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    raw_text = read_text_from_image(file)

    if not raw_text:
        return jsonify({'error': 'OCR failed'}), 400


    formatted_list = format_ingredients(raw_text)

    ingredients_text = ", ".join(formatted_list)

    nutrition_values = extract_nutrition_values(raw_text)

    grade, meaning = predict_food_health(ingredients_text, nutrition_values)

    return jsonify({
        "grade": grade,
        "health_level": meaning,
        "ingredients_detected": formatted_list,
        "nutrition_values": nutrition_values
    })


# -------- Run Server --------
if __name__ == '__main__':
    app.run(debug=True)