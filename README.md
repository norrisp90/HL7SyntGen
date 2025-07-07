# HL7 HealthLink Synthetic Data Generator

A comprehensive Azure Function API that generates highly realistic synthetic HL7 v2.4 messages compliant with the Irish HealthLink service specification.

## Features

- **HealthLink Compliant**: Generates accurate HL7 messages matching the official Irish HealthLink specification
- **31 Message Types**: Supports all HealthLink message types from Laboratory Orders to General Referral Responses
- **Realistic Irish Data**: Uses authentic Irish hospital names, HIPE codes, patient demographics, and medical data
- **Multiple Formats**: Returns messages in XML, HL7, or JSON format
- **Authentic Structure**: XML output matches real HealthLink message structure with proper segment nesting and field names
- **Real Sample Based**: Generated from analysis of actual HealthLink sample messages and official specification

## API Endpoint

### Generate Random Message
```
GET /api/generate?format=xml&type=10
```

**Parameters:**
- `format` (optional): Output format - `xml` (default), `hl7`, or `json`
- `type` (optional): Specific message type ID (1-31). If omitted, generates random message type

## Quick Start

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Locally:**
   ```bash
   func start
   ```

3. **Test the API:**
   ```bash
   # Generate random HealthLink message
   curl http://localhost:7071/api/generate
   
   # Generate specific Laboratory Result (type 10)
   curl http://localhost:7071/api/generate?type=10&format=xml
   
   # Get JSON response with metadata
   curl http://localhost:7071/api/generate?format=json
   ```

## Example Output

**Laboratory Result (Type 10) in XML format:**
```xml
<ORU_R01>
  <MSH>
    <MSH.1>|</MSH.1>
    <MSH.2>^~\&amp;</MSH.2>
    <MSH.3>
      <HD.1>HOSPITALSYSTEM.HEALTHLINK.10</HD.1>
      <HD.2></HD.2>
      <HD.3></HD.3>
    </MSH.3>
    <MSH.4>
      <HD.1>CORK UNIVERSITY HOSPITAL</HD.1>
      <HD.2>913</HD.2>
      <HD.3>L</HD.3>
    </MSH.4>
    <MSH.6>
      <HD.1>Dr O'Brien,Siobhan</HD.1>
      <HD.2>12345.6789</HD.2>
      <HD.3>MCN.HLPracticeID</HD.3>
    </MSH.6>
    <MSH.7>
      <TS.1>20250110120000</TS.1>
    </MSH.7>
    <MSH.9>
      <MSG.1>ORU</MSG.1>
      <MSG.2>R01</MSG.2>
    </MSH.9>
    <MSH.10>ORU_R0120250110120000123</MSH.10>
    <MSH.11>
      <PT.1>P</PT.1>
    </MSH.11>
    <MSH.12>
      <VID.1>2.4</VID.1>
    </MSH.12>
  </MSH>
  <ORU_R01.PATIENT_RESULT>
    <ORU_R01.PATIENT>
      <PID>
        <PID.3>
          <CX.1>M123456</CX.1>
          <CX.4>
            <HD.1>Hospital</HD.1>
          </CX.4>
          <CX.5>MRN</CX.5>
        </PID.3>
        <PID.3>
          <CX.1>IE987654321</CX.1>
          <CX.4>
            <HD.1>HSE</HD.1>
          </CX.4>
          <CX.5>IHINumber</CX.5>
        </PID.3>
        <PID.5>
          <XPN.1>
            <FN.1>Murphy</FN.1>
          </XPN.1>
          <XPN.2>Sean</XPN.2>
        </PID.5>
        <PID.7>
          <TS.1>19750315</TS.1>
        </PID.7>
        <PID.8>M</PID.8>
        <PID.11>
          <XAD.1>
            <SAD.1>15 O'Connell Street</SAD.1>
          </XAD.1>
          <XAD.2>Cork</XAD.2>
          <XAD.3>Cork</XAD.3>
          <XAD.5>T12K8E3</XAD.5>
        </PID.11>
      </PID>
    </ORU_R01.PATIENT>
  </ORU_R01.PATIENT_RESULT>
</ORU_R01>
```

**JSON Response with Metadata:**
```json
{
  "message_type_id": 10,
  "message_type": "Laboratory Result",
  "hl7_type": "ORU_R01",
  "xml_message": "<ORU_R01>...</ORU_R01>",
  "healthlink_message": "Formatted HealthLink XML",
  "hospital_info": "Generated with realistic Irish hospital data and HealthLink-compliant structure"
}
```

## Supported Message Types

The API supports all 31 HealthLink message types based on the official specification:

| ID | HL7 Type | HealthLink Message Type |
|----|----------|-------------------------|
| 1  | OML_O21  | Laboratory Order |
| 2  | ADT_A01  | Inpatient Admission |
| 3  | REF_I12  | Outpatient Clinic Letter |
| 4  | ADT_A01  | A&E Notification |
| 5  | REF_I12  | Discharge Summary |
| 6  | ADT_A03  | Death Notification |
| 7  | ORU_R01  | Radiology Result |
| 8  | SIU_S12  | OPD Appointment |
| 9  | SIU_S12  | Waiting List |
| 10 | ORU_R01  | Laboratory Result |
| 11 | ORL_O22  | Laboratory NACK |
| 12 | ADT_A03  | Discharge Notification |
| 13 | ACK      | Acknowledgement |
| 14 | REF_I12  | Neurology Referral |
| 15 | RRI_I12  | Neurology Referral Response |
| 16 | REF_I12  | Co-op Discharge |
| 17 | ORU_R01  | Cardiology Result |
| 18 | REF_I12  | Oesophageal and Gastric Cancer Referral |
| 19 | REF_I12  | A&E Letter |
| 20 | REF_I12  | Prostate Cancer Referral |
| 21 | RRI_I12  | Prostate Cancer Referral Response |
| 22 | REF_I12  | Breast Cancer Referral |
| 23 | RRI_I12  | Breast Cancer Referral Response |
| 24 | REF_I12  | Lung Cancer Referral |
| 25 | RRI_I12  | Lung Cancer Referral Response |
| 26 | REF_I12  | Chest Pain Referral |
| 27 | RRI_I12  | Chest Pain Referral Response |
| 28 | REF_I12  | MRI Request |
| 29 | RRI_I12  | MRI Request Response |
| 30 | REF_I12  | General Referral |
| 31 | RRI_I12  | General Referral Response |

## Realistic Data Generation

The API generates authentic Irish healthcare data including:

- **Irish Hospitals**: Real hospital names and HIPE codes (Cork University Hospital, Mater Misericordiae, etc.)
- **Patient Demographics**: Irish names, addresses with Eircode, Irish phone numbers
- **Medical Data**: Realistic lab values, medical specialties, test codes
- **Healthcare Identifiers**: Irish Health Identifier numbers, Medical Council numbers
- **HealthLink Structure**: Proper MSH segment formatting, CE data types, segment nesting

## Deployment

Deploy to Azure Functions using Azure CLI:
```bash
# Login to Azure
az login

# Deploy the function
func azure functionapp publish <your-function-app-name>
```

## Technologies

- **Azure Functions** (Python v2 programming model)
- **Faker** with Irish locale for synthetic data generation
- **HL7 v2.4** standard compliance
- **HealthLink** Irish healthcare messaging specification v3.0
- **Real Sample Analysis**: Based on actual HealthLink sample messages and official specification