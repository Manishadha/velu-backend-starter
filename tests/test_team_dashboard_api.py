from fastapi.testclient import TestClient

from team_dashboard_api import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["service"] == "team_dashboard_api"


def test_greet_default():
    r = client.get("/greet")
    assert r.status_code == 200
    data = r.json()
    assert data["message"] == "Hello, Velu!"


def test_greet_custom_name():
    r = client.get("/greet", params={"name": "Mani"})
    assert r.status_code == 200
    data = r.json()
    assert data["message"] == "Hello, Mani!"


# --- Patients ------------------------------------------------------------


def test_list_patients():
    r = client.get("/patients")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    assert "id" in data[0]
    assert "name" in data[0]


def test_get_patient_by_id_ok():
    r = client.get("/patients/1")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == 1
    assert data["name"] == "John Doe"


def test_get_patient_not_found():
    r = client.get("/patients/99999")
    assert r.status_code == 404
    data = r.json()
    assert data["detail"] == "patient not found"


def test_create_patient():
    payload = {
        "name": "New Patient",
        "age": 42,
        "condition": "Flu",
    }
    r = client.post("/patients", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["id"] >= 3
    assert data["name"] == "New Patient"

    r2 = client.get("/patients")
    ids = [p["id"] for p in r2.json()]
    assert data["id"] in ids


# --- Appointments --------------------------------------------------------


def test_list_appointments_basic():
    r = client.get("/appointments")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 2


def test_create_appointment():
    payload = {
        "patient_name": "Test Patient",
        "doctor_name": "Dr. Who",
        "time": "2025-01-01T15:00:00",
    }
    r = client.post("/appointments", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["patient_name"] == "Test Patient"
    assert data["doctor_name"] == "Dr. Who"


def test_get_appointment_by_id_ok():
    r = client.get("/appointments/3")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == 3
    assert data["doctor_name"] == "Dr. Who"
    assert data["patient_name"] == "Test Patient"


def test_appointments_summary():
    r = client.get("/appointments/summary")
    assert r.status_code == 200
    data = r.json()

    assert "total" in data
    assert "by_status" in data
    by_status = data["by_status"]

    assert data["total"] >= 2
    assert "scheduled" in by_status


def test_get_appointment_by_id_not_found():
    r = client.get("/appointments/9999")
    assert r.status_code == 404
    data = r.json()
    assert data["detail"] == "appointment not found"


def test_cancel_appointment():
    r = client.get("/appointments/1")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "scheduled"

    r2 = client.post("/appointments/1/cancel")
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["id"] == 1
    assert data2["status"] == "cancelled"

    r3 = client.get("/appointments/1")
    assert r3.status_code == 200
    data3 = r3.json()
    assert data3["status"] == "cancelled"


# --- Doctors ------------------------------------------------------------


def test_list_doctors_ok():
    r = client.get("/doctors")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 2

    smith = next(d for d in data if d["name"] == "Dr. Smith")
    assert smith["appointment_count"] >= 1


def test_get_doctor_by_id_ok():
    r = client.get("/doctors/1")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Dr. Smith"
    assert data["appointment_count"] >= 1


def test_get_doctor_by_id_not_found():
    r = client.get("/doctors/9999")
    assert r.status_code == 404
    assert r.json()["detail"] == "doctor not found"


def test_dashboard_overview():
    r = client.get("/dashboard/overview")
    assert r.status_code == 200
    data = r.json()

    # basic shape
    assert "total_patients" in data
    assert "total_doctors" in data
    assert "total_appointments" in data
    assert "appointments_by_status" in data

    # sanity: seeded data should give at least some numbers
    assert data["total_patients"] >= 2
    assert data["total_doctors"] >= 2
    assert data["total_appointments"] >= 2
    assert "scheduled" in data["appointments_by_status"]
