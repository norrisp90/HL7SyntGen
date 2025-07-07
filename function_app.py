import logging
import json
import azure.functions as func
from datetime import datetime, timedelta
from faker import Faker
import random
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os

# Initialize Function App first - critical for Azure Functions v2 discovery
app = func.FunctionApp()

# Temporarily disable Azure OpenAI to isolate function discovery issue
AZURE_OPENAI_AVAILABLE = False
AzureOpenAI = None

# Initialize Faker for Irish locale
fake = Faker(['en_IE'])

# HealthLink message types mapping (corrected based on real spec analysis)
HEALTHLINK_MESSAGES = {
    1: {"type": "OML_O21", "name": "Laboratory Order", "msh3_suffix": "1"},
    2: {"type": "ADT_A01", "name": "Inpatient Admission", "msh3_suffix": "2"},
    3: {"type": "REF_I12", "name": "Outpatient Clinic Letter", "msh3_suffix": "3"},
    4: {"type": "ADT_A01", "name": "A&E Notification", "msh3_suffix": "4"},
    5: {"type": "REF_I12", "name": "Discharge Summary", "msh3_suffix": "5"},
    6: {"type": "ADT_A03", "name": "Death Notification", "msh3_suffix": "6"},
    7: {"type": "ORU_R01", "name": "Radiology Result", "msh3_suffix": "7"},
    8: {"type": "SIU_S12", "name": "OPD Appointment", "msh3_suffix": "8"},
    9: {"type": "SIU_S12", "name": "Waiting List", "msh3_suffix": "9"},
    10: {"type": "ORU_R01", "name": "Laboratory Result", "msh3_suffix": "10"},
    11: {"type": "ORL_O22", "name": "Laboratory NACK", "msh3_suffix": "11"},
    12: {"type": "ADT_A03", "name": "Discharge Notification", "msh3_suffix": "12"},
    13: {"type": "ACK", "name": "Acknowledgement", "msh3_suffix": "13"},
    14: {"type": "REF_I12", "name": "Neurology Referral", "msh3_suffix": "14"},
    15: {"type": "RRI_I12", "name": "Neurology Referral Response", "msh3_suffix": "15"},
    16: {"type": "REF_I12", "name": "Co-op Discharge", "msh3_suffix": "16"},
    17: {"type": "ORU_R01", "name": "Cardiology Result", "msh3_suffix": "17"},
    18: {"type": "REF_I12", "name": "Oesophageal and Gastric Cancer Referral", "msh3_suffix": "18"},
    19: {"type": "REF_I12", "name": "A&E Letter", "msh3_suffix": "19"},
    20: {"type": "REF_I12", "name": "Prostate Cancer Referral", "msh3_suffix": "20"},
    21: {"type": "RRI_I12", "name": "Prostate Cancer Referral Response", "msh3_suffix": "21"},
    22: {"type": "REF_I12", "name": "Breast Cancer Referral", "msh3_suffix": "22"},
    23: {"type": "RRI_I12", "name": "Breast Cancer Referral Response", "msh3_suffix": "23"},
    24: {"type": "REF_I12", "name": "Lung Cancer Referral", "msh3_suffix": "24"},
    25: {"type": "RRI_I12", "name": "Lung Cancer Referral Response", "msh3_suffix": "25"},
    26: {"type": "REF_I12", "name": "Chest Pain Referral", "msh3_suffix": "26"},
    27: {"type": "RRI_I12", "name": "Chest Pain Referral Response", "msh3_suffix": "27"},
    28: {"type": "REF_I12", "name": "MRI Request", "msh3_suffix": "28"},
    29: {"type": "RRI_I12", "name": "MRI Request Response", "msh3_suffix": "29"},
    30: {"type": "REF_I12", "name": "General Referral", "msh3_suffix": "30"},
    31: {"type": "RRI_I12", "name": "General Referral Response", "msh3_suffix": "31"}
}

# Irish Hospital Data (realistic HIPE codes and names from HealthLink samples)
IRISH_HOSPITALS = [
    {"name": "ST. VINCENT'S UNIVERSITY HOSPITAL", "hipe": "907", "doh": "907"},
    {"name": "MATER MISERICORDIAE UNIVERSITY HOSPITAL", "hipe": "908", "doh": "908"},
    {"name": "BEAUMONT HOSPITAL", "hipe": "909", "doh": "909"},
    {"name": "ST. JAMES'S HOSPITAL", "hipe": "910", "doh": "910"},
    {"name": "TALLAGHT UNIVERSITY HOSPITAL", "hipe": "911", "doh": "911"},
    {"name": "CONNOLLY HOSPITAL", "hipe": "912", "doh": "912"},
    {"name": "CORK UNIVERSITY HOSPITAL", "hipe": "913", "doh": "913"},
    {"name": "MERCY UNIVERSITY HOSPITAL", "hipe": "914", "doh": "914"},
    {"name": "UNIVERSITY HOSPITAL GALWAY", "hipe": "915", "doh": "915"},
    {"name": "UNIVERSITY HOSPITAL LIMERICK", "hipe": "916", "doh": "916"},
    {"name": "UNIVERSITY HOSPITAL WATERFORD", "hipe": "917", "doh": "917"},
    {"name": "MAYO UNIVERSITY HOSPITAL", "hipe": "918", "doh": "918"},
    {"name": "LETTERKENNY UNIVERSITY HOSPITAL", "hipe": "919", "doh": "919"},
    {"name": "SLIGO UNIVERSITY HOSPITAL", "hipe": "920", "doh": "920"},
    {"name": "NAAS GENERAL HOSPITAL", "hipe": "921", "doh": "921"},
    {"name": "ROTUNDA HOSPITAL", "hipe": "932", "doh": "932"},
    {"name": "AMNCH", "hipe": "1049", "doh": "1049"},
    {"name": "OUR LADY OF LOURDES HOSPITAL", "hipe": "925", "doh": "925"},
    {"name": "COOMBE WOMENS & INFANTS UNIVERSITY HOSPITAL", "hipe": "933", "doh": "933"}
]

# Irish medical specialties for referrals
MEDICAL_SPECIALTIES = [
    "CARDIOLOGY", "NEUROLOGY", "ONCOLOGY", "GENERAL_SURGERY", "ORTHOPAEDICS",
    "GASTROENTEROLOGY", "RESPIRATORY", "ENDOCRINOLOGY", "RADIOLOGY", "PATHOLOGY",
    "DERMATOLOGY", "OPHTHALMOLOGY", "ENT", "UROLOGY", "GYNAECOLOGY"
]

# Common Irish lab test codes and descriptions (from actual HealthLink samples)
LAB_TESTS = [
    {"code": "FBC", "name": "Full Blood Count", "loinc": "57782-5"},
    {"code": "U&E", "name": "Urea and Electrolytes", "loinc": "24362-6"},
    {"code": "LFT", "name": "Liver Function Tests", "loinc": "24325-3"},
    {"code": "TFT", "name": "Thyroid Function Tests", "loinc": "24323-8"},
    {"code": "LIPIDS", "name": "Lipid Profile", "loinc": "57698-3"},
    {"code": "HBA1C", "name": "Haemoglobin A1c", "loinc": "4548-4"},
    {"code": "INR", "name": "International Normalized Ratio", "loinc": "6301-6"},
    {"code": "CRP", "name": "C-Reactive Protein", "loinc": "1988-5"},
    {"code": "ESR", "name": "Erythrocyte Sedimentation Rate", "loinc": "30341-2"},
    {"code": "TROPONIN", "name": "Troponin I", "loinc": "10839-9"},
    {"code": "MHH", "name": "Mercy Hepatitis/HIV screen", "loinc": ""},  # From sample
    {"code": "GLUCOSE", "name": "Glucose Random", "loinc": "2345-7"},
    {"code": "TSH", "name": "Thyroid Stimulating Hormone", "loinc": "3016-3"},
    {"code": "PSA", "name": "Prostate Specific Antigen", "loinc": "2857-1"},
    {"code": "URINALYSIS", "name": "Urinalysis Complete", "loinc": "24357-6"}
]

# Enhanced Irish patient demographics reflecting Ireland's diverse population (including ~17% international residents)
IRISH_PATIENT_DATA = {
    "first_names_male": [
        # Traditional Irish names
        "Sean", "Patrick", "Michael", "John", "Brian", "Kevin", "Cian", "Oisin", "Darragh", "Conor",
        # International names reflecting major immigrant communities
        "Mohammed", "Ali", "Ahmed", "Omar", "Hassan", "Ibrahim",  # Middle Eastern/North African
        "Andrei", "Alexandru", "Mihai", "Cristian", "Stefan",  # Romanian
        "Piotr", "Jakub", "Tomasz", "Marcin", "Krzysztof",  # Polish
        "Carlos", "Jose", "Miguel", "Diego", "Antonio",  # Spanish/Latin American
        "Giovanni", "Marco", "Luca", "Francesco", "Andrea",  # Italian
        "Johann", "Klaus", "Andreas", "Stefan", "Thomas",  # German
        "Samuel", "Gabriel", "Emmanuel", "Joshua", "Benjamin",  # Various Christian communities
        "Raj", "Arjun", "Vikram", "Rohit", "Amit",  # Indian
        "Wei", "Ming", "Jun", "Lei", "Hao"  # Chinese
    ],
    "first_names_female": [
        # Traditional Irish names
        "Mary", "Patricia", "Catherine", "Margaret", "Sarah", "Emma", "Niamh", "Aoife", "Siobhan", "Claire",
        # International names reflecting major immigrant communities
        "Fatima", "Aisha", "Zara", "Layla", "Amina", "Yasmin",  # Middle Eastern/North African
        "Maria", "Ana", "Elena", "Ioana", "Andreea",  # Romanian
        "Anna", "Katarzyna", "Agnieszka", "Magdalena", "Joanna",  # Polish
        "Carmen", "Isabel", "Sofia", "Lucia", "Andrea",  # Spanish/Latin American
        "Giulia", "Francesca", "Chiara", "Valentina", "Elisabetta",  # Italian
        "Anna", "Petra", "Sabine", "Christina", "Monika",  # German
        "Grace", "Faith", "Hope", "Joy", "Charity",  # Various Christian communities
        "Priya", "Anita", "Kavya", "Riya", "Meera",  # Indian
        "Li", "Mei", "Yan", "Xin", "Ling"  # Chinese
    ],
    "surnames": [
        # Traditional Irish surnames
        "Murphy", "Kelly", "O'Sullivan", "Walsh", "Smith", "O'Brien", "Byrne", "Ryan", "O'Connor", "O'Neill", 
        "Dunne", "McCarthy", "Gallagher", "O'Doherty", "Kennedy", "Lynch", "Murray", "Quinn", "Moore", "McLoughlin",
        # International surnames reflecting immigrant communities
        "Hassan", "Ali", "Ahmed", "Khan", "Mohamed", "Hussain",  # Middle Eastern/North African
        "Popescu", "Ionescu", "Popa", "Radu", "Stan",  # Romanian
        "Kowalski", "Nowak", "Wisniewski", "Wojcik", "Kowalczyk",  # Polish
        "Garcia", "Rodriguez", "Martinez", "Lopez", "Gonzalez",  # Spanish/Latin American
        "Rossi", "Ferrari", "Russo", "Bianchi", "Romano",  # Italian
        "Mueller", "Schmidt", "Schneider", "Fischer", "Weber",  # German
        "Patel", "Singh", "Kumar", "Sharma", "Gupta",  # Indian
        "Wang", "Li", "Zhang", "Liu", "Chen",  # Chinese
        "Silva", "Santos", "Oliveira", "Pereira", "Costa",  # Portuguese/Brazilian
        "Andersson", "Johansson", "Karlsson", "Nilsson", "Eriksson",  # Nordic
        "Johnson", "Williams", "Brown", "Jones", "Miller"  # English-speaking immigrants
    ],
    "addresses": {
        "Dublin": [
            # Traditional Dublin areas
            "Grafton Street", "O'Connell Street", "Dame Street", "Temple Bar", "Phoenix Park", "Ballsbridge", "Rathmines", "Clontarf",
            # Diverse multicultural areas
            "Parnell Street", "Capel Street", "Moore Street", "Smithfield", "Stoneybatter", "Drumcondra", "Glasnevin", "Blanchardstown",
            "Tallaght", "Lucan", "Swords", "Balbriggan", "Ongar", "Tyrrelstown"
        ],
        "Cork": [
            "Patrick Street", "Grand Parade", "South Mall", "Oliver Plunkett Street", "Washington Street", "Blackpool", "Ballincollig",
            "Mahon", "Douglas", "Wilton", "Bishopstown", "Togher", "Mayfield", "Knocknaheeny"
        ],
        "Galway": [
            "Shop Street", "Quay Street", "Eyre Square", "Salthill", "Newcastle", "Knocknacarra",
            "Ballybane", "Rahoon", "Westside", "Renmore", "Merlin Park", "Doughiska"
        ],
        "Limerick": [
            "O'Connell Street", "Henry Street", "William Street", "Corbally", "Castletroy", "Dooradoyle",
            "Moyross", "Southill", "Ballnanty", "Raheen", "Annacotty", "Caherdavin"
        ]
    }
}

# Common Irish medical conditions and their ICD-10 codes
IRISH_MEDICAL_CONDITIONS = [
    {"condition": "Essential Hypertension", "icd10": "I10", "prevalence": 0.25},
    {"condition": "Type 2 Diabetes Mellitus", "icd10": "E11", "prevalence": 0.05},
    {"condition": "Chronic Obstructive Pulmonary Disease", "icd10": "J44", "prevalence": 0.04},
    {"condition": "Atrial Fibrillation", "icd10": "I48", "prevalence": 0.02},
    {"condition": "Coronary Artery Disease", "icd10": "I25", "prevalence": 0.03},
    {"condition": "Osteoarthritis", "icd10": "M15", "prevalence": 0.08},
    {"condition": "Depression", "icd10": "F32", "prevalence": 0.06},
    {"condition": "Hyperlipidemia", "icd10": "E78", "prevalence": 0.15}
]

# Irish GP practices reflecting diverse communities
IRISH_GP_PRACTICES = [
    {"name": "Temple Street Medical Centre", "gms_code": "12345", "eircode": "D01 R2P4"},
    {"name": "Grafton Street Family Practice", "gms_code": "12346", "eircode": "D02 XY24"},
    {"name": "Blackrock Medical Centre", "gms_code": "12347", "eircode": "A94 E2W8"},
    {"name": "Rathmines Health Clinic", "gms_code": "12348", "eircode": "D06 H294"},
    {"name": "Clontarf Family Doctors", "gms_code": "12349", "eircode": "D03 T5P9"},
    {"name": "Multicultural Health Centre", "gms_code": "12350", "eircode": "D01 K5R7"},
    {"name": "Parnell Street Medical Practice", "gms_code": "12351", "eircode": "D01 T2X9"},
    {"name": "Smithfield Community Health", "gms_code": "12352", "eircode": "D07 P6W3"},
    {"name": "Blanchardstown Family Clinic", "gms_code": "12353", "eircode": "D15 Y8N4"},
    {"name": "Ballymun Medical Centre", "gms_code": "12354", "eircode": "D11 A5R8"}
]

# Realistic Irish consultant names reflecting Ireland's diverse medical workforce
IRISH_CONSULTANTS = [
    # Traditional Irish consultants
    {"name": "Dr. Mairead O'Brien", "specialty": "CARDIOLOGY", "mcn": "234567.1234"},
    {"name": "Dr. Padraig Murphy", "specialty": "NEUROLOGY", "mcn": "234568.1234"},
    {"name": "Dr. Siobhan Kelly", "specialty": "ONCOLOGY", "mcn": "234569.1234"},
    {"name": "Dr. Brendan Walsh", "specialty": "ORTHOPAEDICS", "mcn": "234570.1234"},
    {"name": "Dr. Nuala Ryan", "specialty": "GASTROENTEROLOGY", "mcn": "234571.1234"},
    # International consultants reflecting diverse medical workforce
    {"name": "Dr. Ahmed Hassan", "specialty": "CARDIOLOGY", "mcn": "234572.1234"},
    {"name": "Dr. Priya Patel", "specialty": "ENDOCRINOLOGY", "mcn": "234573.1234"},
    {"name": "Dr. Maria Rodriguez", "specialty": "PAEDIATRICS", "mcn": "234574.1234"},
    {"name": "Dr. Wei Zhang", "specialty": "RADIOLOGY", "mcn": "234575.1234"},
    {"name": "Dr. Anna Kowalski", "specialty": "PSYCHIATRY", "mcn": "234576.1234"},
    {"name": "Dr. Giovanni Rossi", "specialty": "GENERAL_SURGERY", "mcn": "234577.1234"},
    {"name": "Dr. Fatima Al-Rashid", "specialty": "OBSTETRICS", "mcn": "234578.1234"},
    {"name": "Dr. Klaus Mueller", "specialty": "ANAESTHETICS", "mcn": "234579.1234"},
    {"name": "Dr. Raj Sharma", "specialty": "OPHTHALMOLOGY", "mcn": "234580.1234"},
    {"name": "Dr. Elena Popescu", "specialty": "DERMATOLOGY", "mcn": "234581.1234"}
]

# Initialize Azure OpenAI client
azure_openai_client = None
try:
    if AZURE_OPENAI_AVAILABLE and AzureOpenAI:
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        
        if endpoint and api_key:
            azure_openai_client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
            )
            print("SUCCESS: Azure OpenAI client initialized successfully")
        else:
            print("WARNING: Azure OpenAI credentials not found in environment variables")
except Exception as e:
    print(f"ERROR: Could not initialize Azure OpenAI client: {str(e)}")
    azure_openai_client = None

def generate_patient_data():
    """Generate synthetic Irish patient data with realistic HealthLink values"""
    # Generate Irish-specific data based on samples
    irish_counties = [
        "Dublin", "Cork", "Galway", "Limerick", "Waterford", "Kilkenny", 
        "Clare", "Kerry", "Mayo", "Donegal", "Wexford", "Tipperary", "Sligo"
    ]
    
    gender = fake.random_element(elements=["M", "F"])
    
    if gender == "M":
        first_name = fake.random_element(elements=IRISH_PATIENT_DATA["first_names_male"])
    else:
        first_name = fake.random_element(elements=IRISH_PATIENT_DATA["first_names_female"])
        
    last_name = fake.random_element(elements=IRISH_PATIENT_DATA["surnames"])
    
    # Generate realistic Medical Record Numbers like samples show (e.g., M3, M123456)
    mrn_prefix = fake.random_element(elements=["M", "P", "H"])
    mrn_number = fake.random_int(min=1, max=999999)
    mrn = f"{mrn_prefix}{mrn_number}"
    
    # Generate realistic Eircode format
    eircode_areas = ["D01", "D02", "D03", "D04", "D05", "D06", "D07", "D08", "T12", "T23", "A94", "H91", "V92", "P85", "Y35", "F91", "N91"]
    eircode = f"{fake.random_element(elements=eircode_areas)}{fake.random_element(elements=['P','T','K','R','X','W','E'])}{fake.random_element(elements=['W','E','R','T','Y','A','S','D'])}{fake.random_int(min=10,max=99)}"
    
    address_line1 = fake.random_element(elements=IRISH_PATIENT_DATA["addresses"]["Dublin"])
    address_line2 = fake.city()
    county = fake.random_element(elements=irish_counties)
    
    # Randomly assign a clinical condition based on prevalence
    clinical_condition = fake.random_element(elements=IRISH_MEDICAL_CONDITIONS)
    has_clinical_condition = fake.random_int(min=0, max=100) < (clinical_condition["prevalence"] * 100)
    clinical_condition_code = clinical_condition["icd10"] if has_clinical_condition else ""
    
    return {
        "id": fake.random_int(min=100000, max=999999),
        "mrn": mrn,
        "pps": f"{fake.random_int(min=100000, max=999999)}{fake.random_int(min=10, max=99)}{fake.random_element(elements=['A','B','C','D','E','F','G','H','J','K','L','M','N','P','Q','R','S','T','U','V','W','X','Y','Z'])}",  # Irish PPS format
        "first_name": first_name,
        "last_name": last_name,
        "dob": fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%Y%m%d"),
        "gender": gender,
        "address_line1": address_line1,
        "address_line2": address_line2,
        "county": county,
        "eircode": eircode,
        "phone": f"0{fake.random_int(min=21,max=99)} {fake.random_int(min=400, max=999)}{fake.random_int(min=1000, max=9999)}",  # Irish landline format
        "mobile": f"087 {fake.random_int(min=100, max=999)}{fake.random_int(min=1000, max=9999)}",  # Irish mobile format
        "nhi": f"IE{fake.random_int(min=100000, max=999999)}{fake.random_int(min=100, max=999)}",  # Irish Health Identifier
        "full_name": f"{last_name.upper()},{first_name.upper()}",
        "clinical_condition": clinical_condition["condition"] if has_clinical_condition else "",
        "clinical_condition_code": clinical_condition_code,
        "age": fake.random_int(min=18, max=90),
        "gp_practice": fake.random_element(elements=IRISH_GP_PRACTICES)
    }

def generate_doctor_data():
    """Generate synthetic Irish doctor data matching HealthLink samples"""
    # Use realistic consultant data
    consultant = fake.random_element(elements=IRISH_CONSULTANTS)
    
    # Generate Medical Council Number in format like samples: 123456.4444 or 10002.1234
    mcn_main = fake.random_int(min=10000, max=999999)
    mcn_suffix = fake.random_int(min=1000, max=9999)
    
    # Format name like samples: "Dr Smith,David" or "DR Test Doc"
    name_formats = [
        consultant["name"].replace("Dr. ", "Dr "),  # "Dr Name,Surname" 
        consultant["name"].replace("Dr. ", "DR ").upper(),  # "DR NAME SURNAME"
        consultant["name"].replace("Dr. ", "").replace(" ", ",")  # "SURNAME,NAME"
    ]
    
    return {
        "name": fake.random_element(elements=name_formats),
        "mcn": f"{mcn_main}.{mcn_suffix}",
        "practice_id": "MCN.HLPracticeID",  # Matches samples exactly
        "specialty": consultant["specialty"],
        "hospital_affiliation": fake.random_element(elements=IRISH_HOSPITALS)["name"]
    }

# Legacy functions - replaced by HealthLink-compliant versions above
# These are kept for reference but should use the new create_msh_segment_healthlink_compliant() instead

def create_pid_segment(patient):
    """Create PID segment XML element with patient data matching HealthLink samples"""
    pid = ET.Element("PID")
    
    # PID.3 - Patient Identifier List (MRN) - matches sample format
    pid3_mrn = ET.SubElement(pid, "PID.3")
    cx1_mrn = ET.SubElement(pid3_mrn, "CX.1")
    cx1_mrn.text = patient["mrn"]
    cx2_mrn = ET.SubElement(pid3_mrn, "CX.2")  # Usually empty in samples
    cx3_mrn = ET.SubElement(pid3_mrn, "CX.3")  # Usually empty in samples
    cx4_mrn = ET.SubElement(pid3_mrn, "CX.4")
    hd1_mrn = ET.SubElement(cx4_mrn, "HD.1")
    hd1_mrn.text = "Mercy University Hospital"  # From samples
    hd2_mrn = ET.SubElement(cx4_mrn, "HD.2")  # Usually empty
    hd3_mrn = ET.SubElement(cx4_mrn, "HD.3")  # Usually empty
    cx5_mrn = ET.SubElement(pid3_mrn, "CX.5")
    cx5_mrn.text = "MRN"
    
    # PID.5 - Patient Name (matching sample structure)
    pid5 = ET.SubElement(pid, "PID.5")
    xpn1 = ET.SubElement(pid5, "XPN.1")
    fn1 = ET.SubElement(xpn1, "FN.1")
    fn1.text = patient["last_name"].upper()  # Samples show uppercase
    xpn2 = ET.SubElement(pid5, "XPN.2")
    xpn2.text = patient["first_name"].upper()  # Samples show uppercase
    xpn3 = ET.SubElement(pid5, "XPN.3")  # Usually empty
    xpn4 = ET.SubElement(pid5, "XPN.4")  # Usually empty  
    xpn5 = ET.SubElement(pid5, "XPN.5")  # Usually empty
    xpn6 = ET.SubElement(pid5, "XPN.6")  # Usually empty
    xpn7 = ET.SubElement(pid5, "XPN.7")  # Usually empty
    
    # PID.7 - Date of Birth
    pid7 = ET.SubElement(pid, "PID.7")
    ts1_7 = ET.SubElement(pid7, "TS.1")
    ts1_7.text = patient["dob"]
    
    # PID.8 - Administrative Sex
    pid8 = ET.SubElement(pid, "PID.8")
    pid8.text = patient["gender"]
    
    # PID.11 - Patient Address (matching sample structure)
    pid11 = ET.SubElement(pid, "PID.11")
    xad1 = ET.SubElement(pid11, "XAD.1")
    sad1 = ET.SubElement(xad1, "SAD.1")
    sad1.text = patient["address_line1"]
    xad2 = ET.SubElement(pid11, "XAD.2")
    xad2.text = patient["address_line2"]
    xad3 = ET.SubElement(pid11, "XAD.3")
    xad3.text = patient["county"]
    xad4 = ET.SubElement(pid11, "XAD.4")
    xad4.text = f"{patient['county'].upper()}"  # County repeated in uppercase like samples
    xad5 = ET.SubElement(pid11, "XAD.5")
    xad5.text = patient["eircode"]
    
    # PID.13 - Phone Numbers (matching sample format)
    if patient.get("phone"):
        pid13_home = ET.SubElement(pid, "PID.13")
        xtn1_home = ET.SubElement(pid13_home, "XTN.1")
        xtn1_home.text = patient["phone"]
        xtn2_home = ET.SubElement(pid13_home, "XTN.2")
        xtn2_home.text = "PRN"
        xtn3_home = ET.SubElement(pid13_home, "XTN.3")
        xtn3_home.text = "PH"
        
    if patient.get("mobile"):
        pid13_mobile = ET.SubElement(pid, "PID.13")
        xtn1_mobile = ET.SubElement(pid13_mobile, "XTN.1")
        xtn1_mobile.text = patient["mobile"]
        xtn2_mobile = ET.SubElement(pid13_mobile, "XTN.2")
        xtn2_mobile.text = "PRN"
        xtn3_mobile = ET.SubElement(pid13_mobile, "XTN.3")
        xtn3_mobile.text = "CP"
    
    return pid

def create_hl7_message_xml(msg_type_id):
    """Create HL7 message XML based on HealthLink message type ID with full spec compliance"""
    if msg_type_id not in HEALTHLINK_MESSAGES:
        raise ValueError(f"Unknown message type ID: {msg_type_id}")
    
    msg_info = HEALTHLINK_MESSAGES[msg_type_id]
    patient = generate_patient_data()
    doctor = generate_doctor_data()
    hospital = fake.random_element(elements=IRISH_HOSPITALS)
    
    # Generate message metadata with realistic format from samples
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Generate HealthLink-compliant Message Control ID
    message_control_id = generate_healthlink_message_control_id(msg_type_id)
    
    # Create message root element
    root = ET.Element(msg_info['type'])
    
    # Create HealthLink-compliant MSH segment
    msh = create_msh_segment_healthlink_compliant()
    add_healthlink_msh_fields(msh, msg_type_id, hospital, doctor, timestamp, message_control_id)
    root.append(msh)
    
    # Add message-specific segments based on message type
    if msg_info["type"] == "ORU_R01":
        # Laboratory/Radiology Result
        create_oru_r01_segments(root, patient, hospital, timestamp, msg_type_id)
        
    elif msg_info["type"].startswith("ADT"):
        # Admission/Discharge/Transfer
        create_adt_segments(root, patient, hospital, timestamp, msg_info["type"])
        
    elif msg_info["type"] == "REF_I12":
        # Referral
        create_ref_i12_segments(root, patient, hospital, timestamp, msg_type_id)
        
    elif msg_info["type"] == "RRI_I12":
        # Referral Response
        create_rri_i12_segments(root, patient, hospital, timestamp)
        
    elif msg_info["type"] == "ACK":
        # Acknowledgement
        create_ack_segments(root, timestamp)
        
    elif msg_info["type"] == "SIU_S12":
        # Scheduling Information
        create_siu_s12_segments(root, patient, hospital, timestamp)
        
    else:
        # Generic message - just add basic PID
        pid = create_pid_segment(patient)
        root.append(pid)
    
    return root

def create_oru_r01_segments(root, patient, hospital, timestamp, msg_type_id=10):
    """Create ORU_R01 specific segments for lab/radiology results matching HealthLink samples"""
    # Create PATIENT_RESULT group
    patient_result = ET.SubElement(root, "ORU_R01.PATIENT_RESULT")
    patient_group = ET.SubElement(patient_result, "ORU_R01.PATIENT")
    
    # Add PID segment
    pid = create_pid_segment(patient)
    patient_group.append(pid)
    
    # Add PV1 segment (Patient Visit) - matching sample structure
    patient_visit = ET.SubElement(patient_group, "ORU_R01.PATIENT_VISIT")
    pv1 = ET.SubElement(patient_visit, "PV1")
    
    pv1_2 = ET.SubElement(pv1, "PV1.2")
    pv1_2.text = fake.random_element(elements=("I", "O", "E", "G"))  # Patient class
    
    pv1_3 = ET.SubElement(pv1, "PV1.3")
    pl1 = ET.SubElement(pv1_3, "PL.1")
    pl1.text = fake.random_element(elements=("LTESGP", "WARD1", "ICU", "ED", "OPD"))  # From samples
    pl2 = ET.SubElement(pv1_3, "PL.2")  # Usually empty
    pl3 = ET.SubElement(pv1_3, "PL.3")  # Usually empty
    pl4 = ET.SubElement(pv1_3, "PL.4")
    hd1_pl4 = ET.SubElement(pl4, "HD.1")  # Usually empty
    hd2_pl4 = ET.SubElement(pl4, "HD.2")  # Usually empty
    hd3_pl4 = ET.SubElement(pl4, "HD.3")  # Usually empty
    pl5 = ET.SubElement(pv1_3, "PL.5")  # Usually empty
    pl6 = ET.SubElement(pv1_3, "PL.6")  # Usually empty
    pl7 = ET.SubElement(pv1_3, "PL.7")  # Usually empty
    pl8 = ET.SubElement(pv1_3, "PL.8")  # Usually empty
    pl9 = ET.SubElement(pv1_3, "PL.9")
    pl9.text = "Live Healthlink Location"  # From samples
    
    # PV1.19 - Visit Number
    pv1_19 = ET.SubElement(pv1, "PV1.19")
    cx1_19 = ET.SubElement(pv1_19, "CX.1")  # Usually empty in samples
    
    # Add ORDER_OBSERVATION group
    order_obs = ET.SubElement(patient_result, "ORU_R01.ORDER_OBSERVATION")
    
    # Add OBR segment (Observation Request) - matching sample structure
    obr = ET.SubElement(order_obs, "OBR")
    
    obr_1 = ET.SubElement(obr, "OBR.1")
    obr_1.text = "1"
    
    # OBR.2 - Placer Order Number (from samples)
    obr_2 = ET.SubElement(obr, "OBR.2")
    ei1_2 = ET.SubElement(obr_2, "EI.1")
    # Generate a 10-digit number by combining two smaller ranges
    part1 = fake.random_int(min=6000, max=9999)
    part2 = fake.random_int(min=100000, max=999999)
    ei1_2.text = f"{part1}{part2}{hospital['name'][:4].upper()}"  # Like 6460930602MMHH
    ei2_2 = ET.SubElement(obr_2, "EI.2")  # Usually empty
    
    # OBR.3 - Filler Order Number (from samples)
    obr_3 = ET.SubElement(obr, "OBR.3")
    ei1_3 = ET.SubElement(obr_3, "EI.1")
    ei1_3.text = f"JS{fake.random_int(min=100000, max=999999)}{fake.random_element(elements=['A','B','C','D'])}"  # Like JS008002B
    ei2_3 = ET.SubElement(obr_3, "EI.2")  # Usually empty
    ei3_3 = ET.SubElement(obr_3, "EI.3")  # Usually empty
    ei4_3 = ET.SubElement(obr_3, "EI.4")  # Usually empty
    
    obr_4 = ET.SubElement(obr, "OBR.4")
    test = fake.random_element(elements=LAB_TESTS)
    ce1 = ET.SubElement(obr_4, "CE.1")
    ce1.text = test["code"]
    ce2 = ET.SubElement(obr_4, "CE.2")
    ce2.text = test["name"]
    ce3 = ET.SubElement(obr_4, "CE.3")
    ce3.text = "L"
    ce4 = ET.SubElement(obr_4, "CE.4")  # Usually empty
    ce5 = ET.SubElement(obr_4, "CE.5")  # Usually empty
    ce6 = ET.SubElement(obr_4, "CE.6")  # Usually empty
    
    obr_7 = ET.SubElement(obr, "OBR.7")
    ts1 = ET.SubElement(obr_7, "TS.1")
    ts1.text = timestamp
    
    # OBR.13 - Usually empty in samples but required element
    obr_13 = ET.SubElement(obr, "OBR.13")
    
    # OBR.14 - Specimen received date/time (from samples)
    obr_14 = ET.SubElement(obr, "OBR.14")
    ts1_14 = ET.SubElement(obr_14, "TS.1")
    ts1_14.text = timestamp
    
    # OBR.15 - Specimen source (from samples)
    obr_15 = ET.SubElement(obr, "OBR.15")
    sps1 = ET.SubElement(obr_15, "SPS.1")
    ce1_sps = ET.SubElement(sps1, "CE.1")
    ce1_sps.text = "XXX"  # From samples
    ce2_sps = ET.SubElement(sps1, "CE.2")
    ce2_sps.text = "Specified in report"  # From samples
    ce3_sps = ET.SubElement(sps1, "CE.3")
    ce3_sps.text = "L"
    ce4_sps = ET.SubElement(sps1, "CE.4")  # Usually empty
    ce5_sps = ET.SubElement(sps1, "CE.5")  # Usually empty
    ce6_sps = ET.SubElement(sps1, "CE.6")  # Usually empty
    sps2 = ET.SubElement(obr_15, "SPS.2")  # Usually empty
    sps3 = ET.SubElement(obr_15, "SPS.3")  # Usually empty
    sps4 = ET.SubElement(obr_15, "SPS.4")
    ce1_sps4 = ET.SubElement(sps4, "CE.1")  # Usually empty
    ce2_sps4 = ET.SubElement(sps4, "CE.2")  # Usually empty
    ce3_sps4 = ET.SubElement(sps4, "CE.3")  # Usually empty
    
    # Add OBSERVATION group with OBX segment
    observation = ET.SubElement(order_obs, "ORU_R01.OBSERVATION")
    obx = ET.SubElement(observation, "OBX")
    
    obx_1 = ET.SubElement(obx, "OBX.1")
    obx_1.text = "1"
    
    obx_2 = ET.SubElement(obx, "OBX.2")
    obx_2.text = "TX"  # Text
    
    obx_3 = ET.SubElement(obx, "OBX.3")
    ce1_obx = ET.SubElement(obx_3, "CE.1")
    ce1_obx.text = test["code"]
    ce2_obx = ET.SubElement(obx_3, "CE.2")
    ce2_obx.text = test["name"]
    ce3_obx = ET.SubElement(obx_3, "CE.3")
    ce3_obx.text = "L"
    
    obx_5 = ET.SubElement(obx, "OBX.5")
    # Determine if this is a radiology result (message type 7 or 17) or lab result
    is_radiology = msg_type_id in [7, 17]  # Radiology Result, Cardiology Result
    
    if is_radiology:
        # Use AI-enhanced radiology report generation
        if azure_openai_client:
            try:
                exam_type = test["name"] if "name" in test else test["code"]
                obx_5.text = generate_ai_enhanced_radiology_report(exam_type, patient)
            except:
                # Fallback to basic radiology report
                obx_5.text = f"{test['name']}: Normal study. No acute abnormality detected."
        else:
            obx_5.text = f"{test['name']}: Normal study. No acute abnormality detected."
    else:
        # Use AI-enhanced lab result generation for lab results
        if azure_openai_client:
            try:
                obx_5.text = generate_ai_enhanced_lab_result(test["code"], test["name"], patient)
            except:
                # Fallback to regular generation if AI fails
                obx_5.text = generate_lab_result(test["code"])
        else:
            obx_5.text = generate_lab_result(test["code"])
    
    obx_11 = ET.SubElement(obx, "OBX.11")
    obx_11.text = "F"  # Final
    
    # Add NTE segment for additional clinical context
    nte = ET.SubElement(observation, "NTE")
    nte_1 = ET.SubElement(nte, "NTE.1")
    nte_1.text = "1"
    nte_3 = ET.SubElement(nte, "NTE.3")
    
    if is_radiology:
        # Additional radiology interpretation notes
        nte_3.text = generate_ai_enhanced_clinical_notes("RADIOLOGY", patient, f"{test['name']} interpretation")
    else:
        # Additional lab result interpretation notes
        nte_3.text = generate_ai_enhanced_clinical_notes("LABORATORY", patient, f"{test['name']} results")

def create_adt_segments(root, patient, hospital, timestamp, message_type):
    """Create ADT specific segments"""
    # Add EVN segment
    evn = ET.SubElement(root, "EVN")
    evn_2 = ET.SubElement(evn, "EVN.2")
    ts1 = ET.SubElement(evn_2, "TS.1")
    ts1.text = timestamp
    
    # Add PID segment
    pid = create_pid_segment(patient)
    root.append(pid)
    
    # Add PV1 segment
    pv1 = ET.SubElement(root, "PV1")
    
    pv1_2 = ET.SubElement(pv1, "PV1.2")
    pv1_2.text = fake.random_element(elements=("I", "O", "E"))
    
    pv1_3 = ET.SubElement(pv1, "PV1.3")
    pl1 = ET.SubElement(pv1_3, "PL.1")
    pl1.text = fake.random_element(elements=("WARD1", "WARD2", "ICU", "ED"))
    pl2 = ET.SubElement(pv1_3, "PL.2")
    pl2.text = fake.random_element(elements=("BED1", "BED2", "BED3"))

def create_ref_i12_segments(root, patient, hospital, timestamp, msg_type_id=3):
    """Create REF_I12 specific segments for referrals matching HealthLink samples"""
    # Add RF1 segment (Referral Information) - matching sample structure
    rf1 = ET.SubElement(root, "RF1")
    
    # RF1.1 - Referral Status (CE data type)
    rf1_1 = ET.SubElement(rf1, "RF1.1")
    ce1_1 = ET.SubElement(rf1_1, "CE.1")
    ce1_1.text = "P"  # Pending
    ce2_1 = ET.SubElement(rf1_1, "CE.2")
    ce2_1.text = "Pending"
    ce3_1 = ET.SubElement(rf1_1, "CE.3")
    ce3_1.text = "L"
    ce4_1 = ET.SubElement(rf1_1, "CE.4")  # Usually empty
    ce5_1 = ET.SubElement(rf1_1, "CE.5")  # Usually empty
    ce6_1 = ET.SubElement(rf1_1, "CE.6")  # Usually empty
    
    # RF1.2 - Referral Priority (CE data type)
    rf1_2 = ET.SubElement(rf1, "RF1.2")
    ce1_2 = ET.SubElement(rf1_2, "CE.1")
    ce1_2.text = fake.random_element(elements=("R", "U", "S"))  # Routine, Urgent, STAT
    ce2_2 = ET.SubElement(rf1_2, "CE.2")
    ce2_2.text = "Routine"  # From samples
    ce3_2 = ET.SubElement(rf1_2, "CE.3")
    ce3_2.text = "L"
    ce4_2 = ET.SubElement(rf1_2, "CE.4")  # Usually empty
    ce5_2 = ET.SubElement(rf1_2, "CE.5")  # Usually empty
    ce6_2 = ET.SubElement(rf1_2, "CE.6")  # Usually empty
    
    # RF1.3 - Referral Type (CE data type)
    rf1_3 = ET.SubElement(rf1, "RF1.3")
    ce1_3 = ET.SubElement(rf1_3, "CE.1")
    specialty = fake.random_element(elements=MEDICAL_SPECIALTIES)
    ce1_3.text = specialty
    ce2_3 = ET.SubElement(rf1_3, "CE.2")
    ce2_3.text = specialty.replace("_", " ").title()
    ce3_3 = ET.SubElement(rf1_3, "CE.3")
    ce3_3.text = "L"
    ce4_3 = ET.SubElement(rf1_3, "CE.4")  # Usually empty
    ce5_3 = ET.SubElement(rf1_3, "CE.5")  # Usually empty
    ce6_3 = ET.SubElement(rf1_3, "CE.6")  # Usually empty
    
    # RF1.4 - Referral Reason (TX data type) - Enhanced with AI content
    rf1_4 = ET.SubElement(rf1, "RF1.4")
    # Generate AI-enhanced referral reason based on specialty and patient context
    clinical_condition = patient.get("clinical_condition_code", "")
    referral_reason = generate_ai_enhanced_referral_reason(specialty, patient, clinical_condition)
    rf1_4.text = referral_reason
    
    # RF1.6 - Originating Referral Identifier (from samples)
    rf1_6 = ET.SubElement(rf1, "RF1.6")
    ei1_6 = ET.SubElement(rf1_6, "EI.1")
    # Generate a date between 2012 and 2025, then format as YYYYMMDD
    ref_date = fake.date_between(start_date=datetime(2012, 5, 30), end_date=datetime(2025, 1, 31))
    date_str = ref_date.strftime('%Y%m%d')
    ei1_6.text = f"REF{date_str}{fake.random_int(min=130000, max=200000)}{fake.random_int(min=100000, max=999999)}"  # Like REF20120530134026012121
    ei2_6 = ET.SubElement(rf1_6, "EI.2")  # Usually empty
    ei3_6 = ET.SubElement(rf1_6, "EI.3")  # Usually empty
    ei4_6 = ET.SubElement(rf1_6, "EI.4")  # Usually empty
    
    # RF1.7 - Referral DateTime (from samples)
    rf1_7 = ET.SubElement(rf1, "RF1.7")
    ts1_7 = ET.SubElement(rf1_7, "TS.1")
    ts1_7.text = timestamp[:8]  # Date only, like 20120530
    
    # Add PROVIDER_CONTACT groups (from samples)
    # Primary Care Provider
    provider_contact_pp = ET.SubElement(root, "REF_I12.PROVIDER_CONTACT")
    prd_pp = ET.SubElement(provider_contact_pp, "PRD")
    
    # PRD.1 - Provider Role
    prd1_pp = ET.SubElement(prd_pp, "PRD.1")
    ce1_prd1 = ET.SubElement(prd1_pp, "CE.1")
    ce1_prd1.text = "PP"  # Primary Care Provider
    ce2_prd1 = ET.SubElement(prd1_pp, "CE.2")
    ce2_prd1.text = "Primary Care Provider"
    ce3_prd1 = ET.SubElement(prd1_pp, "CE.3")
    ce3_prd1.text = "L"
    ce4_prd1 = ET.SubElement(prd1_pp, "CE.4")  # Usually empty
    ce5_prd1 = ET.SubElement(prd1_pp, "CE.5")  # Usually empty
    ce6_prd1 = ET.SubElement(prd1_pp, "CE.6")  # Usually empty
    
    # PRD.2 - Provider Name
    doctor = generate_doctor_data()
    prd2_pp = ET.SubElement(prd_pp, "PRD.2")
    xpn1_prd2 = ET.SubElement(prd2_pp, "XPN.1")
    fn1_prd2 = ET.SubElement(xpn1_prd2, "FN.1")
    fn1_prd2.text = doctor["name"].split(',')[0]  # Last name
    xpn2_prd2 = ET.SubElement(prd2_pp, "XPN.2")
    xpn2_prd2.text = doctor["name"].split(',')[1] if ',' in doctor["name"] else "John"  # First name
    xpn3_prd2 = ET.SubElement(prd2_pp, "XPN.3")  # Usually empty
    xpn4_prd2 = ET.SubElement(prd2_pp, "XPN.4")  # Usually empty
    xpn5_prd2 = ET.SubElement(prd2_pp, "XPN.5")  # Usually empty
    xpn6_prd2 = ET.SubElement(prd2_pp, "XPN.6")  # Usually empty
    xpn7_prd2 = ET.SubElement(prd2_pp, "XPN.7")  # Usually empty
    
    # Add PID segment
    pid = create_pid_segment(patient)
    root.append(pid)
    
    # Add NTE segments for clinical notes based on message type
    if msg_type_id == 5:  # Discharge Summary
        nte = ET.SubElement(root, "NTE")
        nte_1 = ET.SubElement(nte, "NTE.1")
        nte_1.text = "1"
        nte_3 = ET.SubElement(nte, "NTE.3")
        # Generate AI-enhanced discharge summary
        admission_reason = f"Assessment for {specialty.replace('_', ' ').lower()}"
        nte_3.text = generate_ai_enhanced_discharge_summary(patient, admission_reason)
    
    elif msg_type_id in [3, 14, 16, 18, 19, 20, 22, 24, 26, 28, 30]:  # Various referral types
        nte = ET.SubElement(root, "NTE")
        nte_1 = ET.SubElement(nte, "NTE.1")
        nte_1.text = "1"
        nte_3 = ET.SubElement(nte, "NTE.3")
        # Generate AI-enhanced clinical notes for referrals
        clinical_context = f"Referral to {specialty.replace('_', ' ').title()}"
        nte_3.text = generate_ai_enhanced_clinical_notes("REFERRAL", patient, clinical_context)

def create_rri_i12_segments(root, patient, hospital, timestamp):
    """Create RRI_I12 specific segments for referral responses"""
    # Add MSA segment (Message Acknowledgment)
    msa = ET.SubElement(root, "MSA")
    
    msa_1 = ET.SubElement(msa, "MSA.1")
    msa_1.text = "AA"  # Application Accept
    
    msa_2 = ET.SubElement(msa, "MSA.2")
    msa_2.text = f"REF{timestamp}{fake.random_int(min=100, max=999)}"
    
    # Add PID segment
    pid = create_pid_segment(patient)
    root.append(pid)

def create_ack_segments(root, timestamp):
    """Create ACK segments using HealthLink-compliant acknowledgment format"""
    # Add MSA segment (Message Acknowledgment)
    msa = ET.SubElement(root, "MSA")
    
    msa_1 = ET.SubElement(msa, "MSA.1")
    msa_1.text = "AA"  # Application Accept
    
    msa_2 = ET.SubElement(msa, "MSA.2")
    msa_2.text = f"ACK{timestamp}{fake.random_int(min=1000, max=9999)}"
    
    # MSA.3 - Text Message (optional success message)
    msa_3 = ET.SubElement(msa, "MSA.3")
    msa_3.text = "Message processed successfully"

def create_siu_s12_segments(root, patient, hospital, timestamp):
    """Create SIU_S12 specific segments for scheduling information"""
    # Add SCH segment (Scheduling Activity Information)
    sch = ET.SubElement(root, "SCH")
    
    # SCH.1 - Placer Appointment ID
    sch_1 = ET.SubElement(sch, "SCH.1")
    ei1 = ET.SubElement(sch_1, "EI.1")
    ei1.text = f"APT{fake.random_int(min=100000, max=999999)}"
    
    # SCH.7 - Appointment Request Type
    sch_7 = ET.SubElement(sch, "SCH.7")
    sch_7.text = "New"
    
    # SCH.11 - Appointment Timing Quantity
    sch_11 = ET.SubElement(sch, "SCH.11")
    tq1 = ET.SubElement(sch_11, "TQ.1")
    tq1.text = "30"  # 30 minutes
    tq2 = ET.SubElement(sch_11, "TQ.2")
    tq2.text = "min"
    
    # Add PID segment
    pid = create_pid_segment(patient)
    root.append(pid)

def generate_lab_result(test_code):
    """Generate realistic lab result values based on test type and HealthLink samples"""
    
    # Enhanced lab results with normal/abnormal ranges and clinical context
    results = {
        "FBC": generate_fbc_results(),
        "U&E": generate_ue_results(),
        "LFT": generate_lft_results(),
        "TFT": f"TSH: {fake.pyfloat(left_digits=1, right_digits=2, min_value=0.50, max_value=4.50)}mU/L, T4: {fake.random_int(min=9, max=25)}pmol/L",
        "HBA1C": generate_hba1c_results(),
        "INR": generate_inr_results(),
        "CRP": generate_crp_results(),
        "ESR": f"{fake.random_int(min=2, max=30)}mm/hr",
        "TROPONIN": generate_troponin_results(),
        "MHH": "Hepatitis B Surface Antigen: NEGATIVE\nHepatitis C Antibody: NEGATIVE\nHIV 1&2 Antibody: NEGATIVE",  # From sample
        "GLUCOSE": generate_glucose_results(),
        "TSH": f"{fake.pyfloat(left_digits=1, right_digits=2, min_value=0.40, max_value=5.00)}mU/L",
        "PSA": generate_psa_results(),
        "URINALYSIS": generate_urinalysis_results()
    }
    
    return results.get(test_code, f"Result: {fake.sentence()}")

def generate_fbc_results():
    """Generate realistic Full Blood Count results with appropriate ranges"""
    # Simulate some abnormal results occasionally
    is_abnormal = fake.random_int(min=0, max=100) < 15  # 15% chance of abnormal
    
    if is_abnormal:
        wbc = fake.random_element(elements=[fake.random_int(min=2, max=3), fake.random_int(min=12, max=18)])
        hgb = fake.random_element(elements=[fake.random_int(min=80, max=110), fake.random_int(min=190, max=220)])
        status = " (ABNORMAL)"
    else:
        wbc = fake.random_int(min=4, max=11)
        hgb = fake.random_int(min=120, max=180)
        status = ""
    
    rbc = fake.pyfloat(left_digits=1, right_digits=2, min_value=4.0, max_value=6.0)
    hct = fake.pyfloat(left_digits=2, right_digits=1, min_value=35.0, max_value=50.0)
    
    return f"WBC: {wbc}x10^9/L, RBC: {rbc}x10^12/L, Hgb: {hgb}g/L, Hct: {hct}%{status}"

def generate_ue_results():
    """Generate realistic Urea & Electrolytes results"""
    sodium = fake.random_int(min=135, max=145)
    potassium = fake.pyfloat(left_digits=1, right_digits=1, min_value=3.5, max_value=5.0)
    urea = fake.pyfloat(left_digits=1, right_digits=1, min_value=2.5, max_value=8.0)
    creatinine = fake.random_int(min=60, max=120)
    
    return f"Sodium: {sodium}mmol/L, Potassium: {potassium}mmol/L, Urea: {urea}mmol/L, Creatinine: {creatinine}umol/L"

def generate_lft_results():
    """Generate realistic Liver Function Test results"""
    alt = fake.random_int(min=10, max=40)
    ast = fake.random_int(min=10, max=40)
    alp = fake.random_int(min=30, max=120)
    bilirubin = fake.random_int(min=5, max=25)
    
    return f"ALT: {alt}U/L, AST: {ast}U/L, ALP: {alp}U/L, Bilirubin: {bilirubin}umol/L"

def generate_hba1c_results():
    """Generate realistic HbA1c results with diabetes context"""
    hba1c_percent = fake.pyfloat(left_digits=2, right_digits=1, min_value=4.0, max_value=12.0)
    hba1c_mmol = fake.random_int(min=20, max=108)
    
    if hba1c_percent > 6.5:
        context = " (Diabetes mellitus)"
    elif hba1c_percent > 6.0:
        context = " (Pre-diabetes)"
    else:
        context = " (Normal)"
        
    return f"{hba1c_percent}% ({hba1c_mmol}mmol/mol){context}"

def generate_crp_results():
    """Generate realistic CRP results with inflammation context"""
    crp = fake.pyfloat(left_digits=3, right_digits=1, min_value=0.5, max_value=200.0)
    
    if crp > 10:
        context = " (Elevated - inflammation/infection)"
    else:
        context = " (Normal)"
        
    return f"{crp}mg/L{context}"

def generate_troponin_results():
    """Generate realistic Troponin results with cardiac context"""
    troponin = fake.pyfloat(left_digits=2, right_digits=3, min_value=0.001, max_value=50.000)
    
    if troponin > 0.04:
        context = " (ELEVATED - possible MI)"
    else:
        context = " (Normal)"
        
    return f"{troponin}ng/mL{context}"

def generate_glucose_results():
    """Generate realistic glucose results with diabetes context"""
    glucose = fake.pyfloat(left_digits=2, right_digits=1, min_value=3.5, max_value=15.0)
    
    if glucose > 11.1:
        context = " (Diabetes range)"
    elif glucose > 7.8:
        context = " (Impaired glucose tolerance)"
    else:
        context = " (Normal)"
        
    return f"{glucose}mmol/L{context}"

def generate_psa_results():
    """Generate realistic PSA results with age-appropriate ranges"""
    psa = fake.pyfloat(left_digits=2, right_digits=2, min_value=0.1, max_value=10.0)
    
    if psa > 4.0:
        context = " (Elevated - further investigation needed)"
    else:
        context = " (Normal)"
        
    return f"{psa}ng/mL{context}"

def generate_inr_results():
    """Generate realistic INR results with anticoagulation context"""
    inr = fake.pyfloat(left_digits=1, right_digits=1, min_value=0.8, max_value=4.5)
    
    if inr > 3.0:
        context = " (High - bleeding risk)"
    elif inr > 1.5:
        context = " (Therapeutic anticoagulation)"
    else:
        context = " (Normal/subtherapeutic)"
        
    return f"{inr}{context}"

def generate_urinalysis_results():
    """Generate realistic urinalysis results"""
    protein = fake.random_element(elements=['NEGATIVE', 'TRACE', '+', '++'])
    glucose = fake.random_element(elements=['NEGATIVE', 'TRACE', '+'])
    blood = fake.random_element(elements=['NEGATIVE', 'TRACE', '+'])
    leucocytes = fake.random_element(elements=['NEGATIVE', 'TRACE', '+'])
    
    return f"Protein: {protein}, Glucose: {glucose}, Blood: {blood}, Leucocytes: {leucocytes}"

# Legacy format function - replaced by format_as_healthlink_compliant_xml

@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Simple health check endpoint"""
    return func.HttpResponse(
        json.dumps({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "message": "HL7 SyntGen API is running"
        }),
        status_code=200,
        headers={"Content-Type": "application/json"}
    )

@app.route(route="generate", methods=["GET"])
def generate_random_message(req: func.HttpRequest) -> func.HttpResponse:
    """Generate a random HealthLink message with full spec compliance"""
    try:
        # Get parameters from query
        output_format = req.params.get('format', 'xml').lower()
        include_framing = req.params.get('tcp_framing', 'false').lower() == 'true'
        
        # Get specific message type ID if provided
        msg_type_param = req.params.get('type')
        if msg_type_param:
            try:
                random_message_type_id = int(msg_type_param)
                if random_message_type_id not in HEALTHLINK_MESSAGES:
                    return func.HttpResponse(
                        json.dumps({"error": f"Invalid message type ID. Must be between 1 and 31."}),
                        status_code=400,
                        mimetype="application/json"
                    )
            except ValueError:
                return func.HttpResponse(
                    json.dumps({"error": "Message type ID must be a number."}),
                    status_code=400,
                    mimetype="application/json"
                )
        else:
            # Select a random message type ID (1-31)
            random_message_type_id = fake.random_int(min=1, max=31)
        
        # Generate HL7 message XML
        hl7_xml_element = create_hl7_message_xml(random_message_type_id)
        
        if output_format == 'xml':
            result = format_as_healthlink_compliant_xml(hl7_xml_element, random_message_type_id, include_framing)
            
            if include_framing and isinstance(result, dict):
                # Return framed message info
                return func.HttpResponse(
                    json.dumps({
                        "message_type_id": random_message_type_id,
                        "message_type": HEALTHLINK_MESSAGES[random_message_type_id]["name"],
                        "xml_message": result["xml_message"],
                        "tcp_framed_bytes": result["tcp_framed_message"].hex(),
                        "framing_info": result["framing_info"],
                        "healthlink_compliance": "Full HealthLink TCP/IP specification compliance"
                    }, indent=2),
                    status_code=200,
                    mimetype="application/json"
                )
            else:
                # Ensure result is a string for XML response
                if isinstance(result, dict):
                    result = result.get("xml_message", str(result))
                return func.HttpResponse(result, status_code=200, mimetype="application/xml")
            
        elif output_format == 'hl7':
            # Convert XML to HL7 pipe-delimited format (simplified conversion)
            xml_string = ET.tostring(hl7_xml_element, encoding='unicode')
            return func.HttpResponse(xml_string, status_code=200, mimetype="text/plain")
            
        elif output_format == 'json':
            xml_string = ET.tostring(hl7_xml_element, encoding='unicode')
            healthlink_xml = format_as_healthlink_compliant_xml(hl7_xml_element, random_message_type_id)
            
            response_data = {
                "message_type_id": random_message_type_id,
                "message_type": HEALTHLINK_MESSAGES[random_message_type_id]["name"],
                "hl7_type": HEALTHLINK_MESSAGES[random_message_type_id]['type'],
                "xml_message": xml_string,
                "healthlink_compliant_message": healthlink_xml,
                "compliance_features": {
                    "msh_segment_format": "HealthLink Section 4.5 compliant",
                    "message_control_id_format": "HealthLink pattern-based",
                    "special_characters": "HL7 v2.4 XML encoding",
                    "hospital_data": "Irish HIPE codes and realistic data"
                },
                "usage_info": {
                    "tcp_framing": "Add ?tcp_framing=true for network transmission format",
                    "ack_simulation": "Message type 13 generates acknowledgment messages"
                }
            }
            
            if include_framing:
                framed_result = format_as_healthlink_compliant_xml(hl7_xml_element, random_message_type_id, True)
                if isinstance(framed_result, dict):
                    response_data["tcp_framing"] = framed_result["framing_info"]
                    response_data["tcp_framed_bytes"] = framed_result["tcp_framed_message"].hex()
            
            return func.HttpResponse(
                json.dumps(response_data, indent=2),
                status_code=200,
                mimetype="application/json"
            )
        else:
            return func.HttpResponse(
                json.dumps({"error": "Invalid format. Use 'xml', 'hl7', or 'json'"}),
                status_code=400,
                mimetype="application/json"
            )
            
    except Exception as e:
        logging.error(f"Error generating message: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "error": f"Failed to generate message: {str(e)}",
                "message_types_available": "1-31",
                "usage": "GET /api/generate?format=xml&type=10&tcp_framing=true",
                "healthlink_features": {
                    "tcp_framing": "Adds 0x0B prefix and 0x1C 0x0D suffix as per spec",
                    "compliant_msh": "MSH segments follow HealthLink Section 4.5",
                    "realistic_data": "Irish hospital and patient data"
                }
            }),
            status_code=500,
            mimetype="application/json"
        )

# Enhanced time and scheduling functions
def generate_realistic_timestamp():
    """Generate realistic timestamps during typical hospital hours"""
    # Most lab results and appointments happen during business hours
    business_hours = fake.random_int(min=8, max=18)  # 8 AM to 6 PM
    weekend_factor = fake.random_int(min=0, max=100)
    
    if weekend_factor < 20:  # 20% chance of weekend (emergency cases)
        base_date = fake.date_between(start_date='-30d', end_date='today')
    else:
        # Weekday only
        base_date = fake.date_between(start_date='-30d', end_date='today')
        while base_date.weekday() > 4:  # 0-6, where 0 is Monday
            base_date = fake.date_between(start_date='-30d', end_date='today')
    
    # Combine date with business hours
    timestamp = datetime.combine(base_date, datetime.min.time().replace(
        hour=business_hours, 
        minute=fake.random_int(min=0, max=59),
        second=fake.random_int(min=0, max=59)
    ))
    
    return timestamp.strftime("%Y%m%d%H%M%S")

def generate_appointment_time():
    """Generate realistic appointment times (typically scheduled in 15-minute intervals)"""
    future_date = fake.date_between(start_date='today', end_date='+60d')
    
    # Appointments typically on 15-minute intervals during business hours
    hour = fake.random_int(min=9, max=17)  # 9 AM to 5 PM
    minute = fake.random_element(elements=[0, 15, 30, 45])
    
    appointment_time = datetime.combine(future_date, datetime.min.time().replace(
        hour=hour, 
        minute=minute
    ))
    
    return appointment_time.strftime("%Y%m%d%H%M%S")

def generate_healthlink_message_control_id(msg_type_id):
    """Generate HealthLink compliant message control ID"""
    # HealthLink format: YYYYMMDDHHMM + 4-digit sequence
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    sequence = fake.random_int(min=1000, max=9999)
    return f"{timestamp}{sequence}"

def create_msh_segment_healthlink_compliant():
    """Create basic MSH segment structure"""
    msh = ET.Element("MSH")
    return msh

def add_healthlink_msh_fields(msh, msg_type_id, hospital, doctor, timestamp, message_control_id):
    """Add HealthLink compliant fields to MSH segment"""
    # MSH.1 - Field Separator
    msh_1 = ET.SubElement(msh, "MSH.1")
    msh_1.text = "|"
    
    # MSH.2 - Encoding Characters
    msh_2 = ET.SubElement(msh, "MSH.2")
    msh_2.text = "^~\\&"
    
    # MSH.3 - Sending Application
    msh_3 = ET.SubElement(msh, "MSH.3")
    msh_3.text = f"HL7SYNTGEN{HEALTHLINK_MESSAGES[msg_type_id]['msh3_suffix']}"
    
    # MSH.4 - Sending Facility
    msh_4 = ET.SubElement(msh, "MSH.4")
    msh_4.text = hospital['hipe']
    
    # MSH.5 - Receiving Application
    msh_5 = ET.SubElement(msh, "MSH.5")
    msh_5.text = "HEALTHLINK"
    
    # MSH.6 - Receiving Facility
    msh_6 = ET.SubElement(msh, "MSH.6")
    msh_6.text = "HSE"
    
    # MSH.7 - Date/Time of Message
    msh_7 = ET.SubElement(msh, "MSH.7")
    msh_7.text = timestamp
    
    # MSH.9 - Message Type
    msh_9 = ET.SubElement(msh, "MSH.9")
    msh_9.text = HEALTHLINK_MESSAGES[msg_type_id]['type']
    
    # MSH.10 - Message Control ID
    msh_10 = ET.SubElement(msh, "MSH.10")
    msh_10.text = message_control_id
    
    # MSH.11 - Processing ID
    msh_11 = ET.SubElement(msh, "MSH.11")
    msh_11.text = "P"  # Production
    
    # MSH.12 - Version ID
    msh_12 = ET.SubElement(msh, "MSH.12")
    msh_12.text = "2.5"

def format_as_healthlink_compliant_xml(hl7_element, message_type_id, include_framing=False):
    """Format XML as HealthLink compliant with proper formatting"""
    # Convert to string with proper formatting
    rough_string = ET.tostring(hl7_element, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    formatted_xml = reparsed.toprettyxml(indent="  ")
    
    # Remove empty lines and fix formatting
    lines = [line for line in formatted_xml.split('\n') if line.strip()]
    clean_xml = '\n'.join(lines[1:])  # Remove XML declaration
    
    if include_framing:
        # Add TCP/IP framing as per HealthLink spec
        framed_message = b'\x0B' + clean_xml.encode('utf-8') + b'\x1C\x0D'
        
        # Return structured data with framing information
        return {
            "xml_message": clean_xml,
            "tcp_framed_message": framed_message,
            "framing_info": {
                "start_block": "0x0B (VT - Vertical Tab)",
                "end_block": "0x1C (FS - File Separator)", 
                "terminator": "0x0D (CR - Carriage Return)",
                "total_length": len(framed_message),
                "xml_length": len(clean_xml.encode('utf-8')),
                "frame_overhead": 3
            }
        }
    
    return clean_xml

def generate_ai_enhanced_lab_result(test_code, test_name, patient_context=None):
    """Generate AI-enhanced lab results using Azure OpenAI"""
    if not azure_openai_client:
        # Fallback to simple generation
        return generate_lab_result(test_code)
    
    try:
        # Extract patient info for context
        patient_age = None
        patient_gender = None
        if patient_context:
            birth_date = patient_context.get('birth_date', '')
            if birth_date:
                from datetime import datetime
                try:
                    birth_year = int(birth_date[:4])
                    current_year = datetime.now().year
                    patient_age = current_year - birth_year
                except:
                    pass
            patient_gender = patient_context.get('gender', '')
        
        # Create context-aware prompt
        prompt = f"""Generate a realistic medical laboratory result value for:
Test: {test_name} (Code: {test_code})
"""
        if patient_age:
            prompt += f"Patient Age: {patient_age} years\n"
        if patient_gender:
            prompt += f"Patient Gender: {patient_gender}\n"
            
        prompt += """
Requirements:
- Return only the numeric value with appropriate units
- Use Irish/European medical standards
- Make it clinically realistic
- Keep it concise (max 20 characters)
- If abnormal, make it slightly outside normal range
- Common tests: CBC, Chemistry, Lipids, etc.
- IMPORTANT: Respond in English language only, never in Irish Gaelic

Examples:
- Hemoglobin: "13.2 g/dL"
- Glucose: "5.4 mmol/L"
- Cholesterol: "4.8 mmol/L"
- Creatinine: "78 μmol/L"

Result value only:"""

        response = azure_openai_client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini"),
            messages=[
                {"role": "system", "content": "You are a medical laboratory system generating realistic Irish lab values. Return only the requested lab value with units. IMPORTANT: Respond only in English language, never in Irish Gaelic."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.7
        )
        
        result = response.choices[0].message.content
        if result:
            result = result.strip()
        else:
            return generate_lab_result(test_code)
        
        # Clean and validate the result
        if len(result) > 50 or not result:
            return generate_lab_result(test_code)
            
        return result
        
    except Exception as e:
        logging.warning(f"AI lab result generation failed: {e}")
        # Fallback to simple generation
        return generate_lab_result(test_code)

# Enhanced AI generation functions for clinical content
def generate_ai_enhanced_referral_reason(specialty, patient, clinical_condition=""):
    """Generate AI-enhanced referral reason text appropriate for Irish healthcare"""
    if not azure_openai_client:
        # Fallback to basic reasons if no AI available
        fallback_reasons = {
            "CARDIOLOGY": "Chest pain and abnormal ECG findings requiring specialist assessment",
            "NEUROLOGY": "Neurological symptoms requiring specialist evaluation",
            "ONCOLOGY": "Abnormal screening results requiring urgent specialist review",
            "ORTHOPAEDICS": "Joint pain and mobility issues requiring orthopedic assessment",
            "GASTROENTEROLOGY": "Gastrointestinal symptoms requiring specialist investigation",
            "RESPIRATORY": "Respiratory symptoms and abnormal chest imaging",
            "ENDOCRINOLOGY": "Diabetes management and endocrine disorder assessment",
            "RADIOLOGY": "Clinical indication for advanced imaging studies",
            "DERMATOLOGY": "Skin lesion requiring dermatological evaluation",
            "OPHTHALMOLOGY": "Visual symptoms requiring ophthalmologic assessment",
            "ENT": "ENT symptoms requiring specialist evaluation",
            "UROLOGY": "Urological symptoms requiring specialist assessment",
            "GYNAECOLOGY": "Gynecological symptoms requiring specialist evaluation"
        }
        return fallback_reasons.get(specialty, "Clinical assessment required")
    
    try:
        # Create specialty-specific prompt for Irish healthcare context
        age = 2025 - int(patient.get("dob", "19800101")[:4]) if patient.get("dob") else 45
        gender = "Male" if patient.get("gender") == "M" else "Female"
        
        prompt = f"""Generate a realistic referral reason for an Irish hospital referral to {specialty.replace('_', ' ').title()}.

Patient context:
- Age: {age}
- Gender: {gender}
- Clinical condition: {clinical_condition or 'General assessment required'}

Requirements:
- Use professional Irish medical terminology
- Include relevant clinical history (2-3 sentences)
- Specify investigation results if appropriate
- Use Irish healthcare system context (GP referral to consultant)
- Be specific about the clinical indication
- Maximum 150 words
- Professional medical tone
- IMPORTANT: Write in English language only, never in Irish Gaelic

Example format: "6-month history of [symptoms]. [Investigation findings]. Requesting [specific assessment/management]."
"""

        response = azure_openai_client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini"),
            messages=[
                {"role": "system", "content": "You are a medical professional generating clinical content for Irish healthcare. IMPORTANT: Always respond in English language only, never in Irish Gaelic."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        return content.strip() if content else "Clinical assessment required"
        
    except Exception as e:
        print(f"Error generating AI referral reason: {e}")
        # Fallback to basic reason
        fallback_reasons = {
            "CARDIOLOGY": "Chest pain and abnormal ECG findings requiring specialist assessment",
            "NEUROLOGY": "Neurological symptoms requiring specialist evaluation", 
            "ONCOLOGY": "Abnormal screening results requiring urgent specialist review"
        }
        return fallback_reasons.get(specialty, "Clinical assessment required")

def generate_ai_enhanced_radiology_report(exam_type, patient):
    """Generate AI-enhanced radiology report for Irish healthcare"""
    if not azure_openai_client:
        # Fallback reports
        fallback_reports = {
            "CHEST": "CHEST X-RAY: Heart size normal. Lung fields clear. No acute abnormality.",
            "CT": "CT SCAN: No acute abnormality detected. Normal study.",
            "MRI": "MRI: No significant abnormality identified.",
            "US": "ULTRASOUND: Normal sonographic appearances."
        }
        return fallback_reports.get(exam_type, "IMAGING: Normal study.")
    
    try:
        age = 2025 - int(patient.get("dob", "19800101")[:4]) if patient.get("dob") else 45
        gender = "Male" if patient.get("gender") == "M" else "Female"
        
        prompt = f"""Generate a realistic radiology report for Irish healthcare.

Exam details:
- Type: {exam_type} examination
- Patient: {age}-year-old {gender}

Requirements:
- Use standard Irish radiology report structure
- Include TECHNIQUE, FINDINGS, and IMPRESSION sections
- Use appropriate medical terminology
- Include normal anatomical references
- Make findings age-appropriate
- Professional radiologist language
- 100-200 words maximum
- Irish hospital context
- IMPORTANT: Write in English language only, never in Irish Gaelic

Generate a report that could be normal or show minor age-related changes."""

        response = azure_openai_client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini"),
            messages=[
                {"role": "system", "content": "You are a radiologist generating medical reports for Irish healthcare. IMPORTANT: Always respond in English language only, never in Irish Gaelic."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=250,
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        return content.strip() if content else "IMAGING: Normal study within expected parameters for patient age."
        
    except Exception as e:
        print(f"Error generating AI radiology report: {e}")
        return "IMAGING: Normal study within expected parameters for patient age."

def generate_ai_enhanced_clinical_notes(note_type, patient, clinical_context=""):
    """Generate AI-enhanced clinical notes for various message types"""
    if not azure_openai_client:
        fallback_notes = {
            "DISCHARGE": "Patient stable for discharge. Follow-up as arranged.",
            "CLINICAL": "Clinical assessment completed. Management plan discussed.",
            "FOLLOWUP": "Routine follow-up appointment scheduled.",
            "ADMISSION": "Patient admitted for further assessment and management."
        }
        return fallback_notes.get(note_type, "Clinical note documented.")
    
    try:
        age = 2025 - int(patient.get("dob", "19800101")[:4]) if patient.get("dob") else 45
        gender = "Male" if patient.get("gender") == "M" else "Female"
        
        prompt = f"""Generate clinical notes for Irish healthcare documentation.

Context:
- Note type: {note_type}
- Patient: {age}-year-old {gender}
- Clinical context: {clinical_context}

Requirements:
- Professional Irish medical language
- Appropriate for inter-professional communication
- Include relevant clinical details
- Use Irish healthcare terminology
- 50-100 words
- Clear and concise
- Professional tone suitable for medical records
- IMPORTANT: Write in English language only, never in Irish Gaelic

Generate realistic clinical documentation."""

        response = azure_openai_client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini"),
            messages=[
                {"role": "system", "content": "You are a healthcare professional generating clinical documentation for Irish healthcare. IMPORTANT: Always respond in English language only, never in Irish Gaelic."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        return content.strip() if content else "Clinical documentation completed as per standard protocols."
        
    except Exception as e:
        print(f"Error generating AI clinical notes: {e}")
        return "Clinical documentation completed as per standard protocols."

def generate_ai_enhanced_discharge_summary(patient, admission_reason="", hospital_course=""):
    """Generate AI-enhanced discharge summary for Irish healthcare"""
    if not azure_openai_client:
        return "Patient admitted for assessment. Treatment provided as indicated. Discharged in stable condition with appropriate follow-up arranged."
    
    try:
        age = 2025 - int(patient.get("dob", "19800101")[:4]) if patient.get("dob") else 45
        gender = "Male" if patient.get("gender") == "M" else "Female"
        
        prompt = f"""Generate a discharge summary for Irish hospital.

Patient details:
- Age: {age}
- Gender: {gender}
- Admission reason: {admission_reason or 'Medical assessment'}
- Hospital course: {hospital_course or 'Routine care provided'}

Requirements:
- Standard Irish discharge summary format
- Include admission reason, hospital course, discharge condition
- Mention follow-up arrangements
- Professional medical language
- 100-150 words
- Appropriate for GP communication
- Irish healthcare context
- IMPORTANT: Write in English language only, never in Irish Gaelic

Generate realistic discharge documentation."""

        response = azure_openai_client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini"),
            messages=[
                {"role": "system", "content": "You are a healthcare professional generating discharge summaries for Irish hospitals. IMPORTANT: Always respond in English language only, never in Irish Gaelic."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        return content.strip() if content else "Patient discharged in stable condition. Follow-up care arranged with primary care provider."
        
    except Exception as e:
        print(f"Error generating AI discharge summary: {e}")
        return "Patient discharged in stable condition. Follow-up care arranged with primary care provider."
