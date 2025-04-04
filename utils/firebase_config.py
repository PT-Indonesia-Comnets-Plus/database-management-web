import firebase_admin
from firebase_admin import credentials, firestore, auth
import streamlit as st
import json
from dotenv import load_dotenv

load_dotenv()


@st.cache_resource
def get_firebase_app():
    if not firebase_admin._apps:
        firebase_key_json = st.secrets["firebase"]["firebase_key_json"]
        key_dict = json.loads(firebase_key_json)

        # Membuat kredensial
        creds = credentials.Certificate(key_dict)

        firebase_admin.initialize_app(creds)

    # Mengakses Firestore dan Auth
    fs = firestore.client()
    return fs, auth
