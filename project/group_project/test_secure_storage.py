from app.database.database_Manager import DatabaseManager

db = DatabaseManager("data")
print("Loaded patients:", list(db.patients.keys()))
db.save_all()
print("Re-saved encrypted files successfully ✅")
