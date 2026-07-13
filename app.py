from flask import Flask, render_template, request, redirect, url_for, session, request, jsonify
from flask_mysqldb import MySQL
import requests

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

@app.route('/submit', methods=['POST'])
def submit_product():
    if request.method == 'POST':
        # 1. Grab data from the HTML form
        id_numero = request.form['id_numero']
        nom_producte = request.form['nom_producte']
        quantitat = request.form['quantitat']
        milligrams = request.form['milligrams']
        preu = request.form['preu']
        caducitat = request.form['caducitat']
        proveedor = request.form['proveedor']
        category = request.form.get('category') 

        cur = mysql.connection.cursor()

        # 2. MATCH THE EXACT DATABASE COLUMNS
        # id, nom, quantitat, miligrams, preu, data_caducitat, proveedor, categories
        query = """INSERT INTO productes 
                   (id, nom, quantitat, miligrams, preu, data_caducitat, proveedor, categories) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        
        values = (id_numero, nom_producte, quantitat, milligrams, preu, caducitat, proveedor, category)

        try:
            cur.execute(query, values)
            mysql.connection.commit()
            cur.close()
            return redirect(url_for('newproduct')) 
            
        except Exception as e:
            return f"Hi ha hagut un error en guardar a la base de dades: {str(e)}"
        
# Move this route UP here!
@app.route('/search-medicine', methods=['POST'])
def search_medicine():
    search_term = request.form.get('med-name')
    cima_url = f"https://cima.aemps.es/cima/rest/medicamentos?nombre={search_term}"
    
    try:
        response = requests.get(cima_url)
        if response.status_code == 200:
            data = response.json()
            return jsonify(data)
        else:
            return jsonify({"error": "Failed to fetch data from CIMA"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    # 1. Route to load the new Symptom Checker webpage
@app.route('/symptomchecker')
def symptom_checker():
    return render_template('components/symptomchecker.html')

# 2. Route to handle the API search
@app.route('/api-symptom-search', methods=['POST'])
def api_symptom_search():
    symptom = request.form.get('symptom')
    cima_url = "https://cima.aemps.es/cima/rest/buscarEnFichaTecnica"
    
    # This is the exact JSON structure CIMA requires to search documents[cite: 1]
    # We are searching Section 4.1 (Therapeutic Indications) for the symptom[cite: 1]
    payload = [
        {
            "seccion": "4.1",
            "texto": symptom,
            "contiene": 1
        }
    ]
    
    try:
        # Note: This endpoint requires a POST request, not a GET request[cite: 1]
        response = requests.post(cima_url, json=payload)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": "Failed to fetch data from CIMA"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# This MUST be the very last thing in your file
if __name__ == "__main__":
    app.run(debug=True)
