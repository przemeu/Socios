from flask import Flask, render_template, request, send_file
from PIL import Image, ImageDraw
import io
import os

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
OVERLAY_FOLDER = "overlays"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OVERLAY_FOLDER, exist_ok=True)

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
    if request.method == "POST":
        file = request.files["image"]
        number = request.form["number"]
        
        if file and number.isdigit():
            image = Image.open(file).convert("RGBA")
            image = crop_to_circle(image)
            image = apply_overlay(image, number)
            
            # Zapisanie do pamięci i wysłanie pliku
            img_io = io.BytesIO()
            image.save(img_io, format="PNG")
            img_io.seek(0)
            
            return send_file(img_io, mimetype="image/png", as_attachment=True, download_name="output.png")
            
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
