from flask import Flask, render_template, request, send_from_directory, url_for
from PIL import Image, ImageDraw, ImageFont
import os
import io
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['PROCESSED_FOLDER'] = 'static/processed'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

def process_image(image_file, number, facebook=False, blue_background=False):
    image = Image.open(image_file).convert("RGBA")

    if blue_background:
        # Create a semi-transparent brighter blue background before cropping
        bg = Image.new('RGBA', image.size, (0, 102, 255, 128))  # 50% transparent
        image = Image.alpha_composite(bg, image)

    # Crop to square from center
    width, height = image.size
    min_dim = min(width, height)
    left = (width - min_dim) // 2
    top = (height - min_dim) // 2
    right = left + min_dim
    bottom = top + min_dim
    image = image.crop((left, top, right, bottom))

    if not facebook:
        # Create a circular mask
        mask = Image.new('L', image.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + image.size, fill=255)
        image.putalpha(mask)

    overlay_path = f"overlays/{number}.png"
    if os.path.exists(overlay_path):
        overlay = Image.open(overlay_path).convert("RGBA").resize(image.size)
        image = Image.alpha_composite(image, overlay)
    else:
        draw = ImageDraw.Draw(image)
        font_size = image.size[0] // 4
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        text = str(number)
        text_width, text_height = draw.textsize(text, font=font)
        position = ((image.size[0] - text_width) // 2, image.size[1] - text_height - 10)
        draw.text(position, text, fill=(255, 255, 255, 255), font=font)

    output_filename = f"processed_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    output_path = os.path.join(app.config['PROCESSED_FOLDER'], output_filename)
    image.save(output_path)
    return output_filename

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'image' not in request.files or request.files['image'].filename == '':
            return render_template('index.html', error='Brak pliku obrazu.')

        image_file = request.files['image']
        number = request.form.get('number')
        facebook = request.form.get('facebook') == 'on'
        blue_background = request.form.get('blue_background') == 'on'

        try:
            number = int(number)
            if not (1 <= number <= 999):
                raise ValueError("Numer poza zakresem")
        except:
            return render_template('index.html', error='Numer Socio musi być liczbą od 1 do 999.')

        try:
            filename = process_image(image_file, number, facebook=facebook, blue_background=blue_background)
            processed_image_url = url_for('static', filename=f"processed/{filename}")
            return render_template('index.html', processed_image=processed_image_url, download_filename=filename)
        except Exception as e:
            return render_template('index.html', error=f'Błąd przetwarzania obrazu: {str(e)}')

    return render_template('index.html')

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
