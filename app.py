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

def process_image(image, number, add_blue_background=False, facebook_mode=False):
    """Przetwarza obraz z nakładką, opcjonalnym niebieskim podkładem, i opcją dla Facebooka."""
    # Ensure image is square by cropping to smallest dimension
    size = min(image.size)
    square_image = image.crop(((image.width - size) // 2, 
                              (image.height - size) // 2, 
                              (image.width + size) // 2, 
                              (image.height + size) // 2))
    
    # For Facebook, we'll use the square image but not crop to circle
    if facebook_mode:
        processed_image = square_image.copy()
    else:
        processed_image = crop_to_circle(square_image.copy())
    
    # Apply blue background if requested
    if add_blue_background:
        # Create a semi-transparent blue layer for the lower part of the image
        width, height = processed_image.width, processed_image.height
        blue_bg_height = int(height * 0.3)
        blue_bg = Image.new("RGBA", (width, blue_bg_height), (100, 150, 230, 128))  # Lighter blue with 50% transparency
        
        # Position the blue background at the bottom 30% of the image
        y_offset = height - blue_bg_height
        
        # Create a mask for the blue layer
        if facebook_mode:
            # For Facebook, use a rectangular mask
            mask = Image.new("L", (width, blue_bg_height), 255)
        else:
            # For circle mode, use a mask that matches the bottom of the circle
            mask = Image.new("L", (width, blue_bg_height), 0)
            draw = ImageDraw.Draw(mask)
            draw.rectangle((0, 0, width, blue_bg_height), fill=255)
        
        # Paste blue background
        processed_image.paste(blue_bg, (0, y_offset), mask)
    
    # Now apply the overlay with number
    overlay_path = os.path.join(OVERLAY_FOLDER, f"{number}.png")
    
    if not os.path.exists(overlay_path):
        # If specific overlay doesn't exist, create a default overlay with the number
        width, height = processed_image.width, processed_image.height
        overlay_height = int(height * 0.3)
        overlay = Image.new("RGBA", (width, overlay_height), (0, 0, 0, 0))  # Transparent background
        draw = ImageDraw.Draw(overlay)
        # Draw number text in the center
        font_size = int(width * 0.2)  # Proportional font size
        from PIL import ImageFont
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()
        
        draw.text((width//2, overlay_height//2), str(number), fill=(255, 255, 255, 255), 
                 font=font, anchor="mm")  # White text, centered
        overlay_width = width
    else:
        overlay = Image.open(overlay_path).convert("RGBA")
        # Calculate overlay dimensions
        overlay_height = int(processed_image.height * 0.3)
        overlay_width = int(overlay.width * (overlay_height / overlay.height))  # Preserve aspect ratio
        overlay = overlay.resize((overlay_width, overlay_height))  # Scale overlay
    
    # Position overlay at the bottom 30% of image
    x_offset = (processed_image.width - overlay_width) // 2
    y_offset = processed_image.height - overlay_height
    
    # Paste overlay
    processed_image.paste(overlay, (x_offset, y_offset), overlay)
    
    return processed_image

@app.route("/", methods=["GET", "POST"])
def index():
    processed_image_url = None
    error = None
    form_data = {
        'blue_background_checked': False,
        'facebook_checked': False
    }

    if request.method == "POST":
        # Check if the post request has the file part
        if 'image' not in request.files:
            error = "Nie znaleziono pliku"
            return render_template("index.html", error=error, **form_data)
            
        file = request.files["image"]
        if file.filename == '':
            error = "Nie wybrano pliku"
            return render_template("index.html", error=error, **form_data)
            
        number = request.form["number"]
        
        # Get checkbox values
        add_blue_background = 'blue_background' in request.form
        facebook_mode = 'facebook' in request.form
        
        # Update form data
        form_data['blue_background_checked'] = add_blue_background
        form_data['facebook_checked'] = facebook_mode
        
        # Validate number is between 1-999
        if not number.isdigit() or not (1 <= int(number) <= 999):
            error = "Numer Socio musi być liczbą między 1 a 999"
            return render_template("index.html", error=error, **form_data)
            
        try:
            image = Image.open(file).convert("RGBA")
            processed_image = process_image(image, number, add_blue_background, facebook_mode)
            
            # Save file with unique name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"output_{timestamp}.png"
            output_path = os.path.join(OUTPUT_FOLDER, filename)
            processed_image.save(output_path, format="PNG")

            # Set URL to display on page
            processed_image_url = f"/static/processed/{filename}"

            return render_template("index.html", 
                                  processed_image=processed_image_url, 
                                  download_filename=filename,
                                  **form_data)
        except Exception as e:
            error = f"Błąd przetwarzania obrazu: {str(e)}"
            return render_template("index.html", error=error, **form_data)

    return render_template("index.html", processed_image=processed_image_url, **form_data)

@app.route('/download/<filename>')
def download(filename):
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=filename)
    else:
        return "File not found", 404

if __name__ == "__main__":
    app.run(debug=True)
