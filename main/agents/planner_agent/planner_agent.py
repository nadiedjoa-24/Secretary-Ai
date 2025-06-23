import os, sys
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(__file__,'..','..','..','..')
    )
)

from common.ai.API_client import API_Client
from common.ai.model.BaseAIModel import Message, BaseAIModel
from common.ai.audio_controller.audio_controller import AUDIO_Controller
from main.agents.planner_agent.planner_controller.planner_controller import Appointment, PlannerController
from typing import Literal, List



class Planner_agent:
    
    def __init__(self, backend: Literal["API", "LOCAL"] = "API", API_KEY: str = None):
        self.API_KEY = API_KEY
        self.audio_ctrl = AUDIO_Controller()
        
        self.backend = backend
        self.client = None
        self._init_backend()


    def _init_backend(self):
        # API mode (we use OpenAI's API but it can be extended to other APIs)
        if self.backend == "API":
            if not self.API_KEY:
                try:
                    self.API_KEY = os.getenv("API_KEY")
                except KeyError as e:
                    raise ValueError(f"API_KEY is required for API backend, please provide one at instantiation or in environment: {e}")
            try:
                self.client = API_Client(API_KEY = self.API_KEY)
            except Exception as e:
                raise ValueError(f"Failed to initialize API backend: {e}")

        # LOCAL mode (we use Huggingface's transformers package for local models)
        elif self.backend == "LOCAL":
            pass

        else:
            raise ValueError("Invalid backend. Choose 'API' or 'LOCAL'.")
        


        def reschedule_appointment(self, appointment: Appointment):  
            rescheduled: bool = False

            while not rescheduled:
                try: 
                    filepath = self.audio_ctrl.listen()
                except Exception as e:
                    print(f"❌ Erreur lors de l'enregistrement audio : {e}")
                    continue
                    
                transcription = self.client.stt(filepath)
                

                    


        


# Test

if __name__ == "__main__":
    pass 