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


def validate_date_format(date_str):
    try:
        return datetime.strptime(date_str, "%d-%m-%Y").strftime("%Y-%m-%d")
    except ValueError:
        st.warning(f"Invalid date format: {date_str}")
        return None

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
        latest_login_date = attendance_data.get(
            "Login_Date", ["-"])[-1]
        latest_login_time = attendance_data.get(
            "Login_Time", ["-"])[-1]
        latest_logout_date = attendance_data.get(
            "Logout_Date", ["-"])[-1]
        latest_logout_time = attendance_data.get(
            "Logout_Time", ["-"])[-1]

        attendance_list.append({
            "Username": doc.id,
            "Last Login": f"{latest_login_date} {latest_login_time}",
            "Last Logout": f"{latest_logout_date} {latest_logout_time}"
        })

    return pd.DataFrame(attendance_list)

# Fungsi untuk menghitung trafik login dan logout selama 7 hari terakhir


def get_traffic_last_7_days():
    """
    Function to calculate total login and logout actions (time entries)
    across all accounts for the last 7 days.
    """
    attendance_ref = fs.collection("employee attendance")
    docs = attendance_ref.stream()

    # Define the time range (last 7 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    traffic_data = {
        (start_date + timedelta(days=i)).strftime("%Y-%m-%d"): {"login": 0, "logout": 0}
        for i in range(7)
    }

    for doc in docs:
        attendance_data = doc.to_dict()
        login_dates = attendance_data.get("Login_Date", [])
        login_times = attendance_data.get("Login_Time", [])
        logout_dates = attendance_data.get("Logout_Date", [])
        logout_times = attendance_data.get("Logout_Time", [])

        # Process login times for each date
        for i, date in enumerate(login_dates):
            validated_date = validate_date_format(date)  # Validate date format
            if validated_date and validated_date in traffic_data:
                traffic_data[validated_date]["login"] += 1

        # Process logout times for each date
        for i, date in enumerate(logout_dates):
            validated_date = validate_date_format(date)
            if validated_date and validated_date in traffic_data:
                # Add count for each logout time
                traffic_data[validated_date]["logout"] += 1

    # Debug final processed traffic data
    st.write("Processed Traffic Data (Total Counts):", traffic_data)

    return traffic_data


def plot_daily_login_logout_totals(traffic_data):
    """
    Function to visualize total login/logout times per day in a stacked bar chart.
    """
    dates = list(traffic_data.keys())
    login_counts = [traffic_data[date]["login"] for date in dates]
    logout_counts = [traffic_data[date]["logout"] for date in dates]
    # Create the stacked bar chart
    fig = go.Figure(data=[
        go.Bar(name="Login", x=dates, y=login_counts, marker_color="blue"),
        go.Bar(name="Logout", x=dates, y=logout_counts, marker_color="red")
    ])
    fig.update_layout(
        barmode="stack",
        title="Daily Login/Logout Totals (Last 7 Days)",
        xaxis_title="Date",
        yaxis_title="Total Actions",
        legend_title="Action Type"
    )

    st.plotly_chart(fig)


# Main logic for admin page
if (
    "role" in st.session_state and
    st.session_state.role == "Admin" and
    "signout" in st.session_state and
    not st.session_state.signout
):
    st.title("Admin User Verification")

    # Display unverified users
    st.subheader("Users to be Verified:")
    unverified_users_df = get_unverified_users()

    if not unverified_users_df.empty:
        st.dataframe(unverified_users_df)
        selected_users = st.multiselect(
            "Select users to verify:", unverified_users_df['email'])
        if st.button("Verify Selected Users"):
            for email in selected_users:
                selected_user = unverified_users_df[unverified_users_df['email'] == email]
                verify_user(selected_user['UID'].values[0])
    else:
        st.warning("No users found who need verification.")

    # Display verified users
    st.subheader("Verified Users:")
    verified_users_df = get_verified_users()
    if not verified_users_df.empty:
        st.dataframe(verified_users_df)
    else:
        st.info("No verified users found.")

    # Display employee attendance
    st.subheader("Employee Attendance:")
    employee_attendance_df = get_employee_attendance()
    if not employee_attendance_df.empty:
        st.dataframe(employee_attendance_df)
    else:
        st.info("No attendance data available.")

    # Display login/logout traffic
    st.subheader("Traffic for Last 7 Days:")
    traffic_data = get_traffic_last_7_days()
    plot_daily_login_logout_totals(traffic_data)

else:
    st.warning("You are not authorized to view this page.")
