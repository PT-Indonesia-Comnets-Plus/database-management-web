import streamlit as st


def app(user_data):
    """
    Streamlit page for Admin User Verification.

    Parameters:
    ----------
    user_data : object
        An object that provides methods to fetch and update user-related data,
        including 'get_users', 'verify_user', and 'get_employee_attendance'.
    """
    # Title
    st.title("Admin User Verification", anchor="page-title")

    # --- Section: Users Pending Verification ---
    st.subheader("Users to be Verified:", anchor="subheader")
    unverified_users_df = user_data.get_users(status='Pending')

    if not unverified_users_df.empty:
        st.dataframe(unverified_users_df, use_container_width=True)

        selected_users = st.multiselect(
            "Select users to verify:",
            unverified_users_df['email']
        )

        if st.button("Verify Selected Users"):
            for email in selected_users:
                selected_user = unverified_users_df[
                    unverified_users_df['email'] == email
                ]
                if not selected_user.empty:
                    uid = selected_user['UID'].values[0]
                    message = user_data.verify_user(uid)
                    st.success(message)
    else:
        st.warning("No users found who need verification.")

    # --- Section: Verified Users ---
    st.subheader("Verified Users:", anchor="subheader")
    verified_users_df = user_data.get_users(status='Verified')

    if not verified_users_df.empty:
        # Rename columns for better readability
        verified_users_df = verified_users_df.rename(columns={
            'created_at': 'Created Time',
            'username': 'Username',
            'email': 'Email',
            'status': 'Status',
            'verification_time': 'Verify Time'
        })

        # Reorder columns
        verified_users_df = verified_users_df[
            ['Created Time', 'Username', 'Email', 'Status', 'Verify Time']
        ]

        # Display top 3 verified users
        st.dataframe(verified_users_df.head(3), use_container_width=True)
    else:
        st.info("No verified users found.")

    # --- Section: Employee Attendance ---
    st.subheader("Employee Attendance:", anchor="subheader")
    employee_attendance_df = user_data.get_employee_attendance()

    if not employee_attendance_df.empty:
        st.dataframe(employee_attendance_df, use_container_width=True)
    else:
        st.info("No attendance data available.")

    # --- Section: Logins and Logouts ---
    st.subheader("Logins and Logouts for the Last 7 Days:", anchor="subheader")
    # Placeholder for future login/logout data implementation
    st.info("Logins and logouts data feature is under development.")
