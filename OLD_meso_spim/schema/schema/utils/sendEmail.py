#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 12 09:52:25 2018

@author: tanmay
"""
"""
The script sends email to users with the summary report of the mouse.
"""

import smtplib
import sys
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.path.append("/data/datajoint/DataJoint_mathis/")
# import login

emailDict = {
    "mackenzie": "adaptivemotorlab@gmail.com",
    "adrian": "hoffmann@rowland.harvard.edu",
    "alexander": "adaptivemotorlab@gmail.com",
    "gary": "gkane@rowland.harvard.edu",
    "tanmay": "nath@rowland.harvard.edu",
    "mathislab": "adaptivemotorlab@gmail.com",
}


def email(user, filename, error, message):
    fromaddr = "adaptivemotorlab@gmail.com"
    # specify users who will receive the email.
    toaddr = ["adaptivemotorlab@gmail.com", emailDict[user]]
    msg = MIMEMultipart()
    msg["From"] = fromaddr
    msg["To"] = ", ".join(toaddr)
    text = msg.as_string()
    if error:
        msg["Subject"] = (
            "Sorry the pipeline failed for Mouse: %s, Training performance on %s and %s"
            % (
                filename.split("_")[1],
                filename.split("_")[2],
                filename.split("_")[3].split(".")[0],
            )
        )
        body = message
        msg.attach(MIMEText(body, "plain"))
    else:
        msg["Subject"] = str(
            "Mouse: "
            + filename.split("_")[1]
            + ". Training Performance on  "
            + filename.split("_")[2]
            + " "
            + filename.split("_")[3].split(".")[0]
        )

        body = str(
            "Please find attached the joystick trajectory summary report for the mouse "
            + filename.split("_")[1]
            + ". The training performance reported here is on "
            + filename.split("_")[2]
            + " and "
            + filename.split("_")[3].split(".")[0]
        )
        msg.attach(MIMEText(body, "plain"))
        attachment = open(filename, "rb")
        part = MIMEBase("application", "octet-stream")
        part.set_payload((attachment).read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment; filename= %s" % filename)
        msg.attach(part)
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    pwd = "rvasadrjyydauvry"  # @Adaptivemotorlab2019#'#login.getEmailPassword()
    server.login(fromaddr, pwd)
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.quit()
    print("Email Sent!")
    return ()
