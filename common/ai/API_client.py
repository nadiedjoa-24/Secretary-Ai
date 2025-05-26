from model.BaseAIModel import BaseAIModel, Message
from typing import Literal, Optional, List, TypedDict
from pydantic import BaseModel
import openai
import os


class API_Client(BaseAIModel):

    def __init__(self,  API_KEY: Optional[str] = None):

        self.API_KEY = API_KEY
        if not self.API_KEY:
            try:
                self.API_KEY = os.getenv("API_KEY")
            except KeyError as e:
                raise ValueError(f"API_KEY is required for API backend, please provide one at instanciation or in environment :{e}")

        self.client = openai.OpenAI(api_key=self.API_KEY)



    def basic(self, messages: List[Message]) -> Message:

        response = self.client.chat.completions.create(
            model = "gpt-4o-mini",
            messages = messages,
            temperature = 0.7,
        )

        if response.choices[0].message.content:
            msg: Message = Message(role="assistant", content=response.choices[0].message.content)
            return msg
        
        else:
            raise ValueError("No response from the API.")
        

    def reflexion(self, messages: List[Message]) -> Message:

        response = self.client.chat.completions.create(
            model = "gpt-4o-mini",
            messages = messages,
            temperature = 0.7,
        )

        if response.choices[0].message.content:
            msg: Message = Message(role="assistant", content=response.choices[0].message.content)
            return msg
        
        else:
            raise ValueError("No response from the API.")
        
    

    def parse(self, messages: List[dict], data_model: BaseModel) -> BaseModel:
        
        response = self.client.responses.parse(
            model = "gpt-4o-mini",
            messages = messages,
            text_format = data_model,
        )

        if response.output_parsed:
            return response.output_parsed
        else:
            raise ValueError("No reponse from the API.")


    def tts(self, text: str, output_path: str = "output.mp3") -> str:

        instr = ""

        response = self.client.audio.speech.with_raw_response.create(
            model = "gpt-4o-mini-tts",
            voice = "coral",
            input = text,
            instructions = instr
        )
        if response.content:
            with open(output_path, "wb") as f:
                f.write(response.content)
            
            return output_path
        else:
            raise ValueError("No response from the API.")

        
    
    def stt(self, audio_path: str) -> Message:

        with open(audio_path, "rb") as f:
            response = self.client.audio.transcriptions.create(
                model = "gpt-4o-mini-transcribe",
                file = f
            )
            if response.text:
                msg: Message = Message(role="assistant", content=response.text)
                return msg
            else:
                raise ValueError("No response from the API.")




    


