from events.event import Event
from admin_api.patient_data_import import PatientDataRow
import json

def write_vitals_event(row: PatientDataRow, event):
    data = json.loads(event.event_metadata)
    row.glycemia = data.get('glycemia')
    row.weight = data.get('weight')
    row.ideal_weight = data.get('idealWeight')
    if data.get('systolic') and data.get('diastolic'):
        row.blood_pressure = f"{data.get('systolic')}/{data.get('diastolic')}"
    row.pulse = data.get('pulse')
    row.respiration = data.get('respiration')
    row.o2_sats = data.get('sats')
    row.height = data.get('height')
    row.temperature = data.get('temp')
    row.blood_type = data.get('bloodType')

def write_evaluation_event(row: PatientDataRow, event):
    data = json.loads(event.event_metadata)
    row.doctor = data.get('doctor')
    row.reason = data.get('reason')
    row.observations = data.get('observations')
    row.medications = data.get('medications')
    row.breast_exam = data.get('breastExam')
    row.diagnosis = data.get('diagnosis')
    row.treatment = data.get('treatment')
    row.community_visit = data.get('communityVisit')
    row.community_visit_date = data.get('communityVisitDate')
    row.promoter_visit = data.get('promoterVisit')
    row.promoter_visit_date = data.get('promoterVisitDate')
    row.refusal = data.get('refusal')
    row.refusal_date = data.get('refusalDate')
    row.next_visit_date = data.get('nextVisitDate')
    row.next_visit_reason = data.get('nextVisitReason')

def write_medical_hx_event(row: PatientDataRow, event):
    data = json.loads(event.event_metadata)
    row.malnutrition = data.get('malnutrition')
    row.prenatal = data.get('prenatal')
    row.sexual_hx = data.get('sexualHx')
    row.nutrition = data.get('nutrition')
    row.parasite_treatment = data.get('parasiteTreatment')
    row.family_hx = data.get('familyHx')
    row.surgery_sx = data.get('surgeryHx')
    row.vaccinations = data.get('vaccinations')
    
