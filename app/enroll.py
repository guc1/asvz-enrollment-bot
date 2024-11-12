# app/enroll.py

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
import logging

from app.extensions import db
from app.models import User, Enrollment
from app.forms import EnrollForm
from app.tasks import perform_enrollment_task  # Import the Celery task

enroll_bp = Blueprint('enroll', __name__, template_folder='templates')

@enroll_bp.route('/enroll', methods=['GET', 'POST'])
@login_required
def enroll():
    form = EnrollForm()
    if form.validate_on_submit():
        # Retrieve user input from the form
        asvz_id = form.ASVZ_ID.data
        password = form.ASVZ_Password.data
        base_url = form.URL.data

        # Save these details to the user's encrypted fields
        user = current_user
        user.ASVZ_ID = asvz_id
        user.ASVZ_Password = password

        # Create a new Enrollment record
        enrollment = Enrollment(
            user_id=user.id,
            asvz_id=asvz_id,
            base_url=base_url,
            status='PENDING'
        )
        db.session.add(enrollment)
        db.session.commit()

        # Enqueue the Celery task
        try:
            task = perform_enrollment_task.delay(
                enrollment_id=enrollment.id,
                asvz_id=asvz_id,
                password=password,
                base_url=base_url
            )
            enrollment.task_id = task.id  # Store the task ID in the Enrollment record
            db.session.commit()
            flash("Enrollment process started. You can check the status on the dashboard.", "info")
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Failed to enqueue enrollment task: {e}", exc_info=True)
            flash("An error occurred while starting the enrollment process.", "error")
            return render_template('enroll.html', form=form)

    return render_template('enroll.html', form=form)







