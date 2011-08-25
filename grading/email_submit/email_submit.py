#!/usr/bin/env python
"""
email_submit.py

Library for dealing with student work submissions via email.

To be used effectively, you also need a mail fetching program that can
send messages to standard output; getmail is recommended.

INTERFACES:

1) When called as 'get-submissions' this program wraps a call to your
   mail fetching program (which you must configure separately),
   setting the EMAIL_SUBMIT_DIRECTORY environment variable if it is
   not set already.

2) When called as 'split-attachments' this program reads a message
   from standard input and saves one or more attachments found in that
   message to the submit directory.  This interface is intended for
   non-interactive use (e.g., as an MDA_external destination for
   getmail).  Attachments are saved with the sender's email address
   prepended to the filename.  This associates the sender's email with
   the file, so that the file can later be sent back to the sender via
   the send-feedback interface.

3) When called as 'send-feedback' this program walks over the files in
   the submit directory and emails them back to their original senders
   (as attachments) using Python's smtplib package.  You must
   configure your connection to an SMTP server by setting
   SMTP_CONNECTION_CLASS and SMTP_ARGS in this script.
"""
import email, smtplib, mimetypes, optparse, sys, os, logging

from email.mime.multipart import MIMEMultipart, MIMEBase
try:
    from email.mime.multipart import MIMEText # 2.7
except ImportError:
    from email.mime.text import MIMEText # 2.6

#####
# Globals for configuration
#####

# name and arguments of mail fetching program
MAIL_FETCH_PROGRAM = 'getmail' # must be in PATH
MAIL_FETCH_ARGS = ('-r', 'your_getmail_config_path')

# content types to prefer if there are multiple attachments
# (leave empty if you want to save all unexcluded attachments)
PREFER_CONTENT_TYPES = (
    'application/pdf',
    'application/msword',
#    'application/vnd.ms-powerpoint',
#    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
#    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
#    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/plain',
    'text/rtf',
    'application/rtf',
)

# content types to never save
# (leave empty if you want to save all attachments)
EXCLUDE_CONTENT_TYPES = (
    'text/x-vcard',
    'text/directory',
)

# user customization options
OPTIONS = {
    'email': 'Your email address',
    'name': 'Your Name', # used in sending email and in feedback message
    'feedback_subject': 'Feedback on your work',
    'submit_directory': os.getcwd(), # may be overriden by command line option
    'log_file': 'email_submit.log', # may be overriden by command line option
    'log_level': logging.INFO,
    'overwrite_existing': False, # if False, always saves attachments under a unique name
}

# feedback message template
FEEDBACK_MSG = """
Hi,

I've graded your work.  My comments and your grade are in the attached file.

Best,
%(signature)s
"""

# the class to use to establish an SMTP connection to send feedback messages
# should be smtplib.SMTP or smtplib.SMTP_SSL
SMTP_CONNECTION_CLASS = smtplib.SMTP

# the arguments to pass to the constructor of SMTP_CONNECTION_CLASS
# when creating a new connection.
# For smtplib.SMTP, these are: host, port, local_hostname, timeout
# For smtplib.SMTP_SSL, they are: host, port, local_hostname, keyfile, certfile, timeout
# See the smtplib documentation.
SMTP_ARGS = ('localhost',)

# does the server require a login?
SMTP_REQUIRES_LOGIN = False

# login credentials (only used if SMTP_REQUIRES_LOGIN is True)
SMTP_USERNAME = ''
SMTP_PASSWORD = ''

#####
# 'inbound' functions: for saving attachments
#####
class SubmissionError(Exception):
    pass

def get_base_filename(m):
    "Return the base name (sender's email from the original message) to prepend to saved attachments"
    # for now, the filename acts as the "database" associating the
    # sender's email address with their submitted work.
    # The format is: <email address>::<modified original name, with extension>
    # Here, we're just concerned to return the email address of the sender; the other parts
    # are appended later 
    # Note: according to RFC3696, ':' is not a valid character for email addresses, so '::'
    # is a good choice for a separator between email address and original filename

    sender = m['From'] or m['X-Envelope-Sender']
    if not sender:
        raise SubmissionError("No sender found for message")

    name, addr = email.utils.parseaddr(sender)

    return addr

def get_mod_original_filename(m):
    "Return the original filename of an attachment part, replacing ' ' and '::' with '-'"
    orig = m.get_filename()
    if not orig:
        # some submissions may not come as an attachment part with a filename
        orig = 'unnamed-msg-part'

    # replacing spaces makes for tidier shell interactions; replacing
    # '::' ensures we can later split a filename at '::' and get the
    # original email and the filename as parts
    return orig.replace(' ', '-').replace('::', '-')

def get_filename(prefix, m):
    "Return the complete path and filename to save an attachment under"
    orig = get_mod_original_filename(m)
    d = determine_submit_directory()
    candidate = os.path.join(d, prefix + '::' + orig)

    # generate a unique filename if the user doesn't want files to be overwritten
    # preserve extension for platforms that rely on it
    if not OPTIONS['overwrite_existing']:
        # these ugly machinations are necessary because os.path.splitext gets 
        # confused by the '.'s in the email address portion of the filename
        orig_base, sep, ext = orig.rpartition('.')
        if not sep: # orig_base is empty and ext == orig
            orig_base, sep, ext = orig, '', ''

        base = d + prefix + '::' + orig_base
        i = 1
        while os.path.exists(candidate):
            candidate = base + '-dup' + str(i) + sep + ext
            i += 1

    return candidate

def write_payload(fname, part):
    "Write part to file named by fname, decoding payload if necessary"
    try:
        # TODO: is it right to always write encoded parts in binary
        # mode?  that is, does the Content-Transfer-Encoding header
        # correlate with or cross-cut the distinction between writing
        # in text vs. binary mode?
        if part['Content-Transfer-Encoding']:
            f = open(fname, 'wb')
            f.write(part.get_payload(decode=True))
        else:
            f = open(fname, 'w')
            f.write(part.get_payload())

    finally:
        f.close()

def determine_submit_directory():
    """
    Return the directory in which attachments should be saved or found.

    Directory is the first of the following values that is found:
    1. the value of the EMAIL_SUBMIT_DIRECTORY environment variable
       (set by the wrap_fetcher interface)
    2. the value of the -d / --directory command line option
    3. the value of OPTIONS['submit_directory']
    4. the current working directory
    """
    dirs = [
        (os.environ.get('EMAIL_SUBMIT_DIRECTORY', None)),
        # implicit here: OPTIONS['submit_directory'] will be set from the
        # command line if provided, overriding the static value defined
        # above
        OPTIONS.get('submit_directory', None),
        os.getcwd()
    ]

    for d in dirs:
        if d:
            if not os.path.isdir(d):
                raise SubmissionError("%s is not a directory" % d)
            return d
    else:
        # this is very bad...we don't even have a current directory?
        raise SubmissionError("No submit directory found!") 

def save_attachments(m):
    "Find and save the attached assignment(s) in a message."
    basename = get_base_filename(m)
    found_attachments = []

    # some mailers may not include a Content-Disposition: attachment... header,
    # so we also consider non-attachment parts that are of preferred content types
    for part in m.walk():
        disp = part['Content-Disposition']
        if (disp and disp[0:10].lower() == 'attachment') or \
           part.get_content_type() in PREFER_CONTENT_TYPES:
            found_attachments.append(part)

    good_attachments = filter(lambda p: p.get_content_type() not in EXCLUDE_CONTENT_TYPES,
                              found_attachments)

    if len(good_attachments) == 0:
        raise SubmissionError("No unexcluded attachments found in message")

    elif len(good_attachments) == 1:
        # the default, expected case: write the sole unexcluded attachment to a
        # file with the name determined by get_filename
        att = good_attachments[0]
        fname = get_filename(basename, att)
        write_payload(fname, att)
        logging.info("Wrote 1 attachment to %s" % fname)

    else:
        # more than one unexcluded attachment; make a (feeble) effort
        # to determine which is the real assignment, otherwise save all attachments
        prefs = filter(lambda p: p.get_content_type() in PREFER_CONTENT_TYPES,
                       good_attachments)
        if len(prefs) == 1:
            att = prefs[0]
            fname = get_filename(basename, att)
            write_payload(fname, att)
            logging.info("Wrote 1 preferred attachment to %s" % fname)
        else:
            logging.info(
              "Could not determine a preferred attachment; saving %d unexcluded attachments." %
              len(good_attachments))
            for i in xrange(len(good_attachments)):
                fname = get_filename(basename, good_attachments[i])
                write_payload(fname, good_attachments[i])
                logging.info("Wrote 1 attachment to %s" % fname)

#####
# 'outbound' functions: for sending feedback messages, with graded work attached
#####
class FeedbackError(Exception):
    pass

def create_message(path):
    "Return a Message object with the file at path attached"
    d, fname = os.path.split(path)

    # create the outer message
    msg = MIMEMultipart()
    msg['From'] = email.utils.formataddr((OPTIONS['name'], OPTIONS['email']))
    
    fname_parts = fname.split('::')
    if len(fname_parts) == 2:
        to_addr, att_name = fname_parts[0], fname_parts[1]
    else:
        raise FeedbackError("Bad filename: %s; can't determine recipient or attachment name" %
                            fname)

    msg['To'] = to_addr
    msg['Subject'] = OPTIONS['feedback_subject']

    # first part: the text/plain message derived from FEEDBACK_MSG
    body = MIMEText(FEEDBACK_MSG % {'signature' : OPTIONS['name']})
    msg.attach(body)

    # second part: attachment 
    ctype, encoding = mimetypes.guess_type(path)
    if ctype is None or encoding is not None:
        ctype = 'application/octet-stream'
    maintype, subtype = ctype.split('/', 1)
    
    f = open(path, 'rb')

    att = MIMEBase(maintype, subtype)
    att.set_payload(f.read())
    email.encoders.encode_base64(att)
    att.add_header('Content-Disposition', 'attachment', filename=att_name)
    msg.attach(att)

    logging.info("Created feedback message for %s from file %s" % (to_addr, path))

    return msg
    
def send_message(m):
    "Send a feedback message to the given SMTP object"
    from_addr = OPTIONS['email']
    to_addr = m['To']

    # NOTE: we make a per-message connection because some servers (notably Exim4) seem to
    # dislike sending multiple messages via smtplib on the same connection
    if isinstance(SMTP_ARGS, dict):
        smtp = SMTP_CONNECTION_CLASS(**SMTP_ARGS)
    else:
        smtp = SMTP_CONNECTION_CLASS(*SMTP_ARGS)
        
    if SMTP_REQUIRES_LOGIN:
        smtp.login(SMTP_USERNAME, SMTP_PASSWORD)

    try:
        logging.info("Sending feedback message to %s" % to_addr) 
        result =  smtp.sendmail(from_addr, to_addr, m.as_string())
    finally:
        smtp.quit()
    
    return result
    
#####
# toplevel interfaces
#####
def act_as_MDA():
    """
    Read a message from standard input, split off attachments, and save them in the submit
    directory.
    """
    logging.info("INTERFACE: ACTING AS MDA")
    logging.info("Submit directory is: %s" % determine_submit_directory())
                 
    failures = 0
    try:
        # read (one and only one) message from stdin
        msg = email.message_from_file(sys.stdin)
        # save attachments from the message 
        save_attachments(msg)
    except SubmissionError, e:
        logging.error(str(e))
        failures += 1

    exit(failures)
    
def wrap_fetcher():
    """
    Determine a directory to save attachments in, set the
    EMAIL_SUBMIT_DIRECTORY environment variable if isn't already, then
    call the mail fetching program (which should be configured to
    route messages back to the act_as_MDA interface).
    """
    logging.info("INTERFACE: WRAPPER FOR MAIL FETCHING PROGRAM")

    # set the EMAIL_SUBMIT_DIRECTORY env variable
    # NOTE: if it was already set, this should leave its value
    # unchanged, since determine_submit_directory checks the value
    # first
    d = determine_submit_directory()
    logging.info("Submit directory is: %s" % d)
    os.environ['EMAIL_SUBMIT_DIRECTORY'] = d
    
    # then exec the mail fetcher in this environment
    # NOTE: MAIL_FETCH_PROGRAM is passed twice so that it's own name is the value of argv[0]
    os.execlp(MAIL_FETCH_PROGRAM, MAIL_FETCH_PROGRAM, *MAIL_FETCH_ARGS)

def send_feedback_emails():
    """
    Walk over the files in the submit directory and email each back to
    the address at the beginning of its filename.
    """
    logging.info("INTERFACE: SENDING FEEDBACK MESSAGES")

    d = determine_submit_directory()
    logging.info("Submit directory is: %s" % d)

    failures = 0

    for f in os.listdir(d):
        p = os.path.join(d, f)
        if not os.path.isfile(p):
            continue
        try:
            m = create_message(p)
            result = send_message(m)
        except FeedbackError, e:
            failures += 1
            logging.error(str(e))
            continue
        finally:
            logging.info("%d errors while sending feedback messages" % failures)
    
    exit(failures)


if __name__ == '__main__':
    # command line options
    parser = optparse.OptionParser(usage='USAGE: %prog [options]')
    parser.add_option('-d', '--directory', dest='submit_directory',
                      help='A directory in which to find or save attachments')
    parser.add_option('-l', '--log', dest='log_file',
                      help='A file in which to log warnings, messages, and errors')
    (cmd_opts, args) = parser.parse_args()

    # update OPTIONS on the basis of command-line options
    if cmd_opts.submit_directory:
        OPTIONS['submit_directory'] = cmd_opts.submit_directory
    if cmd_opts.log_file:
        OPTIONS['log_file'] = cmd_opts.log_file

    # set up logging
    logging.basicConfig(filename=OPTIONS['log_file'], level=OPTIONS['log_level'])

    # dispatch on program name to determine which interface to run
    prog_name = os.path.basename(sys.argv[0])

    try:
        if prog_name.endswith('get-submissions'):
            wrap_fetcher()
        elif prog_name.endswith('split-attachments'):
            act_as_MDA()
        elif prog_name.endswith('send-feedback'):
            send_feedback_emails()
        else:
            print __doc__
            parser.print_help()
    except Exception, e:
        logging.error("Uncaught exception: %s" % str(e))
    finally:
        logging.shutdown()

# TODO LIST
# 2. Move or rename files when feedback has been sent.
# 3. Interface to create feedback files (for people who can't or don't want to modify original attachments)

