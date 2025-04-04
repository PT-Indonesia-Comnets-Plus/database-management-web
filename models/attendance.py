# filepath: c:\Users\rizky\OneDrive\Dokumen\GitHub\intern-iconnet\models\attendance.py
from datetime import datetime
from firebase_admin import firestore


class Attendance:
    """
    A class to handle employee attendance data.
    """

    def __init__(self, fs):
        self.fs = fs

    def save_login_logout(self, username, event_type):
        """
        Save login or logout event for a user.
        """
        now = datetime.now()
        date = now.strftime("%d-%m-%Y")
        time = now.strftime("%H:%M:%S")

        doc_ref = self.fs.collection("employee attendance").document(username)

        try:
            if event_type == "login":
                doc_ref.update({
                    f"activity.{date}.Login_Time": firestore.ArrayUnion([time])
                })
            elif event_type == "logout":
                doc_ref.update({
                    f"activity.{date}.Logout_Time": firestore.ArrayUnion([time])
                })
        except Exception:
            doc_ref.set({
                "activity": {
                    date: {
                        "Login_Time": [time] if event_type == "login" else [],
                        "Logout_Time": [time] if event_type == "logout" else []
                    }
                }
            }, merge=True)

    def get_attendance_report(self, username):
        """
        Retrieve attendance data for a specific user.
        """
        doc_ref = self.fs.collection("employee attendance").document(username)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            return None
