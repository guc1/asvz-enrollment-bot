# tasks.py

from app import celery
from app.enrollment_logic import perform_enrollment
import logging
from celery.exceptions import MaxRetriesExceededError
from app.extensions import db
from app.models import Enrollment
from datetime import datetime

@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def perform_enrollment_task(self, enrollment_id, asvz_id, password, base_url):
    enrollment = Enrollment.query.get(enrollment_id)
    if not enrollment:
        logging.error(f"Enrollment with ID {enrollment_id} not found.")
        return False

    # Update the enrollment status and started_at
    enrollment.status = 'STARTED'
    enrollment.started_at = datetime.utcnow()
    db.session.commit()

    try:
        logging.info(f"Starting enrollment task for enrollment {enrollment_id}")
        success = perform_enrollment(asvz_id, password, base_url)
        enrollment.result = success
        enrollment.status = 'SUCCESS' if success else 'FAILURE'
        enrollment.message = "Enrollment successful." if success else "Enrollment failed."
        enrollment.completed_at = datetime.utcnow()
        db.session.commit()
        logging.info(f"Enrollment task completed for enrollment {enrollment_id}")
        return success
    except Exception as e:
        enrollment.status = 'FAILURE'
        enrollment.message = str(e)
        enrollment.completed_at = datetime.utcnow()
        db.session.commit()
        logging.error(f"Enrollment task failed for enrollment {enrollment_id}: {e}", exc_info=True)
        try:
            self.retry(exc=e)
        except MaxRetriesExceededError:
            logging.error(f"Max retries exceeded for enrollment {enrollment_id}")
            raise


