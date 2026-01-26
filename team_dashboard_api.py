from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel


from team_dashboard import greet as greet_fn

app = FastAPI(title="Team Dashboard API", version="1.0.0")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    ok: bool
    service: str


class GreetResponse(BaseModel):
    message: str


class Team(BaseModel):
    id: int
    name: str
    members: int
    status: str


class Appointment(BaseModel):
    id: int
    patient_name: str
    doctor_name: str
    time: datetime
    status: str = "scheduled"  # scheduled | completed | cancelled


class Patient(BaseModel):
    id: int
    name: str
    age: int
    condition: str


class PatientCreate(BaseModel):
    name: str
    age: int
    condition: str


class Doctor(BaseModel):
    id: int
    name: str
    specialty: str | None = None
    appointment_count: int | None = None  # filled dynamically


class AppointmentCreate(BaseModel):
    patient_name: str
    doctor_name: str
    time: datetime


class DashboardOverview(BaseModel):
    total_patients: int
    total_doctors: int
    total_appointments: int
    appointments_by_status: dict[str, int]


# ---------------------------------------------------------------------------
# Fake in-memory data
# ---------------------------------------------------------------------------

FAKE_TEAMS: list[Team] = [
    Team(id=1, name="Doctors", members=5, status="active"),
    Team(id=2, name="Nurses", members=12, status="active"),
    Team(id=3, name="Admin Staff", members=4, status="active"),
]

FAKE_APPOINTMENTS: list[Appointment] = [
    Appointment(
        id=1,
        patient_name="John Doe",
        doctor_name="Dr. Smith",
        time="2025-01-01T09:00:00",
        status="scheduled",
    ),
    Appointment(
        id=2,
        patient_name="Jane Roe",
        doctor_name="Dr. Brown",
        time="2025-01-01T10:30:00",
        status="scheduled",
    ),
    Appointment(
        id=3,
        patient_name="Test Patient",
        doctor_name="Dr. Who",
        time="2025-01-10T14:30:00",
        status="scheduled",
    ),
]

FAKE_PATIENTS: list[Patient] = [
    Patient(id=1, name="John Doe", age=40, condition="Check-up"),
    Patient(id=2, name="Jane Roe", age=35, condition="Flu"),
]

DOCTORS: list[Doctor] = [
    Doctor(id=1, name="Dr. Smith", specialty="General"),
    Doctor(id=2, name="Dr. Brown", specialty="Internal Medicine"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_doctor_response(doctor: Doctor) -> dict:
    """
    Return a dict for a doctor with appointment_count computed
    from FAKE_APPOINTMENTS.
    """
    count = sum(1 for appt in FAKE_APPOINTMENTS if appt.doctor_name == doctor.name)
    return {
        "id": doctor.id,
        "name": doctor.name,
        "specialty": doctor.specialty,
        "appointment_count": count,
    }


# ---------------------------------------------------------------------------
# Core endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Basic health check used by tests."""
    return HealthResponse(ok=True, service="team_dashboard_api")


@app.get("/greet", response_model=GreetResponse)
def greet(name: str = "Velu") -> GreetResponse:
    """
    HTTP wrapper around team_dashboard.greet.

    - default: /greet              -> "Hello, Velu!"
    - custom:  /greet?name=Mani    -> "Hello, Mani!"
    """
    msg = greet_fn(name)
    return GreetResponse(message=msg)


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------


@app.get("/teams", response_model=list[Team])
def list_teams() -> list[Team]:
    """Return all teams (dummy data)."""
    return FAKE_TEAMS


@app.get("/teams/{team_id}", response_model=Team)
def get_team(team_id: int) -> Team:
    """Return a single team by id (404 if not found)."""
    for t in FAKE_TEAMS:
        if t.id == team_id:
            return t
    raise HTTPException(status_code=404, detail="team not found")


# ---------------------------------------------------------------------------
# Patients
# ---------------------------------------------------------------------------


@app.get("/patients", response_model=list[Patient])
def list_patients() -> list[Patient]:
    """Return all patients."""
    return FAKE_PATIENTS


@app.get("/patients/{patient_id}", response_model=Patient)
def get_patient(patient_id: int) -> Patient:
    """Return a single patient by id, or 404 if not found."""
    for p in FAKE_PATIENTS:
        if p.id == patient_id:
            return p
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="patient not found",
    )


@app.post("/patients", status_code=status.HTTP_201_CREATED, response_model=Patient)
def create_patient(body: PatientCreate) -> Patient:
    """Create a new patient and return it."""
    new_id = max((p.id for p in FAKE_PATIENTS), default=0) + 1
    patient = Patient(id=new_id, **body.model_dump())
    FAKE_PATIENTS.append(patient)
    return patient


# ---------------------------------------------------------------------------
# Appointments
# ---------------------------------------------------------------------------


@app.get("/appointments", response_model=list[Appointment])
def list_appointments(
    doctor: Optional[str] = None,
    patient: Optional[str] = None,
) -> list[Appointment]:
    """
    List appointments, optionally filtered by doctor or patient.
    """
    items = FAKE_APPOINTMENTS
    if doctor:
        items = [a for a in items if a.doctor_name == doctor]
    if patient:
        items = [a for a in items if a.patient_name == patient]
    return items


@app.get("/appointments/summary")
def appointments_summary() -> dict:
    """
    Return a simple summary of appointments:
      - total: total number of appointments
      - by_status: dict of status -> count
    """
    status_counts = Counter(appt.status for appt in FAKE_APPOINTMENTS)
    return {
        "total": len(FAKE_APPOINTMENTS),
        "by_status": dict(status_counts),
    }


@app.get("/appointments/{appointment_id}", response_model=Appointment)
def get_appointment(appointment_id: int) -> Appointment:
    """
    Fetch a single appointment by its ID.
    Returns 404 if not found.
    """
    for appt in FAKE_APPOINTMENTS:
        if appt.id == appointment_id:
            return appt
    raise HTTPException(status_code=404, detail="appointment not found")


@app.post(
    "/appointments/{appointment_id}/cancel",
    response_model=Appointment,
)
def cancel_appointment(appointment_id: int) -> Appointment:
    """
    Mark an appointment as cancelled and return the updated record.
    """
    for appt in FAKE_APPOINTMENTS:
        if appt.id == appointment_id:
            appt.status = "cancelled"
            return appt
    raise HTTPException(status_code=404, detail="appointment not found")


@app.post("/appointments", response_model=Appointment, status_code=201)
def create_appointment(body: AppointmentCreate) -> Appointment:
    """Create a new appointment."""
    new_id = max((a.id for a in FAKE_APPOINTMENTS), default=0) + 1
    appt = Appointment(id=new_id, **body.model_dump())
    FAKE_APPOINTMENTS.append(appt)
    return appt


# ---------------------------------------------------------------------------
# Doctors
# ---------------------------------------------------------------------------


@app.get("/doctors", response_model=list[Doctor])
def list_doctors() -> list[Doctor] | list[dict]:
    """
    List all doctors with their appointment_count.
    """
    return [_build_doctor_response(d) for d in DOCTORS]


@app.get("/doctors/{doctor_id}", response_model=Doctor)
def get_doctor_by_id(doctor_id: int) -> Doctor | dict:
    """
    Return one doctor with appointment_count, or 404 if not found.
    """
    for d in DOCTORS:
        if d.id == doctor_id:
            return _build_doctor_response(d)
    raise HTTPException(status_code=404, detail="doctor not found")


@app.get("/dashboard/overview", response_model=DashboardOverview)
def dashboard_overview() -> DashboardOverview:
    """
    High-level overview numbers for the dashboard.
    """
    status_counts = Counter(appt.status for appt in FAKE_APPOINTMENTS)
    return DashboardOverview(
        total_patients=len(FAKE_PATIENTS),
        total_doctors=len(DOCTORS),
        total_appointments=len(FAKE_APPOINTMENTS),
        appointments_by_status=dict(status_counts),
    )
