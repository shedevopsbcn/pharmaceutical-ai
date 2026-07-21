from flask import Flask, render_template, request, redirect, url_for, session, request, jsonify
from flask_mysqldb import MySQL
import requests

app = Flask(__name__, static_folder='static')
app.secret_key = 'your-secret-key'

# MySQL Configuration
app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'ia_farmacia'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

def get_notifications():
    from datetime import date, timedelta
    cur = mysql.connection.cursor()
    notifications = []
    
    # Check low stock (less than 10 units)
    cur.execute("SELECT nom, quantitat FROM productes WHERE quantitat < 10")
    low_stock = cur.fetchall()
    for item in low_stock:
        notifications.append({
            'type': 'stock',
            'message': f"{item['nom']} té poc estoc: {item['quantitat']} unitats restants"
        })
    
    # Check expiring soon (within 30 days)
    today = date.today()
    soon = today + timedelta(days=30)
    cur.execute("SELECT nom, data_caducitat FROM productes WHERE data_caducitat <= %s AND data_caducitat >= %s", [soon, today])
    expiring = cur.fetchall()
    for item in expiring:
        notifications.append({
            'type': 'expiration',
            'message': f"{item['nom']} caduca el {item['data_caducitat'].strftime('%d/%m/%Y')}"
        })
    
    cur.close()
    return notifications

@app.context_processor
def inject_notifications():
    try:
        notifs = get_notifications()
    except:
        notifs = []
    return dict(notifications=notifs)

@app.route('/notifications')
def notifications():
    notifs = get_notifications()
    return render_template('notifications.html', notifications=notifs)

@app.route("/home")
def home():
    notifs = get_notifications()
    return render_template("index.html", active_page='home', notifications=notifs)

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['email']
        pwd = request.form['password']
        cur = mysql.connection.cursor()
        # ADDED plan_tipus to the SELECT statement
        cur.execute("SELECT correu_electronic, contrasenya, plan_tipus FROM users WHERE correu_electronic = %s", [username])
        user = cur.fetchone()
        cur.close()
        
        if user and pwd == user['contrasenya']:
            session['username'] = user['correu_electronic']
            # SAVES their plan in the background session
            session['plan_tipus'] = user.get('plan_tipus', 'Gratuït') 
            return redirect(url_for('home'))
        else:
            return render_template("components/signin.html", error="Invalid username or password")
            
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

@app.route('/inventory')
def inventory():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM productes ORDER BY data_caducitat ASC")
    productes = cur.fetchall()
    cur.close()
    return render_template('components/inventory.html', active_page='inventory', productes=productes)

@app.route('/transaction')
def transaction():
    # SECURITY: Boot them if not logged in
    if 'username' not in session:
        return redirect(url_for('login'))
        
    # PAYWALL: Redirect to the pricing plans if they are on the free tier
    #if session.get('plan_tipus') == 'Gratuït':
       # return redirect(url_for('plans'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM transactions ORDER BY data_compra DESC")
    transactions = cur.fetchall()
    cur.close()
    return render_template('transactionindex.html', active_page='transaction', transactions=transactions)

@app.route('/plans')
def plans():
    # This is the page where they will see the 3 tiers and Stripe buttons
    return render_template('components/plans.html', active_page='plans')

@app.route('/promotion')
def promotion():
    cur = mysql.connection.cursor()
    # Pulls ONLY products expiring within the next 90 days!
    cur.execute("SELECT * FROM productes WHERE data_caducitat <= DATE_ADD(CURDATE(), INTERVAL 90 DAY) ORDER BY data_caducitat ASC")
    productes = cur.fetchall()
    cur.close()
    return render_template('components/promotionpage.html', active_page='promotion', productes=productes)

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
    # Added active_page='symptomchecker' so the sidebar highlights correctly
    return render_template('components/symptomchecker.html', active_page='symptomchecker')

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

@app.route('/chat-symptom', methods=['POST'])
def chat_symptom():
    data = request.get_json()
    history = data.get('history', [])
    
    system_prompt = """Ets un assistent de farmàcia virtual que parla en català. 
    El teu objectiu és fer preguntes per entendre els símptomes de l'usuari i recomanar medicaments.
    
    Segueix aquestes regles:
    1. Sempre parla en català
    2. Fes preguntes de seguiment per entendre millor els símptomes (màxim 3-4 preguntes)
    3. Quan tinguis prou informació, afegeix al final de la teva resposta exactament aquesta etiqueta:
       [SEARCH:terme_de_cerca]
       On terme_de_cerca és la paraula clau en castellà per buscar a CIMA (ex: [SEARCH:dolor cabeza])
    4. Sigues empàtic i professional
    5. No diagnostiques malalties, només recomanis medicaments"""

    messages = [{"role": m["role"], "content": m["content"]} for m in history]

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": "YOUR_API_KEY_HERE",
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 500,
                "system": system_prompt,
                "messages": messages
            }
        )

        result = response.json()
        reply = result['content'][0]['text']

        # Check if Claude included a search term
        search_term = None
        if '[SEARCH:' in reply:
            start = reply.index('[SEARCH:') + 8
            end = reply.index(']', start)
            search_term = reply[start:end]
            # Remove the tag from the visible reply
            reply = reply[:reply.index('[SEARCH:')].strip()

        return jsonify({ 'reply': reply, 'search_term': search_term })

    except Exception as e:
        return jsonify({ 'reply': 'Hi ha hagut un error. Torna-ho a intentar.', 'search_term': None })
    
@app.route('/ajuda', methods=['GET', 'POST'])
def ajuda():
    success = False
    if request.method == 'POST':
        nom = request.form['nom']
        correo = request.form['correo']
        telefon = request.form.get('telefon', '')
        missatge = request.form['missatge']

        cur = mysql.connection.cursor()
        cur.execute("""INSERT INTO missatges (nom, correo, telefon, missatge) 
                       VALUES (%s, %s, %s, %s)""", (nom, correo, telefon, missatge))
        mysql.connection.commit()
        cur.close()
        success = True

    return render_template('components/contact.html', success=success)

@app.route('/suppliers')
def suppliers():
    cur = mysql.connection.cursor()
    # Calculates the badges
    cur.execute("""
        SELECT proveedor, 
               SUM(quantitat) as total_items, 
               COUNT(id) as unique_products 
        FROM productes 
        WHERE proveedor IS NOT NULL AND proveedor != ''
        GROUP BY proveedor
    """)
    suppliers_data = cur.fetchall()
    cur.close()
    return render_template('components/supplier.html', active_page='suppliers', suppliers=suppliers_data)

# NEW: The dedicated Supplier Profile page
@app.route('/supplier/<supplier_name>')
def supplier_detail(supplier_name):
    cur = mysql.connection.cursor()
    # Grabs only their products, sorted cleanly by category
    cur.execute("SELECT * FROM productes WHERE proveedor = %s ORDER BY categories ASC", [supplier_name])
    productes = cur.fetchall()
    cur.close()
    return render_template('components/supplier_detail.html', active_page='suppliers', supplier_name=supplier_name, productes=productes) 

@app.route('/income')
def income():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    cur = mysql.connection.cursor()
    
    # 1. Calculate total revenue and total sales count
    cur.execute("SELECT SUM(preu) as total_revenue, COUNT(id) as total_sales FROM transactions")
    stats = cur.fetchone()
    
    # 2. Pull all transaction records for the detailed list
    cur.execute("SELECT * FROM transactions ORDER BY data_compra DESC")
    transactions = cur.fetchall()
    cur.close()
    
    return render_template('components/income.html', active_page='income', stats=stats, transactions=transactions)

@app.route('/inbox')
def inbox():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM missatges ORDER BY data_enviament DESC")
    missatges = cur.fetchall()
    cur.close()
    return render_template('inbox.html', missatges=missatges)

@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)