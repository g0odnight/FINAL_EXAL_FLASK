from flask import Flask, flash, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import current_user
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from PIL import Image



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'secret_key'
UPLOAD_FOLDER = 'static/uploads/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('groups', lazy=True))
    photo = db.Column(db.String(255))

    def __init__(self, name, description, user_id, photo=None):
        self.name = name
        self.description = description
        self.user_id = user_id
        self.photo = photo
        
class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(255))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id', ondelete='CASCADE'), nullable=True)

    def __init__(self, name, date, description, group_id):
        self.name = name
        self.date = date
        self.description = description
        self.group_id = group_id


with app.app_context():
     db.create_all()

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['password2']
        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match')
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error='Please enter valid email address')
        user = User(name=name, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        flash('Registered successfully!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('groups'))
        else:
            return render_template('login.html', error='Invalid email or password')
    return render_template('login.html', current_user=current_user)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/groups', methods=['GET', 'POST'])
def groups():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Create the upload folder if it doesn't exist
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo and allowed_file(photo.filename):
                filename = secure_filename(photo.filename)
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                photo_path = os.path.join('uploads', filename)
                # Open the saved image file using PIL
                img = Image.open(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                # Set the maximum image width and height
                max_size = (300, 300)
                img.thumbnail(max_size)
                # Save the resized image file
                img.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            else:
                flash('Invalid file format. Only png, jpg, jpeg, and gif files are allowed.', 'error')
                photo_path = None
        else:
            photo_path = None
        group = Group(name=name, description=description, user_id=session['user_id'], photo=photo_path)
        db.session.add(group)
        db.session.commit()
    groups = Group.query.filter_by(user_id=session['user_id']).all()
    return render_template('categories.html', groups=groups)

@app.route('/groups/<int:group_id>/edit', methods=['GET', 'POST'])
def edit_group(group_id):
    group = Group.query.get_or_404(group_id)

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo and allowed_file(photo.filename):
                filename = secure_filename(photo.filename)
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                photo_path = os.path.join('uploads', filename)
                # Open the saved image file using PIL
                img = Image.open(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                # Set the maximum image width and height
                max_size = (800, 800)
                img.thumbnail(max_size)
                # Save the resized image file
                img.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                group.photo = photo_path
            else:
                flash('Invalid file format. Only png, jpg, jpeg, and gif files are allowed.', 'error')
        group.name = name
        group.description = description
        db.session.commit()
        flash('Group information has been updated.', 'success')
        return redirect(url_for('groups', group_id=group_id))
    
    return render_template('edit_category.html', group=group)



@app.route('/groups/<int:group_id>/delete', methods=['POST'])
def delete_group(group_id):
    group = Group.query.get(group_id)
    if not group:
        abort(404)
    db.session.delete(group)
    db.session.commit()
    flash(f'{group.name} has been deleted!', 'success')
    return redirect(url_for('groups'))


@app.route('/groups/<int:group_id>/bills', methods=['GET', 'POST'])
def bills(group_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        description = request.form['description']
        date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        name = request.form['name']
        bill = Bill(description=description, date=date, name=name, group_id=group_id)
        db.session.add(bill)
        db.session.commit()
    group = Group.query.get_or_404(group_id)
    bills = Bill.query.filter_by(group_id=group_id).all()
    return render_template('notes.html', group=group, bills=bills)

@app.route('/groups/<int:group_id>/bills/<int:bill_id>/edit', methods=['GET', 'POST'])
def edit_bill(group_id, bill_id):
    bill = Bill.query.filter_by(id=bill_id, group_id=group_id).first_or_404()
    if not bill:
        abort(404)
    if request.method == 'POST':
        bill.description = request.form['description']
        bill.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        bill.name = request.form['name']
        db.session.commit()
        flash('The bill has been updated.', 'success')
        return redirect(url_for('bills', group_id=group_id))
    return render_template('edit_note.html', group_id=group_id, bill=bill)

@app.route('/groups/<int:group_id>/bills/<int:bill_id>/delete', methods=['POST'])
def delete_group_bill(group_id, bill_id):
    bill = Bill.query.filter_by(id=bill_id, group_id=group_id).first_or_404()
    if not bill:
        abort(403)
    db.session.delete(bill)
    db.session.commit()
    flash('The bill has been deleted.', 'success')
    return redirect(url_for('bills', group_id=bill.group_id))

@app.route('/search')
def search():
    query = request.args.get('q')
    groups = Group.query.filter(Group.name.ilike(f'%{query}%')).all()
    return render_template('search_results.html', groups=groups, query=query)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
