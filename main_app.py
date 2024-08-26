
from flask import Flask, render_template, request, session, redirect, url_for
from flask import Flask, render_template,request,session,url_for,redirect,flash, send_file
import random
import uuid
from flask_mysqldb import MySQL
import os
import bcrypt
from werkzeug.utils import secure_filename
import random
from datetime import datetime
from deep_translator import GoogleTranslator
import MySQLdb.cursors
from flask_mysqldb import MySQL

import requests
import io
from PIL import Image

# Define the API URL and your Hugging Face token
API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
TOKEN = "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"  # Make sure your token is valid


# from ultralytics import YOLO

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './static/uploads/'
app.config['RESULT_FOLDER'] = './static/results/'

app = Flask(__name__)

app.secret_key = 'Pob'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'img_generator'
mysql = MySQL(app)





@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        address = request.form['address']

        if not username or not email or not password:
            flash("Please fill in all required fields.", "error")
        else:
            # Check if the email is already taken
            cur = mysql.connection.cursor()
            cur.execute("SELECT COUNT(*) FROM users WHERE email = %s", (email,))
            count = cur.fetchone()[0]
            cur.close()

            if count > 0:
                flash("Email is already taken. Please choose a different one.", "error")
            else:
                # Hash the password before storing it
                cur = mysql.connection.cursor()
                cur.execute("INSERT INTO users (username, email, password, phone, address) VALUES (%s, %s, %s, %s, %s)",
                            (username, email, password, phone, address))
                mysql.connection.commit()
                cur.close()

                flash("Signup successful!", "success")
                return redirect(url_for('login'))

    return render_template('user_signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        # Check if the provided email matches a record in your database
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, email, password FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and user[2] == password:
            session['user_id'] = user[0]
            session['user_email'] = user[1]
            flash("You are logged in successfully!", "success")

            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password", "error")

    return render_template('user_login.html')





###########################################################





def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def allowed_file_upload(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

from flask import send_from_directory

# Constant file path
UPLOAD_FOLDER = "static/results"

@app.route('/download_file/<filename>')
def download_file(filename):
    # Ensure filename is secure and does not contain path traversal characters
    from werkzeug.utils import secure_filename
    filename = secure_filename(filename)

    # Construct the full file path
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    # Check if the file exists
    if os.path.exists(file_path):
        return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)
    else:
        # Return a 404 error if the file does not exist
        abort(404)


@app.route('/delete_data/<int:id>', methods=['POST'])
def delete_data(id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    try:
        # Execute the delete query with parameterized input
        cur.execute("DELETE FROM history WHERE id = %s", (id,))
        mysql.connection.commit()
    except Exception as e:
        print(f"Error: {e}")  # Log the error
        mysql.connection.rollback()  # Rollback in case of error
        abort(500)  # Return 500 Internal Server Error

    cur.close()
    return redirect(url_for('history'))

@app.route('/delete_data_admin/<int:id>', methods=['POST'])
def delete_data_admin(id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    try:
        # Execute the delete query with parameterized input
        cur.execute("DELETE FROM history WHERE id = %s", (id,))
        mysql.connection.commit()
    except Exception as e:
        print(f"Error: {e}")  # Log the error
        mysql.connection.rollback()  # Rollback in case of error
        abort(500)  # Return 500 Internal Server Error

    cur.close()
    return redirect(url_for('admin-view-history'))


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('main_dashboard.html')



# Set up headers with the token
headers = {"Authorization": f"Bearer {TOKEN}"}

def query(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    return response

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    user_email = session['user_email']
    userid = session.get('user_id')

    if session.get('user_id'):  # Check if the user is logged in
        if request.method == 'POST':
            text = request.form['txt']  # Get the text input from the form

            # Query the model with the desired prompt
            image_response = query({
                "inputs": text,
            })

            # Check if the response is successful
            if image_response.status_code == 200:
                try:
                    print("Code Run Successfully!")
                    # Open the image from the response content
                    image = Image.open(io.BytesIO(image_response.content))

                    # Generate a unique name for the image using UUID
                    image_name = f"{uuid.uuid4()}.jpeg"

                    # Define the directory where the image will be saved
                    save_dir = "static/results"
                    os.makedirs(save_dir, exist_ok=True)  # Ensure the directory exists

                    # Construct the full path for saving the image
                    save_path = os.path.join(save_dir, image_name)

                    # Save the image to the specified path
                    image.save(save_path)
                    print(f"Image saved as {save_path}")

                    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                    cur.execute("INSERT INTO history (text, image, user_id) VALUES (%s, %s, %s)", (text, image_name, userid))
                    mysql.connection.commit()  # Don't forget to commit the transaction
                    cur.close()

                    # Pass the image filename to the template for rendering
                    return render_template('dashboard.html', detection_result=image_name, user_email=user_email)
                except Exception as e:
                    print(f"Error opening or saving image: {e}")
            else:
                print(f"Request failed with status code {image_response.status_code}")
                print(image_response.text)  # Print the response text for debugging

            return render_template('dashboard.html', user_email=user_email)
        return render_template('dashboard.html', user_email=user_email)
    else:
        return redirect(url_for('login'))


class TextTranslator:
    def __init__(self):
        # Initialize the language codes dictionary
        self.language_codes = {
            'english': 'en',
            'hindi': 'hi',
            'marathi': 'mr',
            'french': 'fr',
            'spanish': 'es',
            'german': 'de',
            'chinese': 'zh-cn',
            'japanese': 'ja',
            # Add more languages as needed
        }

    def get_language_code(self, language_name):
        # Convert language name to its code
        return self.language_codes.get(language_name.lower(), None)

    def translate_to_english(self, text, src_language):
        # Translate the text
        translator = GoogleTranslator(source=src_language, target='en')
        translated_text = translator.translate(text)
        return translated_text


def main(src_language_name, text):
    # Create a TextTranslator instance
    translator = TextTranslator()

    # Convert the language name to its code
    src_language_code = translator.get_language_code(src_language_name)

    if src_language_code:
        try:
            # Translate the text to English
            translated_text = translator.translate_to_english(text, src_language_code)
            return translated_text
        except Exception as e:
            print(f"An error occurred during translation: {e}")
            return None
    else:
        print("Sorry, the language is not supported or incorrectly specified.")
        return None


@app.route('/dashboard_any', methods=['GET', 'POST'])
def dashboard_any():
    userid = session.get('user_id')
    if userid:  # Check if the user is logged in
        if request.method == 'POST':
            utext = request.form['txt']
            lang = request.form['lang']

            print( utext, lang)

            translated_text = main(lang, utext)
            if translated_text:
                print(f"Translated text: {translated_text}")

                # Query the model with the desired prompt
                try:
                    image_response = query({
                        "inputs": translated_text,
                    })


                    # Check if the response is successful
                    if image_response.status_code == 200:
                        try:
                            print("Code Run Successfully!")
                            # Open the image from the response content
                            image = Image.open(io.BytesIO(image_response.content))

                            # Generate a unique name for the image using UUID
                            image_name = f"{uuid.uuid4()}.jpeg"

                            # Define the directory where the image will be saved
                            save_dir = "static/results"
                            os.makedirs(save_dir, exist_ok=True)  # Ensure the directory exists

                            # Construct the full path for saving the image
                            save_path = os.path.join(save_dir, image_name)

                            # Save the image to the specified path
                            image.save(save_path)
                            print(f"Image saved as {save_path}")

                            # Save to the database
                            cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                            cur.execute("INSERT INTO history (text, image, user_id) VALUES (%s, %s, %s)",
                                        (utext, image_name, userid))
                            mysql.connection.commit()  # Don't forget to commit the transaction
                            cur.close()

                            # Pass the image filename to the template for rendering
                            return render_template('dashboard_any.html', detection_result=image_name)
                        except Exception as e:
                            print(f"Error opening or saving image: {e}")
                            return render_template('dashboard_any.html', error="Error processing the image.")
                    else:
                        print(f"Request failed with status code {image_response.status_code}")
                        print(image_response.text)  # Print the response text for debugging
                        return render_template('dashboard_any.html', error="Failed to generate image.")
                except Exception as e:
                    print(f"API request failed: {e}")
                    return render_template('dashboard_any.html', error="API request failed.")
            else:
                print("Sorry, the language is not supported or incorrectly specified.")
                return render_template('dashboard_any.html', error="Language not supported.")
        return render_template('dashboard_any.html')
    else:
        return redirect(url_for('login'))


ALLOWED_EXTENSIONS = {'wav', 'mp3'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_email', None)
    return redirect(url_for('login'))


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    error = None

    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']


        if username=="admin" and password=="star":
            flash("Admin are logged in successfully!")

            return redirect(url_for('admin_dashboard'))

        else:
            flash("Invalid username or password")

    return render_template('admin_login.html', error=error)


@app.route('/admin_dashboard')
def admin_dashboard():
    # Retrieve road requests with user IDs
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM users")
    profilelist = cur.fetchall()
    total_student = len(profilelist)
    cur.close()

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM history")
    h = cur.fetchall()
    total_his = len(h)
    cur.close()

    return render_template('admin_dashboard.html', total_student=total_student, total_his=total_his)


@app.route('/admin-view-user')
def adminviewemp():
    try:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM users")
        profilelist = cur.fetchall()
        cur.close()

        return render_template('admin_userlist.html', profilelist=profilelist, )
    except Exception as e:
        return f"Error: {str(e)}"


@app.route('/admin-view-history')
def adminviewhis():
    try:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM history")
        profilelist = cur.fetchall()
        cur.close()

        return render_template('admin_history.html', profilelist=profilelist, )
    except Exception as e:
        return f"Error: {str(e)}"


@app.route('/history')
def history():
    if session.get('user_id'):
        try:
            cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cur.execute("SELECT * FROM history")
            profilelist = cur.fetchall()
            cur.close()

            return render_template('history.html', all_data=profilelist, )
        except Exception as e:
            return f"Error: {str(e)}"
    else:
        return redirect(url_for('login'))


@app.route('/user_profile', methods=['GET', 'POST'])
def user_profile():
    # Ensure the user is logged in
    if 'user_id' not in session:
        flash("You need to log in first", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']

    if request.method == 'POST':
        # Get the form data
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        address = request.form['address']

        # Update the user's information in the database
        cur = mysql.connection.cursor()
        if password:
            cur.execute("""
                UPDATE users 
                SET username = %s, email = %s, password = %s, phone = %s, address = %s 
                WHERE id = %s
            """, (username, email, password, phone, address, user_id))
        else:
            cur.execute("""
                UPDATE users 
                SET username = %s, email = %s, phone = %s, address = %s 
                WHERE id = %s
            """, (username, email, phone, address, user_id))

        mysql.connection.commit()
        cur.close()

        # Update session data if email was changed
        session['user_email'] = email

        flash("Your profile has been updated successfully!", "success")
        return redirect(url_for('dashboard'))

    # If GET request, fetch the user's current data
    cur = mysql.connection.cursor()
    cur.execute("SELECT username, email, phone, address FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()

    return render_template('user_profile.html', user=user)











if __name__ == '__main__':
    app.run(debug=True)