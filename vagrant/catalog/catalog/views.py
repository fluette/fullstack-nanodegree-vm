"""Defines the views to be presented to the user."""
import os
from flask import render_template, request, redirect, url_for
from flask import send_from_directory
from werkzeug import secure_filename
from sqlalchemy import desc, literal
from sqlalchemy.orm.exc import NoResultFound

from catalog import app, session, ALLOWED_EXTENSIONS
from database_setup import Category, Item


def allowed_file(filename):
    """Check if the filename has one of the allowed extensions."""
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def delete_image(filename):
    """Delete an item image file from the filesystem."""
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    except OSError:
        print "Error deleting image file %s" % filename


@app.route('/')
@app.route('/catalog/')
def show_homepage():
    """Show the homepage diplaying the categories and latest items."""
    categories = session.query(Category).all()
    latest_items = session.query(Item).order_by(desc(Item.id))[0:10]
    return render_template('homepage.html',
                           categories=categories,
                           latest_items=latest_items)


@app.route('/catalog/<category_name>/items/')
def show_items(category_name):
    """Show items belonging to a specified category."""
    try:
        category = session.query(Category).filter_by(name=category_name).one()
    except NoResultFound:
        # TODO Make this a flash message
        return "The category '%s' does not exist." % category_name

    categories = session.query(Category).all()
    items = session.query(Item).filter_by(category=category).all()
    return render_template('items.html',
                           categories=categories,
                           category=category,
                           items=items)


@app.route('/catalog/<category_name>/<item_name>/')
def show_item(category_name, item_name):
    """Show details of a particular item belonging to a specified category."""
    try:
        category = session.query(Category).filter_by(name=category_name).one()
    except NoResultFound:
        # TODO Make this a flash message on homepage.
        return "The category '%s' does not exist." % category_name

    try:
        item = session.query(Item).filter_by(name=item_name).one()
    except NoResultFound:
        # TODO Make this a flash message on homepage.
        return "The item '%s' does not exist." % item_name

    categories = session.query(Category).all()
    return render_template('item.html',
                           categories=categories,
                           category=category,
                           item=item)


@app.route('/catalog/new/', methods=['GET', 'POST'])
def create_item():
    """Allow users to create a new item in the catalog."""
    if request.method == 'POST':
        if request.form['name'] == "items":
            # Can't have an item called "items" as this is a route.
            # TODO Replace with flash message.
            return "Can't have an item called 'items'."

        # Enforce rule that item names are unique
        qry = session.query(Item).filter(Item.name == request.form['name'])
        already_exists = session.query(literal(True)).filter(qry.exists()).scalar()
        if already_exists is True:
            # TODO Replace with flash message.
            return ("There is already an animal with the name '%s'"
                    % request.form['name'])

        category = (session.query(Category)
                    .filter_by(name=request.form['category']).one())
        new_item = Item(category=category,
                        name=request.form['name'],
                        description=request.form['description'])

        # Process optional item image
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            if os.path.isdir(app.config['UPLOAD_FOLDER']) is False:
                os.mkdir(app.config['UPLOAD_FOLDER'])
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_item.image_filename = filename

        session.add(new_item)
        session.commit()
        return redirect(url_for('show_homepage'))
    else:
        categories = session.query(Category).all()
        return render_template('new_item.html',
                               categories=categories)


@app.route('/catalog/<item_name>/edit/', methods=['GET', 'POST'])
def edit_item(item_name):
    """Edit the details of the specified item."""
    try:
        item = session.query(Item).filter_by(name=item_name).one()
    except NoResultFound:
        # TODO Make this a flash message on homepage.
        return "The item '%s' does not exist." % item_name

    if request.method == 'POST':
        form_category = (session.query(Category)
                         .filter_by(name=request.form['category']).one())

        if form_category != item.category:
            item.category = form_category

        if request.form['name']:
            item.name = request.form['name']
        item.description = request.form['description']

        # Process optional item image
        file = request.files['file']
        if file and allowed_file(file.filename):
            if item.image_filename:
                delete_image(item.image_filename)
            filename = secure_filename(file.filename)
            if os.path.isdir(app.config['UPLOAD_FOLDER']) is False:
                os.mkdir(app.config['UPLOAD_FOLDER'])
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            item.image_filename = filename

        elif request.form['delete_image'] == 'delete':
            if item.image_filename:
                delete_image(item.image_filename)
                item.image_filename = None

        session.add(item)
        session.commit()

        return redirect(url_for('show_items', category_name=form_category.name))
    else:
        categories = session.query(Category).all()
        return render_template('edit_item.html',
                               categories=categories,
                               item=item)


@app.route('/catalog/<item_name>/delete/', methods=['GET','POST'])
def delete_item(item_name):
    """Delete a specified item from the database."""
    try:
        item = session.query(Item).filter_by(name=item_name).one()
    except NoResultFound:
        # TODO Make this a flash message on homepage.
        return "The item '%s' does not exist." % item_name

    if request.method == 'POST':
        if item.image_filename:
            delete_image(item.image_filename)
        session.delete(item)
        session.commit()
        category = session.query(Category).filter_by(id=item.category_id).one()
        return redirect(url_for('show_items', category_name=category.name))
    else:
        categories = session.query(Category).all()
        return render_template('delete_item.html',
                               categories=categories,
                               item=item)


@app.route('/item_images/<filename>')
def show_item_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)