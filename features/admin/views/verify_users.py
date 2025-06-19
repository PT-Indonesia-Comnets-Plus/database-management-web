import streamlit as st
import pandas as pd
from core.services.UserDataService import UserDataService  # Import untuk type hinting


def app(user_data_service: UserDataService):
    """
    Displays the user verification page for administrators.
    Allows admins to view pending and verified users, and verify selected users.
    Also shows recent employee attendance.

    Args:
        user_data_service: An instance of UserDataService to fetch and update user data.
    """
    st.title("👤 User Verification Management")

    try:
        # --- Section: Users Pending Verification ---
        st.subheader("⏳ Users Pending Verification")
        unverified_users_df = user_data_service.get_users(status='Pending')

        if not unverified_users_df.empty:
            # Display relevant columns including email verification status
            available_cols = unverified_users_df.columns.tolist()
            display_cols_pending = ['username', 'email', 'created_at']
            
            # Add email verification columns if they exist
            if 'email_verified' in available_cols:
                display_cols_pending.append('email_verified')
            if 'otp_verified_at' in available_cols:
                display_cols_pending.append('otp_verified_at')
                
            # Always include UID at the end (needed for verification)
            display_cols_pending.append('UID')
            
            # Only include columns that actually exist in the dataframe
            display_cols_pending = [col for col in display_cols_pending if col in available_cols]
            
            st.dataframe(
                unverified_users_df[display_cols_pending], use_container_width=True, hide_index=True)
            
            # Show info about email verification status
            email_verified_count = 0
            if 'email_verified' in available_cols:
                email_verified_count = unverified_users_df['email_verified'].sum()
                st.info(f"📧 {email_verified_count} dari {len(unverified_users_df)} user telah memverifikasi email mereka via OTP")

            # Use email for selection as it's more user-friendly than UID
            emails_to_verify = unverified_users_df['email'].tolist()
            selected_emails = st.multiselect(
                "Select users to verify by email:",
                options=emails_to_verify,
                key="verify_multiselect"  # Add key for stability
            )

            if st.button("✅ Verify Selected Users"):
                if not selected_emails:
                    st.warning("Please select at least one user to verify.")
                else:
                    verified_count = 0
                    # Map selected emails back to UIDs for verification
                    uid_map = pd.Series(
                        unverified_users_df.UID.values, index=unverified_users_df.email).to_dict()
                    with st.spinner("Verifying users..."):
                        for email in selected_emails:
                            uid = uid_map.get(email)
                            if uid:
                                # Call the service method to verify
                                message = user_data_service.verify_user(
                                    uid)  # Assuming verify_user exists
                                st.success(f"User {email}: {message}")
                                verified_count += 1
                            else:
                                st.error(
                                    f"Could not find UID for email: {email}")
                    if verified_count > 0:
                        st.toast(
                            f"{verified_count} user(s) verified successfully!")
                        # Optional: Rerun to refresh the lists immediately
                        # st.rerun()
        else:
            st.info("No users are currently pending verification.")

        # --- Section: Verified Users ---
        st.subheader("✔️ Verified Users")
        verified_users_df = user_data_service.get_users(status='Verified')

        if not verified_users_df.empty:
            # Prepare DataFrame for display
            verified_display_df = verified_users_df.rename(columns={
                'created_at': 'Created Time',
                'username': 'Username',
                'email': 'Email',
                'status': 'Status',
                # Assuming this column exists after verification
                'verification_time': 'Verify Time'
            })
            # Select and reorder columns for display
            display_cols_verified = ['Username', 'Email',
                                     'Status', 'Created Time', 'Verify Time']
            # Filter out columns that might not exist yet if verification_time is added later
            display_cols_verified = [
                col for col in display_cols_verified if col in verified_display_df.columns]

            st.dataframe(
                verified_display_df[display_cols_verified], use_container_width=True, hide_index=True)
        else:
            st.info("No verified users found.")

        # --- Section: Employee Attendance ---
        # Consider if this belongs here or in the main dashboard
        st.subheader("🕒 Recent Employee Attendance")
        employee_attendance_df = user_data_service.get_employee_attendance()

        if not employee_attendance_df.empty:
            st.dataframe(employee_attendance_df,
                         use_container_width=True, hide_index=True)
        else:
            st.info("No recent attendance data available.")

    except AttributeError as e:
        st.error(
            f"Error accessing UserDataService method: {e}. Service might not be initialized correctly.")
    except Exception as e:
        st.error(f"An error occurred on the verification page: {e}")
