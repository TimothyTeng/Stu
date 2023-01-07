from flask import Flask, render_template, url_for, request, redirect, make_response
import sqlite3
import hashlib
import os.path
from werkzeug.utils import secure_filename
import json

UPLOAD_FOLDER = '/static/css'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
def getUsername():
    db = sqlite3.connect(db_path)
    query = """
    SELECT Username
    FROM Users
    WHERE Email = ?
    """
    cursor=db.execute(query, (request.cookies.get('Email'),))
    result = cursor.fetchall()
    cursor.close()
    db.close()
    return result[0][0]

def encrypt_string(hash_string):
    sha_signature = \
        hashlib.sha256(hash_string.encode()).hexdigest()
    return sha_signature

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "static/Tutor.db")

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = sqlite3.connect(db_path)
db.close()
@app.route("/", methods=["POST","GET"])
def home():
    if request.method == "GET":
        if request.cookies.get('Email') == None:
            return render_template("home.html", login=False)
        else:
            username = getUsername()
            return render_template("home.html", result = username,login=True)
    else:
        email = request.form["email"].lower()
        password = encrypt_string(request.form["password"])
        db = sqlite3.connect(db_path)
        query = """
        SELECT Email, "Password"
        FROM Users
        WHERE Email = ?
        """
        cursor=db.execute(query, (email,))
        result = cursor.fetchall()
        cursor.close()
        db.close()
        if len(result)==0:
            return redirect(url_for("login", error_message="Account doesnt exist"))
        elif result[0][1]!=password:
            return redirect(url_for("login",error_message="Password is wrong"))
        else:
            db = sqlite3.connect(db_path)
            query = """
            SELECT Username
            FROM Users
            WHERE Email = ?
            """
            cursor=db.execute(query, (email,))
            result = cursor.fetchall()
            cursor.close()
            db.close()
            resp = make_response(render_template('home.html', result = result[0][0]))
            resp.set_cookie('Email', email)
            return resp


@app.route("/login", methods=["POST","GET"])
def login():
    if request.method == "GET":
        if request.cookies.get('Email') == None:
            return render_template("login.html")
        else:
            return redirect(url_for("home"))


@app.route("/signup", methods=["POST","GET"])
def signup():
    if request.method == "GET":
        if request.cookies.get('Email') == None:
            return render_template("signup.html")
        else:
            return redirect(url_for("home"))

    else:
        email = request.form["email"].lower()
        username = request.form["username"]
        year = request.form["year"]
        password = encrypt_string(request.form["password"])
        image = request.files["image"]
        if image:
            filename = secure_filename(image.filename)
            image.save("static/images/"+filename)
            imageName = "static/images/"+filename
        else:
            imageName = "static/images/person.jpeg"
        db = sqlite3.connect(db_path)
        query = """
        SELECT Email, "Password"
        FROM Users
        WHERE Email = ?
        """
        cursor=db.execute(query, (email,))
        result = cursor.fetchall()
        cursor.close()
        db.close()
        if len(result)>0:
            return render_template("signup.html", error="This is already an account with this email.")
        else:
            db = sqlite3.connect(db_path)
            query = """
            INSERT INTO Users
            (Email, Password, Username, Year, Image)
            VALUES
            (?,?,?,?,?)
            """
            db.execute(query, (email,password,username,year,imageName))
            db.commit()
            db.close()
            resp = make_response(redirect(url_for("home")))
            resp.set_cookie('Email', email)
            return resp


@app.route("/signout")
def signout():
    resp = make_response(redirect(url_for("home")))
    resp.set_cookie('Email', '', expires=0)
    return resp


@app.route("/profile", methods=["POST","GET"])
def profile():
    if request.method == "GET":
        if request.cookies.get('Email') == None:
            return redirect(url_for("home"))
        else:
            db = sqlite3.connect(db_path)
            query = """
            SELECT Username, Email, Year, Image
            FROM Users
            WHERE Email = ?
            """
            cursor=db.execute(query, (request.cookies.get('Email'),))
            result = cursor.fetchall()
            cursor.close()
            db.close()
            return render_template("profile.html", result = result[0][0], email=result[0][1], year=result[0][2], image=result[0][3], login=True)

@app.route("/editprofile", methods=["POST","GET"])
def editProfile():
    if request.method == "GET":
        if request.cookies.get('Email') == None:
            return redirect(url_for("home"))
        else:
            db = sqlite3.connect(db_path)
            query = """
            SELECT Username, Year
            FROM Users
            WHERE Email = ?
            """
            cursor = db.execute(query, (request.cookies.get('Email'),))
            result = cursor.fetchone()
            cursor.close()
            db.close()
            return render_template("editProfile.html", result=result[0],username=result[0], year=result[1], login=True)
    else:
        if request.cookies.get('Email') == None:
            return redirect(url_for("home"))
        else:
            username = request.form["username"]
            year = request.form["year"]
            password = encrypt_string(request.form["password"])
            image = request.files["image"]
            email = request.cookies.get('Email')
            if image:
                filename = secure_filename(image.filename)
                image.save("static/images/"+filename)
                imageName = "static/images/"+filename
            else:
                db = sqlite3.connect(db_path)
                query = """
                SELECT Image FROM Users WHERE Email=?
                """
                cursor = db.execute(query, (request.cookies.get('Email'),))
                imageName = cursor.fetchone()[0]
                cursor.close()
                db.close()
            db = sqlite3.connect(db_path)
            query = """
            UPDATE Users
            SET Username=?, "Password"=?, Year=?, Image=?
            WHERE Email = ?
            """
            db.execute(query, [username,password,year,imageName,email])
            db.commit()
            db.close()
            return redirect(url_for("profile"))


@app.route("/posts", methods=["GET","POST"])
def posting():
    if request.cookies.get('Email'):
        db = sqlite3.connect(db_path)
        selectedTopics = request.args.getlist("selectedTopics")
        if request.args.get('search'):
            query = """
            SELECT PostID, Posting.Email, Posting.Image, Title, Question, Subject, Topic, Username
            FROM Posting, Subjects, Users
            WHERE Posting.SubjectID = Subjects.SubjectID
            AND Users.Email= Posting.Email
            AND (Title LIKE ?
            OR Question LIKE ?) 
            """
            if selectedTopics == []:
                query += "ORDER BY PostID DESC"
            else:
                for i in range(len(selectedTopics)):
                    if i==0:
                        query += 'AND (Topic = "{}"'.format(selectedTopics[i])
                    else:
                        query += ' OR Topic = "{}"'.format(selectedTopics[i])
                query += ") ORDER BY PostID DESC"
            cursor = db.execute(query, ['%{}%'.format(request.args.get('search')), '%{}%'.format(request.args.get('search'))])
            result = cursor.fetchall()
        else:
            query = """
            SELECT PostID, Posting.Email, Posting.Image, Title, Question, Subject, Topic, Username
            FROM Posting, Subjects, Users
            WHERE Posting.SubjectID = Subjects.SubjectID
            AND Users.Email= Posting.Email
            """
            if selectedTopics == []:
                query += "ORDER BY PostID DESC"
            else:
                for i in range(len(selectedTopics)):
                    if i==0:
                        query += 'AND (Topic = "{}"'.format(selectedTopics[i])
                    else:
                        query += ' OR Topic = "{}"'.format(selectedTopics[i])
                query += ") ORDER BY PostID DESC"
            cursor = db.execute(query)
            result = cursor.fetchall()
        cursor.close()
        db.close()
        db=sqlite3.connect(db_path)
        query = """
        SELECT Responses.PostID, "Responses", ResponseEmail, ResponseID, Images, Username
        FROM Responses, Users
        WHERE Users.Email = Responses.ResponseEmail
        ORDER BY ResponseID DESC
        """
        cursor = db.execute(query)
        responses = cursor.fetchall()
        cursor.close()

        query = """
        SELECT SubjectNames.Subject
        FROM SubjectNames
        """
        cursor = db.execute(query)
        subjects = cursor.fetchall()
        cursor.close()

        query = """
        SELECT Subjects.Subject, Topic
        FROM Subjects
        ORDER BY Subject, Year ASC
        """
        cursor = db.execute(query)
        topics = cursor.fetchall()
        cursor.close()
        db.close()
        username = getUsername()
        return render_template("posts.html",result=username, records=result, login=True, comments=responses, email=request.cookies.get('Email'),subjects=subjects,topics=topics)
    else:
        return redirect(url_for('login'))

@app.route("/addcomment", methods=["GET","POST"])
def addComment():
    comment = request.args.get('Comment')
    postID = request.args.get('PostID')
    responseEmail = request.args.get('ResponseEmail')
    db = sqlite3.connect(db_path)
    query = """
    INSERT INTO Responses
    (PostID, "Responses", ResponseEmail)
    VALUES
    (?,?,?)
    """
    db.execute(query, [postID, comment,responseEmail])
    db.commit()
    query = """
    SELECT "Responses", Users.Username, ResponseID, Images
    FROM Responses, Users
    WHERE ResponseEmail = Users.Email
    AND PostID=?
    ORDER BY Responses.ResponseID DESC
    """
    cursor = db.execute(query, (postID,))
    allComments = cursor.fetchall()
    cursor.close()
    db.close()
    return json.dumps(allComments)


@app.route("/addcommentimage", methods=["GET","POST"])
def addCommentImage():
    try:
        image = request.files["file"]
        filename = secure_filename(image.filename)
        image.save("static/images/commentImages/"+filename)
        imageName = "static/images/commentImages/"+filename
    except:
        imageName = "ImageNotAdded"
    responseID = request.form["ResponseID"]
    db = sqlite3.connect(db_path)
    query ="""
    UPDATE Responses
    SET Images = ?
    WHERE ResponseID = ?
    """
    db.execute(query, [imageName, responseID])
    db.commit()
    db.close()
    return json.dumps(imageName)
    


@app.route("/addpost", methods=["GET", "POST"])
def addPost():
    if request.method == "GET":
        db=sqlite3.connect(db_path)
        query = """
        SELECT Subject
        FROM SubjectNames
        """
        cursor = db.execute(query)
        subjects = cursor.fetchall()
        cursor.close()
        db.close()
        username = getUsername()
        return render_template("postingPage.html",subjects=subjects, result=username)
    else:
        image = request.files["image"]
        if image:
            filename = secure_filename(image.filename)
            image.save("static/images/postingImages/"+filename)
            imageName = "static/images/postingImages/"+filename
        else:
            imageName = "ImageNotAdded"
        subject = request.form["subject"]
        topic = request.form["topic"]
        print(subject, topic)
        title = request.form["title"]
        question = request.form["question"]
        db = sqlite3.connect(db_path)
        query = """
        SELECT SubjectID
        FROM Subjects
        WHERE Subject = ?
        AND Topic = ?
        """
        cursor = db.execute(query, [subject,topic])
        subjectID = cursor.fetchone()[0]
        cursor.close()
        query = """
        INSERT INTO Posting
        (Email, Image, Title, Question, SubjectID)
        VALUES
        (?,?,?,?,?)
        """
        db.execute(query, (request.cookies.get('Email'), imageName, title, question, subjectID))
        db.commit()
        db.close()
        return redirect(url_for('posting'))


@app.route("/getTopics")
def getTopics():
    db=sqlite3.connect(db_path)
    query = """
    SELECT Topic
    FROM Subjects
    WHERE Subject = ?
    """
    cursor = db.execute(query, (request.args.get('subject'),))
    topics = cursor.fetchall()
    cursor.close()
    db.close()
    return json.dumps(topics)

@app.route("/consultations", methods=["POST", "GET"])
def consultations():
    if request.cookies.get('Email'):
        if request.method == "GET":
            username = getUsername()
            db=sqlite3.connect(db_path)
            query = """
            SELECT *, Subject
            FROM ConsultationClasses, Subjects
            WHERE ConsultationClasses.Topic = Subjects.Topic
            """
            cursor = db.execute(query)
            consultations = cursor.fetchall()
            cursor.close()
            query = """
            SELECT Subject
            FROM SubjectNames
            """
            cursor = db.execute(query)
            subjects = cursor.fetchall()
            cursor.close()
            query = """
            SELECT *
            FROM Students
            WHERE StudentEmail = ?
            """
            cursor = db.execute(query, (request.cookies.get('Email'),))
            allSignUpsGET = cursor.fetchall()
            cursor.close()
            db.close()
            db=sqlite3.connect(db_path)
            query = """
            SELECT MessageID, ConsultationID, Message, ConsultationChat.Email, Username
            FROM ConsultationChat, Users
            WHERE Users.Email = ConsultationChat.Email
            ORDER BY MessageID DESC
            """
            cursor = db.execute(query)
            chat = cursor.fetchall()
            cursor.close()
            db.close()
            arr = []
            for i in allSignUpsGET:
                arr.append(i[1])
            print(arr)
            return render_template('consultation.html', result=username, consultations=consultations, subjects=subjects, email=request.cookies.get('Email'), signUp=arr, chat=chat)
        else:
            try:
                topic = request.form['topic']
                title = request.form['title']
                day = request.form['day']
                if len(str(day))<2:
                    day = "0"+str(day)
                month = request.form['month']
                if len(str(month))<2:
                    month = "0"+str(month)
                year = request.form['year']
                date = str(day) + str(month) + str(year)
                maxCapacity = request.form['maxCapacity']
                description = request.form['description']
                db = sqlite3.connect(db_path)
                query = """
                INSERT INTO ConsultationClasses
                (TeacherEmail, Date, Topic, MaxCapacity, Title, Description)
                VALUES
                (?,?,?,?,?,?)
                """
                db.execute(query, [request.cookies.get('Email'), date, topic, maxCapacity, title, description])
                db.commit()
                db.close()
                return redirect(url_for('consultations'))
            except:
                consultationID = request.form["ConsultationID"]
                db= sqlite3.connect(db_path)
                query = """
                SELECT *
                FROM Students
                """
                cursor = db.execute(query)
                allSignUps = cursor.fetchall()
                cursor.close()
                query = """
                SELECT *
                FROM ConsultationClasses
                WHERE ConsultationID=?
                """
                cursor = db.execute(query, [consultationID,])
                consultation = cursor.fetchone()
                cursor.close()
                print(consultation[1], consultation[1]==request.cookies.get('Email'))
                if ((request.cookies.get('Email'),int(consultationID)) in allSignUps) or consultation[1]==request.cookies.get('Email'):
                    db.close()
                else:
                    query = """
                    INSERT INTO Students
                    (StudentEmail, ConsultationID)
                    VALUES
                    (?,?)
                    """
                    db.execute(query, [request.cookies.get('Email'), consultationID])
                    db.commit()
                    query = """
                    UPDATE ConsultationClasses
                    SET Capacity = Capacity+1
                    WHERE ConsultationID = ?
                    """
                    db.execute(query, [consultationID,])
                    db.commit()
                    db.close()
                return redirect(url_for('consultations'))

    else:
        return redirect(url_for('login'))

@app.route('/addingconsultationpost', methods=["POST", "GET"])
def addconsultmessage():
    if request.method == "GET":
        return redirect(url_for('consultations'))
    else:
        consultationID = request.form["ConsultationID"]
        message = request.form["addMessage"]
        db= sqlite3.connect(db_path)
        query = """
        INSERT INTO ConsultationChat
        (ConsultationID, Message, Email)
        VALUES
        (?,?,?)
        """
        db.execute(query, [consultationID,message,request.cookies.get("Email")])
        db.commit()
        query = """
        SELECT ConsultationID, Message, ConsultationChat.Email, Username
        FROM ConsultationChat, Users
        WHERE Users.Email = ConsultationChat.Email
        AND ConsultationID = ?
        ORDER BY MessageID DESC
        """
        cursor = db.execute(query, (consultationID,))
        allMessages = cursor.fetchall()
        cursor.close()
        db.close()
        return json.dumps(allMessages)

@app.route('/cancelconsult', methods=["POST", "GET"])
def cancelConsult():
    if request.method == "GET":
        return redirect(url_for('consultations'))
    else:
        consultationID = request.form["ConsultationID"]
        db = sqlite3.connect(db_path)
        query = """
        DELETE FROM ConsultationClasses
        WHERE ConsultationID = ?
        """
        db.execute(query, (consultationID,))
        db.commit()
        db.close()
        print(consultationID)
        return redirect(url_for('consultations'))

@app.route('/leaveconsult', methods=["POST", "GET"])
def leaveconsult():
    if request.method == "GET":
        return redirect(url_for('consultations'))
    else:
        consultationID = request.form["ConsultationID"]
        db = sqlite3.connect(db_path)
        query = """
        DELETE FROM Students
        WHERE ConsultationID = ?
        """
        db.execute(query, (consultationID,))
        db.commit()
        query = """
        UPDATE ConsultationClasses
        SET Capacity = Capacity-1
        WHERE ConsultationID = ?
        """
        db.execute(query, (consultationID,))
        db.commit()
        db.close()
        print(consultationID)
        return redirect(url_for('consultations'))

if __name__ == "__main__":
    app.run(debug=True)
