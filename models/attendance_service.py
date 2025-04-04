from datetime import datetime, timedelta
import pandas as pd


class AttendanceService:
    def __init__(self, firestore):
        self.fs = firestore

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
