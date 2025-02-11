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
    """Nakłada przezroczystą nakładkę, a następnie ponownie kadruje obraz do okręgu."""
    overlay_path = os.path.join(OVERLAY_FOLDER, f"{number}.png")
    
    if not os.path.exists(overlay_path):
        return image  # Jeśli brak nakładki, zwraca sam obraz
    
    overlay = Image.open(overlay_path).convert("RGBA")
    overlay = overlay.resize((image.width // 3, image.width // 3))  # Dopasowanie rozmiaru
    
    # Umieszczenie nakładki w dolnym rogu
    x_offset = image.width - overlay.width - 10
    y_offset = image.height - overlay.height - 10
    
    image.paste(overlay, (x_offset, y_offset), overlay)
    
    # Ponowne kadrowanie do okręgu po nałożeniu nakładki
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
