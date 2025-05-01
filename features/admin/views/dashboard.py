import streamlit as st
from core.services.UserDataService import UserDataService  # Import untuk type hinting


def app(user_data_service: UserDataService):
    """
    Displays the Admin Dashboard, focusing on user activity metrics.

    Args:
        user_data_service: An instance of UserDataService to fetch user activity data.
    """
    st.title("📊 Admin Dashboard")
    st.markdown("Overview of user activity.")

    try:
        # Calculate and plot daily login/logout totals
        st.subheader("User Login/Logout Activity (Last 7 Days)")
        daily_totals = user_data_service.calculate_daily_login_logout_totals()

        if not daily_totals:
            st.info("No login/logout data available for the last 7 days.")
        else:
            fig = user_data_service.plot_daily_login_logout_totals(
                daily_totals)
            st.plotly_chart(fig, use_container_width=True)

    except AttributeError as e:
        st.error(
            f"Error accessing UserDataService method: {e}. Service might not be initialized correctly.")
    except Exception as e:
        st.error(f"An error occurred while displaying the dashboard: {e}")

    # Anda bisa menambahkan metrik lain dari UserDataService di sini jika ada
    # Misalnya: Jumlah pengguna pending, jumlah pengguna terverifikasi, dll.
    try:
        pending_users_df = user_data_service.get_users(status='Pending')
        verified_users_df = user_data_service.get_users(status='Verified')
        col1, col2 = st.columns(2)
        col1.metric("Users Pending Verification", len(pending_users_df))
        col2.metric("Verified Users", len(verified_users_df))
    except Exception as e:
        st.warning(f"Could not display user counts: {e}")
