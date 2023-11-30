"""Created on Thu Apr 12 09:52:25 2018.

@author: tanmay.
The script sends email to users with the summary report of the mouse.
"""
import smtplib
import sys
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

sys.path.append("/data/datajoint/DataJoint_mathis/")
# import login


def send_report_email(email, filename, attachment_file, message, error=False):
    """Send email to users with the summary report of the mouse."""
    from_addr = "adaptivemotorlab@gmail.com"
    # specify users who will receive the email.
    to_addr = ["adaptivemotorlab@gmail.com", email]
    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addr)
    text = msg.as_string()

    scan_name = Path(filename).name
    print(filename)

    if error:
        msg["Subject"] = f"Sorry the pipeline failed for Scan: {scan_name}"
        body = f"Error running the pipeline on scan file: {scan_name}"
        msg.attach(MIMEText(body, "plain"))
    else:
        msg["Subject"] = str(f"Scan segmentation for image: {scan_name}")

        body = (
            f"Please find attached the relevant plots of segmentation for the scan file {scan_name}\n"
            + message
        )

        msg.attach(MIMEText(body, "plain"))
        with Path(filename).open(mode="rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition", "attachment; filename= %s" % filename
            )
            msg.attach(part)
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    pwd = (
        "rvasadrjyydauvry"  # @Adaptivemotorlab2019#'#login.getEmailPassword()
    )
    server.login(from_addr, pwd)
    text = msg.as_string()
    server.sendmail(from_addr, to_addr, text)
    server.quit()
    print("Email Sent!")
    return ()
