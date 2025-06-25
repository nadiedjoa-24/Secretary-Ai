from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, session
import os
import sys
import threading


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ai_agents.ordo_agent import OrdoAgent, PatientInfo
from main.agents.email_agent.mail_agent.mail_agent import Mail_Agent

app = Flask(__name__)
app.secret_key = "supersecretkey"
stop_flag = threading.Event()
mail_agent = Mail_Agent()

@app.route("/")
def home():
    return render_template("home.html")

# --- Ordonnance ---
@app.route("/ordonnance", methods=["GET", "POST"])
def ordonnance():
    agent = OrdoAgent()
    if request.method == "POST":
        if "step" not in session:
            flash("Veuillez dicter l'ordonnance après le bip...", "info")
            transcript = agent.reconnaitre_voix()
            infos = agent.extraire_infos_ordonnance(transcript)
            if infos and infos.patient and infos.medicaments:
                medicaments_complets = all(med.nom and med.posologie and med.duree for med in infos.medicaments)
                confirmation_text = get_confirmation_text(infos)
                if medicaments_complets:
                    # Affiche la confirmation sur le site
                    agent.afficher_confirmation(infos)
                    # Demande confirmation orale (micro)
                    confirmation = agent.demander_confirmation_orale()
                    if confirmation is True:
                        chemin_pdf = agent.generer_ordonnance(infos)
                        if chemin_pdf:
                            flash("✅ Ordonnance générée avec succès !", "success")
                            flash(f"{os.path.basename(chemin_pdf)}", "file")
                        else:
                            flash("Erreur lors de la génération du fichier.", "danger")
                        # Propose de recommencer ou d'arrêter après génération
                        session["step"] = "retry"
                        session["infos"] = infos.model_dump()
                        return render_template(
                            "ordonnance.html",
                            infos=infos,
                            retry="after_success",
                            confirmation=False,
                            confirmation_text=confirmation_text
                        )
                    elif confirmation is False:
                        flash("Vous avez demandé une correction. Veuillez recommencer la dictée.", "info")
                        session["step"] = "retry"
                        session["infos"] = infos.model_dump()
                        return render_template(
                            "ordonnance.html",
                            infos=infos,
                            retry=True,
                            confirmation=False,
                            confirmation_text=confirmation_text
                        )
                    else:
                        flash("Réponse non comprise. Veuillez recommencer la dictée.", "danger")
                        session["step"] = "retry"
                        session["infos"] = infos.model_dump()
                        return render_template(
                            "ordonnance.html",
                            infos=infos,
                            retry=True,
                            confirmation=False,
                            confirmation_text=confirmation_text
                        )
                else:
                    flash("❌ Informations de médicaments incomplètes (posologie ou durée manquante).", "danger")
                    flash("Voulez-vous recommencer la dictée ? (Dites 'oui' pour recommencer ou 'non' pour arrêter)", "info")
                    session["step"] = "retry"
                    session["infos"] = infos.model_dump()
                    return render_template(
                        "ordonnance.html",
                        infos=infos,
                        retry=True,
                        confirmation=False,
                        confirmation_text=confirmation_text
                    )
            else:
                flash("❌ Impossible d'extraire les informations de l'ordonnance ou patient manquant.", "danger")
                flash("Voulez-vous recommencer la dictée ? (Dites 'oui' pour recommencer ou 'non' pour arrêter)", "info")
                session["step"] = "retry"
                session["infos"] = infos.model_dump() if infos else None
                return render_template(
                    "ordonnance.html",
                    infos=infos,
                    retry=True,
                    confirmation=False,
                    confirmation_text=None
                )

        # 2. Gestion de l'étape "retry"
        elif session.get("step") == "retry":
            if request.form.get("retry") == "oui":
                session.pop("step", None)
                session.pop("infos", None)
                return redirect(url_for("ordonnance"))
            elif request.form.get("retry") == "non":
                flash("Programme arrêté.", "danger")
                session.pop("step", None)
                session.pop("infos", None)
                return redirect(url_for("ordonnance"))
            else:
                infos = PatientInfo.parse_obj(session["infos"]) if session.get("infos") else None
                confirmation_text = get_confirmation_text(infos) if infos else None
                return render_template(
                    "ordonnance.html",
                    infos=infos,
                    retry=True,
                    confirmation=False,
                    confirmation_text=confirmation_text
                )
    # GET : affichage initial
    session.pop("step", None)
    session.pop("infos", None)
    return render_template("ordonnance.html", infos=None, confirmation=False, retry=False, confirmation_text=None)

@app.route("/stop", methods=["POST"])
def stop_recording():
    stop_flag.set()
    return jsonify({"status": "stopped"})

@app.route('/ordonnances/<filename>')
def download_ordonnance(filename):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dossier_ordonnances = os.path.join(base_dir, "ordonnances")
    return send_from_directory(dossier_ordonnances, filename)

# --- Gestion des mails ---
@app.route('/mails', methods=['GET', 'POST'])
def auto_sort():
    mode = None
    mails = []
    folders = mail_agent.M.get_folders()
    message = None
    messages = None

    # Résumer les mails
    if request.method == 'GET' and request.args.get('action') == 'summarize':
        mode = "summarize"
        unseen_emails = mail_agent.M.get_unread_emails()
        for email in unseen_emails:
            date = getattr(email, "date", "Date inconnue")
            summary = mail_agent.summarize_email(email)
            sender = getattr(email, "sender", "Expéditeur inconnu")
            if not summary or summary.strip() == "":
                summary = "Ce message ne peut pas être résumé."
            mails.append({
                "id": email.id,
                "date": date,
                "summary": summary,
                "sender": sender
            })

    # Déplacement manuel
    if request.method == 'POST' and 'email_id' in request.form:
        mode = "summarize"
        email_id = request.form.get('email_id')
        target_folder = request.form.get('target_folder')
        if email_id and target_folder:
            mail_agent.M.move_email(email_id, target_folder)
            message = "Mail déplacé avec succès !"
        unseen_emails = mail_agent.M.get_unread_emails()
        for email in unseen_emails:
            date = getattr(email, "date", "Date inconnue")
            summary = mail_agent.summarize_email(email)
            sender = getattr(email, "sender", "Expéditeur inconnu")
            if not summary or summary.strip() == "":
                summary = "Ce message ne peut pas être résumé."
            mails.append({
                "id": email.id,
                "date": date,
                "summary": summary,
                "sender": sender
            })
    return render_template("auto_sort.html", mails=mails, folders=folders, mode=mode, message=message, messages=messages)

def get_confirmation_text(infos):
    if not infos:
        return ""
    lines = []
    lines.append("\n" + "="*60)
    lines.append("CONFIRMATION DES INFORMATIONS EXTRAITES")
    lines.append("="*60)
    lines.append(f"Patient : {infos.patient}")
    lines.append("\nMédicaments prescrits :")
    for i, med in enumerate(infos.medicaments, 1):
        lines.append(f"  {i}. Nom : {med.nom}")
        lines.append(f"     Posologie : {med.posologie}")
        lines.append(f"     Durée : {med.duree}")
        lines.append("")
    lines.append("="*60)
    lines.append("Veuillez confirmer ces informations en répondant 'oui' ou 'non' à l'oral.")
    lines.append("="*60)
    return "\n".join(lines)

if __name__ == "__main__":
    app.run(debug=True)