from streamlit_cookies_manager import EncryptedCookieManager
import streamlit as st


cookies = EncryptedCookieManager(
    prefix="Iconnet_Corp",
    password="super_secret_key"
)


# Periksa status cookies
if not cookies.ready():
    st.stop()


def save_user_to_cookie(username, email, role):
    if cookies.ready():
        try:
            cookies["username"] = username
            cookies["email"] = email
            cookies["role"] = role
            cookies["signout"] = "False"
            cookies.save()
        except Exception as e:
            st.error(f"Gagal menyimpan cookies: {e}")
    else:
        st.warning("Cookies belum siap. Tidak dapat menyimpan data.")


def clear_user_cookie():
    if cookies.ready():
        cookies["username"] = ""
        cookies["email"] = ""
        cookies["role"] = ""
        cookies["signout"] = "True"
        cookies.save()
    st.session_state.username = ""
    st.session_state.useremail = ""
    st.session_state.role = ""
    st.session_state.signout = True


def load_cookie_to_session(session_state):
    if cookies.ready():
        session_state.username = cookies.get("username", "") or ""
        session_state.useremail = cookies.get("email", "") or ""
        session_state.role = cookies.get("role", "") or ""
        session_state.signout = cookies.get("signout", "True") == "True"
    else:
        session_state.username = ""
        session_state.useremail = ""
        session_state.role = ""
        session_state.signout = True
