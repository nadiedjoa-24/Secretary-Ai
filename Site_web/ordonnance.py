from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
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
            agent.generer_ordonnance(infos)
            flash("Ordonnance générée avec succès !", "success")
        else:
            flash("Impossible d'extraire les informations de l'ordonnance.", "danger")
        return redirect(url_for("ordonnance"))
    return render_template("ordonnance.html")

@app.route("/stop", methods=["POST"])
def stop_recording():
    stop_flag.set()
    return jsonify({"status": "stopped"})

if __name__ == "__main__":
    app.run(debug=True)