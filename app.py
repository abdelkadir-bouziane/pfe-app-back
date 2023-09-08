from flask import Flask, send_file, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)

CORS(app)

image_folder = 'datasets'

def get_image_list(dataset):
    image_list = os.listdir(os.path.join(image_folder, dataset))
    image_list.sort()
    return image_list

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

@app.route('/image/<dataset>/<image_name>')
def get_image(dataset, image_name):
    image_path = os.path.join(image_folder, dataset, image_name)
    if os.path.isfile(image_path):
        return send_file(image_path, mimetype='image/*')
    else:
        return jsonify({"error": "Image not found"})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)