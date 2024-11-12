from flask import Flask
from celery import Celery
from config import Config
from app.extensions import db, login_manager
import logging
import os
from logging.handlers import RotatingFileHandler
from flask_dance.contrib.google import make_google_blueprint  # Import this

# Initialize Celery (global variable)
celery = Celery(__name__, broker=Config.CELERY_BROKER_URL)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Set up the LoginManager
    login_manager.login_view = 'google.login'  # Ensure this matches your login route

    # Import models after initializing db to avoid circular imports
    from app.models import User

    # Define the user_loader function for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        logging.debug(f"Loading user with ID: {user_id}")
        return User.query.get(int(user_id))

    # Initialize the Google OAuth blueprint without specifying storage
    google_bp = make_google_blueprint(
        client_id=app.config['GOOGLE_OAUTH_CLIENT_ID'],
        client_secret=app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
        redirect_to='main.after_login',  # Ensure this matches your route
        scope=[
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid"  # Added 'openid' scope
        ],
        # Do not specify 'storage' here
    )
    app.register_blueprint(google_bp, url_prefix='/login')

    # Configure Celery with Flask app context
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask

    # Import blueprints
    from app.enroll import enroll_bp
    from app.routes import main as main_blueprint

    # Register blueprints
    app.register_blueprint(enroll_bp)
    app.register_blueprint(main_blueprint)
    

    # Configure logging
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/asvzbot.log', maxBytes=10240, backupCount=10)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)s in %(module)s: %(message)s'
        )
        file_handler.setFormatter(formatter)
        app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('ASVZbot startup')

    return app













