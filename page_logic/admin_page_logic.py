import streamlit as st
from models.user_service import UserService
from models.attendance_service import AttendanceService
import plotly.graph_objects as go
from datetime import datetime, timedelta


class AdminPage:
    def __init__(self, firestore, auth):
        self.user_service = UserService(firestore, auth)
        self.attendance_service = AttendanceService(firestore)

    def load_css(self, file_path):
        """Muat file CSS ke dalam aplikasi Streamlit."""
        with open(file_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

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

        fig = go.Figure(data=[
            go.Bar(name="Login", x=dates, y=login_counts,
                   marker_color="#42c2ff"),
            go.Bar(name="Logout", x=dates,
                   y=logout_counts, marker_color="#3375b1")
        ])

        fig.update_layout(
            barmode="stack",
            title="Daily Login/Logout Totals (Last 7 Days)",
            xaxis_title="Date",
            yaxis_title="Total Times",
            legend_title="Action Type"
        )
        st.plotly_chart(fig, use_container_width=True)

    def render(self):
        # Muat file CSS
        self.load_css("static/css/style.css")

        st.title("Admin User Verification", anchor="page-title")

        st.subheader("Users to be Verified:", anchor="subheader")
        unverified_users_df = self.user_service.get_unverified_users()

        if not unverified_users_df.empty:
            st.dataframe(unverified_users_df, use_container_width=True)

            selected_users = st.multiselect(
                "Select users to verify:", unverified_users_df['email']
            )

            if st.button("Verify Selected Users"):
                for email in selected_users:
                    selected_user = unverified_users_df[
                        unverified_users_df['email'] == email
                    ]
                    message = self.user_service.verify_user(
                        selected_user['UID'].values[0])
                    st.success(message)
        else:
            st.warning("No users found who need verification.")

        st.subheader("Employee Attendance:", anchor="subheader")
        employee_attendance_df = self.attendance_service.get_employee_attendance()

        if not employee_attendance_df.empty:
            st.dataframe(employee_attendance_df, use_container_width=True)
        else:
            st.info("No attendance data available.")

        st.subheader("Logins and Logouts for the Last 7 Days:",
                     anchor="subheader")
        daily_totals = self.attendance_service.calculate_daily_login_logout_totals()
        self.plot_daily_login_logout_totals(daily_totals)
