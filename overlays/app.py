from flask import Flask, render_template, request, send_file, redirect, url_for
from PIL import Image, ImageDraw
import io
import os
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
OVERLAY_FOLDER = "overlays"
OUTPUT_FOLDER = "static/processed"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OVERLAY_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def crop_to_circle(image):
    """Kadruje obraz do okrągłego kształtu."""
    size = min(image.size)
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    
    circular_image = Image.new("RGBA", (size, size))
    circular_image.paste(image.crop((0, 0, size, size)), (0, 0), mask)
    
    return circular_image

def apply_overlay(image, number):
    """Nakłada przezroczystą nakładkę na dolne 30% okręgu."""
    overlay_path = os.path.join(OVERLAY_FOLDER, f"{number}.png")
    
    if not os.path.exists(overlay_path):
        return image  # Jeśli brak nakładki, zwraca sam obraz
    
    overlay = Image.open(overlay_path).convert("RGBA")

    # Obliczenie wysokości nakładki jako 30% średnicy okręgu
    circle_diameter = image.width
    overlay_height = int(circle_diameter * 0.3)
    overlay_width = int(overlay.width * (overlay_height / overlay.height))  # Zachowanie proporcji
    
    overlay = overlay.resize((overlay_width, overlay_height))  # Skalowanie nakładki
    
    # Pozycjonowanie nakładki na dolnych 30% okręgu
    x_offset = (circle_diameter - overlay_width) // 2
    y_offset = circle_diameter - overlay_height

    image.paste(overlay, (x_offset, y_offset), overlay)
    
    return crop_to_circle(image)

@app.route("/", methods=["GET", "POST"])
def index():
    processed_image_url = None

    if request.method == "POST":
        file = request.files["image"]
        number = request.form["number"]
        
        if file and number.isdigit():
            image = Image.open(file).convert("RGBA")
            image = crop_to_circle(image)
            image = apply_overlay(image, number)
            
            # Zapisanie pliku z unikalną nazwą
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"output_{timestamp}.png"
            output_path = os.path.join(OUTPUT_FOLDER, filename)
            image.save(output_path, format="PNG")

            # Ustawienie URL do wyświetlenia na stronie
            processed_image_url = f"/{output_path}"

            return render_template("index.html", processed_image=processed_image_url, download_filename=filename)

    return render_template("index.html", processed_image=processed_image_url)

@app.route('/download/<filename>')
def download(filename):
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=filename)
    else:
        return "File not found", 404

if __name__ == "__main__":
    app.run(debug=True)
