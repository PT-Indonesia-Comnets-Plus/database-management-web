import streamlit as st
from models import UserService, UserDataService


def app(user_data):
    # Render konten admin jika pengguna adalah admin
    st.title("Admin User Verification", anchor="page-title")

    st.subheader("Users to be Verified:", anchor="subheader")
    unverified_users_df = user_data.get_users('Pending')

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
                message = user_data.verify_user(
                    selected_user['UID'].values[0])
                st.success(message)
    else:
        st.warning("No users found who need verification.")

    st.subheader("Verified Users:")
    verified_users_df = user_data.get_users('Verified')
    verified_users_df.rename(columns={
        'created_at': 'Created Time',
        'username': 'Username',
        'email': 'Email',
        'status': 'Status',
        'verification_time': 'Verify Time'
    }, inplace=True)

# Mengatur posisi kolom sesuai urutan yang diinginkan
    verified_users_df = verified_users_df[[
        'Created Time', 'Username', 'Email', 'Status', 'Verify Time']]
    if not verified_users_df.empty:
        # Tampilkan hanya 3 data teratas
        st.dataframe(verified_users_df.head(3))
    else:
        st.info("No verified users found.")

    st.subheader("Employee Attendance:", anchor="subheader")
    employee_attendance_df = user_data.get_employee_attendance()

    if not employee_attendance_df.empty:
        st.dataframe(employee_attendance_df, use_container_width=True)
    else:
        st.info("No attendance data available.")

    st.subheader("Logins and Logouts for the Last 7 Days:",
                 anchor="subheader")
    daily_totals = user_data.calculate_daily_login_logout_totals()
    st.plotly_chart(user_data.plot_daily_login_logout_totals(
        daily_totals), use_container_width=True)
