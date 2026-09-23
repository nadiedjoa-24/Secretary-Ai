import pytest

from secretary_ai.agents import prescription_agent
from secretary_ai.agents.prescription_agent import (
    Medication,
    Prescription,
    PrescriptionAgent,
    safe_filename,
)

DOLIPRANE = Medication(name="Doliprane 1g", dosage="matin et soir", duration="5 jours")


class FakeClient:
    def __init__(self, parsed):
        self.parsed = parsed
        self.calls = []

    def parse(self, messages, data_model):
        self.calls.append((messages, data_model))
        return self.parsed


def test_prescription_is_complete_only_when_every_field_is_filled():
    assert Prescription(patient="Pierre Durand", medications=[DOLIPRANE]).is_complete()
    assert not Prescription(patient="", medications=[DOLIPRANE]).is_complete()
    assert not Prescription(patient="Pierre Durand", medications=[]).is_complete()
    assert not Prescription(
        patient="Pierre Durand", medications=[Medication(name="Doliprane", dosage="", duration="5 jours")]
    ).is_complete()


def test_missing_fields_are_worded_for_the_user():
    prescription = Prescription(
        patient="", medications=[Medication(name="Doliprane", dosage="", duration="5 jours")]
    )

    assert prescription.missing_fields() == ["le nom du patient", "la posologie de Doliprane"]
    assert Prescription(patient="Pierre Durand", medications=[]).missing_fields() == ["au moins un médicament"]


def test_summary_lists_each_medication():
    summary = Prescription(patient="Pierre Durand", medications=[DOLIPRANE]).summary()

    assert "Patient : Pierre Durand" in summary
    assert "1. Doliprane 1g : matin et soir, pendant 5 jours" in summary


@pytest.mark.parametrize("name, expected", [
    ("Hélène Petit", "Helene_Petit"),
    ("../../etc/passwd", "etc_passwd"),
    ("   ", "patient"),
])
def test_safe_filename(name, expected):
    assert safe_filename(name) == expected


def test_generate_pdf_writes_inside_the_prescriptions_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(prescription_agent, "PRESCRIPTIONS_DIR", tmp_path)
    agent = PrescriptionAgent(client=object(), audio=object())

    prescription = Prescription(patient="../Pierre Durand", medications=[DOLIPRANE])
    first, second = agent.generate_pdf(prescription), agent.generate_pdf(prescription)

    assert first.parent == tmp_path
    assert first.name.startswith("ordonnance_Pierre_Durand_")
    assert first != second
    assert first.read_bytes().startswith(b"%PDF")


def test_generate_pdf_refuses_an_incomplete_prescription(tmp_path, monkeypatch):
    monkeypatch.setattr(prescription_agent, "PRESCRIPTIONS_DIR", tmp_path)
    agent = PrescriptionAgent(client=object(), audio=object())

    with pytest.raises(ValueError):
        agent.generate_pdf(Prescription(patient="Pierre Durand", medications=[]))


def test_extract_prescription_sends_the_transcript_to_the_model():
    expected = Prescription(patient="Pierre Durand", medications=[DOLIPRANE])
    client = FakeClient(expected)
    agent = PrescriptionAgent(client=client, audio=object())

    assert agent.extract_prescription("Pierre Durand, Doliprane 1g matin et soir pendant 5 jours") == expected
    messages, data_model = client.calls[0]
    assert data_model is Prescription
    assert messages[-1].content.startswith("Pierre Durand")
