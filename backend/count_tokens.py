"""
Gemini token counter and cost estimator for OnePlug EV.
Uses the actual prompt from gemini_service.py and real transcript samples.
"""
import os, sys
from dotenv import load_dotenv
load_dotenv()
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

# ── Exact static prompt from gemini_service.py ─────────────────────────
STATIC_PROMPT = (
    "You are an expert AI assistant for 'OnePlug EV', an electric vehicle charging "
    "network support center.\n\n"
    "Your task is to process a raw audio transcript and return a clean, structured JSON analysis.\n\n"
    "The transcript was produced by Whisper's speech-to-English translation engine. "
    "It may be a rough English translation of Tamil, Tanglish, or mixed-language speech. "
    "Your job is to clean it up into fluent, natural English - preserving the exact meaning "
    "and all details that were spoken.\n\n"
    'Raw Transcript:\n"""\n{TRANSCRIPT}\n"""\n\n'
    "Requirements:\n"
    "1. transcript: Rewrite the raw transcript into fluent, natural English. Fix grammar, "
    "remove filler words and transcription noise. Preserve ALL specific details (names, places, "
    "error codes, amounts, dates). Do NOT invent or add any information not present in the raw "
    "transcript. Do NOT include speaker labels. If the transcript is a song, poem, or "
    "non-support content, output the cleaned English version of exactly what was said.\n"
    "2. summary: A concise 1-2 sentence summary of the audio content.\n"
    "3. main_concern: The main concern raised. If it is not a support call, describe the main topic instead.\n"
    "4. outcome: The outcome of the interaction, or 'Not applicable' if it is not a call.\n"
    "5. action_needed: Action needed to resolve the concern, or 'None' if not a call.\n"
    "6. issues: A list of issues detected from these options only: 'Delivery Delay', "
    "'Refund Request', 'Technical Issue', 'Billing Issue', 'Angry Customer', 'Escalation Risk'. "
    "If the audio is not a support call, return an empty list: []\n"
    "   Each issue must have a severity: 'Low', 'Medium', or 'High'.\n"
    "7. sentiment: The overall sentiment: 'Positive', 'Neutral', or 'Negative'.\n\n"
    "Return ONLY a valid JSON object without any markdown wrapping or additional text.\n"
    '{\n  "transcript": "string",\n  "summary": "string",\n  "main_concern": "string",\n'
    '  "outcome": "string",\n  "action_needed": "string",\n'
    '  "issues": [{"type": "string", "severity": "string"}],\n  "sentiment": "string"\n}'
)

# ── Realistic transcript samples at 3 audio lengths ────────────────────
TRANSCRIPTS = {
    "SHORT (~1 min, 55 words) — our actual Tamil audio": (
        "Blood glucose is a form of blood that is not easily absorbed. "
        "Water-induced people should consume low-fat milk. "
        "The ingredients for the main dish are wheat flour, basmati rice, inipu vurali, sucrose, "
        "white bread, white rice, cornflakes, glucose, maltose."
    ),
    "MEDIUM (~3 min, 120 words) — typical support call": (
        "Good afternoon, this is a customer calling about OnePlug EV. "
        "My EV charger at Salem station four has not been working for three days. "
        "Every time I connect my vehicle the session starts but stops after two minutes with error code E-14. "
        "I have tried resetting it multiple times. "
        "I have a long trip tomorrow morning and I really need this resolved urgently. "
        "My membership ID is OP-44521. The last successful charge was on Sunday. "
        "I was also billed for an incomplete session on Monday, that charge needs to be reversed. "
        "Please escalate this to your technical team immediately. "
        "I am very frustrated with the service and want a callback today."
    ),
    "LONG (~5 min, 190 words) — complex multi-issue call": (
        "Hello I am calling about multiple issues with my OnePlug EV account. "
        "First my RFID card is not working at any of the stations in Chennai. "
        "I tried at Adyar, Nungambakkam, and Velachery stations today and all three gave the same error. "
        "Second I was supposed to receive a refund of 850 rupees from last month for a cancelled subscription "
        "but it has still not been credited to my account. "
        "I spoke to an agent two weeks ago who said 5 to 7 business days. It has now been 14 days. "
        "I am very frustrated. "
        "Third I was charged twice for the same session on May 28th at Adyar station, that is 120 rupees extra. "
        "I want all three issues resolved today. "
        "If this is not fixed I will post on social media and file a complaint. "
        "My account number is OP-78832. My email is customer at gmail dot com. "
        "Please connect me to a senior manager and note all of this down."
    ),
}

# ── Typical output JSON sizes ──────────────────────────────────────────
SAMPLE_OUTPUTS = {
    "SHORT (~1 min, 55 words) — our actual Tamil audio": (
        '{"transcript": "Blood glucose is not easily absorbed by the body. '
        'People with diabetes should consume low-fat milk. '
        'Foods to avoid include wheat flour, basmati rice, sucrose, white bread, white rice, cornflakes, glucose, and maltose.", '
        '"summary": "An audio clip listing foods high in glucose and dietary advice for people managing blood sugar levels.", '
        '"main_concern": "Dietary guidance for blood glucose management.", '
        '"outcome": "Not applicable", "action_needed": "None", "issues": [], "sentiment": "Neutral"}'
    ),
    "MEDIUM (~3 min, 120 words) — typical support call": (
        '{"transcript": "A customer is calling about an EV charger at Salem station four that has been '
        'non-functional for three days. Sessions start but stop after two minutes with error code E-14. '
        'Multiple resets have failed. The customer needs this resolved before a trip tomorrow morning. '
        'Membership ID OP-44521. A billing reversal is requested for an incomplete session on Monday.", '
        '"summary": "Customer reports a non-functional EV charger at Salem station four showing error E-14 and requests a billing reversal for an incomplete session.", '
        '"main_concern": "Charger malfunction with error code E-14 at Salem station four.", '
        '"outcome": "Pending escalation to technical team.", '
        '"action_needed": "Dispatch technical team to Salem station four, reverse Monday charge for OP-44521.", '
        '"issues": [{"type": "Technical Issue", "severity": "High"}, {"type": "Billing Issue", "severity": "Medium"}], '
        '"sentiment": "Negative"}'
    ),
    "LONG (~5 min, 190 words) — complex multi-issue call": (
        '{"transcript": "A customer is reporting three issues: RFID card not working at Adyar, Nungambakkam, '
        'and Velachery stations. A refund of 850 rupees for a cancelled subscription has not been processed '
        'after 14 days despite prior confirmation of 5-7 business days. A duplicate charge of 120 rupees '
        'for a session on May 28th at Adyar station. Customer threatens social media escalation and formal complaint. '
        'Account OP-78832.", '
        '"summary": "A highly frustrated customer reports three unresolved issues: RFID card failure across Chennai stations, a delayed 850-rupee subscription refund, and a duplicate charge of 120 rupees. Customer is threatening to escalate.", '
        '"main_concern": "RFID card failure, unprocessed refund of 850 rupees, and duplicate billing of 120 rupees.", '
        '"outcome": "Escalation requested. Issues unresolved.", '
        '"action_needed": "Fix RFID for OP-78832, process 850-rupee refund, reverse 120-rupee duplicate charge, connect to senior manager.", '
        '"issues": [{"type": "Technical Issue", "severity": "High"}, {"type": "Refund Request", "severity": "High"}, {"type": "Billing Issue", "severity": "High"}, {"type": "Angry Customer", "severity": "High"}, {"type": "Escalation Risk", "severity": "High"}], '
        '"sentiment": "Negative"}'
    ),
}

print("=" * 72)
print("ONEPLUG EV — GEMINI TOKEN & COST ANALYSIS")
print("=" * 72)

# Static prompt token count
static_only = STATIC_PROMPT.replace("{TRANSCRIPT}", "")
static_tokens = model.count_tokens(static_only).total_tokens
print(f"\nStatic prompt (no transcript): {static_tokens} tokens  |  {len(static_only)} chars\n")

results = {}
for label, transcript in TRANSCRIPTS.items():
    full_prompt = STATIC_PROMPT.replace("{TRANSCRIPT}", transcript)
    input_tokens = model.count_tokens(full_prompt).total_tokens
    output_text = SAMPLE_OUTPUTS[label]
    output_tokens = model.count_tokens(output_text).total_tokens
    transcript_tokens = input_tokens - static_tokens

    results[label] = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "transcript_tokens": transcript_tokens,
        "transcript_words": len(transcript.split()),
    }

    print(f"  {label}")
    print(f"    Transcript: {len(transcript.split())} words -> {transcript_tokens} tokens")
    print(f"    Input total:  {input_tokens} tokens")
    print(f"    Output total: {output_tokens} tokens")
    print(f"    Combined:     {input_tokens + output_tokens} tokens")
    print()

# ── Gemini 2.5 Flash pricing (as of 2025) ─────────────────────────────
# Source: https://ai.google.dev/gemini-api/docs/pricing
INPUT_PRICE_PER_M  = 0.075   # $0.075 per 1M input tokens  (non-thinking, <=1M ctx)
OUTPUT_PRICE_PER_M = 0.30    # $0.30 per 1M output tokens  (non-thinking)

print("=" * 72)
print("MONTHLY COST ESTIMATES  (Gemini 2.5 Flash non-thinking)")
print(f"  Input:  ${INPUT_PRICE_PER_M}/1M tokens")
print(f"  Output: ${OUTPUT_PRICE_PER_M}/1M tokens")
print("=" * 72)

calls_per_day_options = [10, 50, 100, 500]

for label, r in results.items():
    inp = r["input_tokens"]
    out = r["output_tokens"]
    cost_per_call = (inp * INPUT_PRICE_PER_M + out * OUTPUT_PRICE_PER_M) / 1_000_000
    print(f"\n  [{label}]")
    print(f"  Cost per call: ${cost_per_call:.6f}")
    print(f"  {'Calls/day':<12} {'Calls/month':<14} {'Monthly cost':>14}")
    print(f"  {'-'*42}")
    for cpd in calls_per_day_options:
        cpm = cpd * 30
        monthly = cpm * cost_per_call
        print(f"  {cpd:<12} {cpm:<14} ${monthly:>13.4f}")

print("\n" + "=" * 72)
print("NOTE: Gemini 2.5 Flash free tier = 1,500 requests/day, 1M tokens/min")
print("At 10 calls/day (300/month) you stay ENTIRELY on the free tier.")
print("=" * 72)
