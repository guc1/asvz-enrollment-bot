# app/routes.py

from flask import Blueprint, redirect, url_for, render_template, flash, request, jsonify
from flask_dance.contrib.google import google
from flask_login import login_user, logout_user, current_user, login_required
from app.extensions import db
from app.models import User, OAuth, Enrollment
import logging
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

# Create a Blueprint for the main routes
main = Blueprint('main', __name__)

@main.route('/')
def home():
    logging.debug("Rendering home page")
    return render_template('home.html')

@main.route('/after_login')
def after_login():
    if not google.authorized:
        logging.debug("User is not authorized, redirecting to Google login")
        return redirect(url_for("google.login"))

    # Fetch user info from Google
    resp = google.get("/oauth2/v2/userinfo")
    logging.debug(f"Google response status: {resp.status_code}")

    if not resp.ok:
        logging.error(f"Failed to fetch user info from Google: {resp.text}")
        flash("Failed to fetch user info from Google.", "error")
        return redirect(url_for("main.home"))

    user_info = resp.json()
    logging.debug(f"Google user info: {user_info}")

    google_id = user_info.get("id")
    email = user_info.get("email")
    name = user_info.get("name")

    if not google_id or not email:
        logging.error("Incomplete user information received from Google.")
        flash("Incomplete user information received from Google.", "error")
        return redirect(url_for("main.home"))

    try:
        # Check if the user exists by google_id
        user = User.query.filter_by(google_id=google_id).first()

        if not user:
            # If not found by google_id, check by email to link accounts
            user = User.query.filter_by(email=email).first()
            if user:
                logging.debug(f"User found by email: {user.email}, linking Google account.")
                user.google_id = google_id
            else:
                # Create a new user if they don't exist
                logging.debug(f"No user found with google_id={google_id} or email={email}, creating new user.")
                user = User(google_id=google_id, name=name, email=email)
                db.session.add(user)

        db.session.commit()
        logging.debug(f"User {user.email} added/updated in the database.")
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"Error updating user in the database: {e}", exc_info=True)
        flash("An error occurred while updating your information.", "error")
        return redirect(url_for("main.home"))

    # Log the user in
    login_user(user)
    logging.debug(f"User {user.email} logged in successfully.")

    # Set the provider name explicitly
    provider = 'google'

    # Manually store the OAuth token in the OAuth table
    try:
        if google.token:
            # Check if an OAuth record exists for this user and provider
            oauth = OAuth.query.filter_by(provider=provider, user_id=user.id).first()
            if oauth:
                logging.debug(f"Updating existing OAuth token for user {user.email}")
                oauth.token = google.token
            else:
                logging.debug(f"Creating new OAuth token for user {user.email}")
                oauth = OAuth(provider=provider, token=google.token, user_id=user.id)
                db.session.add(oauth)

            db.session.commit()
            logging.debug(f"OAuth token stored successfully for user {user.email}")
        else:
            logging.warning("No OAuth token found to store.")
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"Error storing OAuth token in the database: {e}", exc_info=True)
        flash("An error occurred while storing your authentication token.", "error")
        return redirect(url_for("main.home"))

    return redirect(url_for("main.home"))

@main.route('/enter_details', methods=['GET', 'POST'])
@login_required
def enter_details():
    if request.method == 'POST':
        logging.debug("Processing POST request for /enter_details")
        logging.debug(f"Form data received: {request.form}")

        user = current_user
        try:
            # Retrieve user-submitted details and update the user object
            user.ASVZ_ID = request.form.get('ASVZ_ID') or None
            user.ASVZ_Password = request.form.get('ASVZ_Password') or None
            # Update any additional fields you have

            logging.debug("Attempting to commit user details to the database.")
            db.session.commit()
            logging.info("User details updated successfully.")
            flash("Details updated successfully.", "success")
            return redirect(url_for('main.home'))
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Error updating user details in the database: {e}", exc_info=True)
            flash("An error occurred while updating your details.", "error")
            return render_template('enter_details.html')
    else:
        logging.debug("Rendering enter_details.html for GET request")
        return render_template('enter_details.html')

@main.route('/dashboard')
@login_required
def dashboard():
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).order_by(Enrollment.created_at.desc()).all()
    return render_template('dashboard.html', enrollments=enrollments)

@main.route('/get_enrollments')
@login_required
def get_enrollments():
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).order_by(Enrollment.created_at.desc()).all()
    enrollment_list = []
    for enrollment in enrollments:
        status_html = ''
        if enrollment.status in ['PENDING', 'STARTED']:
            status_html += '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> '
        status_html += enrollment.status

        enrollment_list.append({
            'id': enrollment.id,
            'status': enrollment.status,
            'status_html': status_html,
            'result_text': 'Success' if enrollment.result == True else 'Failure' if enrollment.result == False else 'N/A',
            'message': enrollment.message or '---',
            'started_at': enrollment.started_at.strftime('%Y-%m-%d %H:%M:%S') if enrollment.started_at else None,
            'completed_at': enrollment.completed_at.strftime('%Y-%m-%d %H:%M:%S') if enrollment.completed_at else None,
        })
    return jsonify({'enrollments': enrollment_list})

@main.route('/logout')
@login_required
def logout():
    logging.debug(f"Logging out user {current_user.email}")
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.home"))

# Error handlers
@main.app_errorhandler(500)
def internal_error(error):
    logging.error(f"Internal server error: {error}", exc_info=True)
    return render_template('500.html'), 500

@main.app_errorhandler(404)
def not_found_error(error):
    logging.error(f"404 error: {error}")
    return render_template('404.html'), 404





