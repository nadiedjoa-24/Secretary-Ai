from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from llama_cpp import Llama
import os


print(torch.cuda.is_available())  # Doit retourner True
print(torch.cuda.device_count())  # Nombre de GPU détectés
print(torch.cuda.get_device_name(0))  # Nom du GPU


class LocalTransformer:
    """
    Classe permettant de charger un modèle depuis les packages transformers et de générer des réponses à partir d'un prompt.
    Le modèle est chargé et exécuté localement lors de l'initialisation de la classe.
    """
    def __init__(self, model_name: str = "./mistral"):

        print("Chargement du tokenizer...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        print("Chargement du modèle sur GPU...")
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto",
            load_in_8bit=True  # Réduction mémoire
        )
        self.model.eval()

        print("Modèle chargé avec succès sur le GPU.")
        print("Modèle chargé sur :", next(self.model.parameters()).device)

    def generate_response(self, prompt: str, max_length: int = 50) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt")
        output_ids = self.model.generate(**inputs, max_length=max_length, do_sample=True)
        response = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
        return response



class LlamaModel:
    """
    Classe permettant d'initialiser un modèle disponible dans llama.cpp et de générer une réponse.
    """

    def __init__(self, model_path: str = "./llama.cpp/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
                 n_ctx: int = 512, n_threads: int = 10, n_gpu_layers: int = 80):
        
        self.model = Llama(model_path=model_path, n_ctx=n_ctx, n_threads=n_threads, n_gpu_layers=n_gpu_layers)
        print("Modèle Llama chargé avec succès sur GPU.")

    def generate_response(self, prompt: str, max_tokens: int = 50) -> str:
        """
        Génère une réponse à partir du prompt fourni en utilisant le modèle Llama.
        Remarque : modifier max_tokens pour adapter la taille de la réponse.
        """
        response = self.model(prompt, max_tokens=max_tokens)
        generated_text = response["choices"][0]["text"].strip()
        return generated_text
    




if __name__ == "__main__":
    
    model = LocalTransformer()
    prompt = "Bonjour, comment ça va ?"
    print(model.generate_response(prompt))
