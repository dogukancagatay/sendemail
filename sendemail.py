#!/usr/bin/env python

#########################
#
# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.
#
# Author: Dogukan Cagatay <dcagatay@gmail.com>
# February 8, 2014
#
#########################

import smtplib
import argparse
import os, sys
from email.mime.multipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.mime.text import MIMEText
from email.Header import Header
from email.Utils import COMMASPACE, formatdate, parseaddr, formataddr
import email.encoders as Encoders
from ssl import SSLError 

def main():
    parser = argparse.ArgumentParser()
    group = parser.add_argument_group('Address Arguments')
    group.add_argument('-f', help='From address', required=True)
    group.add_argument('-fn','--from_name', help='Name of the sender', default='', type=str)

    group.add_argument('-t', help='To address(es)', default=[], nargs='+')
    group.add_argument('-cc', help='CC address(es)', default=[], nargs='+')
    group.add_argument('-bcc', help='BCC address(es)', default=[], nargs='+')

    group = parser.add_argument_group('Email Arguments')
    group.add_argument('-u','--subject', help='Email subject', type=str)
    group.add_argument('-m','--message', help='Email content', type=str, default='')
    group.add_argument('stdin', help="Email message from stdin.", nargs='?', type=argparse.FileType('r'), default=sys.stdin)
    group.add_argument('--html', help='Send as HTML', action="store_true", default=False)
    group.add_argument('-a','--attach', help='Attachment(s)', default=[], nargs='+')

    group = parser.add_argument_group('Server Specification')
    group.add_argument('-s','--server', help='SMTP server address', required=True)
    group.add_argument('-p','--port', help='SMTP server port', type=int, default=25)
    group.add_argument('-xu','--username', help='Username for SMTP server', default=None)
    group.add_argument('-xp','--password', help='Password for SMTP server', default=None)
    group.add_argument('--ssl', help='Use SSL', action="store_true", default=False)
    group.add_argument('--tls', help='Use STARTTLS, same with --starttls', action="store_true", default=False)
    group.add_argument('--starttls', help='Use STARTTLS, same with --tls', action="store_true", default=False)

    args = parser.parse_args()

    old_smtplib_fix() ## if necessary

    sendemail(from_addr=args.f,from_name=args.from_name.decode('utf8'), to_addrs=args.t, cc_addrs=args.cc, bcc_addrs=args.bcc, subject=args.subject.decode('utf8'), message=(args.message.decode('utf8') or args.stdin.read().decode('utf8')), html=args.html, attachments=args.attach, server=args.server, port=args.port, username=args.username, password=args.password, ssl=args.ssl, tls=(args.tls or args.starttls)) 

def sendemail(from_addr=None, from_name='', to_addrs=[], subject='', cc_addrs=[], bcc_addrs=[],
              message=None, html=False, attachments=[],
              server='localhost', port=25,
              username=None, password=None, ssl=False, tls=False):
    '''Some parts of this function was originally a part of this code
    https://github.com/mozilla/autophone/blob/master/sendemail.py'''

    assert type(to_addrs)==list
    assert type(cc_addrs)==list
    assert type(bcc_addrs)==list
    assert type(attachments)==list

    if not from_addr or (not to_addrs and not cc_addrs and not bcc_addrs):
        raise Exception("At least one from address and one of to, cc, bcc address must be specified.")

    if ssl and tls:
        raise Exception("SSL and TLS cannot be used at the same time")

    if ssl:
        try:
            server = smtplib.SMTP_SSL(server, port)
        except SSLError:
            print "ERROR: Your email didn't send. Your server may not support SSL connection. Try --tls argument."
            exit()
        except:
            print "Unexpected error:", sys.exc_info()[0]
            raise

    else:
        server = smtplib.SMTP(server, port)

    if not ssl and tls:
        try:
            server.ehlo()
            server.starttls()
            server.ehlo()
        except smtplib.SMTPException:
            print "ERROR: Your email didn't send. Your server may not support STARTTLS connection. Try --ssl argument."
            exit()
        except:
            print "Unexpected error:", sys.exc_info()[0]
            raise


        
    if username and password:
        try:
            server.login(username, password)
        except smtplib.SMTPAuthenticationError as e:
            print "ERROR: Your email didn't send.\nREASON: Server refused your username/password.\n"
            print "SERVER RESPONSE: ", e
            server.quit()
            exit()

    msg = MIMEMultipart()
    msg.preamble = subject.encode('utf-8')

    if not html:
        msg.attach(MIMEText(message.encode('utf-8'), 'plain', 'utf8'))
    else:
        msg.attach(MIMEText(message.encode('utf-8'), 'html', 'utf8'))

    #utf 8
    from_name = str(Header(unicode(from_name),'utf8'))

    msg['From'] = formataddr((from_name, from_addr))
    msg['To'] = ', '.join(to_addrs)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = Header(unicode(subject),'utf-8')

    if not cc_addrs:
        msg['Cc'] = ', '.join(cc_addrs)

    if not bcc_addrs:
        msg['Bcc'] = ', '.join(bcc_addrs)


    for f in attachments:
        part = MIMEBase('application', "octet-stream")
        part.set_payload( open(f,"rb").read() )
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(f))
        msg.attach(part)
 
    try:
        server.sendmail(from_addr, to_addrs + cc_addrs + bcc_addrs, msg.as_string())
    except smtplib.SMTPSenderRefused as e:
        print "ERROR: Your email didn't send."
        print "SERVER RESPONSE: ", e
        server.quit()
        exit()
    except smtplib.SMTPRecipientsRefused as e:
        print "ERROR: Your email didn't send."
        print "SERVER RESPONSE: ", e
        server.quit()
        exit()
    except smtplib.SMTPDataError as e:
        print "ERROR: Your email didn't send."
        print "SERVER RESPONSE: ", e
        server.quit()
        exit()
    except:
        print "Unexpected error:", sys.exc_info()[0]
        raise

    print "SUCCESS: Your email is sent successfully."

    server.quit()

def old_smtplib_fix():
    if sys.hexversion < 0x020603f0:
        # versions earlier than 2.6.3 have a bug in smtplib when sending over SSL:
        #     http://bugs.python.org/issue4066
        import socket
        import ssl

        def _get_socket_fixed(self, host, port, timeout):
            if self.debuglevel > 0: print>>sys.stderr, 'connect:', (host, port)
            new_socket = socket.create_connection((host, port), timeout)
            new_socket = ssl.wrap_socket(new_socket, self.keyfile, self.certfile)
            self.file = smtplib.SSLFakeFile(new_socket)
            return new_socket

        smtplib.SMTP_SSL._get_socket = _get_socket_fixed

if __name__ == "__main__":
    main()
