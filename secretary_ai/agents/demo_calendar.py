"""Fictional calendar of the demo, generated around the current date.

It covers the past 20 months and the next 4, for the four practitioners of the fictional medical center.
Past days are busier than future ones, as in a real office where patients book a few weeks ahead.
Usage: python -m secretary_ai.agents.demo_calendar [--today YYYY-MM-DD]
"""
import argparse
import random
import unicodedata
from datetime import date, time, timedelta

from secretary_ai.agents.planner_controller import DOCTORS, Appointment, PlannerController, is_working_day

MONTHS_BEFORE, MONTHS_AFTER = 20, 4
SEED = 2025

FIRST_NAMES = [
    "Alice", "Antoine", "Camille", "Chloé", "Claire", "David", "Élodie", "Emma", "Fatima", "François",
    "Georges", "Hélène", "Hugo", "Ibrahim", "Inès", "Jeanne", "Julie", "Karim", "Léa", "Louis",
    "Lucas", "Manon", "Mathilde", "Nathalie", "Nicolas", "Nina", "Olivier", "Pauline", "Pierre", "Quentin",
    "Rachid", "Sophie", "Thomas", "Valérie", "Vincent", "Yasmine", "Zoé", "Bernard", "Monique", "Aïcha",
]
SURNAMES = [
    "Martin", "Bernard", "Dubois", "Durand", "Lefevre", "Leroy", "Moreau", "Simon", "Laurent", "Michel",
    "Garcia", "Haddad", "Rossi", "Petit", "Benali", "Nguyen", "Fontaine", "Chevalier", "Robin", "Gauthier",
    "Perrin", "Morin", "Mercier", "Blanc", "Guerin", "Muller", "Henry", "Roussel", "Nicolas", "Colin",
]
REASONS = {
    "médecin généraliste": [
        "Consultation", "Renouvellement d'ordonnance", "Suivi tension", "Suivi diabète", "Fièvre et toux",
        "Douleurs lombaires", "Bilan annuel", "Résultats d'analyses", "Certificat médical", "Consultation fatigue",
    ],
    "chirurgienne-dentiste": [
        "Détartrage", "Soin de carie", "Contrôle annuel", "Douleur dentaire", "Pose de couronne", "Extraction",
    ],
    "kinésithérapeute": [
        "Rééducation genou", "Séance lombalgie", "Rééducation épaule", "Entorse de la cheville",
        "Kinésithérapie respiratoire", "Rééducation post-opératoire",
    ],
}
SEASONAL_REASONS = {9: "Certificat de sport", 10: "Vaccin grippe", 11: "Vaccin grippe"}
SLOTS = [time(hour, minute) for hour in (8, 9, 10, 11, 14, 15, 16, 17) for minute in (0, 30)]


def ascii_lower(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower().replace(" ", "")


def make_patients(rng: random.Random, count: int = 180) -> list[dict]:
    pairs = rng.sample([(name, surname) for name in FIRST_NAMES for surname in SURNAMES], count)
    return [{
        "name": name,
        "surname": surname,
        "mail": f"{ascii_lower(name)}.{ascii_lower(surname)}@example.com",
        # 06 39 98 is a range reserved by the French telecom regulator for fiction.
        "phone": f"06 39 98 {rng.randint(0, 99):02d} {rng.randint(0, 99):02d}",
    } for name, surname in pairs]


def on_leave(day: date, doctor_index: int) -> bool:
    """Each practitioner takes two weeks off in August, one week after the previous one."""
    august = date(day.year, 8, 1)
    start = august + timedelta(days=(7 - august.weekday()) % 7 + 7 * doctor_index)
    return start <= day < start + timedelta(weeks=2)


def daily_load(day: date, today: date) -> float:
    """Average number of appointments per practitioner and day."""
    if day <= today:
        return 2.6
    weeks_ahead = (day - today).days / 7
    return max(0.3, 2.4 - 0.25 * weeks_ahead)


def pick_reason(rng: random.Random, specialty: str, day: date) -> str:
    if specialty == "médecin généraliste" and day.month in SEASONAL_REASONS and rng.random() < 0.3:
        return SEASONAL_REASONS[day.month]
    return rng.choice(REASONS[specialty])


def shift_months(day: date, months: int) -> date:
    """First day of the month `months` months away from `day`."""
    index = day.year * 12 + day.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def generate(today: date) -> list[Appointment]:
    rng = random.Random(SEED)
    patients = make_patients(rng)
    appointments = []
    day, end = shift_months(today, -MONTHS_BEFORE), shift_months(today, MONTHS_AFTER + 1) - timedelta(days=1)
    while day <= end:
        for index, (doctor, specialty) in enumerate(DOCTORS.items()):
            if not is_working_day(day) or on_leave(day, index):
                continue
            # Binomial draw over the 16 daily slots, with the expected load as mean.
            count = sum(rng.random() < daily_load(day, today) / len(SLOTS) for _ in SLOTS)
            for start_time in sorted(rng.sample(SLOTS, count)):
                appointments.append(Appointment(**rng.choice(patients), id=f"{rng.getrandbits(48):012x}", date=day,
                                                start_time=start_time, doctor=doctor,
                                                description=pick_reason(rng, specialty, day)))
        day += timedelta(days=1)
    return appointments


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--today", type=date.fromisoformat, default=date.today(),
                        help="date around which the calendar goes from busy to sparse")
    args = parser.parse_args()

    controller = PlannerController()
    controller.replace_all(generate(args.today))
    print(f"{len(controller.all_appointments())} appointments written to the calendar.")


if __name__ == "__main__":
    main()
