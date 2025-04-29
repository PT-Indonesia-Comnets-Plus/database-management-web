from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
from firebase_admin import firestore


class UserDataService:
    def __init__(self, firestore):
        self.fs = firestore

    # Fungsi untuk mendapatkan pengguna yang belum terverifikasi
    def get_users(self, status):
        users_ref = self.fs.collection("users")

        # Tambahkan filter untuk status dan role (employee)
        query = users_ref.where("status", "==", status).where(
            "role", "==", "Employee")
        docs = query.stream()

        users_list = []
        for doc in docs:
            user_data = doc.to_dict()
            user_data["UID"] = doc.id
            users_list.append(user_data)

        # Kembalikan hasil sebagai DataFrame
        return pd.DataFrame(users_list)

    def get_employee_attendance(self):
        attendance_ref = self.fs.collection("employee attendance")
        docs = attendance_ref.stream()

        attendance_list = []
        for doc in docs:
            attendance_data = doc.to_dict()
            username = doc.id
            activity = attendance_data.get("activity", {})

            latest_login_date = "-"
            latest_login_time = "-"
            latest_logout_date = "-"
            latest_logout_time = "-"

            if activity:
                latest_date = max(
                    activity.keys(), key=lambda date: datetime.strptime(date, "%d-%m-%Y")
                )
                latest_login_time = activity[latest_date].get(
                    "Login_Time", ["-"])[-1] if activity[latest_date].get("Login_Time") else "-"
                latest_logout_time = activity[latest_date].get(
                    "Logout_Time", ["-"])[-1] if activity[latest_date].get("Logout_Time") else "-"

                latest_login_date = latest_date if latest_login_time != "-" else "-"
                latest_logout_date = latest_date if latest_logout_time != "-" else "-"

            attendance_list.append({
                "Username": username,
                "Last Login": f"{latest_login_date} {latest_login_time}",
                "Last Logout": f"{latest_logout_date} {latest_logout_time}"
            })

        return pd.DataFrame(attendance_list)

    def calculate_daily_login_logout_totals(self):
        attendance_ref = self.fs.collection("employee attendance")
        docs = attendance_ref.stream()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        daily_totals = {}

        for doc in docs:
            attendance_data = doc.to_dict()
            activity = attendance_data.get("activity", {})

            for date, times in activity.items():
                date_obj = datetime.strptime(date, "%d-%m-%Y")
                if start_date <= date_obj <= end_date:
                    if date not in daily_totals:
                        daily_totals[date] = {"logins": 0, "logouts": 0}

                    daily_totals[date]["logins"] += len(
                        times.get("Login_Time", []))
                    daily_totals[date]["logouts"] += len(
                        times.get("Logout_Time", []))

        return daily_totals

    def verify_user(self, uid: str) -> str:
        """
        Updates the status of a user with the given UID to 'Verified' in Firestore.

        Args:
            uid: The unique identifier (UID) of the user to verify.

        Returns:
            A status message indicating success or failure.
        """
        if not uid:
            return "Error: User UID cannot be empty."

        user_ref = self.fs.collection('users').document(uid)

        try:
            user_doc = user_ref.get()
            if not user_doc.exists:
                return f"Error: User with UID '{uid}' not found."
            user_ref.update({
                'status': 'Verified',
                'verification_time': datetime.now().strftime("%S:%M:%H %d-%m-%Y")
            })
            return "User verified successfully."
        except Exception as e:
            return f"Error verifying user: {e}"

    def plot_daily_login_logout_totals(self, daily_totals):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=6)
        all_dates = [
            (start_date + timedelta(days=i)).strftime("%d-%m-%Y") for i in range(7)
        ]
        complete_totals = {date: {"logins": 0, "logouts": 0}
                           for date in all_dates}
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
        return fig
