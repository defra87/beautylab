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
CONSULENTE_EMAIL = "consulente@mybeautylab.it"    # Qui la tua copia, anche più indirizzi separati da virgola
WHATSAPP_NUMBER = "393492134144"
WHATSAPP_DISPLAY = "+39 349 21 34 144"
WHATSAPP_MSG = "Ciao Pamela e Anna, vorrei prenotare una consulenza con voi!"
# ---------------------

app = Flask(__name__)

# Configurazione Flask-Mail (Gmail)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = EMAIL_MITTENTE
app.config['MAIL_PASSWORD'] = EMAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = EMAIL_MITTENTE
mail = Mail(app)

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

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

HTML_FORM = """..."""  # Usa qui la tua versione HTML formata (tagliata per brevità, la hai già pronta sopra)

HTML_THANKS = """..."""  # Idem, la tua HTML di ringraziamento

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
             f"[Prodotti Farmogal:]\n{pdf_text[:1500]}\n"
            f"[Listino prezzi:]\n{listino_text[:800]}\n"
            f"[Promo del mese:]\n{promo_text[:400]}"
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
            # INVIO AL CLIENTE (con bcc al consulente)
            msg = Message(
                f"Consulenza estetica personalizzata AMATI by BeautyLab",
                sender=EMAIL_MITTENTE,
                recipients=[email],
                bcc=[CONSULENTE_EMAIL]
            )
            msg.body = (
                f"Ciao {nome} {cognome},\n\n"
                f"Ecco il consiglio personalizzato AMATI:\n\n"
                f"{answer}\n\n"
                f"Ti affiancheremo in questo percorso di bellezza affinchè tu possa realizzare i tuoi obiettivi."
            )
            msg.html = mail_html

            # Logo inline per il cliente
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

    return render_template_string(HTML_FORM, errore=errore)

if __name__ == '__main__':
    app.run(debug=True)
