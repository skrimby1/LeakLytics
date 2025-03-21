import umail
import ustrftime

'''umail.SMTP(host, port, [ssl, username, password])

host - smtp server
port - server's port number
ssl - set True when SSL is required by the server
username - my username/email to the server
password - my password'''
####################################################################################

smtp = umail.SMTP('smtp.gmail.com', 587, username='my@gmail.com', password='mypassword')
smtp.to('someones@gmail.com')
smtp.send("This is an example.")
smtp.quit()