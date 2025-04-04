import streamlit as st
from models.user_service import UserService
from models.attendance_service import AttendanceService
import plotly.graph_objects as go
from datetime import datetime, timedelta
from utils import initialize_session_state
from PIL import Image, ImageOps


class AdminPage:
    def __init__(self, firestore, auth):
        self.user_service = UserService(firestore, auth)
        self.attendance_service = AttendanceService(firestore)

    def configure_page(self):
        """Konfigurasi halaman Streamlit."""
        try:
            logo = Image.open("static/image/icon.png").resize((40, 50))
            logo_with_padding = ImageOps.expand(
                logo, border=8, fill=(255, 255, 255, 0)
            )
            st.set_page_config(page_title="Admin Page",
                               page_icon=logo_with_padding)
        except st.errors.StreamlitSetPageConfigMustBeFirstCommandError:
            pass
        st.logo("static/image/logo_iconplus.png", size="large")

    def render(self):
        # Konfigurasi halaman
        self.configure_page()

        # Inisialisasi session state
        initialize_session_state()

        # Periksa apakah pengguna memiliki role "Admin"
        if "role" not in st.session_state or st.session_state.role != "Admin":
            st.warning(
                "You are not authorized to view this page. Only admins can access this page."
            )
            return  # Hentikan rendering konten admin, tetapi tetap tampilkan elemen umum

        # Render konten admin jika pengguna adalah admin
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
