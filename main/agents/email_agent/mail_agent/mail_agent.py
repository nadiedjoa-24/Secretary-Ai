import os
from mail_handler.mail_handler import MAIL_HANDLER
import openai
from typing import Literal
from transformers import pipeline




class Mail_Agent:
    
    def __init__(self, EMAIL: str = None, PASSWORD: str = None, backend: Literal["API", "LOCAL"] = "API", API_KEY: str = None):
        self.backend = backend
        if EMAIL is not None and PASSWORD is not None:
            self.M = MAIL_HANDLER(EMAIL, PASSWORD)
        else:
            self.M = MAIL_HANDLER()

        self.model = None


    def _init_backend(self):

        # API mode (we use OpenAI's API but it can be extended to other APIs)
        if self.backend == "API":
            self.API_KEY = os.getenv("API_KEY")
            if not self.API_KEY:
                raise ValueError("API_KEY is required for API backend")
            openai.api_key = self.API_KEY
            try:
                self.model = openai.OpenAI(api_key=self.API_KEY)
            except Exception as e:
                raise ValueError(f"Failed to initialize API backend: {e}")

        # LOCAL mode (we use Huggingface's transformers package for local models)
        elif self.backend == "LOCAL":
            
            pass

        else:
            raise ValueError("Invalid backend. Choose 'API' or 'LOCAL'.")
        
    
    def summarize_email(self, content) -> str:
        """
        Summarize a single email's content.
        """
    
    def summarize_mailbox(self) -> dict:
        """
        Summarize inbox's unseen emails.
        """


    def classify_email(self, content) -> str:
        """
        Classify the content of an email.
        """
