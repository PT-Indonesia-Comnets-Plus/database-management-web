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

    def get_all_employee_users(self):
        """
        Get all users with role 'Employee' regardless of status.

        Returns:
            pandas.DataFrame: DataFrame containing all employee users
        """
        users_ref = self.fs.collection("users")

        # Filter only by role (employee), not by status
        query = users_ref.where("role", "==", "Employee")
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

    # MODIFIED
    def calculate_daily_login_logout_totals(self, start_date: datetime = None, end_date: datetime = None):
        attendance_ref = self.fs.collection("employee attendance")
        docs = attendance_ref.stream()

        # Use provided dates or default to last 7 days
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            # Default to 7 days before end_date
            start_date = end_date - timedelta(days=7)

        daily_totals = {}

        for doc in docs:
            attendance_data = doc.to_dict()
            activity = attendance_data.get("activity", {})

            for date_str, times in activity.items():  # Renamed 'date' to 'date_str' to avoid conflict
                try:
                    date_obj = datetime.strptime(date_str, "%d-%m-%Y")
                    # Ensure date_obj is not timezone-aware if start_date/end_date are naive, or vice-versa
                    # For simplicity, assuming naive datetimes for comparison here.
                    # If Firestore dates might have timezone, proper handling would be needed.
                    if start_date.date() <= date_obj.date() <= end_date.date():  # Compare dates directly
                        if date_str not in daily_totals:
                            daily_totals[date_str] = {
                                "logins": 0, "logouts": 0}

                        daily_totals[date_str]["logins"] += len(
                            times.get("Login_Time", []))
                        daily_totals[date_str]["logouts"] += len(
                            times.get("Logout_Time", []))
                except ValueError:
                    # Handle cases where date_str might not be in the expected format
                    print(
                        f"Warning: Could not parse date string '{date_str}' from Firestore. Skipping.")
                    continue

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

    def plot_daily_login_logout_totals(self, daily_totals, plot_start_date: datetime = None, plot_end_date: datetime = None):  # MODIFIED
        if plot_end_date is None:
            plot_end_date = datetime.now()
        if plot_start_date is None:
            plot_start_date = plot_end_date - timedelta(days=6)

        # Generate all dates in the range for a complete axis
        num_days = (plot_end_date.date() - plot_start_date.date()).days + 1
        all_dates = [
            (plot_start_date + timedelta(days=i)).strftime("%d-%m-%Y") for i in range(num_days)
        ]

        complete_totals = {date_str: {"logins": 0, "logouts": 0}  # Renamed 'date' to 'date_str'
                           for date_str in all_dates}

        for date_str_data, counts in daily_totals.items():  # Renamed 'date' to 'date_str_data'
            if date_str_data in complete_totals:
                complete_totals[date_str_data]["logins"] = counts["logins"]
                complete_totals[date_str_data]["logouts"] = counts["logouts"]

        # Sort by date for plotting, ensuring correct chronological order
        # Convert to datetime for sorting, then back to string if needed by Plotly, or use datetime directly
        sorted_dates_dt = sorted([datetime.strptime(d, "%d-%m-%Y")
                                 for d in complete_totals.keys()])
        dates_for_plot = [d.strftime("%d-%m-%Y") for d in sorted_dates_dt]

        login_counts = [complete_totals[date_str]["logins"]
                        for date_str in dates_for_plot]  # Used dates_for_plot
        logout_counts = [complete_totals[date_str]["logouts"]
                         for date_str in dates_for_plot]  # Used dates_for_plot

        # Buat stacked bar chart dengan warna yang disesuaikan
        fig = go.Figure(data=[
            go.Bar(
                name="Login",
                x=dates_for_plot,
                y=login_counts,
                marker_color="#42c2ff",
                hoverinfo="x+y",
                text=login_counts,
                textposition="inside"
            ),
            go.Bar(
                name="Logout",
                x=dates_for_plot,
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
            # MODIFIED title
            title=f"Daily Login/Logout Totals ({plot_start_date.strftime('%d-%m-%Y')} to {plot_end_date.strftime('%d-%m-%Y')})",
            xaxis_title="Date",
            yaxis_title="Total Times",
            legend_title="Action Type",
            # Ensures dates are treated as categories if strings
            xaxis={'type': 'category'}
        )
        return fig
