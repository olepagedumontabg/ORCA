from main import app, db
from models import Product, Compatibility

if __name__ == "__main__":
    with app.app_context():
        print("Updating database schema...")
        db.create_all()
        print("Schema updated successfully!")