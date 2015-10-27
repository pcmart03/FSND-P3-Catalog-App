import os
# flask imports
from flask import Flask, render_template, request, send_from_directory
from flask import redirect, jsonify, url_for, flash, make_response
from flask import session as login_session
from werkzeug import secure_filename


# sqlalchemy imports
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, User, Category, Photo, Item

# imports for oauth
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import random
import string
import httplib2
import json
import requests

UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'gif'])


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

CLIENT_ID = json.loads(
    open('google-client-secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog App"


engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# HELPER FUNCTIONS
# function returns all categories for the navbar
def get_categories():
    return session.query(Category).all()


def get_category(category_id):
    return session.query(Category).filter_by(id=category_id).one()


def get_images(category_id):
    return session.query(Photo).filter_by(category_id=category_id).all()


# grabs all items in category
def get_items(category_id):
    return session.query(Item).filter_by(category_id=category_id).all()


# Joins the Item and Photo tables. It makes alt_text available
def item_join():
    return session.query(Item, Photo).outerjoin(
        Photo, Item.photo_name == Photo.filename)


# returns item from joined table
def get_display_item(item_id):
    return item_join().filter_by(id=item_id).one()


# queries the item table directly for updating
def get_item(item_id):
    return session.query(Item).filter_by(id=item_id).one()


# checks to make sure file extension is in the ALLOWED_EXTENSIONS list
def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


# check items to see if image is active.
def image_in_use(filename):
    items_with_image = session.query(Item).filter_by(photo_name=filename).all()
    if items_with_image:
        return True


# User helper functionsn
def create_user(login_session):
    new_user = User(name=login_session['username'],
                    email=login_session['email'],
                    picture=login_session['picture'])
    session.add(new_user)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def get_user_info(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def get_user_id(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# Views
@app.route('/index.html')
@app.route('/')
def homepage():
    page_title = 'Catalog App'
    categories = get_categories()
    items = item_join().order_by(desc('Item.id')).limit(8)
    return render_template('homepage.html', categories=categories,
                           title=page_title, items=items)


@app.route('/login')
def login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s" % access_token

    app_id = json.loads(
        open('fb-client-secrets.json', 'r').read())['web']['app_id']
    app_secret = json.loads(
        open('fb-client-secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Get user info from API
    userinfo_url = "http://graph.facebook.com/v2.4/me"
    # strip expire tag from access token
    token = result.split("&")[0]
    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    stored_token = token.split('=')[1]
    login_session['access_token'] = stored_token

    # Get user picture
    url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, "GET")[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # Check to see if user exists
    user_id = get_user_id(login_session['email'])
    if not user_id:
        user_id = create_user(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    code = request.data

    try:
        oauth_flow = flow_from_clientsecrets('google-client-secrets.json',
                                             scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # Abort if there is a problem with the access token
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('User is already connected'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    login_session['provider'] = 'google'

    user_id = get_user_id(data["email"])
    if not user_id:
        user_id = create_user(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ''' " style = "width: 300px; height: 300px;border-radius:
         150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '''
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


@app.route('/gdisconnect')
def gdisconnect():
    # check to make sure user is disconnected
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, "GET")[0]

    if result['status'] == '200':
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = make_response(json.dumps('successfully disconnected'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(
            json.dumps('Failed to revoke token for given user'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/logout')
def logout():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['credentials']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('homepage'))
    else:
        flash("You were not logged in")
        return redirect(url_for('homepage'))


@app.route('/<int:category_id>/')
def show_category(category_id):
    categories = get_categories()
    category = get_category(category_id)
    page_title = category.name
    items = item_join().filter_by(category_id=category_id).all()
    return render_template('category-page.html', category_id=category_id,
                           category=category, categories=categories,
                           title=page_title, items=items)


@app.route('/upload-photo/', methods=['GET', 'POST'])
def upload_photo():
    page_title = "Upload Photo"
    categories = get_categories()

    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            alt = request.form['alt']
            category = request.form['category']
            new_photo = Photo(filename=filename, alt_text=alt,
                              category_id=category)
            session.add(new_photo)
            session.commit()
            flash('Photo saved')
            return redirect(url_for('homepage'))
        else:
            flash("Invalid file type")
            return redirect(url_for('upload_photo'))
    else:
        return render_template('add-photo.html', categories=categories,
                               title=page_title)


@app.route('/uploads/<filename>')
def uploaded_photo(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/delete-photo', methods=['GET', 'POST'])
def delete_photo():
    images = session.query(Photo).all()
    categories = get_categories()
    if request.method == 'POST':
        filename = request.form['photo']
        if image_in_use(filename):
            flash("Image is being used by an active item.")
            return redirect(url_for('delete_photo'))
        else:
            deleted_photo = session.query(Photo).filter_by(
                filename=filename).one()
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            session.delete(deleted_photo)
            session.commit()
            os.remove(file_path)
            flash('Image deleted')
            return redirect(url_for('homepage'))
    else:
        return render_template('delete-photo.html', categories=categories,
                               photos=images)


@app.route('/<int:category_id>/<int:item_id>/')
def show_item(category_id, item_id):
    item = get_display_item(item_id)
    categories = get_categories()
    return render_template('show-item.html', category_id=category_id,
                           item_id=item_id, title=item.Item.name,
                           categories=categories, item=item)


@app.route('/<int:category_id>/add-item/', methods=['GET', 'POST'])
def add_item(category_id):
    page_title = 'Add New Item'
    categories = get_categories()
    category = get_category(category_id)
    images = get_images(category_id)
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        image = request.form['photo']
        description = request.form['description']
        new_item = Item(name=name, description=description, price=price,
                        category_id=category_id, photo_name=image)
        session.add(new_item)
        session.commit()
        flash('Item added')
        return redirect(url_for('show_category', category_id=category_id))
    else:
        return render_template('add-item.html', category_id=category_id,
                               category=category, categories=categories,
                               photos=images, title=page_title)


@app.route('/<int:category_id>/<int:item_id>/edit/', methods=['GET', 'POST'])
def edit_item(category_id, item_id):
    edited_item = get_item(item_id)
    categories = get_categories()
    photos = get_images(category_id)
    if request.method == 'POST':
        edited_item.name = request.form['name']
        edited_item.price = request.form['price']
        edited_item.description = request.form['description']
        edited_item.photo_name = request.form['photo']
        session.add(edited_item)
        session.commit()
        flash("Your changes have been saved")
        return redirect(url_for('show_category', category_id=category_id))
    else:
        return render_template('edit-item.html', category_id=category_id,
                               item_id=item_id, item=edited_item,
                               categories=categories, photos=photos)


@app.route('/<int:category_id>/<int:item_id>/delete/', methods=['GET', 'POST'])
def delete_item(category_id, item_id):
    deleted_item = get_item(item_id)
    categories = get_categories()
    if request.method == 'POST':
        session.delete(deleted_item)
        session.commit()
        flash("Item deleted")
        return redirect(url_for('show_category', category_id=category_id))
    else:
        return render_template('delete-item.html', category_id=category_id,
                               item_id=item_id, item=deleted_item,
                               categories=categories)


# API End Points
# JSON
@app.route('/category/JSON')
def all_categories_json():
    categories = get_categories()
    return jsonify(Categories=[i.serialize for i in categories])


@app.route('/category/<int:category_id>/JSON')
def category_json(category_id):
    items = get_items(category_id)
    return jsonify(Items=[i.serialize for i in items])


@app.route('/item/<int:item_id>/JSON')
def item_json(item_id, category_id):
    item = get_item(item_id)
    return jsonify(Item=item.serialize)

if __name__ == '__main__':
    app.secret_key = 'really_lame_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
