import firebase_admin
from firebase_admin import credentials

# Path ke file credentials.json
cred = credentials.Certificate(
    r"C:\Users\rizky\OneDrive\Dokumen\GitHub\intern-iconnet\credentials_firebase.json")
firebase_admin.initialize_app(cred)
