from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL

app = Flask(__name__, static_folder='static')
app.secret_key = 'your-secret-key'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'ia_farmacia'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

@app.route("/home")
def home():
    return render_template("index.html", active_page='home')

# Login handler
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # The HTML form uses 'email', not 'username'
        username = request.form['email']
        pwd = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT correu_electronic, contrasenya FROM users WHERE correu_electronic = %s", [username])
        user = cur.fetchone()
        cur.close()
        
        if user and pwd == user['contrasenya']:
            session['username'] = user['correu_electronic']
            return redirect(url_for('home'))
        else:
            # If login fails, reload the signin page
            return render_template("components/signin.html", error="Invalid username or password")
            
    # Load the signin page by default instead of the register page
    return render_template("components/signin.html")
# Start the Flask app

@app.route('/signin')
def signin():
    return render_template('components/signin.html')

@app.route('/register')
def register():
    return render_template('/components/register.html')

@app.route('/newproduct')
def newproduct(): 
    return render_template('components/newproduct.html')

@app.route('/controltable')
def controltable():
    return render_template('ctindex.html')

@app.route('/expiration')
def expiration():
    return render_template('components/expirationpage.html', active_page='expiration')

@app.route('/transaction')
def transaction():
    return render_template('transactionindex.html', active_page='transaction')

@app.route('/promotion')
def promotion():
    return render_template('components/promotionpage.html', active_page='promotion')

if __name__ == "__main__":
    app.run(debug=True)
