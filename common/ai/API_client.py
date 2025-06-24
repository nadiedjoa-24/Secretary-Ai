import sys
import os
# Ajoute la racine du projet au PYTHONPATH pour permettre les imports absolus de "common"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from common.ai.model.BaseAIModel import BaseAIModel, Message
from typing import Literal, Optional, List, TypedDict
from pydantic import BaseModel

import openai
from google.cloud import texttospeech

import os

from common.ai.audio_controller.audio_controller import AUDIO_Controller


class API_Client(BaseAIModel):

    def __init__(self, API_KEY: Optional[str] = None, google_key_filename: str = "google_cloud_tts_key.json"):
        self.API_KEY = API_KEY
        if not self.API_KEY:
            try:
                self.API_KEY = os.getenv("API_KEY")
            except KeyError as e:
                raise ValueError(f"API_KEY is required for API backend, please provide one at instanciation or in environment :{e}")

        self.client = openai.OpenAI(api_key=self.API_KEY)
        self.google_key_path = os.path.join(os.getcwd(), google_key_filename)



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
            model = "o4-mini",
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
            input = messages,
            text_format = data_model,
        )

        if response.output_parsed:
            return response.output_parsed
        else:
            raise ValueError("No reponse from the API.")
        



    def tts(self, text: str, filename: str = "output.wav", engine: int = 2) -> str:
        output_path = "./audio_recordings/" + filename
        if engine == 1:
            # OpenAI TTS
            instr = "Speak in a neutral tone, you are a secretary assistant and must be professional."
            response = self.client.audio.speech.with_raw_response.create(
                model="gpt-4o-mini-tts",
                voice="alloy",
                input=text,
                instructions=instr
            )
            if response.content:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return filename
            else:
                raise ValueError("No response from the OpenAI TTS API.")
        elif engine == 2:
            # Google Cloud TTS: use service account file if present
            if os.path.isfile(self.google_key_path):
                tts_client = texttospeech.TextToSpeechClient.from_service_account_file(
                    self.google_key_path
                )
            else:
                tts_client = texttospeech.TextToSpeechClient()
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice_params = texttospeech.VoiceSelectionParams(
                language_code="fr-FR",
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16
            )
            response = tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice_params,
                audio_config=audio_config
            )
            if response.audio_content:
                with open(output_path, "wb") as f:
                    f.write(response.audio_content)
                return filename
            else:
                raise ValueError("No response from the Google Cloud TTS API.")
        else:
            raise ValueError("Invalid engine parameter: must be 1 (OpenAI) or 2 (Google Cloud).")

        
    
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



if __name__ == "__main__":
    import os
    from common.ai.model.BaseAIModel import Message
    from pydantic import BaseModel

    client = API_Client()
    audio_ctrl = AUDIO_Controller(device_index=2)

    # # Test basic()
    # print("=== Test basic() ===")
    # basic_msg = client.basic([Message(role="user", content="Bonjour, comment ça va ?")])
    # print(basic_msg.content)

    # # Test reflexion()
    # print("\n=== Test reflexion() ===")
    # reflex_msg = client.reflexion([Message(role="user", content="Explique-moi la loi de Murphy.")])
    # print(reflex_msg.content)

    # print("\n=== Test parse() ===")
    # parsed = client.parse([{"role": "user", "content": "Que vaut 6 + 3"}], Message)
    # print(parsed)

    # # Test TTS avec AUDIO_Controller
    # print("\n=== Test TTS via AUDIO_Controller ===")
    # tts_path = client.tts("Dans le silence doré du matin, un vieux vélo rouillé reposait contre le mur couvert de lierre.q")
    # print(f"tts path : {tts_path}")
    # path = "./audio_recordings/" + tts_path
    # audio_ctrl.play(path)
    # print(f"TTS généré et joué depuis : {tts_path}")

    # # Test STT avec AUDIO_Controller
    # print("\n=== Test STT via AUDIO_Controller ===")
    # audio_path = audio_ctrl._listen()
    # stt_msg = client.stt(audio_path)
    # print(f"Transcription: {stt_msg.content}")


    # Conversation continue : dit "exit" pour quitter
    print("\n=== Conversation continue (dit 'exit' pour quitter) ===")
    try:
        while True:
            print("Veuillez poser une question après le bip...")
            conv_audio = audio_ctrl._listen()
            conv_input = client.stt(conv_audio)
            content = conv_input.content.strip().lower()
            if content in ("exit", "quit", "stop"):
                print("Fin de la conversation.")
                break

            # Générer réponse AI
            ai_response = client.basic([Message(role="user", content=conv_input.content)])
            print(f"Réponse AI : {ai_response.content}")

            # Synthèse vocale et lecture
            response_tts_path = client.tts(ai_response.content)
            print(f"Fichier TTS généré : {response_tts_path}")
            audio_ctrl.play("./audio_recordings/" + response_tts_path)
    except KeyboardInterrupt:
        print("\nConversation interrompue par l'utilisateur.")