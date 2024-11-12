from app import create_app, db  # Import db from app
import os

app = create_app()

# Create the database tables if they don't exist
with app.app_context():
    if not os.path.exists('site.db'):
        db.create_all()
        print('Database tables created.')

if __name__ == '__main__':
    app.run()