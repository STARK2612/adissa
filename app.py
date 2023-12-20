import os
import locale
from flask import Flask
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, g
from flask_mysqldb import MySQL
from twilio.rest import Client
from flask_sqlalchemy import SQLAlchemy
from flask_mysql_connector import MySQL
from flask import g


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://nebwdlzelzz3019i:xrn795sttju562nd@jbb8y3dri1ywovy2.cbetxkdyhwsb.us-east-1.rds.amazonaws.com:3306/vhylcj5gcv7nd0uw'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MYSQL_HOST'] = 'jbb8y3dri1ywovy2.cbetxkdyhwsb.us-east-1.rds.amazonaws.com	'
app.config['MYSQL_USER'] = 'nebwdlzelzz3019i'
app.config['MYSQL_PASSWORD'] = 'xrn795sttju562nd'
app.config['MYSQL_DB'] = 'vhylcj5gcv7nd0uw'
#app.config['MYSQL_HOST'] = '127.0.0.1'
#app.config['MYSQL_USER'] = 'root'
#app.config['MYSQL_PASSWORD'] = ''
#app.config['MYSQL_DB'] = 'association'
mysql = MySQL(app)
db = SQLAlchemy(app)

# Définir votre modèle de base de données
class membres(db.Model):
    date_naissance = db.Column(db.Date)
    id = db.Column(db.Integer, primary_key=True)
    identifiant = db.Column(db.String(50))
    mot_de_passe = db.Column(db.String(50))
    nom = db.Column(db.String(50))
    prenom = db.Column(db.String(50))
    
# Gestion de la localisation
try:
    locale.setlocale(locale.LC_TIME, 'en_US.utf8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'en_US.utf8')  # Variante avec utf8
    except locale.Error:
        # Log ou gestion d'erreur appropriée
        print("La localisation en_US.utf8 et en_US.utf8 ne sont pas disponibles. La localisation par défaut sera utilisée.")
        locale.setlocale(locale.LC_TIME, '')  # Utiliser la localisation par défaut

def obtenir_membres_par_mois():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM membres WHERE id NOT IN (1, 2) ORDER BY MONTH(date_naissance), DAY(date_naissance)")
    membres = cur.fetchall()
    cur.close()

    membres_par_mois = {}

    for membre in membres:
        mois_naissance = membre[5].month
        if mois_naissance not in membres_par_mois:
            membres_par_mois[mois_naissance] = {'membres': [], 'numero_mois': mois_naissance}
        membres_par_mois[mois_naissance]['membres'].append(membre)

    return membres_par_mois

@app.before_request
def avant_requete():
    if 'mysql' not in g:
        g.mysql = MySQL(app)
    g.membres_par_mois = obtenir_membres_par_mois()
    #g.membres_par_mois = obtenir_membres_par_mois()

def envoyer_message_whatsapp(details_mois):
    # Placez ces informations dans des variables d'environnement sécurisées sur votre serveur
    account_sid = 'AC5eb1ca46f5d5b1f846d0408537fa94e5'
    auth_token = 'fb7f1bc71af73d1934c77bfeded7638e'
    
    client = Client(account_sid, auth_token)

    recipient_number = 'whatsapp:+33658299720'
    sender_number = 'whatsapp:+14155238886'

    contenu_message = f"Récapitulatif des dates de naissance du mois en cours ({details_mois['numero_mois']} - {details_mois['membres'][0][5].strftime('%B')}):\n\n"
   
    for membre in details_mois['membres']:
        contenu_message += f"{membre[3]} {membre[4]} - {membre[5].strftime('%d %B')}\n"

    message = client.messages.create(
        body=contenu_message,
        from_=sender_number,
        to=recipient_number
    )

    return message.sid

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/supprimer_membre/<int:membre_id>', methods=['POST'])
def supprimer_membre(membre_id):
    with mysql.connection.cursor() as cur:
        cur.execute("DELETE FROM membres WHERE id = %s", (membre_id,))
        mysql.connection.commit()
    
    return redirect(url_for('ajouter_membre'))

@app.route('/ajouter_membre', methods=['GET', 'POST'])
def ajouter_membre():
    maintenant = datetime.now()
    mois_en_cours = maintenant.month

    if request.method == 'POST':
        nom = request.form['nom']
        prenom = request.form['prenom']
        date_naissance = request.form['date_naissance']

        with mysql.connection.cursor() as cur:
            cur.execute("INSERT INTO membres (nom, prenom, date_naissance) VALUES (%s, %s, %s)", (nom, prenom, date_naissance))
            mysql.connection.commit()

        return trier_membres()

    with mysql.connection.cursor() as cur:
        cur.execute("SELECT * FROM membres WHERE id NOT IN (1, 2)")
        membres = cur.fetchall()

    return render_template('ajouter_membre.html', membres=membres)

@app.route('/login', methods=['POST'])
def login():
    identifiant = request.form['identifiant']
    mot_de_passe = request.form['mot_de_passe']
    
    with mysql.connection.cursor() as cur:
        cur.execute("SELECT * FROM membres WHERE identifiant = %s AND mot_de_passe = %s", (identifiant, mot_de_passe))
        user = cur.fetchone()

    if user:
        return redirect(url_for('ajouter_membre'))
    else:
        return render_template('login.html', error='Identifiant ou mot de passe incorrect!')

@app.route('/deconnexion')
def deconnexion():
    return redirect(url_for('index'))

locale.setlocale(locale.LC_TIME, 'en_US.utf8')

@app.route('/envoyer_message_whatsapp/<int:mois>', methods=['POST'])
def envoyer_message_whatsapp_route(mois):
    try:
        membres_par_mois = g.membres_par_mois
        details_mois = membres_par_mois.get(mois)
        
        if details_mois:
            envoyer_message_whatsapp(details_mois)

        return redirect(url_for('ajouter_membre', mois=mois))
    except Exception as e:
        print(f"Erreur lors de l'envoi du message WhatsApp : {e}")
        return "Une erreur s'est produite lors de l'envoi du message WhatsApp."

    
@app.errorhandler(500)
def internal_server_error(e):
    return "Internal Server Error. Veuillez consulter les journaux pour plus d'informations.", 500


@app.route('/trier_membres')
def trier_membres():
    with mysql.connection.cursor() as cur:
        cur.execute("SELECT * FROM membres WHERE id NOT IN (1, 2) ORDER BY MONTH(date_naissance)")
        membres = cur.fetchall()

    membres_par_mois = {}

    maintenant = datetime.now()

    for membre in membres:
        mois_naissance = membre[5].month
        jour_naissance = membre[5].day

        # Vérifier si c'est le mois d'aujourd'hui
        if mois_naissance == maintenant.month:
            if mois_naissance not in membres_par_mois:
                membres_par_mois[mois_naissance] = {'membres': [], 'numero_mois': mois_naissance, 'jours_anniversaire': set()}
            membres_par_mois[mois_naissance]['membres'].append(membre)
            membres_par_mois[mois_naissance]['jours_anniversaire'].add(jour_naissance)

    for details_mois in membres_par_mois.values():
        envoyer_message_whatsapp(details_mois)

    membres_par_mois = obtenir_membres_par_mois()
    return render_template('trier_membres.html', membres_par_mois=membres_par_mois)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)