import streamlit as st
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from firebase_admin import auth, firestore
from datetime import datetime
from utils.firebase_config import fs
from utils.cookies import clear_user_cookie, save_user_to_cookie

# configuration Firebase
FIREBASE_API_KEY = st.secrets["firebase"]["firebase_api"]

# configuration SMTP
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USERNAME = st.secrets["smtp"]["username"]
SMTP_PASSWORD = st.secrets["smtp"]["password"]


def save_login_logout(username, event_type):
    now = datetime.now()
    date = now.strftime("%d-%m-%Y")
    time = now.strftime("%H:%M:%S")
    doc_ref = fs.collection("employee attendance").document(username)

    try:
        if event_type == "login":
            doc_ref.update({
                "Login_Date": firestore.ArrayUnion([date]),
                "Login_Time": firestore.ArrayUnion([time])
            })
        elif event_type == "logout":
            doc_ref.update({
                "Logout_Date": firestore.ArrayUnion([date]),
                "Logout_Time": firestore.ArrayUnion([time])
            })
    except Exception as e:
        if event_type == "login":
            doc_ref.set({
                "Login_Date": [date],
                "Login_Time": [time],
                "Logout_Date": [],
                "Logout_Time": []
            })
        elif event_type == "logout":
            doc_ref.set({
                "Login_Date": [],
                "Login_Time": [],
                "Logout_Date": [date],
                "Logout_Time": [time]
            })


def verify_password(email, password):
    api_key = FIREBASE_API_KEY
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


def login(email, password):
    user_data = verify_password(email, password)
    if user_data:
        try:
            user = auth.get_user_by_email(email)
            if not user.email_verified:
                st.warning("Email not verified. Please check your inbox.")
                return
            user_doc = fs.collection('users').document(user.uid).get()

            if user_doc.exists:
                user_data = user_doc.to_dict()
                if user_data["status"] != "Verified":
                    st.warning("Your account is not verified by admin yet.")
                    return
                st.session_state.username = user.uid
                st.session_state.useremail = user.email
                st.session_state.role = user_data['role']
                st.session_state.signout = False
                save_login_logout(user.uid, "login")  # Simpan data login
                save_user_to_cookie(user.uid, user.email,
                                    user_data['role'])  # Simpan cookies
                st.success(f"Login successful as {user_data['role']}!")
            else:
                st.warning("User data not found.")
        except Exception as e:
            st.warning(f"Login Failed: {e}")
    else:
        st.warning("Invalid email or password")


def signup(username, email, password, role):
    try:
        db = st.session_state.db  # Akses Firestore dari session_state
        # Membuat pengguna baru menggunakan Firebase Authentication
        user = auth.create_user(email=email, password=password, uid=username)

        # Menyimpan data tambahan ke Firestore
        user_ref = db.collection("Absensi Karyawan").document(username)
        user_ref.set({
            "nama": username,
            "email": email,
            "role": role,
            # Status email akan diatur menjadi belum terverifikasi
            "status": "Belum terverifikasi"
        })

        send_verification_email(email)
        st.success("Account created successfully! Please verify your email.")
        st.markdown("Please Login using your email and password")
        st.balloons()
    except Exception as e:
        st.error(f"Error creating account: {e}")


def logout():
    save_login_logout(st.session_state.username, "logout")
    clear_user_cookie()  # Hapus cookies
    st.session_state.signout = True
    st.session_state.username = ''
    st.session_state.useremail = ''
    st.session_state.role = ''


def send_verification_email(email):
    try:
        user = auth.get_user_by_email(email)
        link = auth.generate_email_verification_link(email)

        # Create the email content
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = email
        msg['Subject'] = 'Verify your email address'

        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .email-container {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: auto;
                    padding: 20px;
                    border: 1px solid #ddd;
                    border-radius: 10px;
                    background-color: #f9f9f9;
                }}
                .email-header {{
                    text-align: center;
                    padding-bottom: 20px;
                }}
                .email-header img {{
                    max-width: 100px;
                }}
                .email-body {{
                    padding: 20px;
                    background-color: #fff;
                    border-radius: 10px;
                }}
                .email-footer {{
                    text-align: center;
                    padding-top: 20px;
                    font-size: 12px;
                    color: #777;
                }}
                .verify-button {{
                    display: inline-block;
                    padding: 10px 20px;
                    margin: 20px 0;
                    font-size: 16px;
                    color: #fff;
                    background-color: #b9c4c6;
                    text-decoration: none;
                    border-radius: 5px;
                }}
                .verify-button:hover {{
                    background-color: #a0b0b2;
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="email-header">
                    <img src="https://raw.githubusercontent.com/rizkyyanuark/RPL-HarmonCorp/main/prototyping/image/logo.jpg" alt="Harmon Corp Logo">
                </div>
                <div class="email-body">
                    <p>Hi {user.display_name or user.email},</p>
                    <p>Please verify your email address by clicking the button below:</p>
                    <p style="text-align: center;">
                        <a href="{link}" class="verify-button">Verify Email</a>
                    </p>
                    <p>If you did not create an account, please ignore this email.</p>
                    <p>Thanks,<br>Harmon Corp Team</p>
                </div>
                <div class="email-footer">
                    <p>&copy; {datetime.now().year} Harmon Corp. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(body, 'html'))

        # Send the email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.set_debuglevel(1)  # Enable debug output
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, email, msg.as_string())
            st.success("Verification link sent to admin.")
    except Exception as e:
        st.error(f"Error sending verification email: {e}")
