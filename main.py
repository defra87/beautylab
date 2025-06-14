from flask import Flask, request, render_template_string, send_from_directory
from PyPDF2 import PdfReader
import openai
from flask_mail import Mail, Message
import pandas as pd
import os
import re

# --- CONFIGURA QUI ---
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
EMAIL_MITTENTE = os.environ.get('MAIL_USERNAME')
EMAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
WHATSAPP_NUMBER = "393492134144"  # numero senza spazi e senza +
WHATSAPP_DISPLAY = "+39 349 21 34 144"  # come vuoi che appaia
WHATSAPP_MSG = "Ciao Pamela e Anna, vorrei prenotare una consulenza con voi!"
# ---------------------

app = Flask(__name__)

# Configurazione Flask-Mail (Aruba)
app.config['MAIL_SERVER'] = 'smtp.aruba.it'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'consulente@mybeautylab.it'
app.config['MAIL_PASSWORD'] = 'Damiano20!'
app.config['MAIL_DEFAULT_SENDER'] = 'consulente@mybeautylab.it'
mail = Mail(app)

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# Inizializza OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

def estrai_testo_pdf_da_cartella(cartella='data'):
    testo = ""
    if not os.path.exists(cartella):
        return "Cartella PDF non trovata!"
    for filename in os.listdir(cartella):
        if filename.lower().endswith('.pdf'):
            with open(os.path.join(cartella, filename), 'rb') as f:
                reader = PdfReader(f)
                for i, page in enumerate(reader.pages):
                    if i >= 2:  # Solo le prime 2 pagine di ogni PDF
                        break
                    testo_pagina = page.extract_text() or ""
                    # Elimina righe vuote e spazi inutili
                    testo_pagina = "\n".join([line.strip() for line in testo_pagina.splitlines() if line.strip()])
                    testo += f"\n[File: {filename} - Pagina {i+1}]\n" + testo_pagina
    return testo

def estrai_listino_excel(path='data/listprezzi.xlsx'):
    try:
        df = pd.read_excel(path)
        return df.head(15).to_string(index=False)
    except Exception as e:
        return f"Errore lettura listino: {e}"

def estrai_promo_txt(path='data/promo.txt'):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Nessuna promozione attiva."

def email_valida(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

AMATI_PROMPT = """
Se ricevi i dati (età, sesso, come ti vedi allo specchio, cosa vuoi migliorare, quali sono i tuoi obiettivi nel lato estetico), analizzali e consiglia una routine estetica completa usando solo i prodotti descritti nei documenti dei prodotti Farmogal allegati con il prezzo dei prodotti che proponi. Fai attenzione alle parole se è maschio oppure femmina, usando la terminologia corretta. Non inventare nomi di prodotti. Specifica prodotti per mattino, sera e trattamento in cabina (i vari titoli devono essere in grassetto), e spiega il motivo del consiglio. Verifica che ci siano promo. Ricordagli che Pamela e Anna sono a disposizione per qualsiasi consiglio e usa un tono cortese e affettuoso. Fagli capire che un trattamento estetico per essere efficace prevede una routine di estetica quotidiana e in cabina dalle 3 alle 6 sedute (decidi tu un numero), affinchè tutto ciò possa essere personalizzato e ancora piu mirato sulla sua persona. Dopo questo, inserisci una frase motivazione. La frase motivazionale dev'essere una frase che il cliente possa leggere e sentirsi motivato. Inizia la mail salutando il cliente con il suo nome, fai capire al cliente quanto è importante la sua bellezza e che lui è unico e merita il meglio. Inserisci come firma della mail: "Pamela e Anna AMATI by BeautyLab"
"""

HTML_FORM = """
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Consulenza AMATI - Farmogal</title>
  <link href="https://fonts.googleapis.com/css?family=Montserrat:600,400&display=swap" rel="stylesheet">
  <style>
    body {
      background: linear-gradient(120deg, #e6f0fa, #f7fafc 90%);
      font-family: 'Montserrat', Arial, sans-serif;
      color: #222;
      margin: 0;
      min-height: 100vh;
    }
    .form-container {
      background: #fff;
      max-width: 420px;
      margin: 50px auto 0 auto;
      padding: 34px 28px 26px 28px;
      border-radius: 20px;
      box-shadow: 0 8px 32px rgba(50,90,200,0.07);
      border: 1.5px solid #e3eafc;
    }
    .logo {
      display: block;
      margin: 0 auto 18px auto;
      max-width: 140px;
    }
    h2 {
      text-align: center;
      color: #0085cc;
      margin-bottom: 28px;
      font-size: 2rem;
      font-weight: 600;
    }
    label {
      display: block;
      margin-bottom: 14px;
      font-weight: 500;
    }
    input[type="text"], input[type="email"], input[type="number"], select, textarea {
      width: 100%;
      padding: 10px 12px;
      margin-top: 6px;
      border: 1px solid #d6e5f5;
      border-radius: 8px;
      font-size: 1em;
      background: #f6fbff;
      transition: border-color 0.2s;
      box-sizing: border-box;
      font-family: inherit;
      resize: vertical;
    }
    input:focus, textarea:focus, select:focus {
      border-color: #6ec6ff;
      outline: none;
      background: #eef6fc;
    }
    button {
      width: 100%;
      margin-top: 18px;
      padding: 12px;
      background: linear-gradient(90deg,#47b5ed,#0085cc);
      color: #fff;
      border: none;
      border-radius: 10px;
      font-size: 1.1em;
      font-weight: 600;
      box-shadow: 0 4px 20px rgba(0,90,190,0.08);
      cursor: pointer;
      letter-spacing: 0.5px;
      transition: background 0.2s, box-shadow 0.2s;
    }
    button:hover {
      background: linear-gradient(90deg,#0085cc,#47b5ed);
      box-shadow: 0 6px 24px rgba(0,90,190,0.15);
    }
    .loading {
      display: none;
      text-align: center;
      margin-top: 18px;
    }
    .loading img {
      width: 42px;
      vertical-align: middle;
      margin-right: 10px;
    }
    .loading span {
      font-size: 1.1em;
      color: #0085cc;
      font-weight: 600;
      letter-spacing: 0.2px;
    }
    .error {
      color: #b01c1c;
      text-align: center;
      margin-top: 16px;
      margin-bottom: -10px;
      font-weight: 500;
    }
    @media (max-width: 500px) {
      .form-container {
        margin: 20px 6px;
        padding: 22px 8px 16px 8px;
      }
      h2 { font-size: 1.3rem; }
    }
  </style>
</head>
<body>
  <div class="form-container">
    <img src="/static/logo.jpg" class="logo" alt="Logo">
    <h2>Consulenza Estetica<br>AMATI by BeautyLab</h2>
    {{ errore|safe }}
    <form method="post" onsubmit="startLoading()">
      <label>Nome:
        <textarea name="nome" required></textarea>
      </label>
      <label>Cognome:
        <textarea name="cognome" required></textarea>
      </label>
      <label>Età:
        <input name="eta" required type="number" min="10" max="120">
      </label>
      <label>Sesso:
        <select name="sesso" required>
          <option value="Femmina">Femmina</option>
          <option value="Maschio">Maschio</option>
          <option value="Altro">Altro</option>
        </select>
      </label>
      <label>Quanto ti guardi allo specchio, cosa pensi di te stessa? Come ti vedi la pelle?<br>
        <textarea name="specchio" rows=2 required></textarea>
      </label>
      <label>Come vuoi migliorare?<br>
        <textarea name="migliorare" rows=2 required></textarea>
      </label>
      <label>Quali sono i tuoi obiettivi?<br>
        <textarea name="obiettivi" rows=2 required></textarea>
      </label>
      <label>Email:
        <input name="email" type="email" required>
      </label>
      <button id="submit-btn" type="submit">Richiedi la tua consulenza</button>
      <div class="loading" id="loading-div">
        <img src="https://i.gifer.com/ZZ5H.gif" alt="Caricamento...">
        <span>Sto contattando le consulenti Pamela & Anna...</span>
      </div>
    </form>
  </div>
  <script>
    function startLoading() {
      document.getElementById('submit-btn').style.display = 'none';
      document.getElementById('loading-div').style.display = 'block';
    }
  </script>
</body>
</html>
"""

HTML_THANKS = """
<!doctype html>
<html lang='it'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width,initial-scale=1'>
  <link href="https://fonts.googleapis.com/css?family=Montserrat:600,400&display=swap" rel="stylesheet">
  <style>
    body { background: linear-gradient(120deg, #e6f0fa, #f7fafc 90%); font-family: 'Montserrat', Arial, sans-serif; margin:0;}
    .thanks { max-width:410px;margin:60px auto 0 auto;background:#fff;padding:44px 24px 30px 24px;border-radius:22px;box-shadow:0 6px 32px rgba(60,110,190,0.07);}
    .logo {display:block; margin:0 auto 24px auto; max-width:110px;}
    h2 { color:#0085cc;text-align:center; font-size:1.4em;}
    p { text-align:center;font-size:1.1em;margin-bottom:18px;}
    a { display:block; text-align:center; color:#0085cc; text-decoration:underline;}
  </style>
</head>
<body>
  <div class='thanks'>
    <img src="/static/logo.jpg" class="logo" alt="Logo">
    <h2>Grazie per aver compilato il Form!</h2>
    <p>A breve riceverai una mail con la tua consulenza gratuita.</p>
    <a href="/">Torna al form</a>
  </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    errore = ""
    if request.method == 'POST':
        nome = request.form['nome']
        cognome = request.form['cognome']
        eta = request.form['eta']
        sesso = request.form['sesso']
        specchio = request.form['specchio']
        migliorare = request.form['migliorare']
        obiettivi = request.form['obiettivi']
        email = request.form['email']

        if not email_valida(email):
            errore = '<div class="error">L\'indirizzo email inserito non è valido. Riprova.</div>'
            return render_template_string(HTML_FORM, errore=errore)

        pdf_text = estrai_testo_pdf_da_cartella('data')
        listino_text = estrai_listino_excel('data/listprezzi.xlsx')
        promo_text = estrai_promo_txt('data/promo.txt')

        user_prompt = (
            f"Nome: {nome}\n"
            f"Cognome: {cognome}\n"
            f"Età: {eta}\n"
            f"Sesso: {sesso}\n"
            f"Come mi vedo allo specchio: {specchio}\n"
            f"Come voglio migliorare: {migliorare}\n"
            f"I miei obiettivi: {obiettivi}\n"
            f"---\n"
            f"[Prodotti Farmogal:]\n{pdf_text[:3000]}\n"
            f"[Listino prezzi:]\n{listino_text[:1800]}\n"
            f"[Promozioni attive nel mese:]\n{promo_text}"
        )

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": AMATI_PROMPT.format(nome=nome)},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=900
            )
            answer = response.choices[0].message.content
        except Exception as e:
            return f"Errore API OpenAI: {e}"

        answer_html = answer.replace('\n','<br>')

        # WhatsApp link
        whatsapp_link = f"https://wa.me/{WHATSAPP_NUMBER}?text={re.sub(' ', '%20', WHATSAPP_MSG)}"
        whatsapp_html = f"""
            <div style="margin-top:28px; text-align:center;">
                <a href="{whatsapp_link}" target="_blank"
                style="color:#0085cc;font-weight:600; font-size:1.1em; text-decoration:underline; border-radius:8px; padding:8px 18px; display:inline-block;">
                    Prenota subito un appuntamento con noi via Whatsapp al numero {WHATSAPP_DISPLAY}
                </a>
            </div>
        """

        mail_html = f"""
        <div style="background:#fff; border-radius:16px; font-family:Montserrat,Arial,sans-serif; color:#222; max-width:480px; margin:auto; border:1.5px solid #e3eafc; box-shadow:0 8px 32px rgba(50,90,200,0.07); padding:28px;">
            <img src="cid:logo_img" style="display:block; margin:0 auto 18px auto; max-width:120px;">
            <h2 style="text-align:center; color:#0085cc; font-size:1.35em; margin-bottom:26px; margin-top:0; font-weight:600;">Consulenza Estetica AMATI by BeautyLab</h2>
            <hr style="margin:18px 0 18px 0;border:none;border-top:1.5px solid #e3eafc;">
            <div style="font-size:1.1em;line-height:1.6; color:#222;">
                {answer_html}
                {whatsapp_html}
            </div>
        </div>
        """

        try:
            msg = Message(
                f"Consulenza estetica personalizzata AMATI by BeautyLab",
                sender=EMAIL_MITTENTE,
                recipients=[email]
            )
            msg.body = (
                f"Ciao {nome} {cognome},\n\n"
                f"Ecco il consiglio personalizzato AMATI:\n\n"
                f"{answer}\n\n"
                f"Ti affiancheremo in questo percorso di bellezza affinchè tu possa realizzare i tuoi obiettivi."
            )
            msg.html = mail_html

            # Allegare il logo inline per la mail HTML
            with app.open_resource("static/logo.jpg") as fp:
                msg.attach(
                    "logo.jpg",
                    "image/jpeg",
                    fp.read(),
                    'inline',
                    headers={'Content-ID': '<logo_img>'}
                )
            mail.send(msg)
        except Exception as e:
            return f"Risposta generata ma errore invio mail: {e}<br><br><b>Risposta AMATI:</b><br><pre>{answer}</pre>"

        return HTML_THANKS

    # GET request
    return render_template_string(HTML_FORM, errore=errore)

if __name__ == '__main__':
    app.run(debug=True)
