import streamlit as st
from firebase_admin import auth
from utils.firebase_config import fs
from utils.cookies import load_cookie_to_session
import pandas as pd

# Load data from cookies
username, useremail, role, signout = load_cookie_to_session()
try:
    st.set_page_config(page_title="Admin Page", page_icon="👨‍💼")
except st.errors.StreamlitSetPageConfigMustBeFirstCommandError:
    pass

# Sekarang objek Firestore tersedia di st.session_state.db
db = fs


def get_unverified_users():
    users_ref = db.collection("users")
    query = users_ref.where("status", "==", "Pending")
    docs = query.stream()

    users_list = []
    for doc in docs:
        user_data = doc.to_dict()
        user_data["UID"] = doc.id
        users_list.append(user_data)

    return pd.DataFrame(users_list)


def verify_user(uid):
    user = auth.get_user(uid)

    # Update email_verified ke True di Firebase Authentication
    auth.update_user(uid, email_verified=True)

    # Update status verifikasi di Firestore untuk koleksi "users"
    user_ref = db.collection("users").document(uid)
    user_ref.update({
        "status": "Verified"  # Ubah status di Firestore
    })

    st.success(
        f"User with email {user.email} has been verified and updated in Firestore.")


if role == "Admin" and not signout:
    st.title("Admin User Verification")

    # Menampilkan pengguna yang belum terverifikasi
    st.subheader("Users to be Verified:")

    # Ambil pengguna yang belum terverifikasi
    unverified_users_df = get_unverified_users()

    if not unverified_users_df.empty:
        # Menampilkan DataFrame pengguna yang belum terverifikasi
        st.dataframe(unverified_users_df)

        # Pilih pengguna yang akan diverifikasi
        selected_users = st.multiselect(
            "Select users to verify:", unverified_users_df['email'])

        if st.button("Verify Selected Users"):
            for email in selected_users:
                selected_user = unverified_users_df[unverified_users_df['email'] == email]
                verify_user(selected_user['UID'].values[0])
    else:
        st.warning("No users found who need verification.")
else:
    st.warning("You are not authorized to view this page.")
