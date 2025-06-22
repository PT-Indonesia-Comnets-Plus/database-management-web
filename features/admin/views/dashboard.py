import streamlit as st
from core.services.UserDataService import UserDataService  # Import untuk type hinting
import datetime  # Added for date input


def app(user_data_service: UserDataService):
    """
    Displays the Admin Dashboard, focusing on user activity metrics.

    Args:
        user_data_service: An instance of UserDataService to fetch user activity data.
    """
    st.title("📊 Admin Dashboard")
    st.markdown("Overview of user activity and system metrics.")

    # Key Metrics Section
    st.subheader("Key Metrics")
    col1, col2, col3 = st.columns(3)
    try:
        pending_users_df = user_data_service.get_users(status='Pending')
        verified_users_df = user_data_service.get_users(status='Verified')

        # Get all employee users regardless of status
        try:
            all_users_df = user_data_service.get_all_employee_users()
            col1.metric("Total Registered Users", len(all_users_df))
        except Exception as e:
            col1.metric("Total Registered Users", "Error")
            st.sidebar.error(f"Could not display total user count: {e}")

        col2.metric("Users Pending Verification", len(pending_users_df))
        col3.metric("Verified Users", len(verified_users_df))

    except Exception as e:
        st.warning(f"Could not display user counts: {e}")
        if 'col1' in locals():
            col1.metric("Total Registered Users", "Error")
        if 'col2' in locals():
            col2.metric("Users Pending Verification", "Error")
        if 'col3' in locals():
            col3.metric("Verified Users", "Error")

    st.divider()

    # User Login/Logout Activity Section
    st.subheader("User Login/Logout Activity")

    # Date range selector
    # Default to last 7 days
    today = datetime.date.today()
    default_start_date = today - datetime.timedelta(days=6)

    col_date1, col_date2 = st.columns(2)
    with col_date1:
        start_date = st.date_input(
            "Start Date", value=default_start_date, max_value=today)
    with col_date2:
        end_date = st.date_input(
            "End Date", value=today, min_value=start_date, max_value=today)

    if start_date > end_date:
        st.error("Error: Start date must be before end date.")
    else:
        try:
            # Modify calculate_daily_login_logout_totals to accept date range
            # This assumes your UserDataService can be modified or already supports this
            daily_totals = user_data_service.calculate_daily_login_logout_totals(
                start_date=datetime.datetime.combine(
                    start_date, datetime.datetime.min.time()),
                end_date=datetime.datetime.combine(
                    end_date, datetime.datetime.max.time())
            )

            if not daily_totals:
                st.info(
                    f"No login/logout data available between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}.")
            else:
                # Pass the selected date range to the plotting function as well
                fig = user_data_service.plot_daily_login_logout_totals(
                    daily_totals,
                    plot_start_date=datetime.datetime.combine(
                        start_date, datetime.datetime.min.time()),
                    plot_end_date=datetime.datetime.combine(
                        end_date, datetime.datetime.max.time())
                )
                st.plotly_chart(fig, use_container_width=True)

        except AttributeError as e:
            st.error(
                f"Error accessing UserDataService method: {e}. The service might not support date ranges or the method name is incorrect. Please ensure 'calculate_daily_login_logout_totals' accepts 'start_date' and 'end_date' arguments.")
        except Exception as e:
            st.error(
                f"An error occurred while displaying the login/logout activity: {e}")
