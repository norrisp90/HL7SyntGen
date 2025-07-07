# Azure OpenAI Configuration for HealthLink HL7 Message Generator
# 
# To enable AI-enhanced content generation, set these environment variables:

# Required: Your Azure OpenAI endpoint URL
AZURE_OPENAI_ENDPOINT=https://your-aoai-instance.openai.azure.com/

# Option 1: Use API Key authentication
AZURE_OPENAI_API_KEY=your-api-key-here

# Option 2: Use Managed Identity (recommended for production)
# Leave AZURE_OPENAI_API_KEY empty to use DefaultAzureCredential

# Your deployed model name (e.g., gpt-4, gpt-35-turbo)
AZURE_OPENAI_DEPLOYMENT=gpt-4

# API Version (use latest stable version)
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Example local.settings.json for Azure Functions:
# {
#   "IsEncrypted": false,
#   "Values": {
#     "AzureWebJobsStorage": "UseDevelopmentStorage=true",
#     "FUNCTIONS_WORKER_RUNTIME": "python",
#     "AZURE_OPENAI_ENDPOINT": "https://your-aoai-instance.openai.azure.com/",
#     "AZURE_OPENAI_API_KEY": "your-api-key-here",
#     "AZURE_OPENAI_DEPLOYMENT": "gpt-4",
#     "AZURE_OPENAI_API_VERSION": "2024-02-15-preview"
#   }
# }

# Benefits of AI Enhancement:

# 1. OBX.5 (Lab Results): Realistic values with proper medical context
#    - Age/gender appropriate ranges
#    - Clinically correlated abnormalities
#    - Proper Irish medical units and terminology

# 2. Clinical Notes: Context-aware medical narratives
#    - Specialty-specific language
#    - Appropriate clinical reasoning
#    - Irish healthcare pathway references

# 3. Radiology Reports: Professional imaging interpretations
#    - Standard radiological structure
#    - Anatomically accurate descriptions
#    - Appropriate clinical correlations

# 4. Referral Reasons: Realistic specialist referral justifications
#    - Specialty-appropriate indications
#    - Clinical decision-making context
#    - Irish healthcare practice patterns

# 5. Diagnosis Text: ICD-10 appropriate clinical summaries
#    - Professional medical language
#    - Appropriate clinical detail
#    - Inter-provider communication style
