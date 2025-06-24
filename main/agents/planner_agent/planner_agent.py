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
from typing import Literal, List, Optional, Dict
from pydantic import BaseModel
from pydantic import field_validator
from datetime import datetime, date, time



class Conv(BaseModel):
    conversation: List[Message] = []

    def append(self, msg: Message):
        self.conversation.append(msg)

    def to_dict(self):
        L = []
        for msg in self.conversation:
            L.append({
                "role": msg.role,
                "content": msg.content
            })
        return L
    

class NewDate(BaseModel):
    new_date: Optional[date] = None
    new_time: Optional[time] = None
    final: bool = False


    



class Planner_agent:
    
    def __init__(self, backend: Literal["API", "LOCAL"] = "API", API_KEY: str = None):
        self.API_KEY = API_KEY
        self.audio_ctrl = AUDIO_Controller()
        self.planner_controller = PlannerController(year=2025)
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
    
    def get_available_timeslots(self, from_date: date) -> List[datetime]:
        """
        Get available timeslots for a given date.
        """
        if not isinstance(from_date, date):
            raise ValueError("from_date must be a date object.")
        
        mois = from_date.month
        year = from_date.year
        next_mont = (mois + 1)%12
        next_year = year + (mois+1)//12
        date1 = datetime(year, mois, 1)
        date2 = datetime(next_year, next_mont, 1)
        print(date1, date2)
        month_slots: List[List[List[datetime]]] = self.planner_controller.get_month_available_timeslots(date = date1)
        next_month_slots = self.planner_controller.get_month_available_timeslots(date = date2)
        available_slots: List[datetime] = []
        for x in month_slots:
            for y in x:
                for z in y:
                    if z.day >= from_date.day:
                        available_slots.append(z)

        for x in next_month_slots:
            for y in x:
                for z in y:
                    available_slots.append(z)

        result: Dict[int, Dict[int, List[str]]] = dict()
        for slot in available_slots:
            month = slot.month
            day = slot.day
            time_slot = slot.strftime("%H:%M")
            if month not in result:
                result[month] = dict()
            if day not in result[month]:
                result[month][day] = []
            
            result[month][day].append(time_slot)
        return result
 

    def reschedule_appointment(self, appointment: Appointment): 

        rescheduled: bool = False
        system_prompt = f"""
        Vous êtes **l’agent de planification** chargé de reprogrammer le rendez-vous suivant : {appointment}

        Contexte
        ────────
        • Date du jour : {datetime.now().date()}
        • Créneaux libres (à partir d’aujourd’hui, pour les deux mois à venir) :
        {self.get_available_timeslots(from_date=datetime.today().date())}

        Objectif
        ────────
        Guider le patient jusqu’à ce qu’un nouveau créneau soit validé.

        Règles de conversation
        1. Restez professionnel(le), empathique et toujours clair(e).
        2. Demandez d'abord au patient quel jour lui conviendrait le mieux et si il a une préférence entre matin ou après-midi. 
        3. Utilisez uniquement les créneaux listés pour proposer des dates / heures.
        4. Reformulez brièvement les choix et demandez une confirmation explicite avant validation.
        5. Poursuivez le dialogue tant que la replanification n'a pas été validée.

        IL S'AGIT D'UNE CONVERSATION VOCALE QUI DOIT ÊTRE NATURELLE ET DONC ON NE PEUT PAS LISTER 10 CRÉNEAUX D'AFFILÉE PAR EXEMPLE.
        Il est impératif que la conversation soit la plus fluide et naturelle possible, comme si vous discutiez avec un patient en face à face.
        """        
        
        parsing_prompt = (
                    f"Tu es un agent d'extraction de données. Tu dois extraire de la conversation uniquement "
                    f"la date et l'heure du nouveau rendez-vous si et seulement si ils ont été clairement validé dans la conversation "
                    f"au format YYYY-MM-DD pour la date et HH:MM pour l'heure, sans aucune inférence. "
                    f"Si tu es certain que ces deux informations sont présentes, fixe le champ final à True, "
                    f"sinon laisse le champ final à False. Si l'utilisateur n'a pas explicitement fourni la date "
                    f"ou l'heure, les champs date et time doivent rester à None. Date du jour : {datetime.now().date()}."
                )
        conversation: Conv = Conv()
        parsing_conv: Conv = Conv()
        conversation.append(Message(role="system", content=system_prompt))
        parsing_conv.append(Message(role="system", content=parsing_prompt))


        new_date: NewDate = NewDate(date=None, time=None, final=False)

        response = self.client.basic(conversation.to_dict())
        try:
            output_path = self.client.tts(response.content)
            self.audio_ctrl.play("./audio_recordings/"+output_path)
        except Exception as e:
            print(f"❌ Erreur lors de la synthèse vocale : {e}")
            

        print(f"Réponse de l'agent : {response.role}, {response.content}")
        
        
        while not rescheduled:
            try: 
                filepath = self.audio_ctrl._listen()
                # text = input("Entrez votre message (ou 'exit' pour quitter) : ")
            except Exception as e:
                print(f"❌ Erreur lors de l'enregistrement audio : {e}")
                continue
            
            try:
                transcription = self.client.stt(filepath).content
                print(f"Transcription : {transcription}")
            except Exception as e:
                print(f"❌ Erreur lors de la transcription : {e}")
                continue

            new_msg = Message(role="user", content=transcription)
            # new_msg = Message(role="user", content=text)
            conversation.append(new_msg)
            parsing_conv.append(new_msg)


            try:
                new_date = self.client.parse(messages = parsing_conv.to_dict(), data_model= NewDate)
            except Exception as e:
                print(f"❌ Erreur lors de la réponse : {e}")
                continue

            print(f"Nouvelle date proposée : {new_date.new_date} à {new_date.new_time}, final : {new_date.final}")
            
            if new_date.final:
                self.planner_controller.delete_rdv(appointment=appointment)
                appointment.date = new_date.new_date
                appointment.start_time = new_date.new_time
                self.planner_controller.add_rdv(appointment=appointment)
                rescheduled = True
            
            answwer = self.client.basic(conversation.to_dict())
            conversation.append(answwer)
            parsing_conv.append(answwer)
            try:
                output_path = self.client.tts(answwer.content)
                self.audio_ctrl.play("./audio_recordings/"+output_path)
            except Exception as e:
                print(f"❌ Erreur lors de la synthèse vocale : {e}")
                continue
            print(f"Réponse de l'agent : {answwer.content}")
        
        print(f"✅ Rendez-vous reprogrammé pour le {appointment.date} à {appointment.start_time}.")


if __name__ == "__main__":

    appointment = Appointment(
        name="Alice",
        surname="Dupont",
        date=date(2025, 6, 30),
        mail="alice.dupont@example.com",
        phone=None,
        description="Test de replanification",
        start_time=time(10, 0)
    )

    agent = Planner_agent(backend="API")

    agent.planner_controller.add_rdv(appointment=appointment)

    # Exécution du test
    agent.reschedule_appointment(appointment)
    print(f"Nouveau rendez-vous : {appointment.date} à {appointment.start_time}")