from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DATABASE = 'database.db'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# تحديد بيانات الأدمن
ADMIN_EMAIL = 'sandy12@gmail.com'
ADMIN_PASSWORD = '123456'

# إنشاء الاتصال بقاعدة البيانات
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        # إنشاء جدول المستخدمين إذا لم يكن موجودًا
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            password TEXT NOT NULL
        )''')
        
        # إنشاء جدول الدورات إذا لم يكن موجودًا
        conn.execute('''CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            image_path TEXT NOT NULL,
            video_link TEXT  -- حقل رابط الفيديو
        )''')

        # إضافة عمود video_link إذا لم يكن موجودًا بالفعل
        try:
            conn.execute("ALTER TABLE courses ADD COLUMN video_link TEXT;")
        except sqlite3.OperationalError:
            pass  # إذا كان العمود موجودًا بالفعل فلن يحدث شيء

# عرض الصفحة الرئيسية
@app.route('/')
def home():
    return redirect(url_for('login'))

# تسجيل المستخدم
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO users (name, email, phone, password) VALUES (?, ?, ?, ?)",
                    (name, email, phone, password)
                )
                conn.commit()
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash('Email already exists. Please try a different email.', 'error')

    return render_template('register.html')

# تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # تحقق إذا كان المستخدم هو الأدمن
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session['user_id'] = 1  # يمكن استخدام 1 كمؤشر للأدمن
            session['user_name'] = 'Admin'
            session['is_admin'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        
        # تحقق من المستخدم العادي في قاعدة البيانات
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE email = ? AND password = ?", (email, password)
            )
            user = cursor.fetchone()
            if user:
                session['user_id'] = user[0]
                session['user_name'] = user[1]
                session['is_admin'] = False
                flash('Login successful!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Invalid email or password.', 'error')

    return render_template('login.html')

# عرض لوحة التحكم للمستخدم العادي
@app.route('/index')
def index():
    if 'user_id' in session:
        return render_template('index.html', name=session.get('user_name', 'Guest'))
    return redirect(url_for('login'))

# عرض لوحة تحكم الأدمن
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' in session and session.get('is_admin'):
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, email, phone FROM users")
            users = cursor.fetchall()

            cursor.execute("SELECT id, name, description, image_path, video_link FROM courses")
            courses = cursor.fetchall()

        return render_template('admin_dashboard.html', users=users, courses=courses, name=session.get('user_name', 'Admin'))

    return redirect(url_for('login'))

# إضافة مستخدم جديد من قبل الأدمن
@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if 'user_id' in session and session.get('is_admin'):
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            phone = request.form['phone']
            password = request.form['password']

            with sqlite3.connect(DATABASE) as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "INSERT INTO users (name, email, phone, password) VALUES (?, ?, ?, ?)",
                        (name, email, phone, password)
                    )
                    conn.commit()
                    flash('User added successfully!', 'success')
                    return redirect(url_for('admin_dashboard'))
                except sqlite3.IntegrityError:
                    flash('Email already exists. Please try a different email.', 'error')

        return render_template('add_user.html')
    return redirect(url_for('login'))

# إضافة دورة جديدة
@app.route('/add_course', methods=['GET', 'POST'])
def add_course():
    if 'user_id' in session and session.get('is_admin'):
        if request.method == 'POST':
            name = request.form['course_name']
            description = request.form['course_description']
            image = request.files['course_image']
            video_link = request.form['course_video']  

            if image:
                filename = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = f'{UPLOAD_FOLDER}/{filename}'

                # إضافة الدورة إلى قاعدة البيانات
                with sqlite3.connect(DATABASE) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO courses (name, description, image_path, video_link) VALUES (?, ?, ?, ?)",
                        (name, description, image_path, video_link)  # إضافة رابط الفيديو
                    )
                    conn.commit()

                flash('Course added successfully!', 'success')
                return redirect(url_for('admin_dashboard'))

        return render_template('add_course.html')
    return redirect(url_for('login'))

# حذف مستخدم
@app.route('/delete_user/<int:user_id>', methods=['GET', 'POST'])
def delete_user(user_id):
    if 'user_id' in session and session.get('is_admin'):
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            flash('User deleted successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('login'))

# حذف دورة
@app.route('/delete_course/<int:course_id>', methods=['POST'])
def delete_course(course_id):
    if 'user_id' in session and session.get('is_admin'):
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM courses WHERE id = ?", (course_id,))
            conn.commit()
            flash('Course deleted successfully!', 'success')
        return redirect(url_for('courses'))
    return redirect(url_for('login'))

# تسجيل الخروج
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/project', methods=['GET','POST'])
def project():
    if 'user_id' in session:
        try:
            with sqlite3.connect(DATABASE) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, description, image_path, video_link FROM courses")
                courses = cursor.fetchall()

            if not courses:
                flash("No courses found!", "info")

            # Render the correct template (project.html)
            return render_template('project.html', courses=courses)

        except Exception as e:
            print("Error fetching courses:", e)
            flash("An error occurred while fetching courses.", "error")
            return redirect(url_for('index'))  # إعادة التوجيه إلى الصفحة الرئيسية للمستخدم

    flash("You need to log in first.", "error")
    return redirect(url_for('login'))



@app.route('/food_menu')
def food_menu():
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row  # يجعل الصفوف تُرجع كقواميس
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, description, image_path, video_link FROM courses")
        courses = cursor.fetchall()  # قائمة من القواميس

    return render_template('food_menu.html', courses=courses)

@app.route('/courses', methods=['GET'])
def courses():
    if 'user_id' in session and session.get('is_admin'):
        try:
            with sqlite3.connect(DATABASE) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, description, image_path, video_link FROM courses")
                courses = cursor.fetchall()

            if not courses:
                flash("No courses found!", "info")  # عرض رسالة إذا لم توجد دورات

            return render_template('courses.html', courses=courses)

        except Exception as e:
            print("Error fetching courses:", e)
            flash("An error occurred while fetching courses.", "error")
            return redirect(url_for('admin_dashboard'))

    flash("You are not authorized to view this page.", "error")
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
