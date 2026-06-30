import os
import json
import logging
from typing import Dict, Any

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.azure_api_key = os.getenv("AZURE_AI_API_KEY")
        self.azure_endpoint = os.getenv("AZURE_AI_ENDPOINT")
        
        if self.azure_api_key and self.azure_endpoint:
            logger.info("GeminiService: Microsoft Foundry Azure AI configured as primary AI engine.")
            self.model = "azure"
        elif self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-2.5-flash")
            logger.info("GeminiService: Gemini configured as primary AI engine.")
        else:
            self.model = None
            logger.warning("GeminiService: Neither Azure AI nor Gemini credentials found.")

    @property
    def is_available(self) -> bool:
        return self.model is not None

    def process_transcript(self, raw_input: Any) -> Dict[str, Any]:
        """
        Pass the raw Whisper transcript or segments to Azure AI Foundry or Gemini.
        Returns JSON containing the cleaned segments, English transcript, summary, issues, and sentiment.
        """
        if not self.is_available:
            raise ValueError("No AI service credentials configured.")

        if isinstance(raw_input, list):
            # Format segments nicely to be processed
            formatted_segments = []
            for s in raw_input:
                formatted_segments.append({
                    "start": s.get("start"),
                    "end": s.get("end"),
                    "text": s.get("text")
                })
            input_context = f"Raw Transcription Segments (JSON):\n{json.dumps(formatted_segments, indent=2)}"
        else:
            input_context = f"Raw Transcript:\n\"\"\"\n{raw_input}\n\"\"\""

        system_instructions = (
            "You are an expert AI assistant for 'OnePlug EV', an electric vehicle charging "
            "network support center in Tamil Nadu, India.\n\n"
            "Your task is to process a raw audio transcript/segments and return a clean, structured JSON analysis.\n\n"
            "The transcription was produced by Whisper's speech-to-English translation engine from a Tamil "
            "or Tamil-English (Tanglish) customer support call. Whisper often makes transcription errors "
            "on Tamil or English audio — correct them using context.\n\n"
            "COMMON WHISPER ERRORS ON TAMIL SUPPORT CALLS:\n"
            "- Tamil place names get garbled (e.g. 'Vinayachirur' or 'Vinayakshri' likely refer to 'Vinayachirur' or other actual Tamil towns hosting EV stations)\n"
            "- Vehicle model codes get garbled (e.g. 'XCV9E' or 'XCV 90' or '9E XTB 4N' refer to Tata Nexon EV, MG ZS EV, etc. Replace these directly with clean EV model names like 'Tata Nexon EV' or 'MG ZS EV' without adding explanatory notes)\n"
            "- 'Concealers office' / 'consumable cost' likely means 'energy consumption cost'\n"
            "- '1.5g app' or 'OneFlag TV app' or 'OnePlus app' means 'OnePlug EV app'\n"
            "- 'OnePlus' or 'One Plus' (representing the company/support center) means 'OnePlug' / 'OnePlug EV'\n"
            "- 'BlackSmart app' / 'Black Smart' / 'Blacksmart' refers to 'Plugzmart app' (also written as 'PlugSmart app' or 'Plugzmart') or 'BluSmart app' depending on context\n"
            "- 'balance card' likely means 'RFID card' or 'wallet balance'\n"
            "- '402 stop' / '402 service stop' is a charging error code — keep as-is\n"
            "- Phone numbers and OTPs may have garbled digits — transcribe what was said\n"
            "- Repeated 'Thank you' at end of call — trim to one natural closing sentence\n"
            "- 'closing it before the movie ends' likely means 'session ended before charging was complete'\n"
            "- 'entrepreneur' in this context likely means 'account number' or 'charger ID'\n"
            "- EV CAR MODEL MISSPELLINGS: Correct any garbled car names to their clean proper model name:\n"
            "  * 'Tiago', 'Diago', 'Thiago' -> 'Tata Tiago EV'\n"
            "  * 'Nexon', 'Next on', 'Next-on' -> 'Tata Nexon EV'\n"
            "  * 'MG', 'MG ZS', 'ZS EV', 'MGS', 'XCV9E' -> 'MG ZS EV'\n"
            "  * 'BYD', 'Atto', 'Atto 3', 'B18' -> 'BYD Atto 3'\n"
            "  * 'XUV', '400', 'XUV 400', 'XUV400' -> 'Mahindra XUV400'\n"
            "- Hold music IVR messages like 'The person you are speaking to has put your call on hold. Please stay on.' — remove these segments completely\n\n"
            "ROLE DISTINCTION RULES:\n"
            "- 'OnePlug EV' is the name of our support center / company.\n"
            "- Therefore, any speaker who says 'I am calling from OnePlug EV' or 'calling from OnePlug EV' is the AGENT, not the customer.\n"
            "- If the transcript contains only an introductory message like 'Good evening, calling from OnePlug EV...' and there is no customer response, "
            "this means the AGENT made an outbound call and left a voicemail/message for the customer because the customer was unavailable. "
            "Do NOT summarize this as 'a customer called' or 'the customer introduced themselves as OnePlug EV'. "
            "Instead, clarify that the AGENT made an outbound call and left a message.\n\n"
            "CALL DIRECTION DEFAULT: The vast majority of calls in this system are OUTBOUND calls made BY THE AGENT TO THE CUSTOMER "
            "(e.g. agent calling to check in, follow up, gather feedback, or resolve an open issue). Unless the transcript clearly "
            "shows the customer initiating contact (e.g. customer says 'I am calling about...' or 'I have a problem with...' as the "
            "very first line), assume the call is AGENT-INITIATED. This means: the agent opens the call, the agent explains the "
            "reason for calling, and any follow-up actions or promises made BY THE CUSTOMER (e.g. 'I will call back', 'I will check "
            "and let you know') must be attributed to the CUSTOMER — not the agent.\n\n"
            "CRITICAL ACCURACY RULE: When describing actions, timeframes, or promises (e.g. 'will call back in 5 minutes', "
            "'will set up in 5 minutes', 'will check and respond'), carefully re-read the transcript segment order and "
            "attribute each statement to the EXACT speaker who said it. Do not swap or assume which party said a given line "
            "based on typical call patterns — verify against the actual sequence of dialogue.\n\n"
	    "ONEPLUG EV DOMAIN VOCABULARY:\n"
            "- Charging stations, RFID cards, charging sessions, wallet top-up, transaction history\n"
            "- EV Charging Networks/Apps: Plugzmart, PlugSmart, BluSmart, Tata Power EZ Charge, Zeon Charging\n"
            "- Error codes: E-14, 402, 500 series\n"
            "- Common Indian EVs: Tata Nexon EV, Tata Tiago EV, MG ZS EV, Ather 450, Ola S1\n"
            "- Tamil Nadu locations: Chennai, Salem, Coimbatore, Madurai, Trichy, Vellore\n"
            "- App features: Profile section, Transaction History, Wallet Balance, Session History\n\n"
            "Requirements:\n"
            "1. segments: If the input was a list of segments, return a cleaned list of segments where the text of each segment has been rewritten to be "
            "fluent, natural conversational English. Fix grammar, correct EV model names/codes (e.g. replace 'XCV9E' with 'MG ZS EV') and other terms correctly. "
            "Filter out ONLY: hold-music IVR messages (e.g. 'The person you are speaking to has put your call on hold. Please stay on.'), "
            "and exact repeated consecutive duplicates of the same sentence (e.g. 'Sir it is in preparing' repeated 200 times — keep only one). "
            "DO NOT delete real conversation segments even if they are short, simple, or contain filler words like 'okay', 'yes', 'hello'. "
            "Keep ALL actual spoken dialogue between agent and customer, no matter how short.\n"
            "2. transcript: Rewrite the raw transcript into fluent, natural conversational English matching the cleaned segments.\n"
            "3. summary: A concise 1-2 sentence summary of the support call in English.\n"
            "4. main_concern: The primary issue discussed in the call. If this is an OUTBOUND call made by the AGENT to the customer, describe what the AGENT called about, not what the customer complained about. Always identify WHO raised the concern.\n"
            "5. outcome: The outcome of the interaction (in English), or 'Not applicable' if not a call.\n"
            "6. action_needed: Specific action needed to resolve the concern (in English), or 'None' if resolved.\n"
            "7. what_happened: A clear, objective, and detailed paragraph in plain English written strictly in the third person explaining exactly what happened during this call chronologically (e.g. 'A customer called from the Avinashi charging station reporting a 402 server stop error...'). Do not use first-person pronouns like 'I' or 'we'.\n"
            "8. issues: A list of issues detected from these options only: 'Delivery Delay', 'Refund Request', "
            "'Technical Issue', 'Billing Issue', 'Angry Customer', 'Escalation Risk'. "
            "If the audio is not a support call, return an empty list: []\n"
            "   Each issue must have a severity: 'Low', 'Medium', or 'High'.\n"
            "9. sentiment: The overall sentiment: 'Positive', 'Neutral', or 'Negative'.\n\n"
            "Return ONLY a valid JSON object without any markdown wrapping or additional text:\n"
            "{\n"
            '  "segments": [{"start": 0.0, "end": 2.0, "text": "string"}],\n'
            '  "transcript": "string",\n'
            '  "summary": "string",\n'
            '  "main_concern": "string",\n'
            '  "outcome": "string",\n'
            '  "action_needed": "string",\n'
            '  "what_happened": "string",\n'
            '  "issues": [{"type": "string", "severity": "string"}],\n'
            '  "sentiment": "string"\n'
            "}"
        )

        # --- Route 1: Microsoft/Azure AI Foundry ---
        if self.azure_api_key and self.azure_endpoint:
            import requests
            endpoint = self.azure_endpoint
            if endpoint.endswith("/responses"):
                endpoint = endpoint[:-10] + "/chat/completions"
            elif "/chat/completions" not in endpoint:
                endpoint = endpoint.rstrip("/") + "/openai/deployments/gpt-4o/chat/completions?api-version=2024-12-01-preview"
            
            headers = {
                "api-key": self.azure_api_key,
                "Authorization": f"Bearer {self.azure_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messages": [
                    {"role": "system", "content": system_instructions},
                    {"role": "user", "content": input_context}
                ],
                "response_format": {"type": "json_object"},
                "model": "gpt-4o"
            }
            
            logger.info(f"GeminiService: Sending request to Azure AI Foundry ({endpoint})...")
            try:
                response = requests.post(endpoint, headers=headers, json=payload, timeout=45)
                if response.status_code == 400:
                    # Retry without response_format if model version/endpoint rejects it
                    logger.warning("GeminiService: Azure 400 Bad Request, retrying without response_format...")
                    payload_retry = {
                        "messages": [
                            {"role": "system", "content": system_instructions},
                            {"role": "user", "content": input_context}
                        ],
                        "model": "gpt-4o"
                    }
                    response = requests.post(endpoint, headers=headers, json=payload_retry, timeout=45)
                
                response.raise_for_status()
                res_data = response.json()
                completion_text = res_data["choices"][0]["message"]["content"]
                
                # Strip markdown code block wrappers if any
                completion_clean = completion_text.strip()
                if completion_clean.startswith("```"):
                    lines = completion_clean.splitlines()
                    if lines[0].startswith("```json") or lines[0].startswith("```"):
                        completion_clean = "\n".join(lines[1:-1])
                
                data = json.loads(completion_clean)
                logger.info("GeminiService: Successfully received response from Azure AI Foundry.")
                return data
            except Exception as e:
                logger.error(f"GeminiService: Azure AI Foundry failed: {e}. Falling back to Gemini or local.")

        # --- Route 2: Gemini API ---
        if self.api_key and not isinstance(self.model, str):
            prompt_full = f"{system_instructions}\n\nInput Context:\n{input_context}"
            import time
            from google.api_core.exceptions import ResourceExhausted

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(f"GeminiService: Sending transcript to Gemini API (Attempt {attempt+1}/{max_retries})...")
                    response = self.model.generate_content(
                        prompt_full,
                        generation_config=genai.types.GenerationConfig(
                            response_mime_type="application/json"
                        )
                    )
                    data = json.loads(response.text)
                    logger.info("GeminiService: Successfully received structured JSON from Gemini.")
                    return data

                except ResourceExhausted:
                    if attempt < max_retries - 1:
                        logger.warning("GeminiService: Rate limit hit (429). Waiting 15 seconds before retrying...")
                        time.sleep(15)
                    else:
                        logger.error("GeminiService: Failed to process via Gemini due to Rate Limit. Using local fallback.")
                        return self._get_local_fallback(raw_input)
                except Exception as e:
                    logger.error(f"GeminiService: Failed to process via Gemini: {e}. Using local fallback.")
                    return self._get_local_fallback(raw_input)

        return self._get_local_fallback(raw_input)

    def _get_local_fallback(self, raw_input: Any) -> Dict[str, Any]:
        """
        Creates a clean structured local fallback analysis if Gemini API is offline or rate-limited.
        Prevents None.mp3 failures by running local keyword analysis.
        """
        # Get raw text
        text = ""
        if isinstance(raw_input, list):
            text = " ".join([s.get("text", "") for s in raw_input])
        else:
            text = str(raw_input)

        # Basic keyword detection for concern
        concern = "support inquiry"
        issues = []
        
        lower_text = text.lower()
        if "app" in lower_text or "play store" in lower_text:
            concern = "app login issue"
            issues.append({"type": "Technical Issue", "severity": "Medium"})
        elif "charging" in lower_text or "charger" in lower_text or "station" in lower_text:
            concern = "charging session issue"
            issues.append({"type": "Technical Issue", "severity": "High"})
        elif "money" in lower_text or "refund" in lower_text or "payment" in lower_text or "wallet" in lower_text or "failed" in lower_text:
            concern = "refund payment issue"
            issues.append({"type": "Billing Issue", "severity": "Medium"})
        elif "rfid" in lower_text or "card" in lower_text:
            concern = "rfid card setup"
            issues.append({"type": "Technical Issue", "severity": "Low"})
        
        return {
            "segments": raw_input if isinstance(raw_input, list) else [{"start": 0.0, "end": 10.0, "text": text}],
            "transcript": text,
            "summary": f"Support call regarding {concern}.",
            "main_concern": concern,
            "outcome": "Logged in system.",
            "action_needed": "Requires review by support team.",
            "what_happened": f"A customer called to report a {concern}. Details: {text}",
            "issues": issues if issues else [{"type": "Technical Issue", "severity": "Low"}],
            "sentiment": "Neutral"
        }
