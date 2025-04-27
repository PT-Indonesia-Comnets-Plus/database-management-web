from datetime import datetime
import streamlit as st
from firebase_admin import exceptions
from utils.cookies import save_user_to_cookie, clear_user_cookie
import requests


class UserService:
    def __init__(self, firestore, auth, firebase_api, email_service):
        self.fs = firestore
        self.auth = auth
        self.firebase_api = firebase_api
        self.email_service = email_service

    def login(self, email, password):
        # Validasi input
        if not email.strip():
            st.warning("Email cannot be empty")
            return
        if not password.strip():
            st.warning("Password cannot be empty")
            return

        # Verifikasi melalui Firebase REST API
        user_data = self.verify_password(email, password)
        if user_data:
            try:
                user = self.auth.get_user_by_email(email)
                if not user.email_verified:
                    st.warning("Email not verified. Please check your inbox.")
                    return

                # Validasi pengguna di Firestore
                user_doc = self.fs.collection('users').document(user.uid).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    if user_data["status"] != "Verified":
                        st.warning(
                            "Your account is not verified by admin yet.")
                        return

                    # Simpan data ke session_state
                    st.session_state.username = user.uid
                    st.session_state.useremail = user.email
                    st.session_state.role = user_data['role']
                    st.session_state.signout = False

                    # Catat waktu login
                    self.save_login_logout(user.uid, "login")
                    save_user_to_cookie(
                        user.uid, user.email, user_data['role'])

                    # Pesan sukses
                    st.success(f"Login successful as {user_data['role']}!")
                else:
                    st.warning("User data not found.")
            except exceptions.FirebaseError as e:
                st.warning(f"A Firebase error occurred: {e}")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")
        else:
            st.warning("Invalid email or password")

    def signup(self, username, email, password, confirm_password, role):
        # Validasi input
        if not username.strip():
            st.warning("Username cannot be empty")
            return

        if not email.strip():
            st.warning("Email cannot be empty")
            return

        if not password or not confirm_password:
            st.warning("Password cannot be empty")
            return

        if password != confirm_password:
            st.warning("Passwords do not match")
            return

        user_ref = self.fs.collection("users").document(username)

        # Cek apakah username sudah digunakan
        if user_ref.get().exists:
            st.warning("Username already taken")
            return

        # Cek apakah email sudah digunakan
        try:
            self.auth.get_user_by_email(email)
            st.warning("Email already taken")
            return
        except exceptions.NotFoundError:
            pass

        try:
            # Membuat pengguna di Firebase Authentication
            self.auth.create_user(email=email, password=password, uid=username)
            user_ref.set({
                "username": username,
                "email": email,
                "role": role,
                "status": "Pending",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            })

            # Kirim email verifikasi
            user = self.auth.get_user_by_email(email)
            verification_link = self.auth.generate_email_verification_link(
                email)
            self.email_service.send_verification_email(
                email, user, verification_link)

            # Tampilkan pesan sukses
            st.success(
                "Account created successfully! Please verify your email.")
            st.balloons()

        except exceptions.AlreadyExistsError:
            st.warning("Email or username already taken.")
        except Exception as e:
            st.error(f"An error occurred: {e}")

    def logout(self):
        self.save_login_logout(st.session_state.username, "logout")
        clear_user_cookie()  # Hapus cookies
        st.session_state.signout = True
        st.session_state.username = ''
        st.session_state.useremail = ''
        st.session_state.role = ''

    def verify_password(self, email, password):
        api_key = st.secrets["firebase"]["firebase_api"]
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            return None

    def save_login_logout(self, username, event_type):
        now = datetime.now()
        date = now.strftime("%d-%m-%Y")
        time = now.strftime("%H:%M:%S")

        doc_ref = self.fs.collection("employee attendance").document(username)

        try:
            if event_type == "login":
                doc_ref.update({
                    f"activity.{date}.Login_Time": self.firebase_api.ArrayUnion([time])
                })
            elif event_type == "logout":
                doc_ref.update({
                    f"activity.{date}.Logout_Time": self.firebase_api.ArrayUnion([time])
                })
        except Exception:
            doc_ref.set({
                "activity": {
                    date: {
                        "Login_Time": [time] if event_type == "login" else [],
                        "Logout_Time": [time] if event_type == "logout" else []
                    }
                }
            }, merge=True)
