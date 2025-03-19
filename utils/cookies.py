from streamlit_cookies_manager import EncryptedCookieManager

# Inisialisasi cookie manager
cookies = EncryptedCookieManager(
    prefix="Iconnet_Corp",
    password="super_secret_key"  # Ganti dengan password yang aman
)

# Fungsi untuk menyimpan data pengguna ke dalam cookie


def save_user_to_cookie(username, email, role):
    if cookies.ready():
        cookies["username"] = username
        cookies["email"] = email
        cookies["role"] = role
        cookies["signout"] = "False"
        cookies.save()

# Fungsi untuk menghapus data pengguna dari cookie


def clear_user_cookie():
    if cookies.ready():
        cookies["username"] = ""
        cookies["email"] = ""
        cookies["role"] = ""
        cookies["signout"] = "True"
        cookies.save()

# Fungsi untuk memuat data dari cookie ke session state


def load_cookie_to_session(session_state):
    if cookies.ready():
        session_state.username = cookies.get("username", "")
        session_state.useremail = cookies.get("email", "")
        session_state.role = cookies.get("role", "")
        session_state.signout = cookies.get("signout", "True") == "True"
