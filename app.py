from flask import Flask, send_file, jsonify, request, render_template, make_response
from flask_cors import CORS
from PIL import Image
from werkzeug.routing import BaseConverter
import io
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'

# create a python dictionary for your models d = {<key>: <value>, <key>: <value>, ..., <key>: <value>}
dictOfModels = {}
# create a list of keys to use them in the select part of the html code
listOfKeys = []

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

datasets_folder = 'datasets'


def get_image_list(dataset):
    image_list = os.listdir(os.path.join(datasets_folder, dataset, "images"))
    image_list.sort()
    return image_list


def get_filtred_image_list(dataset, classIdsList):
    image_list = os.listdir(os.path.join(datasets_folder, dataset, 'images'))
    annot_list = os.listdir(os.path.join(datasets_folder, dataset, 'annotations'))
    image_list.sort()
    filtered_images = []
    for image_name in image_list:
        # get the iamge name without extension
        image_name_without_extension = os.path.splitext(image_name)[0]
        # get the annotation with the same name
        annot_name = image_name_without_extension + '.txt'
        if annot_name in annot_list:
            # get annotation path
            annot_path = os.path.join(datasets_folder, dataset, 'annotations', annot_name)
            # read annotation file
            with open(annot_path, 'r') as annot_file:
                lines = annot_file.readlines()
                for line in lines:
                    # get the annotation id
                    class_id = line.strip().split()[0]
                    if class_id in classIdsList:
                        filtered_images.append(image_name)
                        break
    return filtered_images


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


def allowed_file(filename):
    # Check if the file has a valid extension (e.g., image formats)
    allowed_extensions = {'jpg', 'jpeg', 'png', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_prediction(img_bytes, model, overleap, confience):
    img = Image.open(io.BytesIO(img_bytes))
    results = model(img, confience, overleap, size=640)
    return results


@app.route('/images/<dataset>/<int:page>/<int:nbImagesPerPage>')
def get_images(dataset, page, nbImagesPerPage):
    # Get the 'classIds' query parameter
    classIds = request.args.get('classIds')
    if classIds is not None and classIds != "":
        image_list = get_filtred_image_list(dataset, classIds.split(','))
    else:
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
    image_path = os.path.join(datasets_folder, dataset, "images", image_name)
    if os.path.isfile(image_path):
        if(compressed):
            return send_file(resize_image(image_path), mimetype='image/*')
        else:
            return send_file(image_path, mimetype='image/*')
    else:
        return jsonify({"error": "Image not found"})


@app.route('/test')
def get_test():
    return jsonify({"error": "Image not found"})


# get method
@app.route('/', methods=['GET'])
def index():
    # in the select we will have each key of the list in option (name of model file).
    return render_template("index.html", len=len(listOfKeys), listOfKeys=listOfKeys)


@app.route('/predict', methods=['POST'])
def predict():
    # Get input values from the request
    image_file = request.files['image'].read()
    model_name = request.form['model_name']
    overlap_value = float(request.form['overlap_value'])
    confidence_value = float(request.form['confidence_value'])

    # Check if the image_file is valid
    if image_file and allowed_file(image_file.filename):
        # Save the uploaded file
        filename = os.path.join(UPLOAD_FOLDER, image_file.filename)
        image_file.save(filename)

        # Perform object detection using your model
        # You will need to use the appropriate object detection code here.
        # This code will depend on the framework and model you are using.

        # Example code (assuming TensorFlow and a model with a detection function)
        img_bytes = image_file.read()  # or you can use: image = cv2.imread(filename)
        detections = get_prediction(img_bytes, dictOfModels[model_name], overlap_value, confidence_value)

        # updates results.imgs with boxes and labels
        detections.render()

        # Clean up the uploaded image
        os.remove(filename)

        # encoding the resulting image and return it
        response = None
        for img in detections.ims:
            RGB_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            im_arr = cv2.imencode('.jpg', RGB_img) [1]
            response = make_response(im_arr.tobytes())
            response.headers['Content-Type'] = 'image/jpeg'
        return response

    return jsonify({"error": "Invalid file or parameters"})


if __name__ == '__main__':
    print('Uploading models ...')
    models_directory = 'models'
    print('getting all models files from {models_directory} ...')
    for root, dirs, files in os.walk(models_directory):
        for file in files:
            if ".pt" in file:
                # example: file = "model_1.pt"
                # the path of each model: os.path.join(r, file) models/model_1.pt
                model_name = os.path.splitext(file)[0]  # model_1
                model_path = os.path.join(root, file)  # models/model_1.pt

                print(f'Loading model {model_name} with path {model_path}...')
                dictOfModels[model_name] = torch.hub.load('ultralytics/yolov5', 'custom', path=model_path, force_reload=True)
                # you would obtain: dictOfModels = {"model_1" : model1 , "model_2" : model2, ....}

                for key in dictOfModels:
                    listOfKeys.append(key)  # put all the keys in the listOfKeys ["model_1", "model_2"]
                print(model_name)

    # app.run(host="0.0.0.0", port=8080, debug=True)
