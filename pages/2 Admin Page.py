import streamlit as st
from firebase_admin import auth
from utils.firebase_config import get_firebase_app
from utils.cookies import load_cookie_to_session
import pandas as pd
from PIL import Image
import os
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Load data from cookies
try:
    load_cookie_to_session(st.session_state)
except RuntimeError:
    st.stop()

# Set page configuration
logo_path = os.path.join("image", "icon.png")
logo = Image.open(logo_path)

# Resize the logo to a smaller size
logo_resized = logo.resize((32, 32))

try:
    st.set_page_config(page_title="Admin Page", page_icon=logo_resized)
except st.errors.StreamlitSetPageConfigMustBeFirstCommandError:
    pass

fs = get_firebase_app()


# Fungsi untuk mendapatkan pengguna yang belum terverifikasi
def get_unverified_users():
    users_ref = fs.collection("users")
    query = users_ref.where("status", "==", "Pending")
    docs = query.stream()

    users_list = []
    for doc in docs:
        user_data = doc.to_dict()
        user_data["UID"] = doc.id
        users_list.append(user_data)

    return pd.DataFrame(users_list)


# Fungsi untuk mendapatkan pengguna yang sudah terverifikasi
def get_verified_users():
    users_ref = fs.collection("users")
    query = users_ref.where("status", "==", "Verified")
    docs = query.stream()

    users_list = []
    for doc in docs:
        user_data = doc.to_dict()
        user_data["UID"] = doc.id
        users_list.append(user_data)

    return pd.DataFrame(users_list)


# Fungsi untuk memverifikasi pengguna berdasarkan UID
def verify_user(uid):
    user = auth.get_user(uid)

    auth.update_user(uid, email_verified=True)
    user_ref = fs.collection("users").document(uid)
    user_ref.update({
        "status": "Verified"
    })

    st.success(
        f"User with email {user.email} has been verified and updated in Firestore."
    )


# Fungsi untuk mendapatkan kehadiran pengguna terakhir kali login dan logout
def get_employee_attendance():
    attendance_ref = fs.collection("employee attendance")
    docs = attendance_ref.stream()

    attendance_list = []
    for doc in docs:
        attendance_data = doc.to_dict()
        username = doc.id  # Asumsikan username adalah ID dokumen
        activity = attendance_data.get("activity", {})

        latest_login_date = "-"
        latest_login_time = "-"
        latest_logout_date = "-"
        latest_logout_time = "-"

        if activity:
            latest_date = max(
                activity.keys(), key=lambda date: datetime.strptime(date, "%d-%m-%Y"))
            latest_login_time = activity[latest_date].get(
                "Login_Time", ["-"])[-1]
            latest_logout_time = activity[latest_date].get(
                "Logout_Time", ["-"])[-1]

            latest_login_date = latest_date if latest_login_time != "-" else "-"
            latest_logout_date = latest_date if latest_logout_time != "-" else "-"

        attendance_list.append({
            "Username": username,
            "Last Login": f"{latest_login_date} {latest_login_time}",
            "Last Logout": f"{latest_logout_date} {latest_logout_time}"
        })

    return pd.DataFrame(attendance_list)

# Fungsi untuk menghitung total login dan logout berdasarkan tanggal selama 7 hari terakhir


def calculate_daily_login_logout_totals():
    attendance_ref = fs.collection("employee attendance")
    docs = attendance_ref.stream()
    users_ref = fs.collection("users")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    daily_totals = {}

    for doc in docs:
        attendance_data = doc.to_dict()
        username = doc.id
        user_doc = users_ref.document(username).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            role = user_data.get("role", "Employee")
            if role == "Admin":
                continue
        activity = attendance_data.get("activity", {})

        for date, times in activity.items():
            date_obj = datetime.strptime(date, "%d-%m-%Y")
            if start_date <= date_obj <= end_date:
                if date not in daily_totals:
                    daily_totals[date] = {"logins": 0, "logouts": 0}

                # Tambahkan jumlah Login_Time dan Logout_Time
                daily_totals[date]["logins"] += len(
                    times.get("Login_Time", []))
                daily_totals[date]["logouts"] += len(
                    times.get("Logout_Time", []))

    return daily_totals

# Fungsi untuk membuat grafik stacked bar berdasarkan hasil penghitungan


def plot_daily_login_logout_totals(daily_totals):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=6)
    all_dates = [
        (start_date + timedelta(days=i)).strftime("%d-%m-%Y") for i in range(7)
    ]
    complete_totals = {date: {"logins": 0, "logouts": 0} for date in all_dates}
    for date in daily_totals:
        if date in complete_totals:
            complete_totals[date]["logins"] = daily_totals[date]["logins"]
            complete_totals[date]["logouts"] = daily_totals[date]["logouts"]
    dates = sorted(complete_totals.keys())
    login_counts = [complete_totals[date]["logins"] for date in dates]
    logout_counts = [complete_totals[date]["logouts"] for date in dates]

    # Buat stacked bar chart dengan warna yang disesuaikan
    fig = go.Figure(data=[
        go.Bar(
            name="Login",
            x=dates,
            y=login_counts,
            marker_color="#42c2ff",
            hoverinfo="x+y",
            text=login_counts,
            textposition="inside"
        ),
        go.Bar(
            name="Logout",
            x=dates,
            y=logout_counts,
            marker_color="#3375b1",
            hoverinfo="x+y",
            text=logout_counts,
            textposition="inside"
        )
    ])

    # Tambahkan konfigurasi layout
    fig.update_layout(
        barmode="stack",
        title="Daily Login/Logout Totals (Last 7 Days)",
        xaxis_title="Date",
        yaxis_title="Total Times",
        legend_title="Action Type"
    )
    st.plotly_chart(fig, use_container_width=True)


# Tambahkan di Streamlit bagian Admin Page
if (
    "role" in st.session_state and
    st.session_state.role == "Admin" and
    "signout" in st.session_state and
    not st.session_state.signout
):
    st.title("Admin User Verification")

    st.subheader("Users to be Verified:")
    unverified_users_df = get_unverified_users()

    if not unverified_users_df.empty:
        st.dataframe(unverified_users_df)

        selected_users = st.multiselect(
            "Select users to verify:", unverified_users_df['email']
        )

        if st.button("Verify Selected Users"):
            for email in selected_users:
                selected_user = unverified_users_df[
                    unverified_users_df['email'] == email
                ]
                verify_user(selected_user['UID'].values[0])
    else:
        st.warning("No users found who need verification.")

    st.subheader("Verified Users:")
    verified_users_df = get_verified_users()

    if not verified_users_df.empty:
        st.dataframe(verified_users_df)
    else:
        st.info("No verified users found.")

    st.subheader("Employee Attendance:")
    employee_attendance_df = get_employee_attendance()

    if not employee_attendance_df.empty:
        st.dataframe(employee_attendance_df)
    else:
        st.info("No attendance data available.")

    # Visualisasi Total Login dan Logout
    st.subheader("Logins and Logouts for the Last 7 Days:")
    daily_totals = calculate_daily_login_logout_totals()
    plot_daily_login_logout_totals(daily_totals)

else:
    st.warning("You are not authorized to view this page.")
