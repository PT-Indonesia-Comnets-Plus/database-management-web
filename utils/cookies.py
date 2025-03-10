from streamlit_cookies_manager import EncryptedCookieManager

# Inisialisasi cookie manager
cookies = EncryptedCookieManager(
    prefix="Iconnet Corp", password="super_secret_key")

# Fungsi untuk menyimpan data pengguna ke dalam cookie


def save_user_to_cookie(username, email, role):
    cookies["username"] = username
    cookies["email"] = email
    cookies["role"] = role
    cookies["signout"] = "False"
    cookies.save()

# Fungsi untuk menghapus data pengguna dari cookie


def clear_user_cookie():
    cookies["username"] = ""
    cookies["email"] = ""
    cookies["role"] = ""
    cookies["signout"] = "True"
    cookies.save()

# Fungsi untuk memuat data dari cookie ke session state


def load_cookie_to_session():
    if not cookies.ready():
        return "", "", "", True
    username = cookies.get("username", "")
    useremail = cookies.get("email", "")
    role = cookies.get("role", "")
    signout = cookies.get("signout", "True") == "True"
    return username, useremail, role, signout
