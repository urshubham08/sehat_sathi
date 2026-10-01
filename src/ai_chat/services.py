import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not configured.")

client = genai.Client(api_key=API_KEY)


SYSTEM_INSTRUCTION = """
You are Sehat Saathi, a healthcare information assistant.

Provide general, safe and understandable health information.

Rules:
- Do not diagnose diseases.
- Do not prescribe medicines or dosages.
- Do not replace a qualified doctor.
- Explain medical terms and report information in simple language.
- Clearly mention when a doctor should review the report.
- If serious emergency warning signs are mentioned, recommend urgent medical care.
- Do not invent values or information that is not present in the report.
"""


def ask_gemini(question: str) -> str:
    if not question or not question.strip():
        return "Please enter a health-related question."

    interaction = client.interactions.create(
        model="gemini-3.8-flash",
        input=question.strip(),
        system_instruction=SYSTEM_INSTRUCTION,
    )

    if not interaction.output_text:
        return "Sorry, I could not generate a response."

    return interaction.output_text


def explain_medical_report(report_text: str) -> str:
    if not report_text.strip():
        return "The medical report does not contain readable text."

    prompt = f"""
Explain the following medical report in simple language.

Include:
1. What tests or sections are present
2. Important values or findings
3. Meaning of difficult medical terms
4. Which findings may need discussion with a doctor
5. A short simple summary

Do not diagnose the patient.
Do not prescribe medicines.
Do not invent information.

Medical report:

{report_text}
"""

    interaction = client.interactions.create(
        model="gemini-3.8-flash",
        input=prompt,
        system_instruction=SYSTEM_INSTRUCTION,
    )

    if not interaction.output_text:
        return "Sorry, I could not explain this report."

    return interaction.output_text

def analyze_prescription_image(image_bytes: bytes, mime_type: str) -> str:
    if not image_bytes:
        return "Prescription image is empty."

    prompt = """
Analyze this prescription image for general health information.

Explain only what can be clearly read from the image.

Include:
1. Medicine names that are clearly visible
2. Clearly visible instructions, if any
3. Difficult medical terms in simple language
4. Any unclear or unreadable parts

Important safety rules:
- Do NOT prescribe medicines.
- Do NOT recommend changing, starting, or stopping medicines.
- Do NOT guess unreadable medicine names or dosages.
- If something is unclear, explicitly say that it is unclear.
- Tell the patient to confirm the prescription with their doctor or pharmacist.
"""

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": image_bytes,
                        }
                    },
                ],
            }
        ],
    )

    if not response.text:
        return "Sorry, I could not analyze this prescription image."

    return response.text