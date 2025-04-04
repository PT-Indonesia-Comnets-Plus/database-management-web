from datetime import datetime
import pandas as pd


class UserService:
    def __init__(self, firestore, auth):
        self.fs = firestore
        self.auth = auth

    def get_unverified_users(self):
        users_ref = self.fs.collection("users")
        query = users_ref.where("status", "==", "Pending")
        docs = query.stream()

        users_list = []
        for doc in docs:
            user_data = doc.to_dict()
            user_data["UID"] = doc.id
            users_list.append(user_data)

        return pd.DataFrame(users_list)

    def get_verified_users(self):
        users_ref = self.fs.collection("users")
        query = users_ref.where("status", "==", "Verified")
        docs = query.stream()

        users_list = []
        for doc in docs:
            user_data = doc.to_dict()
            user_data["UID"] = doc.id
            users_list.append(user_data)

        return pd.DataFrame(users_list)

    def verify_user(self, uid):
        user = self.auth.get_user(uid)

        # Perbarui status pengguna di Firebase Authentication
        self.auth.update_user(uid, email_verified=True)

        # Perbarui status pengguna di Firestore
        user_ref = self.fs.collection("users").document(uid)
        verification_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        user_ref.update({
            "status": "Verified",
            "verification_time": verification_time
        })

        return f"User with email {user.email} has been verified."
