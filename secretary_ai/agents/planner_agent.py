import logging
from datetime import date, time
from typing import Dict, List, Optional

from pydantic import BaseModel

from secretary_ai.agents.planner_controller import Appointment, PlannerController
from secretary_ai.ai.api_client import APIClient
from secretary_ai.ai.audio_controller import AudioController
from secretary_ai.ai.base_model import BaseAIModel, Message

logger = logging.getLogger(__name__)


class RescheduleDecision(BaseModel):
    new_date: Optional[date] = None
    new_time: Optional[time] = None
    final: bool = False


def _next_month(day: date) -> date:
    return date(day.year + 1, 1, 1) if day.month == 12 else date(day.year, day.month + 1, 1)


class PlannerAgent:
    """Voice agent that reschedules an appointment through a spoken conversation with the patient."""

    def __init__(self, year: int = 2025, client: Optional[BaseAIModel] = None,
                 controller: Optional[PlannerController] = None, audio: Optional[AudioController] = None):
        self.client = client or APIClient()
        self.controller = controller or PlannerController(year=year)
        self.audio = audio or AudioController()

    def get_available_timeslots(self, from_date: date) -> Dict[int, Dict[int, List[str]]]:
        """Free slots from `from_date` to the end of the following month, as {month: {day: ["HH:MM", ...]}}."""
        slots = []
        for first_day in (date(from_date.year, from_date.month, 1), _next_month(from_date)):
            for week in self.controller.get_month_available_timeslots(first_day):
                for day_slots in week:
                    slots.extend(slot for slot in day_slots if slot.date() >= from_date)

        result: Dict[int, Dict[int, List[str]]] = {}
        for slot in slots:
            result.setdefault(slot.month, {}).setdefault(slot.day, []).append(slot.strftime("%H:%M"))
        return result

    def _say(self, text: str) -> None:
        logger.info("Agent: %s", text)
        try:
            self.audio.play(self.client.tts(text))
        except Exception:
            logger.exception("Text-to-speech failed, continuing without audio.")

    def reschedule_appointment(self, appointment: Appointment) -> Appointment:
        today = date.today()
        conversation: List[Message] = [Message(role="system", content=(
            "You are the scheduling assistant of a medical office. You talk with a patient over voice, in French, "
            f"to reschedule this appointment: {appointment}.\n"
            f"Today is {today.strftime('%A')} {today.isoformat()}.\n"
            f"Available slots for the next two months, as {{month: {{day: [times]}}}}: "
            f"{self.get_available_timeslots(today)}\n\n"
            "Rules:\n"
            "1. Stay professional, warm and clear.\n"
            "2. First ask which day suits the patient and whether they prefer morning or afternoon.\n"
            "3. Only offer slots from the list above.\n"
            "4. Sum up the chosen slot and ask for explicit confirmation before validating it.\n"
            "5. Keep the conversation going until a new slot is confirmed.\n"
            "This is a spoken conversation: keep answers short and never read out a long list of slots."
        ))]
        extraction: List[Message] = [Message(role="system", content=(
            "Extract the new appointment date (YYYY-MM-DD) and time (HH:MM) from the conversation, only if the "
            "patient explicitly confirmed both. Do not infer anything. Set final to true only when both are "
            f"confirmed; otherwise leave the missing fields empty and final false. Today is {today.isoformat()}."
        ))]

        reply = self.client.basic(conversation)
        conversation.append(reply)
        self._say(reply.content)

        while True:
            try:
                patient = Message(role="user", content=self.client.stt(self.audio.listen()).content)
            except Exception:
                logger.exception("Could not record or transcribe the patient, listening again.")
                continue
            logger.info("Patient: %s", patient.content)
            conversation.append(patient)
            extraction.append(patient)

            decision = self.client.parse(extraction, RescheduleDecision)
            if decision.final and decision.new_date and decision.new_time:
                self.controller.delete_appointment(appointment)
                appointment.date, appointment.start_time = decision.new_date, decision.new_time
                self.controller.add_appointment(appointment)
                conversation.append(Message(role="system", content=(
                    f"The appointment is now booked on {appointment.date} at {appointment.start_time}. "
                    "Confirm it to the patient and end the conversation politely."
                )))
                self._say(self.client.basic(conversation).content)
                return appointment

            reply = self.client.basic(conversation)
            conversation.append(reply)
            extraction.append(reply)
            self._say(reply.content)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = PlannerAgent()
    first_appointment = agent.controller.all_appointments()[0]
    agent.reschedule_appointment(first_appointment)
