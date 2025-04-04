import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st
from datetime import datetime
import re


class EmailService:
    def __init__(self, smtp_server, smtp_port, smtp_username, smtp_password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password

    def send_email(self, recipient, subject, body):
        try:
            # Membuat pesan email
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))

            # Mengirim email menggunakan SMTP
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.smtp_username, recipient, msg.as_string())

            st.success(f"Email sent successfully to {recipient}")
        except Exception as e:
            st.error(f"Failed to send email: {e}")

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
                <div class="email-body">
                    <p>Hi {user.display_name or user.email},</p>
                    <p>Please verify your email address by clicking the button below:</p>
                    <p style="text-align: center;">
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
