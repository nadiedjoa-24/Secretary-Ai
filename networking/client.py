import requests


class Client:
    def __init__(self, server_url="http://137.194.192.96:8000"):  # IP de la machine qui héberge le serveur
        self.server_url = server_url
        self.check_connection()

    def check_connection(self):
        """ Vérifie si la connexion au serveur est bien établie """
        try:
            response = requests.get(f"{self.server_url}/docs", timeout=5)
            if response.status_code == 200:
                print("🟢Connexion établie avec succès au serveur !")
            else:
                print(f"Réponse inattendue du serveur : {response.status_code}")
        except requests.ConnectionError:
            print("🔴Impossible de se connecter au serveur. Vérifiez l'adresse et que le serveur est bien démarré.")
        except requests.Timeout:
            print("🔴Temps d'attente dépassé. Vérifiez si le serveur est accessible.")

    def generate(self, prompt, max_new_tokens=50):
        data = {"prompt": prompt, "max_new_tokens": max_new_tokens}
        try:
            response = requests.post(f"{self.server_url}/generate", json=data)
            if response.status_code == 200:
                return response.json()["response"]
            else:
                print("Erreur lors de la requête :", response.status_code, response.text)
                return None
        except Exception as e:
            print("Erreur lors de l'envoi de la requête :", e)
            return None
        



if __name__ == "__main__":
    
    client = Client()   

    print("Démarrage du chat. 'exit' pour quitter.")
    while True:
        prompt = input("Vous: ")
        if prompt.lower() == "exit":
            print("Fin de la conversation.")
            break
        
        result = client.generate(prompt)
        if result:
            print("Assistant:", result)