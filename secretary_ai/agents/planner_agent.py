import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import TYPE_CHECKING, Dict, List, Optional

from pydantic import BaseModel

from secretary_ai.agents.planner_controller import Appointment, PlannerController
from secretary_ai.ai.api_client import APIClient
from secretary_ai.ai.base_model import BaseAIModel, Message

if TYPE_CHECKING:
    from secretary_ai.ai.audio_controller import AudioController

logger = logging.getLogger(__name__)


class RescheduleDecision(BaseModel):
    new_date: Optional[date] = None
    new_time: Optional[time] = None
    final: bool = False


@dataclass
class RescheduleConversation:
    appointment: Appointment
    messages: List[Message] = field(default_factory=list)
    extraction: List[Message] = field(default_factory=list)
    done: bool = False


def current_date() -> date:
    return date.today()


def _next_month(day: date) -> date:
    return date(day.year + 1, 1, 1) if day.month == 12 else date(day.year, day.month + 1, 1)


def describe(appointment: Appointment) -> str:
    return (f"{appointment.name} {appointment.surname}, {appointment.date.isoformat()} at "
            f"{appointment.start_time:%H:%M} ({appointment.description or 'no reason given'})")


class PlannerAgent:
    """Agent that reschedules an appointment through a conversation with the patient."""

    def __init__(self, year: int = 2025, client: Optional[BaseAIModel] = None,
                 controller: Optional[PlannerController] = None, audio: Optional["AudioController"] = None):
        self.client = client or APIClient()
        self.controller = controller or PlannerController(year=year)
        self._audio = audio

    @property
    def audio(self) -> "AudioController":
        """Local microphone and speakers, only used by the command line version."""
        if self._audio is None:
            # Imported here because PyAudio is an optional dependency (requirements-cli.txt).
            from secretary_ai.ai.audio_controller import AudioController
            self._audio = AudioController()
        return self._audio

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

    def _reference_date(self, appointment: Appointment) -> date:
        # The calendar covers a single year. Outside of it, reason from the appointment date instead of today.
        today = current_date()
        return today if today.year == self.controller.year else appointment.date

    def start_rescheduling(self, appointment: Appointment) -> tuple[RescheduleConversation, str]:
        """Open the conversation and return it with the agent's first message."""
        today = self._reference_date(appointment)
        conversation = RescheduleConversation(appointment=appointment)
        conversation.messages.append(Message(role="system", content=(
            "You are the scheduling assistant of a medical office. You talk with a patient, in French, "
            f"to reschedule this appointment: {describe(appointment)}.\n"
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
        )))
        conversation.extraction.append(Message(role="system", content=(
            "Extract the new appointment date (YYYY-MM-DD) and time (HH:MM) from the conversation, only if the "
            "patient explicitly confirmed both. Do not infer anything. Set final to true only when both are "
            f"confirmed; otherwise leave the missing fields empty and final false. Today is {today.isoformat()}."
        )))
        return conversation, self._reply(conversation)

    def handle_patient_message(self, conversation: RescheduleConversation, text: str) -> str:
        """Process what the patient said and return the agent's answer. Sets `conversation.done` once rebooked."""
        if conversation.done:
            raise ValueError("This conversation is already finished.")
        patient = Message(role="user", content=text)
        conversation.messages.append(patient)
        conversation.extraction.append(patient)

        decision = self.client.parse(conversation.extraction, RescheduleDecision)
        if decision.final and decision.new_date and decision.new_time:
            appointment = conversation.appointment
            if self._move(appointment, decision.new_date, decision.new_time):
                conversation.done = True
                instruction = (f"The appointment is now booked on {appointment.date.isoformat()} at "
                               f"{appointment.start_time:%H:%M}. Confirm it to the patient and end the conversation politely.")
            else:
                instruction = ("That slot is not available. Apologize briefly and offer another slot from the list.")
            conversation.messages.append(Message(role="system", content=instruction))
        return self._reply(conversation)

    def _reply(self, conversation: RescheduleConversation) -> str:
        reply = self.client.basic(conversation.messages)
        conversation.messages.append(reply)
        conversation.extraction.append(reply)
        return reply.content

    def _move(self, appointment: Appointment, new_date: date, new_time: time) -> bool:
        self.controller.delete_appointment(appointment)
        new_start = datetime.combine(new_date, new_time.replace(tzinfo=None))
        free = new_date.year == self.controller.year and new_start in self.controller.get_day_available_timeslots(new_date)
        if free:
            appointment.date, appointment.start_time = new_date, new_time
        self.controller.add_appointment(appointment)
        return free

    def reschedule_appointment(self, appointment: Appointment) -> Appointment:
        """Voice version for the command line: talks through the local microphone and speakers."""
        conversation, reply = self.start_rescheduling(appointment)
        self._say(reply)
        while not conversation.done:
            try:
                text = self.client.stt(self.audio.listen()).content
            except Exception:
                logger.exception("Could not record or transcribe the patient, listening again.")
                continue
            logger.info("Patient: %s", text)
            self._say(self.handle_patient_message(conversation, text))
        return appointment

    def _say(self, text: str) -> None:
        logger.info("Agent: %s", text)
        try:
            self.audio.play(self.client.tts(text))
        except Exception:
            logger.exception("Text-to-speech failed, continuing without audio.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = PlannerAgent()
    agent.reschedule_appointment(agent.controller.all_appointments()[0])
