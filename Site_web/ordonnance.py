from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
import os
import sys
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ai_agents.ordo_agent import OrdoAgent

app = Flask(__name__)
app.secret_key = "supersecretkey"

stop_flag = threading.Event()

@app.route("/", methods=["GET", "POST"])
def ordonnance():
    result = None
    if request.method == "POST":
        agent = OrdoAgent()
        flash("Veuillez dicter l'ordonnance après le bip...", "info")
        transcript = agent.reconnaitre_voix()
        infos = agent.extraire_infos_ordonnance(transcript)
        if infos:
            chemin_pdf = agent.generer_ordonnance(infos)
            if chemin_pdf:
                flash("Ordonnance générée avec succès !", "success")
                flash(f"Fichier généré : {os.path.basename(chemin_pdf)}", "file")
            else:
                flash("Erreur lors de la génération du fichier.", "danger")
        else:
            flash("Impossible d'extraire les informations de l'ordonnance.", "danger")
        return redirect(url_for("ordonnance"))
    return render_template("ordonnance.html")

@app.route("/stop", methods=["POST"])
def stop_recording():
    stop_flag.set()
    return jsonify({"status": "stopped"})

@app.route('/ordonnances/<filename>')
def download_ordonnance(filename):
    # Chemin absolu vers le dossier 'ordonnances' à la racine du projet
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dossier_ordonnances = os.path.join(base_dir, "ordonnances")
    return send_from_directory(dossier_ordonnances, filename)

if __name__ == "__main__":
    app.run(debug=True)