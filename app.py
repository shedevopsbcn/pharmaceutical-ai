from flask import Flask, render_template, request, redirect, url_for, session, jsonify
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
    if 'username' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    
    # 1. Grab the active filters from the dropdowns (defaults to 'all' and 'month')
    exp_filter = request.args.get('exp_filter', 'all')
    stat_filter = request.args.get('stat_filter', 'month')

    # Total Revenue & Stock
    cur.execute("SELECT SUM(preu) as total_revenue FROM transactions")
    revenue_data = cur.fetchone()
    total_revenue = revenue_data['total_revenue'] if revenue_data['total_revenue'] else 0

    cur.execute("SELECT SUM(quantitat) as total_stock FROM productes")
    stock_data = cur.fetchone()
    total_stock = stock_data['total_stock'] if stock_data['total_stock'] else 0

    # 2. Expiration Filter Logic
    if exp_filter == 'month':
        # Show everything expiring in the next 30 days
        cur.execute("SELECT nom, miligrams, data_caducitat FROM productes WHERE data_caducitat <= DATE_ADD(CURDATE(), INTERVAL 30 DAY) AND data_caducitat >= CURDATE() ORDER BY data_caducitat ASC")
    else:
        # Default: Show the 3 closest expirations
        cur.execute("SELECT nom, miligrams, data_caducitat FROM productes ORDER BY data_caducitat ASC LIMIT 3")
    expiring_products = cur.fetchall()

    # 3. Statistics Filter Logic
    if stat_filter == 'year':
        # Last 4 Months
        cur.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN data_compra >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH) THEN preu ELSE 0 END), 0) as week4,
                COALESCE(SUM(CASE WHEN data_compra >= DATE_SUB(CURDATE(), INTERVAL 2 MONTH) AND data_compra < DATE_SUB(CURDATE(), INTERVAL 1 MONTH) THEN preu ELSE 0 END), 0) as week3,
                COALESCE(SUM(CASE WHEN data_compra >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH) AND data_compra < DATE_SUB(CURDATE(), INTERVAL 2 MONTH) THEN preu ELSE 0 END), 0) as week2,
                COALESCE(SUM(CASE WHEN data_compra >= DATE_SUB(CURDATE(), INTERVAL 4 MONTH) AND data_compra < DATE_SUB(CURDATE(), INTERVAL 3 MONTH) THEN preu ELSE 0 END), 0) as week1
        FROM transactions
        """)
        stat_labels = "['Mes 1', 'Mes 2', 'Mes 3', 'Mes 4']"
    else:
        # Default: Last 4 Weeks
        cur.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN data_compra >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) THEN preu ELSE 0 END), 0) as week4,
                COALESCE(SUM(CASE WHEN data_compra >= DATE_SUB(CURDATE(), INTERVAL 14 DAY) AND data_compra < DATE_SUB(CURDATE(), INTERVAL 7 DAY) THEN preu ELSE 0 END), 0) as week3,
                COALESCE(SUM(CASE WHEN data_compra >= DATE_SUB(CURDATE(), INTERVAL 21 DAY) AND data_compra < DATE_SUB(CURDATE(), INTERVAL 14 DAY) THEN preu ELSE 0 END), 0) as week2,
                COALESCE(SUM(CASE WHEN data_compra >= DATE_SUB(CURDATE(), INTERVAL 28 DAY) AND data_compra < DATE_SUB(CURDATE(), INTERVAL 21 DAY) THEN preu ELSE 0 END), 0) as week1
            FROM transactions
        """)
        stat_labels = "['Semana 1', 'Semana 2', 'Semana 3', 'Semana 4']"
        
    weekly_stats = cur.fetchone()
    cur.close()

    max_weekly = max([weekly_stats['week1'], weekly_stats['week2'], weekly_stats['week3'], weekly_stats['week4']])
    if max_weekly == 0:
        max_weekly = 1 

    notifs = get_notifications()
    
    return render_template("index.html", 
                           active_page='home', 
                           notifications=notifs, 
                           total_revenue=total_revenue, 
                           total_stock=total_stock, 
                           expiring_products=expiring_products,
                           weekly_stats=weekly_stats,
                           max_weekly=max_weekly,
                           exp_filter=exp_filter,
                           stat_filter=stat_filter,
                           stat_labels=stat_labels)

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['email']
        pwd = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT correu_electronic, contrasenya, plan_tipus FROM users WHERE correu_electronic = %s", [username])
        user = cur.fetchone()
        cur.close()
        
        if user and pwd == user['contrasenya']:
            session['username'] = user['correu_electronic']
            session['plan_tipus'] = user.get('plan_tipus', 'Gratuït') 
            return redirect(url_for('home'))
        else:
            return render_template("components/signin.html", error="Invalid username or password")
            
    return render_template("components/signin.html")

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
    if 'username' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM transactions ORDER BY data_compra DESC")
    transactions = cur.fetchall()
    cur.close()
    return render_template('transactionindex.html', active_page='transaction', transactions=transactions)

@app.route('/plans')
def plans():
    return render_template('components/plans.html', active_page='plans')

@app.route('/promotion')
def promotion():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM productes WHERE data_caducitat <= DATE_ADD(CURDATE(), INTERVAL 90 DAY) ORDER BY data_caducitat ASC")
    productes = cur.fetchall()
    cur.close()
    return render_template('components/promotionpage.html', active_page='promotion', productes=productes)

@app.route('/submit', methods=['POST'])
def submit_product():
    if request.method == 'POST':
        id_numero = request.form['id_numero']
        nom_producte = request.form['nom_producte']
        quantitat = request.form['quantitat']
        milligrams = request.form['milligrams']
        preu = request.form['preu']
        preu_compra = request.form['preu_compra'] # <-- NEW COST FIELD ADDED
        caducitat = request.form['caducitat']
        proveedor = request.form['proveedor']
        category = request.form.get('category') 

        cur = mysql.connection.cursor()
        
        # <-- UPDATED SQL QUERY to include preu_compra and extra %s
        query = """INSERT INTO productes 
                   (id, nom, quantitat, miligrams, preu, preu_compra, data_caducitat, proveedor, categories) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                   
        # <-- UPDATED VALUES to pass the new variable           
        values = (id_numero, nom_producte, quantitat, milligrams, preu, preu_compra, caducitat, proveedor, category)

        try:
            cur.execute(query, values)
            mysql.connection.commit()
            cur.close()
            return redirect(url_for('newproduct')) 
            
        except Exception as e:
            return f"Hi ha hagut un error en guardar a la base de dades: {str(e)}"
        
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
    
@app.route('/symptomchecker')
def symptom_checker():
    return render_template('components/symptomchecker.html', active_page='symptomchecker')

@app.route('/api-symptom-search', methods=['POST'])
def api_symptom_search():
    symptom = request.form.get('symptom')
    cima_url = "https://cima.aemps.es/cima/rest/buscarEnFichaTecnica"
    
    payload = [
        {
            "seccion": "4.1",
            "texto": symptom,
            "contiene": 1
        }
    ]
    
    try:
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

        search_term = None
        if '[SEARCH:' in reply:
            start = reply.index('[SEARCH:') + 8
            end = reply.index(']', start)
            search_term = reply[start:end]
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

@app.route('/supplier/<supplier_name>')
def supplier_detail(supplier_name):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM productes WHERE proveedor = %s ORDER BY categories ASC", [supplier_name])
    productes = cur.fetchall()
    cur.close()
    return render_template('components/supplier_detail.html', active_page='suppliers', supplier_name=supplier_name, productes=productes) 

# RESTORED: Monthly filter logic for the Income page
@app.route('/income')
def income():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    cur = mysql.connection.cursor()
    selected_month = request.args.get('month')
    
    try:
        if selected_month:
            year, month = selected_month.split('-')
            cur.execute("SELECT SUM(preu) as total_revenue, COUNT(id) as total_sales FROM transactions WHERE YEAR(data_compra) = %s AND MONTH(data_compra) = %s", (year, month))
            stats = cur.fetchone()
            cur.execute("SELECT * FROM transactions WHERE YEAR(data_compra) = %s AND MONTH(data_compra) = %s ORDER BY data_compra DESC", (year, month))
            transactions = cur.fetchall()
        else:
            cur.execute("SELECT SUM(preu) as total_revenue, COUNT(id) as total_sales FROM transactions")
            stats = cur.fetchone()
            cur.execute("SELECT * FROM transactions ORDER BY data_compra DESC")
            transactions = cur.fetchall()
    except Exception as e:
        cur.execute("SELECT SUM(preu) as total_revenue, COUNT(id) as total_sales FROM transactions")
        stats = cur.fetchone()
        cur.execute("SELECT * FROM transactions ORDER BY data_compra DESC")
        transactions = cur.fetchall()
        selected_month = None
        
    cur.close()
    return render_template('components/income.html', active_page='income', stats=stats, transactions=transactions, selected_month=selected_month)


@app.route('/analysis')
def analysis():
    if 'username' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    # 1. Get total inventory grouped by category for the Doughnut Chart
    cur.execute("""
        SELECT categories, SUM(quantitat) as total_items 
        FROM productes 
        GROUP BY categories
    """)
    category_data = cur.fetchall()

    # 2. Get revenue and calculate expenses (65% of revenue) for the Line Chart
    cur.execute("""
        SELECT DATE_FORMAT(data_compra, '%Y-%m') as month, 
               SUM(preu) as revenue,
               SUM(preu) * 0.65 as expenses
        FROM transactions 
        GROUP BY month 
        ORDER BY month DESC 
        LIMIT 6
    """)
    
    monthly_revenue = list(cur.fetchall())
    monthly_revenue.reverse()
    cur.close()

    return render_template('components/analysis.html', 
                           active_page='analysis', 
                           category_data=category_data, 
                           monthly_revenue=monthly_revenue)

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