from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,PasswordField,validators,TextAreaField
from passlib.hash import sha256_crypt
from functools import wraps


#Makale Formu Oluşturma
class ArticleForm(Form):
    title=StringField("Makale Başlığı")
    content = TextAreaField("Makale İçeriği")


#Kullanıcı giriş decoratorü
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için yönetici olarak sisteme girin.","danger")
            return redirect(url_for("login"))
    return decorated_function

#Kullanıcı kayıt formu
class RegisterForm(Form):
    name=StringField("İsim Soyisim",validators=[validators.DataRequired()])
    user_name=StringField("Kullanıcı Adı",validators=[validators.Length(min=3,max=15)])
    e_mail=StringField("E-Mail",validators=[validators.DataRequired()])
    password=PasswordField("Parola",validators=[validators.DataRequired(message="Lütfen Bir Parola Belirleyin"),validators.EqualTo(fieldname="confirm",message="Parolanızı Kontrol Edin")])
    
    confirm=PasswordField("Parola Doğrula")

#Kullanıcı giriş formu
class LoginForm(Form):
    user_name=StringField("Kullanıcı Adı")
    password=PasswordField("Parola")


app=Flask(__name__,template_folder="templates")

app.secret_key="yazilim_guncesi"
app.config["MYSQL_HOST"]="localhost"
app.config["MYSQL_USER"]="root"
app.config["MYSQL_PASSWORD"]=""
app.config["MYSQL_DB"]="yazilimguncesi"
app.config["MYSQL_CURSORCLASS"]="DictCursor"

mysql=MySQL(app)


@app.route("/")
def root():
    return redirect(url_for("index"))

@app.route("/index")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/register",methods=["GET","POST"])
def register():
    form=RegisterForm(request.form)
    
    if request.method == "POST" and form.validate():
        name=form.name.data
        user_name=form.user_name.data
        e_mail=form.e_mail.data
        password=sha256_crypt.encrypt(form.password.data)

        cursor=mysql.connection.cursor()

        que="Insert into users (name,e_mail,user_name,password) VALUES(%s,%s,%s,%s)"
        cursor.execute(que,(name,e_mail,user_name,password))

        mysql.connection.commit()
        cursor.close()

        flash(message="Başarı ile Kayıt Oldunuz...",category="success")

        return redirect(url_for("login"))
    else:
        return render_template("register.html",form=form)
@app.route("/login",methods=["GET","POST"])
def login():
    form=LoginForm(request.form)
    if request.method == "POST":
        user_name = form.user_name.data
        password_entered=form.password.data

        cursor=mysql.connection.cursor()
        que="Select * from users where user_name = %s"

        result=cursor.execute(que,(user_name,))

        if result > 0:
            data=cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered,real_password):
                flash("Başarı ile giriş yaptınız","success")
                session["logged_in"]=True
                session["user_name"]=user_name
                session["admin"]=(user_name=="okty")
                return redirect(url_for("index"))
            else:
                flash("Parolanızı yanlış girdiniz.","danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı bulunmamaktadır","danger")
            return redirect(url_for("login"))
    else:
        return render_template("login.html",form=form)
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard ():
    cursor=mysql.connection.cursor()
    que="Select * from articles"

    result=cursor.execute(que)

    if result > 0:
        articles=cursor.fetchall()
        return render_template("dashboard.html",articles=articles)
    else:
        return render_template("dashboard.html")

@app.route("/addarticle",methods=["GET","POST"])
def addarticle():
    form= ArticleForm(request.form)
    if request.method=="POST":
        title=form.title.data
        content=form.content.data

        cursor= mysql.connection.cursor()
        que="Insert into articles(title,author,content) VALUE (%s,%s,%s)"

        cursor.execute(que,(title,session["user_name"],content))
        mysql.connection.commit()
        cursor.close()
        flash("Makale Başarı ile Eklendi","success")
        return redirect(url_for("dashboard"))
    else:
        return render_template("addarticle.html",form=form)

@app.route("/article/<string:id>")
def article(id):
    cursor=mysql.connection.cursor()
    que="Select * from articles where id=%s"

    result=cursor.execute(que,(id,))

    if result > 0:
        article=cursor.fetchone()
        return render_template("article.html",article=article)
    else:
        return render_template("articles.html")
    
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor=mysql.connection.cursor()
    que="Select * from articles where author = %s and id= %s"

    result=cursor.execute(que,(session["user_name"],id))
    if result > 0:
        que2="Delete from articles where id =%s"
        cursor.execute(que2,(id,))
        mysql.connection.commit()
        
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale bulunmamaktadır.","warning")
        return redirect(url_for("index"))

@app.route("/edit/<string:id>",methods=["GET","POST"])
@login_required
def edit(id):
    if request.method=="GET":
        cursor=mysql.connection.cursor()
        que="Select * from articles where id =%s and author=%s"

        result=cursor.execute(que,(id,session["user_name"]))
        
        if result==0:
            flash("Böyle bir makale bulunmamaktadır","warning")
            return redirect(url_for("index"))
        else:
            article=cursor.fetchone()
            form=ArticleForm()

            form.title.data=article["title"]
            form.content.data=article["content"]
            return render_template("update.html",form=form)
    else:
        form=ArticleForm(request.form)

        new_title=form.title.data
        new_content=form.content.data
        que2="Update articles set title = %s,content=%s where id=%s"

        cursor=mysql.connection.cursor()
        cursor.execute(que2,(new_title,new_content,id))
        mysql.connection.commit()

        flash("Makale başarı ile güncellendi","success")
        return redirect(url_for("dashboard"))

@app.route("/articles")
def articles():
    cursor=mysql.connection.cursor()
    que="Select * from articles"
    result=cursor.execute(que)

    if result > 0:
        articles=cursor.fetchall()
        return render_template("articles.html",articles=articles)
    else:
        return render_template("articles.html")

@app.route("/search",methods=["GET","POST"])
def search():
    if request.method=="GET":
        return redirect(url_for("index"))
    else:
        keyword=request.form.get("keyword")
        cursor=mysql.connection.cursor()
        que="Select * from articles where title like '%"+keyword+"%'"

        result=cursor.execute(que)

        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadı","warning")
            return redirect(url_for("articles"))
        else:
            articles=cursor.fetchall()
            return render_template("articles.html",articles=articles)

if __name__== "__main__":
    app.run(debug=True)

