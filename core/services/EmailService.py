import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st
from datetime import datetime


class EmailService:
    def __init__(self, smtp_server, smtp_port, smtp_username, smtp_password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password

    def send_email(self, recipient, subject, body):
        try:
            # Validasi konfigurasi email
            if not all([self.smtp_server, self.smtp_port, self.smtp_username, self.smtp_password]):
                st.error("❌ Konfigurasi email tidak lengkap. Hubungi administrator.")
                return False

            # Log konfigurasi (tanpa password)
            st.info(f"🔄 Mengirim email ke {recipient} menggunakan {self.smtp_server}:{self.smtp_port}")

            # Membuat pesan email
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))

            # Mengirim email menggunakan SMTP
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                st.info("🔄 Memulai koneksi STARTTLS...")
                server.starttls()
                
                st.info("🔄 Melakukan autentikasi...")
                server.login(self.smtp_username, self.smtp_password)
                
                st.info("🔄 Mengirim email...")
                server.sendmail(self.smtp_username, recipient, msg.as_string())

            st.success("✅ Email berhasil dikirim!")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            st.error(f"❌ Gagal autentikasi email: {str(e)}")
            st.error("💡 **Solusi:** Pastikan menggunakan App Password Gmail, bukan password biasa!")
            st.info("📋 **Cara membuat App Password Gmail:**")
            st.info("1. Masuk ke Google Account Settings")
            st.info("2. Pilih Security > 2-Step Verification")
            st.info("3. Di bagian bawah, pilih App passwords")
            st.info("4. Buat App password untuk 'Mail'")
            st.info("5. Gunakan App password tersebut di konfigurasi SMTP")
            return False
        except smtplib.SMTPRecipientsRefused as e:
            st.error(f"❌ Email tujuan ditolak: {str(e)}")
            return False
        except smtplib.SMTPServerDisconnected as e:
            st.error(f"❌ Koneksi ke server email terputus: {str(e)}")
            return False
        except Exception as e:
            st.error(f"❌ Gagal mengirim email: {str(e)}")
            st.error(f"**Detail error:** {type(e).__name__}")
            return False

    def send_verification_email(self, recipient, user, verification_link):
        subject = "Verify Your Email Address"
        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .email-container {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: auto;
                    padding: 20px;
                    border: 1px solid #ddd;
                    border-radius: 10px;
                    background-color: #f9f9f9;
                }}
                .email-header {{
                    text-align: center;
                    padding-bottom: 20px;
                }}
                .email-header img {{
                    max-width: 100px;
                }}
                .email-body {{
                    padding: 20px;
                    background-color: #fff;
                    border-radius: 10px;
                }}
                .email-footer {{
                    text-align: center;
                    padding-top: 20px;
                    font-size: 12px;
                    color: #777;
                }}
                .verify-button {{
                    display: inline-block;
                    padding: 10px 20px;
                    margin: 20px 0;
                    font-size: 16px;
                    color: #fff;
                    background-color: #b9c4c6;
                    text-decoration: none;
                    border-radius: 5px;
                }}
                .verify-button:hover {{
                    background-color: #a0b0b2;
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="email-header">
                    <img src="https://raw.githubusercontent.com/rizkyyanuark/intern-iconnet/blob/main/image/static\image\logo_Iconnet.png" alt="Harmon Corp Logo">
                </div>
                <div class="email-body">                    <p>Hi {user.display_name or user.email},</p>
                    <p>Please verify your email address by clicking the button below:</p>
                    <p class="email-text-center">
                        <a href="{verification_link}" class="verify-button">Verify Email</a>
                    </p>
                    <p>If you did not create an account, please ignore this email.</p>
                    <p>Thanks,<br>Harmon Corp Team</p>
                </div>
                <div class="email-footer">
                    <p>&copy; {datetime.now().year} Harmon Corp. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        self.send_email(recipient, subject, body)
