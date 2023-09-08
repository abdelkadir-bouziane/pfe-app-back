from flask import Flask, send_file, jsonify
from flask_cors import CORS
from PIL import Image
from werkzeug.routing import BaseConverter
import io
import os

app = Flask(__name__)

CORS(app)

class BooleanConverter(BaseConverter):
    def to_python(self, value):
        if value.lower() in ['true', '1', 'yes']:
            return True
        elif value.lower() in ['false', '0', 'no']:
            return False
        else:
            return None  # Return None for invalid values
    def to_url(self, value):
        return str(value)

app.url_map.converters['bool'] = BooleanConverter

image_folder = 'datasets'

def get_image_list(dataset):
    image_list = os.listdir(os.path.join(image_folder, dataset, "images"))
    image_list.sort()
    return image_list

def fix_image_orientation(img):
    try:
        # Check if the image has an EXIF orientation tag
        if hasattr(img, '_getexif'):
            exif = img._getexif()
            if exif is not None:
                orientation = exif.get(0x0112)
                if orientation is not None:
                    # Rotate/transpose the image based on the orientation value
                    if orientation == 3:
                        img = img.transpose(Image.ROTATE_180)
                    elif orientation == 6:
                        img = img.transpose(Image.ROTATE_270)
                    elif orientation == 8:
                        img = img.transpose(Image.ROTATE_90)
    except Exception as e:
        pass  # Handle any exceptions gracefully
    return img

def resize_image(image_url):
    # Open the original image using Pillow
    original_image = Image.open(image_url)
    # Fix orientation (if it's an issue)
    original_image = fix_image_orientation(original_image)
    # Resize the image to a smaller dimension (e.g., 400x400)
    resized_image = original_image.resize((200, 200), Image.BILINEAR)
    # Compress the image with a specified quality (0-100, higher is better quality)
    resized_image = resized_image.convert('RGB')
    output = io.BytesIO()
    resized_image.save(output, format='JPEG', quality=50)
    output.seek(0)
    # Return the resized and compressed image
    return output

@app.route('/images/<dataset>/<int:page>/<int:nbImagesPerPage>')
def get_images(dataset, page, nbImagesPerPage):
    image_list = get_image_list(dataset)
    total_images = len(image_list)
    start = nbImagesPerPage*(page-1)
    end = min(nbImagesPerPage*page, total_images)
    if start >= total_images:
        return jsonify(error="Start index out of range"), 400
    sliced_images = image_list[start:end]
    return jsonify(images=sliced_images, total=total_images)

@app.route('/image/<dataset>/<image_name>/<bool:compressed>')
def get_image(dataset, image_name, compressed):
    image_path = os.path.join(image_folder, dataset, "images", image_name)
    if os.path.isfile(image_path):
        if(compressed):
            return send_file(resize_image(image_path), mimetype='image/*')
        else:
            return send_file(image_path, mimetype='image/*')
    else:
        return jsonify({"error": "Image not found"})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)