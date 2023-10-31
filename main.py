import os
import time
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask.views import MethodView
from flask import Flask, render_template, request, flash, redirect, url_for, send_file
from PIL import Image, ImageFilter, ImageEnhance, ImageFont, ImageDraw
import requests

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Upload configurations
UPLOAD_FOLDER = 'static/img'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database configurations
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///images.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class EditedImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_path = db.Column(db.String(120), nullable=False)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

headers = {
    'pragma': 'no-cache',
    'cache-control': 'no-cache',
    'dnt': '1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
}

class HomePage(MethodView):
    def get(self):
        return render_template("index.html")

    def post(self):
        path = request.form.get("path")
        global user_image
        user_image = ProcessImage(path)
        user_image.save()
        global user_image_path
        user_image_path = f"{current_time}.png"
        global initial_image_width
        initial_image_width = user_image.width
        global initial_image_height
        initial_image_height = user_image.height
        return render_template("edit.html",
                               initial_image=user_image_path,
                               initial_width=initial_image_width,
                               initial_height=initial_image_height)


class EditPage(MethodView):

    def get(self):
        return render_template("edit.html")

    def post(self):

        # Receive add text values.
        insert_text = False
        try:
            text = request.form.get("text")
            if text != "":
                text_size = int(request.form.get("text_size"))
                text_color = str(request.form.get("text_color"))
                text_x = int((int(request.form.get("text_x")) / 100) * user_image.width)
                text_y = int((int(request.form.get("text_y")) / 100) * user_image.height)
                insert_text = True
        except:
            pass
        ####

        # Receive gradient values.
        insert_gradient = False
        gradient_color = str(request.form.get("gradient_color"))
        if gradient_color != "none":
            gradient_magnitude = float(request.form.get("gradient_magnitude"))
            insert_gradient = True
        ####

        # Receive filter values
        add_filter = False
        user_filter = str(request.form.get("user_filter"))
        if user_filter != "none":
            add_filter = True

        # receive cropping values
        crop_image = False
        checkbox_crop = request.form.get("opt-crop")
        if checkbox_crop == "crop":
            crop_image = True
            crop_left = int((int(request.form.get("crop_left")) / 100) * user_image.width)
            crop_top = int((int(request.form.get("crop_top")) / 100) * user_image.height)
            crop_right = int((int(request.form.get("crop_right")) / 100) * user_image.width)
            crop_bottom = int((int(request.form.get("crop_bottom")) / 100) * user_image.height)

        # Receive add image values.
        insert_image = False
        try:
            new_image_link = request.form.get("new_image_url")
            if new_image_link != "":
                new_image_x = int((int(request.form.get("new_image_x")) / 100) * user_image.width)
                new_image_y = int((int(request.form.get("new_image_y")) / 100) * user_image.height)
                shrink_perc = int(request.form.get("shrink_percentage"))
                insert_image = True
        except:
            pass
        ####

        # Receive rotation values.
        user_degree = int(request.form.get("user_degree"))
        main_user_degree = int(request.form.get("main_user_degree"))

        # Receive enhancement values.
        contrast_value = float(request.form.get("contrast_value"))
        print("Contrast:", contrast_value)
        color_value = float(request.form.get("color_value"))
        print("Color:", color_value)
        sharpness_value = float(request.form.get("sharpness_value"))
        print("Sharpness:", sharpness_value)

        user_image.modify_contrast(contrast_value=contrast_value)
        user_image.modify_color(color_value=color_value)
        user_image.modify_sharpness(sharpness_value=sharpness_value)

        # Checks the used filters and applies them before saving the image.
        if insert_image == True:
            user_image.add_image(new_image_url=new_image_link, x=new_image_x, y=new_image_y, shrink_perc=shrink_perc, user_degree=user_degree)

        if insert_text == True:
            user_image.add_text(x=text_x, y=text_y, text_input=text, text_size=text_size, text_color=text_color)

        if insert_gradient == True:
            user_image.add_gradient(gradient_magnitude=gradient_magnitude, color=gradient_color)

        if main_user_degree != 0:
            user_image.rotate_image(degree=main_user_degree)

        if crop_image == True:
            user_image.crop_image(left=crop_left, top=crop_top, right=crop_right, bottom=crop_bottom)

        if add_filter == True:
            user_image.add_filter(filter=user_filter)

        # Generates a new image.
        user_image.save()
        final_user_image_path = f"{current_time}.png"

        return render_template("edit.html",
                               initial_image=user_image_path,
                               result=True,
                               final_image=final_user_image_path,
                               initial_width=initial_image_width,
                               initial_height=initial_image_height)


class ProcessImage:

    def __init__(self, img_path):
        self.img_path = img_path
        try:
            if img_path == "random":
                img_path = "https://picsum.photos/1100/500"
                self.image = Image.open(requests.get(img_path, stream=True, headers=headers).raw)
            else:
                self.image = Image.open(requests.get(img_path, stream=True, headers=headers).raw)
        except:
            print("Görsel hatası.")
            print("Mevcut konum:", os.getcwd())
            self.image = Image.open("static/404.jpg")
        self.width, self.height = self.image.size

    def add_text(self, x=10, y=10, text_input="", text_size="24", text_color="red"):
        self.x = x
        self.y = y
        self.text = text_input
        self.text_size = text_size
        self.text_color = text_color
        try:
            font = ImageFont.truetype("static/arial.ttf", size=text_size)
        except:
            font = ImageFont.load_default()
        draw = ImageDraw.Draw(self.image)
        draw.text((x, y), text_input, fill=text_color, font=font, align="right")

    def add_gradient(self, gradient_magnitude=1, color="black"):
        self.gradient_magnitude = gradient_magnitude
        self.color = color
        if color == "none":
            pass
        else:
            colors = {"black": 0, "red": 1500, "yellow": 100000, "orange": 150000}
            color = colors[color]
            im = self.image
            if im.mode != 'RGBA':
                im = im.convert('RGBA')
            width, height = im.size
            gradient = Image.new('L', (width, 1), color=0xFF)
            for x in range(width):
                gradient.putpixel((x, 0), int(255 * (1 - gradient_magnitude * float(x) / width))
                                  )
            alpha = gradient.resize(im.size)
            black_im = Image.new('RGBA', (width, height), color=color)
            black_im.putalpha(alpha)
            gradient_im = Image.alpha_composite(im, black_im)
            self.image = gradient_im

    def add_image(self, new_image_url, x=10, y=10, shrink_perc=80, user_degree=0):
        self.new_image_url = new_image_url
        self.x = x
        self.y = y
        self.shrink_perc = shrink_perc
        self.user_degree = user_degree
        shrink_perc = shrink_perc / 100
        try:
            new_image = Image.open(requests.get(new_image_url, stream=True, headers=headers).raw)
        except:
            new_image = Image.open("static/404.jpg")
        if user_degree != 0:
            new_image = new_image.rotate(-1 * user_degree, expand=1)
        new_image.thumbnail((new_image.width * shrink_perc, new_image.width * shrink_perc))
        position = (x, y)
        try:
            self.image.paste(new_image, position, new_image)
        except:
            print("Error loading the new image.")

    def add_filter(self, filter):
        self.filter = filter
        if filter == "grayscale":
            self.image.convert("CMYK")
            self.image = self.image.convert("L")
        if filter == "blur":
            self.image = self.image.filter(ImageFilter.BoxBlur(2))

    def modify_contrast(self, contrast_value):
        self.contrast_value = contrast_value
        contrast = ImageEnhance.Contrast(self.image)
        self.image = contrast.enhance(contrast_value)

    def modify_color(self, color_value):
        self.color_value = color_value
        color = ImageEnhance.Color(self.image)
        self.image = color.enhance(color_value)

    def modify_sharpness(self, sharpness_value):
        self.sharpness_value = sharpness_value
        sharpness = ImageEnhance.Sharpness(self.image)
        self.image = sharpness.enhance(sharpness_value)

    def rotate_image(self, degree):
        self.degree = degree
        rotated_img = self.image.rotate(-1 * degree, expand=1)
        self.image = rotated_img

    def crop_image(self, left, top, right, bottom):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
        try:
            cropped_image = self.image.crop((left, top, right, bottom))
            self.image = cropped_image
        except:
            print("Error cropping the image.")

    def save(self):
        get_time = time.localtime()
        global current_time
        current_time = time.strftime("%y-%m-%d--%H-%M-%S", get_time)
        os.chdir("static")
        os.chdir("img")
        global edited_img
        edited_img = self.image.save(f"{current_time}.png")
        os.chdir("..")
        os.chdir("..")


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        photo = Photo(image_data=file.read())
        db.session.add(photo)
        db.session.commit()

        global user_image
        user_image = ProcessImage(file)
        user_image.save()

        global user_image_path
        user_image_path = f"{current_time}.png"

        global initial_image_width
        initial_image_width = user_image.width

        global initial_image_height
        initial_image_height = user_image.height

        return render_template("edit.html", initial_image=user_image_path, initial_width=initial_image_width, initial_height=initial_image_height)


@app.route('/download', methods=['GET'])
def download_file():
    global current_time  # Make sure 'current_time' is accessible here.
    file_path = os.path.join('static/img', f"{current_time}.png")

    # Check if the edited image file exists
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=f"{current_time}.png")
    else:
        flash('The edited image file does not exist.')
        return redirect(url_for('edit_page'))


app.add_url_rule("/", view_func=HomePage.as_view("home_page"))
app.add_url_rule("/edit", view_func=EditPage.as_view("edit_page"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=8080)

