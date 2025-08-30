# --- We need to import our tools first! ---
# We are adding render_template to serve our HTML file.
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import pytesseract
from PIL import Image
import re

# --- IMPORTANT: Tell Python where to find Tesseract ---
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# --- Initialize our Flask Web App ---
# We specify the 'templates' folder for our HTML files.
app = Flask(__name__, template_folder='.')
CORS(app)


# --- All our data processing functions remain the same ---

# This function is now RE-ENABLED and will be used to read uploaded images.
def read_text_from_image(image_file):
    try:
        # We open the image directly from the uploaded file data.
        image = Image.open(image_file)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        # A general catch for any errors during image processing.
        print(f"Error processing image: {e}")
        return ""

def format_ingredients(text):
    cleaned_text = text.lower()
    keyword = "ingredients:"
    start_pos = cleaned_text.find(keyword)
    if start_pos != -1:
        ingredients_section = cleaned_text[start_pos + len(keyword):]
    else:
        ingredients_section = cleaned_text
    ingredient_list = ingredients_section.split(',')
    final_list = [item.strip().replace('.', '') for item in ingredient_list if item.strip()]
    return final_list

def calculate_health_score(ingredient_list):
    bad_ingredients = ["sugar", "palm oil", "refined wheat flour (maida)", "invert sugar syrup", "fructose", "molasses"]
    good_ingredients = ["whole wheat", "oats", "protein", "fiber", "vitamins", "minerals"]
    score = 5
    found_bad_ingredients = []
    found_good_ingredients = []
    total_ingredients = len(ingredient_list)

    for index, ingredient in enumerate(ingredient_list):
        for bad_item in bad_ingredients:
            if bad_item in ingredient:
                if index < total_ingredients / 3:
                    score -= 3
                elif index < 2 * total_ingredients / 3:
                    score -= 2
                else:
                    score -= 1
                found_bad_ingredients.append(ingredient)
                break 

    for ingredient in ingredient_list:
        for good_item in good_ingredients:
            if good_item in ingredient:
                score += 1
                found_good_ingredients.append(ingredient)
                break

    final_score = max(1, min(10, score))
    return final_score, found_bad_ingredients, found_good_ingredients


# --- This route serves our main HTML page ---
@app.route('/')
def home():
    return render_template('index.html')


# --- UPGRADED Main API Endpoint ---
# This endpoint now accepts an image file upload.
@app.route('/analyze', methods=['POST'])
def analyze_ingredients():
    # Check if an image file was included in the request.
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    
    # Check if the user submitted an empty file part.
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        # We now use our image reading function with the uploaded file.
        raw_text = read_text_from_image(file)
        
        if not raw_text:
            return jsonify({'error': 'Could not extract text from image. Please try a clearer picture.'}), 400

        formatted_list = format_ingredients(raw_text)
        
        if formatted_list:
            final_score, culprits, goodies = calculate_health_score(formatted_list)
            unique_culprits = list(set(culprits))
            unique_goodies = list(set(goodies))

            # We package our results into a JSON object to send to the frontend.
            return jsonify({
                'score': final_score,
                'unhealthy_ingredients': unique_culprits,
                'healthy_ingredients': unique_goodies,
                'full_list': formatted_list
            })
        else:
            return jsonify({'error': 'Could not process the extracted ingredients'}), 400

# --- This makes the server run when you execute `python main.py` ---
if __name__ == '__main__':
    app.run(debug=True)

