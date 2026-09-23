import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING, Annotated, Dict, List, Optional

from pydantic import BaseModel, WithJsonSchema

from secretary_ai.agents.planner_controller import DOCTORS, Appointment, PlannerController
from secretary_ai.ai.api_client import APIClient
from secretary_ai.ai.base_model import BaseAIModel, Message

if TYPE_CHECKING:
    from secretary_ai.ai.audio_controller import AudioController

logger = logging.getLogger(__name__)

SLOT_LENGTH = timedelta(minutes=30)
FRENCH_MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin",
                 "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
FRENCH_WEEKDAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


# Asks the model for "HH:MM". The default JSON schema of `time` requires seconds, which models often leave out.
ClockTime = Annotated[time, WithJsonSchema({"type": "string", "pattern": "^([01][0-9]|2[0-3]):[0-5][0-9]$"})]


class RescheduleDecision(BaseModel):
    new_date: Optional[date] = None
    new_time: Optional[ClockTime] = None
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


def french_day(day: date) -> str:
    """ "mardi 29 septembre", or "jeudi 1er octobre" as French writes the first day of a month."""
    number = "1er" if day.day == 1 else str(day.day)
    return f"{FRENCH_WEEKDAYS[day.weekday()]} {number} {FRENCH_MONTHS[day.month - 1]}"


def french_date(day: date) -> str:
    """ "mardi 29 septembre 2026". Models map weekdays to dates poorly, so the prompt spells both out."""
    return f"{french_day(day)} {day.year}"


def describe(appointment: Appointment) -> str:
    doctor = f" with {appointment.doctor} ({DOCTORS.get(appointment.doctor, 'practitioner')})" if appointment.doctor else ""
    return (f"{appointment.name} {appointment.surname}, {french_date(appointment.date)} at "
            f"{appointment.start_time:%H:%M}{doctor} ({appointment.description or 'no reason given'})")


class PlannerAgent:
    """Agent that reschedules an appointment through a conversation with the patient."""

    def __init__(self, client: Optional[BaseAIModel] = None, controller: Optional[PlannerController] = None,
                 audio: Optional["AudioController"] = None):
        self.client = client or APIClient()
        self.controller = controller or PlannerController()
        self._audio = audio

    @property
    def audio(self) -> "AudioController":
        """Local microphone and speakers, only used by the command line version."""
        if self._audio is None:
            # Imported here because PyAudio is an optional dependency (requirements-cli.txt).
            from secretary_ai.ai.audio_controller import AudioController
            self._audio = AudioController()
        return self._audio

    def get_available_timeslots(self, from_date: date, doctor: Optional[str] = None) -> Dict[date, List[str]]:
        """Free slots of `doctor` from `from_date` to the end of the following month, as {day: ["HH:MM", ...]}."""
        result: Dict[date, List[str]] = {}
        for first_day in (from_date.replace(day=1), _next_month(from_date)):
            for week in self.controller.get_month_available_timeslots(first_day, doctor):
                for day_slots in week:
                    for slot in day_slots:
                        if slot.date() >= from_date:
                            result.setdefault(slot.date(), []).append(slot.strftime("%H:%M"))
        return result

    def describe_free_time(self, from_date: date, doctor: Optional[str] = None) -> str:
        """Free periods from `from_date`, one line per day, e.g. "mardi 14 janvier 2025: 08:00-12:00, 14:00-15:30".

        Much shorter than the list of every slot, which keeps the prompt small.
        """
        lines = []
        for day, times in self.get_available_timeslots(from_date, doctor).items():
            starts = [datetime.combine(day, time.fromisoformat(t)) for t in times]
            periods, period_start = [], starts[0]
            for previous, following in zip(starts, starts[1:] + [None]):
                if following != previous + SLOT_LENGTH:
                    periods.append(f"{period_start:%H:%M}-{previous + SLOT_LENGTH:%H:%M}")
                    period_start = following
            lines.append(f"{french_date(day)}: {', '.join(periods)}")
        return "\n".join(lines)

    def start_rescheduling(self, appointment: Appointment) -> tuple[RescheduleConversation, str]:
        """Open the conversation and return it with the agent's first message."""
        # Slots start tomorrow: a new appointment on the same day would leave the patient no time to plan.
        today = current_date()
        conversation = RescheduleConversation(appointment=appointment)
        conversation.messages.append(Message(role="system", content=(
            "You are the scheduling assistant of a medical office. You talk with a patient, in French, "
            f"to reschedule this appointment: {describe(appointment)}.\n"
            f"Today is {french_date(today)}.\n"
            "Free time of the same practitioner until the end of next month, one line per day. Always use the "
            "weekday written next to each date, never work it out yourself. Appointments last "
            "30 minutes and start on the hour or half hour, so a free period 08:00-10:00 means that 08:00, 08:30, "
            f"09:00 and 09:30 are available:\n"
            f"{self.describe_free_time(today + timedelta(days=1), appointment.doctor)}\n\n"
            "Rules:\n"
            "1. Stay professional, warm and clear.\n"
            "2. First ask which day suits the patient and whether they prefer morning or afternoon.\n"
            "3. Only offer slots within the free time above.\n"
            "4. Sum up the chosen slot and ask for explicit confirmation before validating it.\n"
            "5. Keep the conversation going until a new slot is confirmed.\n"
            "This is a spoken conversation: answer in plain sentences without any formatting, lists or dashes, "
            "keep answers short, offer at most three slots at a time, and say dates and times the way people speak (\"mardi 7 janvier à 9 heures\"), without the year and never "
            "as 2025-01-07 or 09:00."
        )))
        conversation.extraction.append(Message(role="system", content=(
            "Extract the new appointment date (YYYY-MM-DD) and time (HH:MM) from the conversation, only if the "
            "patient explicitly confirmed both. Do not infer anything. Set final to true only when both are "
            "confirmed; otherwise leave the missing fields empty and final false. "
            f"Today is {french_date(today)} ({today.isoformat()})."
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
                instruction = ("That slot is not available. Apologize briefly and offer another slot within the free time.")
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
        free = (new_date > current_date()
                and new_start in self.controller.get_day_available_timeslots(new_date, appointment.doctor))
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
    upcoming = [a for a in agent.controller.all_appointments() if a.date > current_date()]
    agent.reschedule_appointment(upcoming[0])
