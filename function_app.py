import logging
import json
import azure.functions as func
from datetime import datetime, timedelta
import random
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os
import sys

# Configure logging for better debugging in Azure
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log startup information for debugging in Azure
logger.info("=== Azure Functions App Starting ===")
logger.info(f"Python version: {sys.version}")
logger.info(f"Working directory: {os.getcwd()}")
logger.info(f"Python path: {sys.path[:3]}")

# Try to import faker with detailed error reporting
try:
    from faker import Faker
    fake = Faker(['en_IE'])
    logger.info("✓ Faker module imported successfully")
    # Get Faker version safely - use faker instance, not class
    try:
        faker_version = getattr(fake, '__version__', 'unknown')
    except:
        faker_version = 'unknown'
    logger.info(f"Faker version: {faker_version}")
    FAKER_AVAILABLE = True
except ImportError as e:
    logger.error(f"✗ CRITICAL: Failed to import Faker: {e}")
    logger.error(f"Current working directory: {os.getcwd()}")
    logger.error(f"Contents of current directory: {os.listdir('.')}")
    logger.error("Check if requirements.txt was processed during deployment")
    # This will cause the function to fail, which is what we want for debugging
    raise ImportError(f"Faker module is required but not available: {e}")

# Import other modules
try:
    from openai import AzureOpenAI
    AZURE_OPENAI_AVAILABLE = True
    logger.info("✓ Azure OpenAI module loaded")
except ImportError as e:
    logger.warning(f"Azure OpenAI not available: {e}")
    AzureOpenAI = None
    AZURE_OPENAI_AVAILABLE = False

# Initialize Function App
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
logger.info("Function App initialized successfully")

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

def safe_faker_call(method_name, *args, **kwargs):
    """Safely call faker methods with fallback values when faker is not available"""
    if not FAKER_AVAILABLE or fake is None:
        # Provide fallback values when faker is not available
        fallbacks = {
            'random_element': lambda elements: random.choice(elements) if elements else "DefaultValue",
            'random_int': lambda min=1, max=100: random.randint(min, max),
            'city': lambda: "Dublin",
            'date_of_birth': lambda minimum_age=18, maximum_age=90: datetime.now() - timedelta(days=random.randint(minimum_age*365, maximum_age*365))
        }
        if method_name in fallbacks:
            return fallbacks[method_name](*args, **kwargs)
        else:
            logger.warning(f"Faker method '{method_name}' not available, returning default")
            return "DefaultValue"
    
    # Use faker if available
    method = getattr(fake, method_name, None)
    if method:
        return method(*args, **kwargs)
    else:
        logger.warning(f"Faker method '{method_name}' not found")
        return "DefaultValue"

def format_date_of_birth():
    """Generate and format date of birth safely"""
    if FAKER_AVAILABLE:
        # Use faker to generate date of birth
        dob_result = safe_faker_call('date_of_birth', minimum_age=18, maximum_age=90)
        
        # Check if we got a valid date object (not a string fallback)
        if not isinstance(dob_result, str) and hasattr(dob_result, 'strftime'):
            return dob_result.strftime("%Y%m%d")
    
    # Fallback to manual generation (when faker not available or returns string)
    days_ago = random.randint(18*365, 90*365)
    return (datetime.now() - timedelta(days=days_ago)).strftime("%Y%m%d")

def generate_patient_data():
    """Generate synthetic Irish patient data with realistic HealthLink values"""
    # Generate Irish-specific data based on samples
    irish_counties = [
        "Dublin", "Cork", "Galway", "Limerick", "Waterford", "Kilkenny", 
        "Clare", "Kerry", "Mayo", "Donegal", "Wexford", "Tipperary", "Sligo"
    ]
    
    gender = safe_faker_call('random_element', elements=["M", "F"])
    
    if gender == "M":
        first_name = safe_faker_call('random_element', elements=IRISH_PATIENT_DATA["first_names_male"])
    else:
        first_name = safe_faker_call('random_element', elements=IRISH_PATIENT_DATA["first_names_female"])
        
    last_name = safe_faker_call('random_element', elements=IRISH_PATIENT_DATA["surnames"])
    
    # Generate realistic Medical Record Numbers like samples show (e.g., M3, M123456)
    mrn_prefix = safe_faker_call('random_element', elements=["M", "P", "H"])
    mrn_number = safe_faker_call('random_int', min=1, max=999999)
    mrn = f"{mrn_prefix}{mrn_number}"
    
    # Generate realistic Eircode format
    eircode_areas = ["D01", "D02", "D03", "D04", "D05", "D06", "D07", "D08", "T12", "T23", "A94", "H91", "V92", "P85", "Y35", "F91", "N91"]
    eircode = f"{safe_faker_call('random_element', elements=eircode_areas)}{safe_faker_call('random_element', elements=['P','T','K','R','X','W','E'])}{safe_faker_call('random_element', elements=['W','E','R','T','Y','A','S','D'])}{safe_faker_call('random_int', min=10, max=99)}"
    
    address_line1 = safe_faker_call('random_element', elements=IRISH_PATIENT_DATA["addresses"]["Dublin"])
    address_line2 = safe_faker_call('city')
    county = safe_faker_call('random_element', elements=irish_counties)
    
    # Randomly assign a clinical condition based on prevalence
    clinical_condition = safe_faker_call('random_element', elements=IRISH_MEDICAL_CONDITIONS)
    
    # Safely handle clinical condition data
    if isinstance(clinical_condition, dict) and "prevalence" in clinical_condition:
        has_clinical_condition = safe_faker_call('random_int', min=0, max=100) < (clinical_condition["prevalence"] * 100)
        clinical_condition_code = clinical_condition.get("icd10", "") if has_clinical_condition else ""
        clinical_condition_name = clinical_condition.get("condition", "") if has_clinical_condition else ""
    else:
        # Fallback when faker returns "DefaultValue" or unexpected format
        has_clinical_condition = False
        clinical_condition_code = ""
        clinical_condition_name = ""
    
    return {
        "id": safe_faker_call('random_int', min=100000, max=999999),
        "mrn": mrn,
        "pps": f"{safe_faker_call('random_int', min=100000, max=999999)}{safe_faker_call('random_int', min=10, max=99)}{safe_faker_call('random_element', elements=['A','B','C','D','E','F','G','H','J','K','L','M','N','P','Q','R','S','T','U','V','W','X','Y','Z'])}",  # Irish PPS format
        "first_name": first_name,
        "last_name": last_name,
        "dob": format_date_of_birth(),
        "gender": gender,
        "address_line1": address_line1,
        "address_line2": address_line2,
        "county": county,
        "eircode": eircode,
        "phone": f"0{safe_faker_call('random_int', min=21, max=99)} {safe_faker_call('random_int', min=400, max=999)}{safe_faker_call('random_int', min=1000, max=9999)}",  # Irish landline format
        "mobile": f"087 {safe_faker_call('random_int', min=100, max=999)}{safe_faker_call('random_int', min=1000, max=9999)}",  # Irish mobile format
        "nhi": f"IE{safe_faker_call('random_int', min=100000, max=999999)}{safe_faker_call('random_int', min=100, max=999)}",  # Irish Health Identifier
        "full_name": f"{last_name.upper()},{first_name.upper()}",
        "clinical_condition": clinical_condition_name,
        "clinical_condition_code": clinical_condition_code,
        "age": safe_faker_call('random_int', min=18, max=90),
        "gp_practice": safe_faker_call('random_element', elements=IRISH_GP_PRACTICES)
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

def generate_lab_result(test_code):
    """Generate realistic lab results based on test code"""
    if test_code == "FBC":
        return generate_fbc_results()
    elif test_code == "U&E":
        return generate_ue_results()
    elif test_code == "LFT":
        return generate_lft_results()
    elif test_code == "HBA1C":
        return generate_hba1c_results()
    elif test_code == "CRP":
        return generate_crp_results()
    elif test_code == "TROPONIN":
        return generate_troponin_results()
    elif test_code == "GLUCOSE":
        return generate_glucose_results()
    elif test_code == "PSA":
        return generate_psa_results()
    elif test_code == "INR":
        return generate_inr_results()
    elif test_code == "URINALYSIS":
        return generate_urinalysis_results()
    else:
        return f"{test_code}: Normal range"

def generate_fbc_results():
    """Generate Full Blood Count results"""
    return f"""Haemoglobin: {fake.random_int(min=120, max=160)} g/L (120-160)
White Cell Count: {fake.pyfloat(left_digits=1, right_digits=1, min_value=4.0, max_value=11.0)} x10^9/L (4.0-11.0)
Platelets: {fake.random_int(min=150, max=400)} x10^9/L (150-400)
Neutrophils: {fake.pyfloat(left_digits=1, right_digits=1, min_value=2.0, max_value=7.5)} x10^9/L (2.0-7.5)"""

def generate_ue_results():
    """Generate Urea and Electrolytes results"""
    return f"""Sodium: {fake.random_int(min=136, max=145)} mmol/L (136-145)
Potassium: {fake.pyfloat(left_digits=1, right_digits=1, min_value=3.5, max_value=5.1)} mmol/L (3.5-5.1)
Urea: {fake.pyfloat(left_digits=1, right_digits=1, min_value=2.5, max_value=7.5)} mmol/L (2.5-7.5)
Creatinine: {fake.random_int(min=60, max=120)} μmol/L (60-120)"""

def generate_lft_results():
    """Generate Liver Function Tests results"""
    return f"""ALT: {fake.random_int(min=10, max=50)} U/L (10-50)
AST: {fake.random_int(min=10, max=40)} U/L (10-40)
ALP: {fake.random_int(min=40, max=150)} U/L (40-150)
Bilirubin: {fake.random_int(min=3, max=20)} μmol/L (3-20)"""

def generate_hba1c_results():
    """Generate HbA1c results"""
    hba1c_mmol = fake.random_int(min=35, max=65)
    hba1c_percent = round(((hba1c_mmol / 10.929) - 2.15), 1)
    return f"HbA1c: {hba1c_mmol} mmol/mol ({hba1c_percent}%) (≤42 mmol/mol)"

def generate_crp_results():
    """Generate C-Reactive Protein results"""
    return f"CRP: {fake.pyfloat(left_digits=1, right_digits=1, min_value=0.5, max_value=8.0)} mg/L (<8.0)"

def generate_troponin_results():
    """Generate Troponin results"""
    return f"Troponin I: {fake.pyfloat(left_digits=1, right_digits=2, min_value=0.01, max_value=0.04)} ng/mL (<0.04)"

def generate_glucose_results():
    """Generate Random Glucose results"""
    return f"Glucose: {fake.pyfloat(left_digits=1, right_digits=1, min_value=4.0, max_value=7.8)} mmol/L (4.0-7.8)"

def generate_psa_results():
    """Generate PSA results"""
    return f"PSA: {fake.pyfloat(left_digits=1, right_digits=2, min_value=0.5, max_value=4.0)} ng/mL (<4.0)"

def generate_inr_results():
    """Generate INR results"""
    return f"INR: {fake.pyfloat(left_digits=1, right_digits=1, min_value=0.8, max_value=1.2)} (0.8-1.2)"

def generate_urinalysis_results():
    """Generate Urinalysis results"""
    protein = fake.random_element(elements=["Negative", "Trace", "+"])
    glucose = fake.random_element(elements=["Negative", "Trace"])
    blood = fake.random_element(elements=["Negative", "Trace"])
    return f"""Protein: {protein}
Glucose: {glucose}  
Blood: {blood}
Leucocytes: Negative
Nitrites: Negative"""

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

# Legacy functions - replaced by HealthLink-compliant versions above

def generate_ai_enhanced_lab_result(test_code, test_name, patient_context=None):
    """Generate AI-enhanced lab results with fallback to basic generation"""
    try:
        if azure_openai_client and AZURE_OPENAI_AVAILABLE:
            # AI-enhanced generation would go here
            return generate_lab_result(test_code)
        else:
            return generate_lab_result(test_code)
    except:
        return generate_lab_result(test_code)

def generate_ai_enhanced_radiology_report(exam_type, patient):
    """Generate AI-enhanced radiology reports with fallback to basic generation"""
    try:
        if azure_openai_client and AZURE_OPENAI_AVAILABLE:
            # AI-enhanced generation would go here
            return f"{exam_type}: Normal study. No acute abnormality detected."
        else:
            return f"{exam_type}: Normal study. No acute abnormality detected."
    except:
        return f"{exam_type}: Normal study. No acute abnormality detected."

def generate_ai_enhanced_clinical_notes(note_type, patient, clinical_context=""):
    """Generate AI-enhanced clinical notes with fallback to basic generation"""
    try:
        if azure_openai_client and AZURE_OPENAI_AVAILABLE:
            # AI-enhanced generation would go here
            return f"{note_type} notes: {clinical_context}. Patient stable, no acute concerns."
        else:
            return f"{note_type} notes: {clinical_context}. Patient stable, no acute concerns."
    except:
        return f"{note_type} notes: {clinical_context}. Patient stable, no acute concerns."

def generate_ai_enhanced_referral_reason(specialty, patient, clinical_condition=""):
    """Generate AI-enhanced referral reasons with fallback to basic generation"""
    try:
        if azure_openai_client and AZURE_OPENAI_AVAILABLE:
            # AI-enhanced generation would go here
            condition = clinical_condition if clinical_condition else "routine assessment"
            return f"Referral to {specialty} for {condition}. Please see and advise."
        else:
            condition = clinical_condition if clinical_condition else "routine assessment"
            return f"Referral to {specialty} for {condition}. Please see and advise."
    except:
        condition = clinical_condition if clinical_condition else "routine assessment"
        return f"Referral to {specialty} for {condition}. Please see and advise."

def generate_ai_enhanced_discharge_summary(patient, admission_reason="", hospital_course=""):
    """Generate AI-enhanced discharge summaries with fallback to basic generation"""
    try:
        if azure_openai_client and AZURE_OPENAI_AVAILABLE:
            # AI-enhanced generation would go here
            reason = admission_reason if admission_reason else "routine care"
            return f"Patient admitted for {reason}. Hospital course uneventful. Discharged home in stable condition."
        else:
            reason = admission_reason if admission_reason else "routine care"
            return f"Patient admitted for {reason}. Hospital course uneventful. Discharged home in stable condition."
    except:
        reason = admission_reason if admission_reason else "routine care"
        return f"Patient admitted for {reason}. Hospital course uneventful. Discharged home in stable condition."

def format_as_healthlink_compliant_xml(xml_element, msg_type_id, include_framing=False):
    """Format XML element as HealthLink-compliant XML string"""
    try:
        # Convert to string with proper formatting
        rough_string = ET.tostring(xml_element, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ")
        
        # Remove extra whitespace and empty lines
        lines = [line for line in pretty_xml.split('\n') if line.strip()]
        formatted_xml = '\n'.join(lines[1:])  # Remove XML declaration
        
        if include_framing:
            # Add HL7 framing characters for transmission
            return f"\x0b{formatted_xml}\x1c\x0d"
        else:
            return formatted_xml
    except Exception as e:
        logger.error(f"Error formatting XML: {e}")
        # Fallback to basic string conversion
        return ET.tostring(xml_element, encoding='unicode')

# Placeholder functions for incomplete sections that may be called
def create_ref_i12_segments(root, patient, hospital, timestamp, msg_type_id=3):
    """Create REF_I12 specific segments for referral messages"""
    # Add PID segment
    pid = create_pid_segment(patient)
    root.append(pid)
    
    # Add basic referral information
    rf1 = ET.SubElement(root, "RF1")
    rf1_1 = ET.SubElement(rf1, "RF1.1")
    rf1_1.text = "A"  # Referral status
    
    return root

def create_rri_i12_segments(root, patient, hospital, timestamp):
    """Create RRI_I12 specific segments for referral response messages"""
    # Add PID segment
    pid = create_pid_segment(patient)
    root.append(pid)
    
    # Add basic response information
    rf1 = ET.SubElement(root, "RF1")
    rf1_1 = ET.SubElement(rf1, "RF1.1")
    rf1_1.text = "A"  # Response status
    
    return root

def create_ack_segments(root, timestamp):
    """Create ACK specific segments for acknowledgement messages"""
    # Add MSA segment
    msa = ET.SubElement(root, "MSA")
    msa_1 = ET.SubElement(msa, "MSA.1")
    msa_1.text = "AA"  # Application Accept
    msa_2 = ET.SubElement(msa, "MSA.2")
    msa_2.text = f"ACK{timestamp}"
    
    return root

def create_siu_s12_segments(root, patient, hospital, timestamp):
    """Create SIU_S12 specific segments for scheduling messages"""
    # Add PID segment
    pid = create_pid_segment(patient)
    root.append(pid)
    
    # Add SCH segment for scheduling
    sch = ET.SubElement(root, "SCH")
    sch_1 = ET.SubElement(sch, "SCH.1")
    sch_1.text = "1"
    sch_2 = ET.SubElement(sch, "SCH.2")
    sch_2.text = f"APPT{timestamp}"
    
    return root

def create_adt_segments(root, patient, hospital, timestamp, adt_type):
    """Create ADT specific segments for admission/discharge/transfer messages"""
    # Add PID segment
    pid = create_pid_segment(patient)
    root.append(pid)
    
    # Add EVN segment
    evn = ET.SubElement(root, "EVN")
    evn_1 = ET.SubElement(evn, "EVN.1")
    if "A01" in adt_type:
        evn_1.text = "A01"  # Admission
    elif "A03" in adt_type:
        evn_1.text = "A03"  # Discharge
    else:
        evn_1.text = "A08"  # Update
    evn_2 = ET.SubElement(evn, "EVN.2")
    evn_2.text = timestamp
    
    # Add PV1 segment
    pv1 = ET.SubElement(root, "PV1")
    pv1_1 = ET.SubElement(pv1, "PV1.1")
    pv1_1.text = "1"
    pv1_2 = ET.SubElement(pv1, "PV1.2")
    pv1_2.text = "I" if "A01" in adt_type else "O"  # Inpatient or Outpatient
    
    return root

def generate_healthlink_message_control_id(msg_type_id):
    """Generate HealthLink-compliant Message Control ID based on message type"""
    # Format: YYYYMMDDHHMMSSSSS where last 3 digits are msg_type_id padded
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    msg_id_padded = str(msg_type_id).zfill(3)
    return f"{timestamp}{msg_id_padded}"

def create_msh_segment_healthlink_compliant():
    """Create MSH segment XML element with HealthLink-compliant structure"""
    msh = ET.Element("MSH")
    
    # MSH.1 - Field Separator
    msh1 = ET.SubElement(msh, "MSH.1")
    msh1.text = "|"
    
    # MSH.2 - Encoding Characters
    msh2 = ET.SubElement(msh, "MSH.2")
    msh2.text = "^~\\&"
    
    return msh

def add_healthlink_msh_fields(msh, msg_type_id, hospital, doctor, timestamp, message_control_id):
    """Add HealthLink-specific fields to MSH segment"""
    msg_info = HEALTHLINK_MESSAGES[msg_type_id]
    
    # MSH.3 - Sending Application
    msh3 = ET.SubElement(msh, "MSH.3")
    hd1_3 = ET.SubElement(msh3, "HD.1")
    hd1_3.text = f"HL7SyntGen.{msg_info['msh3_suffix']}"
    hd2_3 = ET.SubElement(msh3, "HD.2")
    hd3_3 = ET.SubElement(msh3, "HD.3")
    
    # MSH.4 - Sending Facility
    msh4 = ET.SubElement(msh, "MSH.4")
    hd1_4 = ET.SubElement(msh4, "HD.1")
    hd1_4.text = hospital["name"]
    hd2_4 = ET.SubElement(msh4, "HD.2")
    hd2_4.text = hospital["hipe"]
    hd3_4 = ET.SubElement(msh4, "HD.3")
    hd3_4.text = "HIPE"
    
    # MSH.5 - Receiving Application
    msh5 = ET.SubElement(msh, "MSH.5")
    hd1_5 = ET.SubElement(msh5, "HD.1")
    hd1_5.text = "HealthLink"
    hd2_5 = ET.SubElement(msh5, "HD.2")
    hd3_5 = ET.SubElement(msh5, "HD.3")
    
    # MSH.6 - Receiving Facility
    msh6 = ET.SubElement(msh, "MSH.6")
    hd1_6 = ET.SubElement(msh6, "HD.1")
    hd1_6.text = "HSE"
    hd2_6 = ET.SubElement(msh6, "HD.2")
    hd3_6 = ET.SubElement(msh6, "HD.3")
    
    # MSH.7 - Date/Time of Message
    msh7 = ET.SubElement(msh, "MSH.7")
    ts1_7 = ET.SubElement(msh7, "TS.1")
    ts1_7.text = timestamp
    
    # MSH.8 - Security (usually empty)
    msh8 = ET.SubElement(msh, "MSH.8")
    
    # MSH.9 - Message Type
    msh9 = ET.SubElement(msh, "MSH.9")
    msg1_9 = ET.SubElement(msh9, "MSG.1")
    msg1_9.text = msg_info["type"].split("_")[0]  # e.g., "ORU"
    msg2_9 = ET.SubElement(msh9, "MSG.2")
    msg2_9.text = msg_info["type"].split("_")[1] if "_" in msg_info["type"] else ""  # e.g., "R01"
    msg3_9 = ET.SubElement(msh9, "MSG.3")
    msg3_9.text = msg_info["type"]  # e.g., "ORU_R01"
    
    # MSH.10 - Message Control ID
    msh10 = ET.SubElement(msh, "MSH.10")
    msh10.text = message_control_id
    
    # MSH.11 - Processing ID
    msh11 = ET.SubElement(msh, "MSH.11")
    pt1_11 = ET.SubElement(msh11, "PT.1")
    pt1_11.text = "P"  # Production
    pt2_11 = ET.SubElement(msh11, "PT.2")
    
    # MSH.12 - Version ID
    msh12 = ET.SubElement(msh, "MSH.12")
    vid1_12 = ET.SubElement(msh12, "VID.1")
    vid1_12.text = "2.4"
    vid2_12 = ET.SubElement(msh12, "VID.2")
    vid3_12 = ET.SubElement(msh12, "VID.3")

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
    
    return root

# Azure Functions HTTP triggers
@app.route(route="generate_random_message", auth_level=func.AuthLevel.ANONYMOUS)
def generate_random_message(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function to generate random HL7 messages based on HealthLink specification.
    """
    logger.info('Python HTTP trigger function processed a request.')
    
    try:
        # Parse request parameters
        include_framing = req.params.get('include_framing', 'false').lower() == 'true'
        raw_xml = req.params.get('raw_xml', 'false').lower() == 'true'
        message_type_id = req.params.get('message_type_id')
        
        # If specific message type requested, use it, otherwise random
        if message_type_id:
            try:
                random_message_type_id = int(message_type_id)
                if random_message_type_id not in HEALTHLINK_MESSAGES:
                    return func.HttpResponse(
                        f"Invalid message_type_id. Valid options are: {list(HEALTHLINK_MESSAGES.keys())}",
                        status_code=400
                    )
            except ValueError:
                return func.HttpResponse("message_type_id must be an integer", status_code=400)
        else:
            random_message_type_id = fake.random_element(elements=list(HEALTHLINK_MESSAGES.keys()))
        
        # Generate HL7 message
        hl7_xml_element = create_hl7_message_xml(random_message_type_id)
        
        if raw_xml:
            # Return raw XML without pretty printing
            result = ET.tostring(hl7_xml_element, encoding='unicode')
        else:
            # Return formatted XML
            result = format_as_healthlink_compliant_xml(hl7_xml_element, random_message_type_id, include_framing)
        
        # Log successful generation for monitoring
        logger.info(f"Successfully generated HL7 message type {random_message_type_id}")
        
        # Return HTTP response
        return func.HttpResponse(result, mimetype="application/xml")
        
    except Exception as e:
        logger.error(f"Error generating HL7 message: {str(e)}")
        return func.HttpResponse(f"Error generating message: {str(e)}", status_code=500)

@app.route(route="list_message_types", auth_level=func.AuthLevel.ANONYMOUS)  
def list_message_types(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function to list all available HealthLink message types.
    """
    logger.info('List message types request received.')
    
    try:
        # Create JSON response with message types
        response_data = {
            "available_message_types": HEALTHLINK_MESSAGES,
            "total_count": len(HEALTHLINK_MESSAGES)
        }
        
        # Convert to JSON and return
        import json
        result = json.dumps(response_data, indent=2)
        
        return func.HttpResponse(result, mimetype="application/json")
        
    except Exception as e:
        logger.error(f"Error listing message types: {str(e)}")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)

@app.route(route="generate_specific_message", auth_level=func.AuthLevel.ANONYMOUS)
def generate_specific_message(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function to generate a specific HL7 message type with optional formatting.
    """
    logger.info('Generate specific message request received.')
    
    try:
        # Get required message type
        message_type_id = req.params.get('message_type_id')
        if not message_type_id:
            return func.HttpResponse("message_type_id parameter is required", status_code=400)
        
        try:
            message_type_id = int(message_type_id)
        except ValueError:
            return func.HttpResponse("message_type_id must be an integer", status_code=400)
        
        if message_type_id not in HEALTHLINK_MESSAGES:
            return func.HttpResponse(
                f"Invalid message_type_id. Valid options are: {list(HEALTHLINK_MESSAGES.keys())}",
                status_code=400
            )
        
        # Parse optional parameters
        include_framing = req.params.get('include_framing', 'false').lower() == 'true'
        pretty_print = req.params.get('pretty_print', 'true').lower() == 'true'
        
        # Generate HL7 message
        hl7_xml_element = create_hl7_message_xml(message_type_id)
        
        if pretty_print:
            healthlink_xml = format_as_healthlink_compliant_xml(hl7_xml_element, message_type_id)
        else:
            healthlink_xml = ET.tostring(hl7_xml_element, encoding='unicode')
        
        # Apply framing if requested
        if include_framing:
            framed_result = format_as_healthlink_compliant_xml(hl7_xml_element, message_type_id, True)
            return func.HttpResponse(framed_result, mimetype="application/xml")
        
        # Log successful generation
        logger.info(f"Successfully generated specific HL7 message type {message_type_id}")
        
        return func.HttpResponse(healthlink_xml, mimetype="application/xml")
        
    except Exception as e:
        logger.error(f"Error generating specific message: {str(e)}")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)


@app.route(route="health", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """
    Health check endpoint for Azure deployment verification.
    """
    logger.info("Health check request received.")
    
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "functions": {
                "generate_random_message": "available",
                "generate_specific_message": "available",
                "list_message_types": "available"
            },
            "dependencies": {
                "faker": "loaded",
                "xml": "loaded",
                "azure_functions": "loaded"
            },
            "message_types_count": len(HEALTHLINK_MESSAGES)
        }
        
        return func.HttpResponse(
            json.dumps(health_status, indent=2),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        error_response = {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }
        return func.HttpResponse(
            json.dumps(error_response, indent=2),
            mimetype="application/json",
            status_code=500
        )


# Add a simple root endpoint for Azure deployment testing
@app.route(route="", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def root_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Root endpoint providing API documentation.
    """
    logger.info("Root endpoint request received.")
    
    api_info = {
        "name": "HL7 Synthetic Data Generator",
        "version": "1.0.0",
        "description": "Generate synthetic HL7 messages for Irish healthcare systems",
        "endpoints": {
            "GET /api/health": "Health check endpoint",
            "GET /api/list_message_types": "List all available HL7 message types",
            "GET /api/generate_random_message": "Generate a random HL7 message",
            "GET /api/generate_specific_message": "Generate a specific HL7 message type",
        },
        "parameters": {
            "generate_specific_message": {
                "message_type_id": "Required integer (1-31)",
                "include_framing": "Optional boolean (default: false)",
                "pretty_print": "Optional boolean (default: true)"
            }
        },
        "total_message_types": len(HEALTHLINK_MESSAGES)
    }
    
    return func.HttpResponse(
        json.dumps(api_info, indent=2),
        mimetype="application/json",
        status_code=200
    )


# Ensure the function app is properly initialized for Azure
if __name__ == "__main__":
    logger.info("Function app module loaded successfully")
    logger.info(f"Total functions registered: 5")
    logger.info(f"Available message types: {len(HEALTHLINK_MESSAGES)}")
