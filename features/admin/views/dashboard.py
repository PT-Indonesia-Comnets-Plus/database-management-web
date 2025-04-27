import streamlit as st


def app(user_data):
    # Render konten admin jika pengguna adalah admin
    st.title("Admin Dashboard")
    daily_totals = user_data.calculate_daily_login_logout_totals()
    st.plotly_chart(user_data.plot_daily_login_logout_totals(
        daily_totals), use_container_width=True)
