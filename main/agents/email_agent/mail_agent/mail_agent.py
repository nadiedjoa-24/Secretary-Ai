import os
from mail_handler.mail_handler import MAIL_HANDLER
from common.ai.API_client import API_Client
from common.ai.model.BaseAIModel import Message
import openai
from typing import Literal




class Mail_Agent:
    
    def __init__(self, EMAIL: str = None, PASSWORD: str = None, backend: Literal["API", "LOCAL"] = "API", API_KEY: str = None):
        self.backend = backend
        if EMAIL is not None and PASSWORD is not None:
            self.M = MAIL_HANDLER(EMAIL, PASSWORD)
        else:
            self.M = MAIL_HANDLER()

        self.client = None


    def _init_backend(self):

        # API mode (we use OpenAI's API but it can be extended to other APIs)
        if self.backend == "API":
            self.API_KEY = os.getenv("API_KEY")
            if not self.API_KEY:
                raise ValueError("API_KEY is required for API backend")
            openai.api_key = self.API_KEY
            try:
                self.client = API_Client(APi_KEY = self.API_KEY)
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
        prompt = f"You are an helpful assistant that gives a relevant summary of the following text. The summary has to be short and should containt the key elements. This is the text you have to sum up : {content}."
        msg: Message = Message(role="assistant", content=prompt)
        response = self.client.basic([msg]).content
        return response

    
    def summarize_mailbox(self) -> dict:
        """
        Summarize inbox's unseen emails.
        """



    def classify_email(self, content) -> str:
        """
        Classify the content of an email.
        """



# Test example 

if __name__ == "__main__":
    mail_agent = Mail_Agent()
