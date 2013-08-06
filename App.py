import cgi
import pymongo
import re
import sessionDAO
import tornado.ioloop
import tornado.web
import userDAO

__author__ = 'bruno farina'

connection_string = "mongodb://localhost"
connection = pymongo.MongoClient(connection_string)
database = connection.blog

users = userDAO.UserDAO(database)
sessions = sessionDAO.SessionDAO(database)

def validate_signup(username, password, verify, email, errors):
    USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
    PASS_RE = re.compile(r"^.{3,20}$")
    EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")

    errors['username_error'] = ""
    errors['password_error'] = ""
    errors['verify_error'] = ""
    errors['email_error'] = ""

    if not USER_RE.match(username):
        errors['username_error'] = "invalid username. try just letters and numbers"
        return False

    if not PASS_RE.match(password):
        errors['password_error'] = "invalid password."
        return False
    if password != verify:
        errors['verify_error'] = "password must match"
        return False
    if email != "":
        if not EMAIL_RE.match(email):
            errors['email_error'] = "invalid email address"
            return False
    return True

class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        cookie = self.get_cookie("session")
        username = sessions.get_username(cookie)
        self.render('templates/blog_template.html', username=username)      
    
class SignupHandler(tornado.web.RequestHandler):
    def get(self):
        return self.render("templates/signup.html",
                           username="", password="",
                           password_error="",
                           email="", username_error="", email_error="",
                           verify_error="")
        
    def post(self):
        email = self.get_argument("email")
        username = self.get_argument("username")
        password = self.get_argument("password")
        verify = self.get_argument("verify")
    
        # set these up in case we have an error case
        errors = {'username': cgi.escape(username), 'email': cgi.escape(email)}
        if validate_signup(username, password, verify, email, errors):
    
            if not users.add_user(username, password, email):
                # this was a duplicate
                errors['username_error'] = "Username already in use. Please choose another"
                return self.render("views/signup", errors)
    
            session_id = sessions.start_session(username)
            print (session_id)
            self.set_cookie("session", session_id)
            self.redirect("/welcome")
        else:
            print ("user did not validate")
            return self.render("templates/signup.html", errors)

class LoginHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('templates/login.html', username="", password="", login_error="")
        
    def post(self):
        username = self.get_argument("username")
        password = self.get_argument("password")
    
        print ("user submitted ", username, "pass ", password)
    
        user_record = users.validate_login(username, password)
        if user_record:
            # username is stored in the user collection in the _id key
            session_id = sessions.start_session(user_record['_id'])
    
            if session_id is None:
                self.redirect("/internal_error")
    
            cookie = session_id

            self.set_cookie("session", cookie)
    
            self.redirect("/welcome")
    
        else:
            return self.render("templates/login.html",
                               username=cgi.escape(username),
                               password="",
                               login_error="Invalid Login")     

class WelcomeHandler(tornado.web.RequestHandler):
    def get(self):
        # check for a cookie, if present, then extract value
    
        cookie = self.get_cookie("session")
        username = sessions.get_username(cookie)  # see if user is logged in
        if username is None:
            print ("welcome: can't identify user...redirecting to signup")
            self.redirect("templates/signup.html")
    
        return self.render("templates/welcome.html", username=username)  
    
class LogoutHandler(tornado.web.RequestHandler):
    def get(self):
        cookie = self.get_cookie("session")
        sessions.end_session(cookie)
        self.set_cookie("session", "")
        self.redirect("/signup")

class InternalError(tornado.web.RequestHandler):
    def get(self):
        return self.render("templates/error_template.html", error ="System has encountered a DB error")        

def main():
    application = tornado.web.Application([
            (r"/", IndexHandler),
            (r"/login", LoginHandler),
            (r"/signup", SignupHandler),
            (r"/welcome", WelcomeHandler),
            (r"/logout", LogoutHandler),
            (r"/internalerror", InternalError),
    ])
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
