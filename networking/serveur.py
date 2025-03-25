import torch
import subprocess
from transformers import AutoTokenizer, AutoModelForCausalLM
from fastapi import FastAPI, Depends
from pydantic import BaseModel
import uvicorn
import sys
import os
from ai_model import LocalTransformer, LlamaModel


class QueryRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 50


class Server:
    def __init__(self, host="0.0.0.0", port=8000, use_llama=False):
        self.host = host
        self.port = port
        self.use_llama = use_llama

        if self.use_llama:
            self.model = LlamaModel()
        else:
            self.model = LocalTransformer()
        
        self.app = FastAPI()
        self._add_routes()

    def _add_routes(self):
        @self.app.post("/generate")
        async def generate(request: QueryRequest):
            print(f"Requête reçue: prompt={request.prompt}, max_new_tokens={request.max_new_tokens}")
            
            try:
                response_text = self.model.generate_response(request.prompt, request.max_new_tokens)
                print(f"Réponse générée: {response_text}")
                return {"response": response_text}
            except Exception as e:
                print(f"Erreur lors de la génération : {e}")
                return {"response": "Erreur lors de la génération"}

    def start(self):
        uvicorn.run(self.app, host=self.host, port=self.port)





if __name__ == "__main__":
    use_llama = "--llama" in sys.argv
    server = Server(use_llama=use_llama)
    server.start()

