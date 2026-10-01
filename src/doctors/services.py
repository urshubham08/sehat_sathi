import json
import os

from dotenv import load_dotenv
from google import genai

from src.database.models import Doctor


load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not configured."
    )

client = genai.Client(
    api_key=API_KEY
)


SPECIALTY_INSTRUCTION = """
You are Sehat Saathi's doctor-specialty matching assistant.

Your job is to identify the most appropriate medical
specialty based on the patient's health question.

Important rules:
- Do not diagnose a disease.
- Do not prescribe medicines.
- Do not claim certainty.
- Choose only from the specialties provided.
- If no specialty is a reasonable match,
  return "General Physician".
- Return only valid JSON.

JSON format:

{
    "specialty": "specialty name",
    "reason": "short simple explanation"
}
"""


def fallback_specialty(
    question: str,
    available_specialties: list[str]
):
    """
    Local fallback matching.

    This is used if Gemini is temporarily unavailable.
    It does not diagnose the patient.
    """

    if not available_specialties:
        return {
            "specialty": "General Physician",
            "reason": (
                "No doctor specialties are currently available."
            )
        }

    question_lower = question.lower()

    keyword_map = {
        "cardiology": [
            "heart",
            "chest pain",
            "chest pressure",
            "heartbeat",
            "palpitation",
            "blood pressure",
            "bp"
        ],

        "dermatology": [
            "skin",
            "rash",
            "acne",
            "itching",
            "pimple",
            "eczema",
            "hair loss",
            "fungal"
        ],

        "neurology": [
            "headache",
            "migraine",
            "seizure",
            "memory",
            "dizziness",
            "nerve",
            "numbness",
            "tingling"
        ],

        "orthopedics": [
            "bone",
            "joint",
            "knee",
            "back pain",
            "shoulder",
            "fracture",
            "arthritis",
            "muscle"
        ],

        "gastroenterology": [
            "stomach",
            "gas",
            "acidity",
            "vomiting",
            "diarrhea",
            "constipation",
            "digestion",
            "abdomen"
        ],

        "pediatrics": [
            "child",
            "baby",
            "infant",
            "kid",
            "son",
            "daughter"
        ],

        "gynecology": [
            "period",
            "menstrual",
            "pregnancy",
            "ovulation",
            "gynecology"
        ],

        "ophthalmology": [
            "eye",
            "vision",
            "blurred vision",
            "eyesight",
            "red eye"
        ],

        "ent": [
            "ear",
            "nose",
            "throat",
            "hearing",
            "sinus",
            "tonsil"
        ]
    }

    normalized_specialties = {
        specialty.lower().strip(): specialty
        for specialty in available_specialties
    }

    for specialty_key, keywords in keyword_map.items():

        matched_keyword = None

        for keyword in keywords:

            if keyword in question_lower:
                matched_keyword = keyword
                break

        if matched_keyword:

            for available_key, original_name in (
                normalized_specialties.items()
            ):

                if (
                    specialty_key in available_key
                    or available_key in specialty_key
                ):
                    return {
                        "specialty": original_name,
                        "reason": (
                            "The health question contains "
                            f"terms related to {specialty_key}. "
                            "This is a general specialty match, "
                            "not a medical diagnosis."
                        )
                    }

    # General Physician fallback
    for available_key, original_name in (
        normalized_specialties.items()
    ):

        if (
            "general" in available_key
            and "physician" in available_key
        ):
            return {
                "specialty": original_name,
                "reason": (
                    "A general medical evaluation may be "
                    "appropriate for this question."
                )
            }

    return {
        "specialty": available_specialties[0],
        "reason": (
            "No specific specialty could be determined "
            "from the question, so an available doctor "
            "has been shown for general evaluation."
        )
    }


def suggest_specialty(
    question: str,
    available_specialties: list[str]
):
    if not question or not question.strip():

        return {
            "specialty": "General Physician",
            "reason": (
                "No health question was provided."
            )
        }

    if not available_specialties:

        return {
            "specialty": "General Physician",
            "reason": (
                "No doctor specialties are currently available."
            )
        }

    specialties_text = ", ".join(
        available_specialties
    )

    prompt = f"""
Patient's health question:

{question}

Available doctor specialties:

{specialties_text}

Select the most appropriate specialty
from the available specialties.

Do not diagnose the patient.

Return JSON only.
"""

    try:

        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=[
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            config={
                "system_instruction":
                    SPECIALTY_INSTRUCTION,
                "response_mime_type":
                    "application/json"
            }
        )

        if not response.text:

            return fallback_specialty(
                question,
                available_specialties
            )

        try:

            result = json.loads(
                response.text
            )

            specialty = result.get(
                "specialty",
                "General Physician"
            )

            reason = result.get(
                "reason",
                "General medical evaluation may be appropriate."
            )

            # Security/safety:
            # Only accept a specialty that exists
            # in the database.

            specialty_match = None

            for available in available_specialties:

                if (
                    available.strip().lower()
                    == specialty.strip().lower()
                ):
                    specialty_match = available
                    break

            if not specialty_match:

                return fallback_specialty(
                    question,
                    available_specialties
                )

            return {
                "specialty": specialty_match,
                "reason": reason
            }

        except (
            json.JSONDecodeError,
            AttributeError,
            TypeError
        ):

            return fallback_specialty(
                question,
                available_specialties
            )

    except Exception as error:

        print(
            "SMART MATCH GEMINI ERROR:",
            error
        )

        # Gemini unavailable / overloaded / network issue
        # should NOT crash the application.

        return fallback_specialty(
            question,
            available_specialties
        )


def match_doctors(
    specialty: str,
    doctors: list[Doctor]
):
    specialty_lower = (
        specialty.strip().lower()
    )

    matching_doctors = []

    for doctor in doctors:

        doctor_specialty = (
            doctor.specialty or ""
        ).strip().lower()

        if doctor_specialty == specialty_lower:

            matching_doctors.append(
                doctor
            )

    return matching_doctors