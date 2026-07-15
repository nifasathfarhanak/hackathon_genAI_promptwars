# pylint: disable=line-too-long, missing-function-docstring, invalid-name, broad-exception-caught, too-many-lines, too-many-branches, consider-using-in, redefined-builtin, no-else-return, global-statement

#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║        🏟️  SMART STADIUM OPERATIONS HUB — FIFA WORLD CUP 2026              ║
║        Production-Grade Zero-Dependency Micro-Web Application              ║
║                                                                            ║
║  Architecture : Single-file, stdlib-only Python 3.9+                       ║
║  AI Engine    : Groq Llama 3.3 70B / Gemini 2.0 Flash / OpenRouter         ║
║  Weather      : Open-Meteo live telemetry for 16 WC2026 venues             ║
║  Security     : XSS/injection sanitization, CSP headers, rate limiting     ║
║  Accessibility: WCAG AAA contrast, semantic HTML5, full ARIA, keyboard nav ║
║  Testing      : Embedded unittest suite (run with --test)                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import http.server
import json
import os
import re
import sys
import threading
import unittest
import urllib.request
import urllib.parse
import urllib.error
import html
import time
from datetime import datetime, timezone

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: CONFIGURATION & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 8080))

# Multi-provider AI support: set ANY ONE of these keys
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"
GEOCODE_BASE = "https://geocoding-api.open-meteo.com/v1/search"


def get_ai_provider() -> str:
    """Detect which AI provider is configured."""
    if GROQ_API_KEY:
        return "groq"
    if GEMINI_API_KEY:
        return "gemini"
    if OPENROUTER_API_KEY:
        return "openrouter"
    return "none"


# ── FIFA World Cup 2026 Venue Database (Real coordinates & capacity) ──────────

WC2026_VENUES = {
    "metlife": {
        "name": "MetLife Stadium",
        "city": "East Rutherford, NJ",
        "country": "USA",
        "capacity": 82500,
        "lat": 40.8128,
        "lon": -74.0742,
        "timezone": "America/New_York",
        "features": ["retractable_roof_none", "parking_lots_30000", "transit_nj_transit"],
    },
    "att": {
        "name": "AT&T Stadium",
        "city": "Arlington, TX",
        "country": "USA",
        "capacity": 80000,
        "lat": 32.7473,
        "lon": -97.0945,
        "timezone": "America/Chicago",
        "features": ["retractable_roof_yes", "parking_lots_12000", "transit_tre"],
    },
    "hardrock": {
        "name": "Hard Rock Stadium",
        "city": "Miami Gardens, FL",
        "country": "USA",
        "capacity": 65326,
        "lat": 25.9580,
        "lon": -80.2389,
        "timezone": "America/New_York",
        "features": ["canopy_roof", "parking_lots_10000", "transit_tri_rail"],
    },
    "nrg": {
        "name": "NRG Stadium",
        "city": "Houston, TX",
        "country": "USA",
        "capacity": 72220,
        "lat": 29.6847,
        "lon": -95.4107,
        "timezone": "America/Chicago",
        "features": ["retractable_roof_yes", "parking_lots_26000", "transit_metrorail"],
    },
    "sofi": {
        "name": "SoFi Stadium",
        "city": "Inglewood, CA",
        "country": "USA",
        "capacity": 70240,
        "lat": 33.9535,
        "lon": -118.3392,
        "timezone": "America/Los_Angeles",
        "features": ["fixed_roof_yes", "parking_lots_9000", "transit_metro_c_line"],
    },
    "lincoln": {
        "name": "Lincoln Financial Field",
        "city": "Philadelphia, PA",
        "country": "USA",
        "capacity": 69796,
        "lat": 39.9008,
        "lon": -75.1675,
        "timezone": "America/New_York",
        "features": ["open_air", "parking_lots_9000", "transit_septa_bsl"],
    },
    "lumen": {
        "name": "Lumen Field",
        "city": "Seattle, WA",
        "country": "USA",
        "capacity": 68740,
        "lat": 47.5952,
        "lon": -122.3316,
        "timezone": "America/Los_Angeles",
        "features": ["partial_roof", "parking_lots_5000", "transit_link_light_rail"],
    },
    "arrowhead": {
        "name": "GEHA Field at Arrowhead Stadium",
        "city": "Kansas City, MO",
        "country": "USA",
        "capacity": 76416,
        "lat": 39.0489,
        "lon": -94.4839,
        "timezone": "America/Chicago",
        "features": ["open_air", "parking_lots_15000", "transit_kcata"],
    },
    "mercedesbenz": {
        "name": "Mercedes-Benz Stadium",
        "city": "Atlanta, GA",
        "country": "USA",
        "capacity": 71000,
        "lat": 33.7554,
        "lon": -84.4010,
        "timezone": "America/New_York",
        "features": ["retractable_roof_yes", "parking_lots_8000", "transit_marta"],
    },
    "gillette": {
        "name": "Gillette Stadium",
        "city": "Foxborough, MA",
        "country": "USA",
        "capacity": 65878,
        "lat": 42.0909,
        "lon": -71.2643,
        "timezone": "America/New_York",
        "features": ["open_air", "parking_lots_16000", "transit_mbta_commuter_rail"],
    },
    "levis": {
        "name": "Levi's Stadium",
        "city": "Santa Clara, CA",
        "country": "USA",
        "capacity": 68500,
        "lat": 37.4033,
        "lon": -121.9694,
        "timezone": "America/Los_Angeles",
        "features": ["open_air", "parking_lots_7000", "transit_vta_light_rail"],
    },
    "azteca": {
        "name": "Estadio Azteca",
        "city": "Mexico City",
        "country": "Mexico",
        "capacity": 87523,
        "lat": 19.3029,
        "lon": -99.1505,
        "timezone": "America/Mexico_City",
        "features": ["open_air", "parking_lots_5000", "transit_metro_linea_2"],
    },
    "bbva": {
        "name": "Estadio BBVA",
        "city": "Monterrey",
        "country": "Mexico",
        "capacity": 53500,
        "lat": 25.6669,
        "lon": -100.2447,
        "timezone": "America/Monterrey",
        "features": ["open_air", "parking_lots_8000", "transit_metrorrey"],
    },
    "akron": {
        "name": "Estadio Akron",
        "city": "Guadalajara",
        "country": "Mexico",
        "capacity": 49850,
        "lat": 20.6825,
        "lon": -103.4624,
        "timezone": "America/Mexico_City",
        "features": ["open_air", "parking_lots_6000", "transit_mi_macro_periferico"],
    },
    "bmo": {
        "name": "BMO Field",
        "city": "Toronto",
        "country": "Canada",
        "capacity": 30000,
        "lat": 43.6335,
        "lon": -79.4186,
        "timezone": "America/Toronto",
        "features": ["open_air", "parking_lots_2000", "transit_ttc_streetcar"],
    },
    "bcplace": {
        "name": "BC Place",
        "city": "Vancouver",
        "country": "Canada",
        "capacity": 54500,
        "lat": 49.2768,
        "lon": -123.1120,
        "timezone": "America/Vancouver",
        "features": ["retractable_roof_yes", "parking_lots_3000", "transit_skytrain"],
    },
}

# Match types for operational context
MATCH_TYPES = ["group_stage", "round_of_32", "round_of_16", "quarter_final",
               "semi_final", "third_place", "final"]

# Staff roles for ops decision support
STAFF_ROLES = ["security", "medical", "logistics", "hospitality",
               "volunteer_coordinator", "facilities", "general_manager"]

# Supported languages for multilingual assistant
SUPPORTED_LANGUAGES = {
    "English", "Spanish", "French", "Portuguese", "Arabic", "German",
    "Japanese", "Korean", "Chinese", "Hindi", "Italian", "Dutch",
}

# Fan query categories
FAN_QUERY_CATEGORIES = {
    "navigation", "food_beverage", "accessibility", "transport",
    "safety", "tickets", "merchandise", "general",
}

# Rate limiting
_rate_lock = threading.Lock()
_rate_tokens = {}
RATE_LIMIT_MAX = 15
RATE_LIMIT_WINDOW = 60  # seconds

# API response cache
_cache_lock = threading.Lock()
_api_cache = {}
CACHE_TTL = 600  # 10 minutes


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: SECURITY — INPUT SANITIZATION & VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

# Regex patterns for XSS/injection detection
_XSS_PATTERNS = [
    re.compile(r'<\s*script', re.IGNORECASE),
    re.compile(r'javascript\s*:', re.IGNORECASE),
    re.compile(r'on\w+\s*=', re.IGNORECASE),
    re.compile(r'<\s*iframe', re.IGNORECASE),
    re.compile(r'<\s*object', re.IGNORECASE),
    re.compile(r'<\s*embed', re.IGNORECASE),
    re.compile(r'<\s*form', re.IGNORECASE),
    re.compile(r'expression\s*\(', re.IGNORECASE),
    re.compile(r'url\s*\(', re.IGNORECASE),
    re.compile(r'vbscript\s*:', re.IGNORECASE),
]

_SQL_PATTERNS = [
    re.compile(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b)", re.IGNORECASE),
    re.compile(r"(--|;|\/\*|\*\/)", re.IGNORECASE),
]

_VENUE_ID_REGEX = re.compile(r'^[a-z]{2,15}$')
_QUERY_TEXT_REGEX = re.compile(r'^[A-Za-z0-9\s\-,.\?!\'"():/@#&%+;]{1,500}$')
_ATTENDANCE_RANGE = (1000, 100000)
_MAX_POST_BODY = 10240  # 10KB


def sanitize_input(value: str) -> str:
    """Sanitize user input: HTML-escape and strip XSS/injection vectors."""
    if not isinstance(value, str):
        return ""
    value = value.strip()
    for pattern in _XSS_PATTERNS:
        if pattern.search(value):
            return ""
    for pattern in _SQL_PATTERNS:
        if pattern.search(value):
            return ""
    return html.escape(value, quote=True)


def validate_venue_id(vid: str) -> str:
    """Validate venue ID is one of the known WC2026 venues."""
    clean = sanitize_input(vid).lower()
    return clean if clean in WC2026_VENUES else ""


def validate_match_type(mt: str) -> str:
    """Validate match type is one of the allowed values."""
    clean = sanitize_input(mt).lower().replace(" ", "_")
    return clean if clean in MATCH_TYPES else "group_stage"


def validate_staff_role(role: str) -> str:
    """Validate staff role is one of the allowed values."""
    clean = sanitize_input(role).lower().replace(" ", "_")
    return clean if clean in STAFF_ROLES else "general_manager"


def validate_language(lang: str) -> str:
    """Validate language is one of the supported ones."""
    clean = sanitize_input(lang)
    for supported in SUPPORTED_LANGUAGES:
        if clean.lower() == supported.lower():
            return supported
    return "English"


def validate_attendance(val: str) -> int:
    """Validate expected attendance is within acceptable range."""
    try:
        n = int(val)
        if _ATTENDANCE_RANGE[0] <= n <= _ATTENDANCE_RANGE[1]:
            return n
    except (ValueError, TypeError):
        pass
    return 0


def validate_query_text(text: str) -> str:
    """Validate and sanitize free-text query for fan assistant."""
    clean = sanitize_input(text)
    if not clean or len(clean) > 500:
        return ""
    return clean


def validate_fan_category(cat: str) -> str:
    """Validate fan query category."""
    clean = sanitize_input(cat).lower().replace(" ", "_")
    return clean if clean in FAN_QUERY_CATEGORIES else "general"


def check_rate_limit(client_ip: str) -> bool:
    """Token-bucket rate limiter per client IP."""
    now = time.time()
    with _rate_lock:
        if client_ip not in _rate_tokens:
            _rate_tokens[client_ip] = {"count": 1, "window_start": now}
            return True
        bucket = _rate_tokens[client_ip]
        if now - bucket["window_start"] > RATE_LIMIT_WINDOW:
            bucket["count"] = 1
            bucket["window_start"] = now
            return True
        if bucket["count"] < RATE_LIMIT_MAX:
            bucket["count"] += 1
            return True
        return False


def _get_cache(key: str):
    """Retrieve cached API response if still valid."""
    with _cache_lock:
        if key in _api_cache:
            entry = _api_cache[key]
            if time.time() - entry["timestamp"] < CACHE_TTL:
                return entry["data"]
            else:
                del _api_cache[key]
    return None


def _set_cache(key: str, data):
    """Store API response in cache."""
    with _cache_lock:
        _api_cache[key] = {"data": data, "timestamp": time.time()}


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: WEATHER TELEMETRY — OPEN-METEO LIVE DATA
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_venue_weather(venue_id: str) -> dict:
    """Fetch live weather telemetry for a WC2026 venue from Open-Meteo API."""
    if venue_id not in WC2026_VENUES:
        return {}
    venue = WC2026_VENUES[venue_id]
    return fetch_weather(venue["lat"], venue["lon"])


def fetch_weather(lat: float, lon: float) -> dict:
    """Fetch live weather telemetry from Open-Meteo API."""
    cache_key = f"wx_{lat:.4f}_{lon:.4f}"
    cached = _get_cache(cache_key)
    if cached:
        return cached
    try:
        params = urllib.parse.urlencode({
            "latitude": lat,
            "longitude": lon,
            "current": (
                "temperature_2m,relative_humidity_2m,apparent_temperature,"
                "precipitation,rain,weather_code,wind_speed_10m,"
                "wind_gusts_10m,surface_pressure"
            ),
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,"
                "precipitation_sum,rain_sum,wind_speed_10m_max,"
                "wind_gusts_10m_max,precipitation_probability_max"
            ),
            "timezone": "auto",
            "forecast_days": 3
        })
        url = f"{OPEN_METEO_BASE}?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "StadiumOpsHub/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            _set_cache(cache_key, data)
            return data
    except Exception:
        return {}


def interpret_weather_code(code: int) -> str:
    """Map WMO weather code to human-readable description."""
    wmo = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Foggy", 48: "Depositing rime fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        56: "Light freezing drizzle", 57: "Dense freezing drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        66: "Light freezing rain", 67: "Heavy freezing rain",
        71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
        77: "Snow grains",
        80: "Slight rain showers", 81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers", 86: "Heavy snow showers",
        95: "Thunderstorm", 96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    return wmo.get(code, f"Weather code {code}")


def assess_weather_risk(weather_data: dict) -> str:
    """Assess operational risk level based on weather conditions."""
    if not weather_data or "current" not in weather_data:
        return "UNKNOWN"
    c = weather_data["current"]
    code = c.get("weather_code", 0)
    wind = c.get("wind_speed_10m", 0)
    gusts = c.get("wind_gusts_10m", 0)
    precip = c.get("precipitation", 0)
    temp = c.get("temperature_2m", 20)

    score = 0
    if code >= 95:
        score += 4
    elif code >= 80:
        score += 3
    elif code >= 61:
        score += 2
    elif code >= 45:
        score += 1
    if wind > 60 or gusts > 80:
        score += 3
    elif wind > 40 or gusts > 60:
        score += 2
    elif wind > 25:
        score += 1
    if precip > 20:
        score += 3
    elif precip > 10:
        score += 2
    elif precip > 2:
        score += 1
    if temp > 40 or temp < -10:
        score += 2
    elif temp > 35 or temp < 0:
        score += 1

    if score >= 8:
        return "EXTREME"
    elif score >= 6:
        return "SEVERE"
    elif score >= 4:
        return "HIGH"
    elif score >= 2:
        return "MODERATE"
    return "LOW"


def format_weather_summary(weather_data: dict, venue_name: str = "") -> str:
    """Create a rich text summary of current + forecast weather for AI prompts."""
    if not weather_data or "current" not in weather_data:
        return "Weather data unavailable — provide general operational guidance."

    c = weather_data["current"]
    risk = assess_weather_risk(weather_data)
    lines = [
        f"=== LIVE WEATHER TELEMETRY{' — ' + venue_name if venue_name else ''} ===",
        f"Temperature: {c.get('temperature_2m', 'N/A')}°C "
        f"(Feels like: {c.get('apparent_temperature', 'N/A')}°C)",
        f"Humidity: {c.get('relative_humidity_2m', 'N/A')}%",
        f"Precipitation: {c.get('precipitation', 0)} mm | Rain: {c.get('rain', 0)} mm",
        f"Wind: {c.get('wind_speed_10m', 'N/A')} km/h "
        f"(Gusts: {c.get('wind_gusts_10m', 'N/A')} km/h)",
        f"Pressure: {c.get('surface_pressure', 'N/A')} hPa",
        f"Condition: {interpret_weather_code(c.get('weather_code', -1))}",
        f"Operational Risk Level: {risk}",
    ]

    if "daily" in weather_data:
        d = weather_data["daily"]
        lines.append("\n=== 3-DAY FORECAST ===")
        dates = d.get("time", [])
        for i, date in enumerate(dates[:3]):
            code = d.get("weather_code", [0])[i] if i < len(d.get("weather_code", [])) else 0
            t_max = d.get("temperature_2m_max", ["?"])[i] if i < len(d.get("temperature_2m_max", [])) else "?"
            t_min = d.get("temperature_2m_min", ["?"])[i] if i < len(d.get("temperature_2m_min", [])) else "?"
            precip = d.get("precipitation_sum", [0])[i] if i < len(d.get("precipitation_sum", [])) else 0
            prob = d.get("precipitation_probability_max", [0])[i] if i < len(d.get("precipitation_probability_max", [])) else 0
            w_max = d.get("wind_speed_10m_max", [0])[i] if i < len(d.get("wind_speed_10m_max", [])) else 0
            lines.append(
                f"  {date}: {interpret_weather_code(code)} | "
                f"{t_min}–{t_max}°C | Rain: {precip}mm (Prob: {prob}%) | "
                f"Wind: {w_max} km/h"
            )

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: GENAI ENGINE — MULTI-FEATURE AI PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def _call_gemini(prompt: str) -> dict:
    """Call Google Gemini API via urllib."""
    url = f"{GEMINI_ENDPOINT}?key={GEMINI_API_KEY}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4096}
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "StadiumOpsHub/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            text = text.strip()
            if text.startswith("```"):
                text = re.sub(r'^```[a-zA-Z]*\n?', '', text)
                text = re.sub(r'\n?```$', '', text)
            return json.loads(text)
    except Exception as e:
        return {"error": f"Gemini API error: {str(e)}"}


def _call_openai_compatible(prompt: str, endpoint: str, api_key: str,
                            model: str) -> dict:
    """Call OpenAI-compatible APIs (Groq, OpenRouter) via urllib."""
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an expert FIFA World Cup 2026 stadium operations AI. Always respond with valid JSON only — no markdown, no extra text."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
        "response_format": {"type": "json_object"}
    }).encode("utf-8")
    req = urllib.request.Request(
        endpoint, data=payload, method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "StadiumOpsHub/1.0",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["choices"][0]["message"]["content"].strip()
            if text.startswith("```"):
                text = re.sub(r'^```[a-zA-Z]*\n?', '', text)
                text = re.sub(r'\n?```$', '', text)
            return json.loads(text)
    except Exception as e:
        return {"error": f"AI API error: {str(e)}"}


def call_ai(prompt: str) -> dict:
    """Route AI request to the configured provider."""
    provider = get_ai_provider()
    if provider == "none":
        return {"error": "No AI provider configured. Set GROQ_API_KEY, "
                         "GEMINI_API_KEY, or OPENROUTER_API_KEY"}
    elif provider == "groq":
        return _call_openai_compatible(prompt, GROQ_ENDPOINT, GROQ_API_KEY,
                                       "llama-3.3-70b-versatile")
    elif provider == "gemini":
        return _call_gemini(prompt)
    elif provider == "openrouter":
        return _call_openai_compatible(prompt, OPENROUTER_ENDPOINT,
                                       OPENROUTER_API_KEY,
                                       "meta-llama/llama-3.3-70b-instruct:free")
    return {"error": "Unknown AI provider"}


# ── Prompt Builders for Each Feature ──────────────────────────────────────────

def build_crowd_management_prompt(venue: dict, attendance: int,
                                  match_type: str, weather_summary: str) -> str:
    """Build AI prompt for crowd management analysis."""
    capacity = venue["capacity"]
    occupancy_pct = round((attendance / capacity) * 100, 1) if capacity > 0 else 0

    return f"""You are an expert crowd management and stadium operations advisor for FIFA World Cup 2026.

CONTEXT:
- Stadium: {venue['name']}, {venue['city']}, {venue['country']}
- Capacity: {capacity:,} seats
- Expected Attendance: {attendance:,} ({occupancy_pct}% capacity)
- Match Type: {match_type.replace('_', ' ').title()}
- Stadium Features: {', '.join(venue.get('features', []))}
- Current Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

{weather_summary}

TASK: Generate a comprehensive crowd management analysis as STRICT JSON.

CRITICAL RULES:
1. All recommendations MUST be weather-aware using the live data above.
2. Gate allocations MUST sum to 100%.
3. Personnel numbers MUST scale with attendance.
4. Provide specific, actionable recommendations — not generic advice.

OUTPUT FORMAT — respond with ONLY this JSON structure:
{{
  "crowd_analysis": {{
    "risk_level": "LOW|MODERATE|HIGH|SEVERE|EXTREME",
    "predicted_peak_arrival": "time window string",
    "predicted_peak_exit": "time window string",
    "density_zones": [
      {{"zone": "zone name", "expected_density": "LOW|MODERATE|HIGH|CRITICAL", "capacity": number, "recommendation": "specific action"}}
    ]
  }},
  "gate_strategy": [
    {{"gate": "gate identifier", "allocation_pct": number, "direction": "entry|exit|both", "reason": "weather/crowd based reason"}}
  ],
  "flow_recommendations": [
    {{"title": "recommendation title", "description": "detailed action", "priority": "CRITICAL|HIGH|MEDIUM|LOW", "department": "security|logistics|facilities"}}
  ],
  "staffing_plan": {{
    "security_personnel": number,
    "medical_staff": number,
    "volunteer_guides": number,
    "traffic_controllers": number
  }},
  "emergency_protocols": [
    {{"scenario": "scenario description", "action": "specific protocol", "personnel_needed": number, "evacuation_time_minutes": number}}
  ],
  "weather_adaptations": [
    {{"condition": "weather condition", "adaptation": "specific operational change", "urgency": "IMMEDIATE|PRE_EVENT|DURING_EVENT"}}
  ]
}}"""


def build_fan_assistant_prompt(venue: dict, query: str, language: str,
                               weather_summary: str) -> str:
    """Build AI prompt for multilingual fan assistant."""
    return f"""You are a friendly, knowledgeable multilingual fan assistant for FIFA World Cup 2026.

CONTEXT:
- Stadium: {venue['name']}, {venue['city']}, {venue['country']}
- Capacity: {venue['capacity']:,} seats
- Stadium Features: {', '.join(venue.get('features', []))}
- Response Language: {language}
- Current Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

{weather_summary}

FAN QUESTION: {query}

TASK: Provide a helpful, accurate response to the fan's question.

CRITICAL RULES:
1. Respond ENTIRELY in {language} (except JSON keys).
2. Be warm, helpful, and culturally sensitive.
3. Include practical details (locations, times, prices where relevant).
4. If weather affects the answer, mention it.
5. Always include a safety tip related to current conditions.

OUTPUT FORMAT — respond with ONLY this JSON structure:
{{
  "response": "main answer in {language}",
  "category": "NAVIGATION|FOOD_BEVERAGE|ACCESSIBILITY|TRANSPORT|SAFETY|TICKETS|MERCHANDISE|GENERAL",
  "related_tips": ["tip 1 in {language}", "tip 2 in {language}", "tip 3 in {language}"],
  "accessibility_note": "accessibility-related info if relevant, in {language}",
  "emergency_contacts": {{
    "stadium_security": "local emergency number",
    "medical": "local medical number",
    "general_emergency": "local emergency number"
  }},
  "weather_advisory": "current weather impact on the fan's activity, in {language}"
}}"""


def build_sustainability_prompt(venue: dict, attendance: int,
                                match_type: str, weather_summary: str) -> str:
    """Build AI prompt for sustainability analysis."""
    return f"""You are a sustainability and environmental expert for FIFA World Cup 2026 Green Initiative.

CONTEXT:
- Stadium: {venue['name']}, {venue['city']}, {venue['country']}
- Capacity: {venue['capacity']:,} seats
- Expected Attendance: {attendance:,}
- Match Type: {match_type.replace('_', ' ').title()}
- Stadium Features: {', '.join(venue.get('features', []))}
- Current Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

{weather_summary}

TASK: Generate a comprehensive sustainability analysis for this match day.

CRITICAL RULES:
1. Use realistic metrics based on industry data for stadium events.
2. Carbon estimates should be data-grounded (not random numbers).
3. Recommendations must be actionable and specific to this venue.
4. Weather data should inform energy/water recommendations.

OUTPUT FORMAT — respond with ONLY this JSON structure:
{{
  "carbon_metrics": {{
    "estimated_event_footprint_tonnes": number,
    "per_fan_kg": number,
    "breakdown": [
      {{"source": "source name", "percentage": number, "tonnes": number}}
    ]
  }},
  "waste_strategy": {{
    "estimated_waste_kg": number,
    "recycling_target_pct": number,
    "recycling_stations_needed": number,
    "composting_zones": number,
    "recommendations": ["specific waste recommendation"]
  }},
  "energy_optimization": [
    {{"system": "system name", "current_status": "description", "recommendation": "specific action", "savings_pct": number}}
  ],
  "water_conservation": [
    {{"area": "area name", "recommendation": "specific action", "savings_liters": number}}
  ],
  "transportation_emissions": {{
    "public_transit_pct_target": number,
    "carbon_offset_recommended_tonnes": number,
    "recommendations": ["transport recommendation"]
  }},
  "sustainability_score": {{
    "current": number,
    "target": number,
    "grade": "A|B|C|D|F"
  }}
}}"""


def build_ops_decision_prompt(venue: dict, staff_role: str, attendance: int,
                              match_type: str, weather_summary: str) -> str:
    """Build AI prompt for operational decision support."""
    return f"""You are an expert operational intelligence advisor for FIFA World Cup 2026 venue management.

CONTEXT:
- Stadium: {venue['name']}, {venue['city']}, {venue['country']}
- Capacity: {venue['capacity']:,} seats
- Expected Attendance: {attendance:,}
- Match Type: {match_type.replace('_', ' ').title()}
- Staff Role Requesting: {staff_role.replace('_', ' ').title()}
- Stadium Features: {', '.join(venue.get('features', []))}
- Current Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

{weather_summary}

TASK: Generate operational intelligence briefing for the {staff_role.replace('_', ' ')} team.

CRITICAL RULES:
1. Tailor ALL recommendations to the specific staff role: {staff_role}.
2. Use weather data to inform every operational decision.
3. Provide specific numbers, times, and locations — not vague advice.
4. Priority actions should be time-sequenced (pre-event → during → post-event).

OUTPUT FORMAT — respond with ONLY this JSON structure:
{{
  "briefing_title": "Operational Briefing for {staff_role.replace('_', ' ').title()}",
  "situation_assessment": "current operational assessment paragraph",
  "risk_matrix": [
    {{"risk": "risk description", "likelihood": "LOW|MEDIUM|HIGH", "impact": "LOW|MEDIUM|HIGH|CRITICAL", "mitigation": "specific action"}}
  ],
  "priority_actions": [
    {{"phase": "PRE_EVENT|DURING_EVENT|POST_EVENT", "action": "specific action", "urgency": "IMMEDIATE|HIGH|MEDIUM|LOW", "department": "department name", "personnel": number, "location": "specific location"}}
  ],
  "resource_allocation": [
    {{"resource": "resource type", "quantity": number, "location": "deployment location", "timing": "when to deploy"}}
  ],
  "communication_plan": [
    {{"channel": "communication channel", "audience": "target audience", "message_type": "type", "frequency": "how often"}}
  ],
  "weather_impact": {{
    "severity": "NONE|LOW|MODERATE|HIGH|SEVERE",
    "adaptations": ["specific weather adaptation"],
    "contingency": "contingency plan if conditions worsen"
  }},
  "kpis": [
    {{"metric": "KPI name", "target": "target value", "measurement": "how to measure"}}
  ]
}}"""


def build_transport_prompt(venue: dict, attendance: int, match_type: str,
                           weather_summary: str) -> str:
    """Build AI prompt for transportation optimization."""
    return f"""You are a transportation and logistics expert for FIFA World Cup 2026.

CONTEXT:
- Stadium: {venue['name']}, {venue['city']}, {venue['country']}
- Capacity: {venue['capacity']:,} seats
- Expected Attendance: {attendance:,}
- Match Type: {match_type.replace('_', ' ').title()}
- Stadium Features: {', '.join(venue.get('features', []))}
- Current Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

{weather_summary}

TASK: Generate a comprehensive transportation plan for this match day.

CRITICAL RULES:
1. Use realistic local transit data for {venue['city']}.
2. Account for weather impact on all transport modes.
3. Include accessibility transport options.
4. Provide specific timing recommendations.

OUTPUT FORMAT — respond with ONLY this JSON structure:
{{
  "transit_plan": [
    {{"mode": "transport mode", "route": "specific route/line", "capacity_per_hour": number, "recommended_timing": "time window", "weather_impact": "impact description"}}
  ],
  "parking_strategy": {{
    "total_spaces": number,
    "recommended_arrival": "time window",
    "overflow_plan": "overflow strategy",
    "lots": [
      {{"name": "lot name", "spaces": number, "distance_km": number, "shuttle": true}}
    ]
  }},
  "rideshare_zones": [
    {{"zone_name": "zone identifier", "location": "specific location", "capacity": number, "estimated_wait_minutes": number}}
  ],
  "accessibility_transport": [
    {{"service": "service name", "details": "specific details", "booking": "how to book", "cost": "cost info"}}
  ],
  "pedestrian_routes": [
    {{"route": "route description", "distance_km": number, "estimated_time_minutes": number, "accessibility": "fully_accessible|partial|stairs_only"}}
  ],
  "traffic_management": [
    {{"action": "traffic action", "location": "where", "timing": "when", "personnel": number}}
  ],
  "post_match_dispersal": {{
    "estimated_dispersal_time_minutes": number,
    "staggered_exit_plan": "plan description",
    "holding_areas": ["area description"]
  }}
}}"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5: HTTP SERVER & REQUEST HANDLER
# ═══════════════════════════════════════════════════════════════════════════════

def _security_headers() -> dict:
    """Return standard security response headers."""
    return {
        "Content-Security-Policy": "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                                   "connect-src 'self'; frame-ancestors 'none';",
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }


class StadiumOpsHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for the Smart Stadium Operations Hub."""

    def log_message(self, format, *args):
        """Structured logging with timestamp."""
        sys.stderr.write(f"[{datetime.now(timezone.utc).isoformat()}] "
                         f"{self.client_address[0]} - {format % args}\n")

    def _send_response(self, code: int, content_type: str, body: bytes):
        """Send HTTP response with security headers."""
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for header, value in _security_headers().items():
            self.send_header(header, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, code: int, data: dict):
        """Send JSON response."""
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self._send_response(code, "application/json; charset=utf-8", body)

    def _read_post_body(self) -> dict:
        """Read and parse POST body with size limit."""
        length = int(self.headers.get("Content-Length", 0))
        if length > _MAX_POST_BODY:
            return None
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def do_GET(self):
        """Handle GET requests."""
        path = self.path.split("?")[0]

        if path == "/" or path == "":
            self._serve_dashboard()
        elif path == "/api/venues":
            self._handle_get_venues()
        elif path.startswith("/api/weather/"):
            venue_id = path.split("/")[-1]
            self._handle_get_weather(venue_id)
        elif path == "/api/health":
            self._send_json(200, {
                "status": "healthy",
                "ai_provider": get_ai_provider(),
                "venues": len(WC2026_VENUES),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        """Handle POST requests."""
        client_ip = self.client_address[0]
        if not check_rate_limit(client_ip):
            self._send_json(429, {"error": "Rate limit exceeded. Try again later."})
            return

        body = self._read_post_body()
        if body is None:
            self._send_json(400, {"error": "Invalid or oversized request body."})
            return

        path = self.path.split("?")[0]
        route_map = {
            "/api/crowd": self._handle_crowd_management,
            "/api/assist": self._handle_fan_assistant,
            "/api/sustainability": self._handle_sustainability,
            "/api/ops": self._handle_ops_decision,
            "/api/transport": self._handle_transport,
        }

        handler = route_map.get(path)
        if handler:
            handler(body)
        else:
            self._send_json(404, {"error": "Endpoint not found"})

    # ── GET Handlers ──────────────────────────────────────────────────────────

    def _handle_get_venues(self):
        """Return list of all WC2026 venues."""
        venues = []
        for vid, v in WC2026_VENUES.items():
            venues.append({
                "id": vid,
                "name": v["name"],
                "city": v["city"],
                "country": v["country"],
                "capacity": v["capacity"],
            })
        self._send_json(200, {"venues": venues})

    def _handle_get_weather(self, venue_id: str):
        """Return live weather for a specific venue."""
        vid = validate_venue_id(venue_id)
        if not vid:
            self._send_json(400, {"error": "Invalid venue ID"})
            return
        venue = WC2026_VENUES[vid]
        weather = fetch_venue_weather(vid)
        if not weather:
            self._send_json(502, {"error": "Weather service unavailable"})
            return
        risk = assess_weather_risk(weather)
        self._send_json(200, {
            "venue": venue["name"],
            "city": venue["city"],
            "weather": weather.get("current", {}),
            "forecast": weather.get("daily", {}),
            "risk_level": risk,
            "condition": interpret_weather_code(
                weather.get("current", {}).get("weather_code", -1)
            ),
        })

    # ── POST Handlers ─────────────────────────────────────────────────────────

    def _handle_crowd_management(self, body: dict):
        """AI crowd management analysis."""
        vid = validate_venue_id(body.get("venue_id", ""))
        attendance = validate_attendance(str(body.get("attendance", 0)))
        match_type = validate_match_type(body.get("match_type", "group_stage"))

        if not vid:
            self._send_json(400, {"error": "Invalid venue. Select a WC2026 stadium."})
            return
        if not attendance:
            self._send_json(400, {"error": "Invalid attendance (1,000–100,000)."})
            return

        venue = WC2026_VENUES[vid]
        weather = fetch_venue_weather(vid)
        weather_summary = format_weather_summary(weather, venue["name"])
        prompt = build_crowd_management_prompt(venue, attendance, match_type,
                                               weather_summary)
        result = call_ai(prompt)
        result["venue"] = venue["name"]
        result["weather_risk"] = assess_weather_risk(weather)
        result["live_weather"] = weather.get("current", {})
        self._send_json(200, result)

    def _handle_fan_assistant(self, body: dict):
        """Multilingual fan assistant."""
        vid = validate_venue_id(body.get("venue_id", ""))
        query = validate_query_text(body.get("query", ""))
        language = validate_language(body.get("language", "English"))

        if not vid:
            self._send_json(400, {"error": "Invalid venue. Select a WC2026 stadium."})
            return
        if not query:
            self._send_json(400, {"error": "Please enter a question (max 500 chars)."})
            return

        venue = WC2026_VENUES[vid]
        weather = fetch_venue_weather(vid)
        weather_summary = format_weather_summary(weather, venue["name"])
        prompt = build_fan_assistant_prompt(venue, query, language, weather_summary)
        result = call_ai(prompt)
        result["venue"] = venue["name"]
        result["language_used"] = language
        self._send_json(200, result)

    def _handle_sustainability(self, body: dict):
        """Sustainability analysis."""
        vid = validate_venue_id(body.get("venue_id", ""))
        attendance = validate_attendance(str(body.get("attendance", 0)))
        match_type = validate_match_type(body.get("match_type", "group_stage"))

        if not vid:
            self._send_json(400, {"error": "Invalid venue. Select a WC2026 stadium."})
            return
        if not attendance:
            self._send_json(400, {"error": "Invalid attendance (1,000–100,000)."})
            return

        venue = WC2026_VENUES[vid]
        weather = fetch_venue_weather(vid)
        weather_summary = format_weather_summary(weather, venue["name"])
        prompt = build_sustainability_prompt(venue, attendance, match_type,
                                             weather_summary)
        result = call_ai(prompt)
        result["venue"] = venue["name"]
        self._send_json(200, result)

    def _handle_ops_decision(self, body: dict):
        """Operational decision support."""
        vid = validate_venue_id(body.get("venue_id", ""))
        staff_role = validate_staff_role(body.get("staff_role", "general_manager"))
        attendance = validate_attendance(str(body.get("attendance", 0)))
        match_type = validate_match_type(body.get("match_type", "group_stage"))

        if not vid:
            self._send_json(400, {"error": "Invalid venue. Select a WC2026 stadium."})
            return
        if not attendance:
            self._send_json(400, {"error": "Invalid attendance (1,000–100,000)."})
            return

        venue = WC2026_VENUES[vid]
        weather = fetch_venue_weather(vid)
        weather_summary = format_weather_summary(weather, venue["name"])
        prompt = build_ops_decision_prompt(venue, staff_role, attendance,
                                           match_type, weather_summary)
        result = call_ai(prompt)
        result["venue"] = venue["name"]
        result["role"] = staff_role
        result["weather_risk"] = assess_weather_risk(weather)
        self._send_json(200, result)

    def _handle_transport(self, body: dict):
        """Transportation optimization."""
        vid = validate_venue_id(body.get("venue_id", ""))
        attendance = validate_attendance(str(body.get("attendance", 0)))
        match_type = validate_match_type(body.get("match_type", "group_stage"))

        if not vid:
            self._send_json(400, {"error": "Invalid venue. Select a WC2026 stadium."})
            return
        if not attendance:
            self._send_json(400, {"error": "Invalid attendance (1,000–100,000)."})
            return

        venue = WC2026_VENUES[vid]
        weather = fetch_venue_weather(vid)
        weather_summary = format_weather_summary(weather, venue["name"])
        prompt = build_transport_prompt(venue, attendance, match_type,
                                        weather_summary)
        result = call_ai(prompt)
        result["venue"] = venue["name"]
        result["weather_risk"] = assess_weather_risk(weather)
        self._send_json(200, result)

    # ── Dashboard HTML ────────────────────────────────────────────────────────

    def _serve_dashboard(self):
        """Serve the main dashboard HTML page."""
        html_content = _build_dashboard_html()
        self._send_response(200, "text/html; charset=utf-8",
                            html_content.encode("utf-8"))


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6: FRONTEND — EMBEDDED HTML/CSS/JS DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

def _build_dashboard_html() -> str:
    """Build the complete dashboard HTML with embedded CSS and JS."""
    provider = get_ai_provider()
    provider_label = {
        "groq": "Groq (Llama 3.3 70B)",
        "gemini": "Google Gemini 2.0 Flash",
        "openrouter": "OpenRouter (Llama 3.3 70B)",
        "none": "⚠️ No AI Key Set"
    }.get(provider, "Unknown")

    venues_json = json.dumps([
        {"id": vid, "name": v["name"], "city": v["city"],
         "country": v["country"], "capacity": v["capacity"]}
        for vid, v in WC2026_VENUES.items()
    ])

    return f'''<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="AI-powered Smart Stadium Operations Hub for FIFA World Cup 2026. Real-time crowd management, multilingual fan assistance, sustainability monitoring, and operational intelligence.">
<meta name="theme-color" content="#0a0f1c">
<title>🏟️ Smart Stadium Operations Hub — FIFA World Cup 2026</title>
<style>
/* ═══════════════════════════════════════════════════════════════════════════
   DESIGN SYSTEM — Dark Theme, WCAG AAA (≥7:1 contrast)
   ═══════════════════════════════════════════════════════════════════════════ */
:root {{
  --bg-primary: #0a0f1c;
  --bg-secondary: #111827;
  --bg-card: #1a2236;
  --bg-card-hover: #1f2b42;
  --bg-glass: rgba(26, 34, 54, 0.85);
  --text-primary: #f0f4ff;
  --text-secondary: #c8d3e8;
  --text-muted: #8b9dc3;
  --accent-blue: #3b82f6;
  --accent-purple: #8b5cf6;
  --accent-green: #10b981;
  --accent-amber: #f59e0b;
  --accent-red: #ef4444;
  --accent-cyan: #06b6d4;
  --gradient-primary: linear-gradient(135deg, #3b82f6, #8b5cf6);
  --gradient-hero: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
  --border-color: rgba(139, 92, 246, 0.2);
  --border-glow: rgba(59, 130, 246, 0.3);
  --shadow-card: 0 4px 24px rgba(0,0,0,0.4);
  --shadow-glow: 0 0 30px rgba(59, 130, 246, 0.15);
  --radius: 12px;
  --radius-lg: 16px;
  --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
}}
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ scroll-behavior: smooth; }}
body {{
  font-family: var(--font-sans);
  background: var(--bg-primary);
  color: var(--text-primary);
  line-height: 1.6;
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}}
/* Skip Link */
.skip-link {{
  position: absolute; top: -100%; left: 0;
  background: var(--accent-blue); color: #fff;
  padding: 8px 16px; z-index: 10000;
  font-weight: 600; text-decoration: none;
  border-radius: 0 0 var(--radius) 0;
}}
.skip-link:focus {{ top: 0; }}
/* Focus indicator */
*:focus-visible {{
  outline: 3px solid var(--accent-blue);
  outline-offset: 2px;
}}
/* ── Header ── */
.site-header {{
  background: var(--gradient-hero);
  border-bottom: 1px solid var(--border-color);
  padding: 0;
  position: sticky; top: 0; z-index: 100;
  backdrop-filter: blur(20px);
}}
.header-inner {{
  max-width: 1400px; margin: 0 auto;
  padding: 16px 24px;
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 12px;
}}
.header-brand {{
  display: flex; align-items: center; gap: 12px;
}}
.header-brand h1 {{
  font-size: 1.35rem; font-weight: 800;
  background: var(--gradient-primary);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}}
.header-brand .subtitle {{
  font-size: 0.75rem; color: var(--text-muted);
  font-weight: 500; letter-spacing: 0.5px;
}}
.header-meta {{
  display: flex; align-items: center; gap: 16px;
  font-size: 0.8rem; color: var(--text-muted);
}}
.provider-badge {{
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-green);
  padding: 4px 12px; border-radius: 20px;
  font-weight: 600; font-size: 0.75rem;
  border: 1px solid rgba(16, 185, 129, 0.3);
}}
.provider-badge.no-key {{
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-red);
  border-color: rgba(239, 68, 68, 0.3);
}}
/* ── Navigation Tabs ── */
.nav-tabs {{
  display: flex; gap: 0; overflow-x: auto;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  padding: 0 24px;
  max-width: 100%;
}}
.nav-tab {{
  padding: 12px 20px; cursor: pointer;
  font-size: 0.85rem; font-weight: 600;
  color: var(--text-muted);
  border: none; background: none;
  border-bottom: 3px solid transparent;
  transition: var(--transition);
  white-space: nowrap;
  display: flex; align-items: center; gap: 6px;
}}
.nav-tab:hover {{ color: var(--text-primary); background: rgba(59,130,246,0.05); }}
.nav-tab.active {{
  color: var(--accent-blue);
  border-bottom-color: var(--accent-blue);
  background: rgba(59,130,246,0.08);
}}
/* ── Main Layout ── */
main {{
  max-width: 1400px; margin: 0 auto;
  padding: 24px;
}}
.tab-content {{ display: none; animation: fadeIn 0.4s ease; }}
.tab-content.active {{ display: block; }}
@keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: translateY(0); }} }}
/* ── Cards ── */
.card {{
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: var(--shadow-card);
  transition: var(--transition);
}}
.card:hover {{
  border-color: var(--border-glow);
  box-shadow: var(--shadow-glow);
}}
.card-header {{
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 16px;
}}
.card-header h2, .card-header h3 {{
  font-size: 1.1rem; font-weight: 700;
  color: var(--text-primary);
}}
.card-header .icon {{
  font-size: 1.3rem;
}}
/* ── Forms ── */
.form-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}}
.form-group {{
  display: flex; flex-direction: column; gap: 6px;
}}
.form-group label {{
  font-size: 0.82rem; font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 0.3px;
}}
.form-group select, .form-group input, .form-group textarea {{
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  padding: 10px 14px;
  color: var(--text-primary);
  font-size: 0.9rem;
  font-family: var(--font-sans);
  transition: var(--transition);
}}
.form-group select:focus, .form-group input:focus, .form-group textarea:focus {{
  border-color: var(--accent-blue);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}}
.form-group textarea {{ resize: vertical; min-height: 80px; }}
.btn {{
  display: inline-flex; align-items: center; gap: 8px;
  padding: 12px 24px;
  border: none; border-radius: var(--radius);
  font-size: 0.9rem; font-weight: 700;
  cursor: pointer; transition: var(--transition);
  font-family: var(--font-sans);
}}
.btn-primary {{
  background: var(--gradient-primary);
  color: #fff;
  box-shadow: 0 4px 14px rgba(59, 130, 246, 0.35);
}}
.btn-primary:hover {{
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.45);
}}
.btn-primary:disabled {{
  opacity: 0.6; cursor: not-allowed; transform: none;
}}
/* ── Weather Widget ── */
.weather-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px; margin-top: 12px;
}}
.weather-metric {{
  background: var(--bg-secondary);
  border-radius: var(--radius);
  padding: 14px;
  text-align: center;
  border: 1px solid var(--border-color);
}}
.weather-metric .value {{
  font-size: 1.5rem; font-weight: 800;
  color: var(--accent-cyan);
  font-family: var(--font-mono);
}}
.weather-metric .label {{
  font-size: 0.72rem; color: var(--text-muted);
  margin-top: 4px; text-transform: uppercase;
  letter-spacing: 0.5px;
}}
/* ── Risk Badge ── */
.risk-badge {{
  display: inline-flex; padding: 4px 12px;
  border-radius: 20px; font-size: 0.75rem;
  font-weight: 700; letter-spacing: 0.5px;
}}
.risk-LOW {{ background: rgba(16,185,129,0.15); color: var(--accent-green); border: 1px solid rgba(16,185,129,0.3); }}
.risk-MODERATE {{ background: rgba(6,182,212,0.15); color: var(--accent-cyan); border: 1px solid rgba(6,182,212,0.3); }}
.risk-HIGH {{ background: rgba(245,158,11,0.15); color: var(--accent-amber); border: 1px solid rgba(245,158,11,0.3); }}
.risk-SEVERE {{ background: rgba(239,68,68,0.15); color: var(--accent-red); border: 1px solid rgba(239,68,68,0.3); }}
.risk-EXTREME {{ background: rgba(239,68,68,0.25); color: #ff6b6b; border: 1px solid rgba(239,68,68,0.5); }}
.risk-UNKNOWN {{ background: rgba(139,157,195,0.15); color: var(--text-muted); border: 1px solid rgba(139,157,195,0.3); }}
/* ── Results ── */
.results-container {{
  margin-top: 20px;
  animation: fadeIn 0.5s ease;
}}
.result-section {{
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  padding: 18px;
  margin-bottom: 14px;
}}
.result-section h4 {{
  font-size: 0.95rem; font-weight: 700;
  color: var(--accent-blue); margin-bottom: 10px;
  display: flex; align-items: center; gap: 8px;
}}
.result-item {{
  padding: 10px 14px;
  border-left: 3px solid var(--accent-purple);
  margin-bottom: 8px;
  background: rgba(139, 92, 246, 0.05);
  border-radius: 0 var(--radius) var(--radius) 0;
}}
.result-item .title {{ font-weight: 600; color: var(--text-primary); font-size: 0.88rem; }}
.result-item .desc {{ color: var(--text-secondary); font-size: 0.82rem; margin-top: 4px; }}
.result-item .meta {{ color: var(--text-muted); font-size: 0.75rem; margin-top: 4px; }}
.priority-CRITICAL {{ border-left-color: var(--accent-red); background: rgba(239,68,68,0.05); }}
.priority-HIGH {{ border-left-color: var(--accent-amber); background: rgba(245,158,11,0.05); }}
.priority-MEDIUM {{ border-left-color: var(--accent-blue); background: rgba(59,130,246,0.05); }}
.priority-LOW {{ border-left-color: var(--accent-green); background: rgba(16,185,129,0.05); }}
.priority-IMMEDIATE {{ border-left-color: var(--accent-red); background: rgba(239,68,68,0.08); }}
/* ── Loading ── */
.spinner {{
  display: none; text-align: center; padding: 40px;
}}
.spinner.active {{ display: block; }}
.spinner::after {{
  content: ''; display: inline-block;
  width: 40px; height: 40px;
  border: 4px solid var(--border-color);
  border-top-color: var(--accent-blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}
.spinner-text {{
  color: var(--text-muted); font-size: 0.85rem;
  margin-top: 12px;
}}
/* ── Error ── */
.error-box {{
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: var(--radius);
  padding: 14px 18px;
  color: #ff8a8a;
  font-size: 0.88rem;
  display: none;
}}
.error-box.active {{ display: block; }}
/* ── Table ── */
.data-table {{
  width: 100%; border-collapse: separate;
  border-spacing: 0; font-size: 0.85rem;
}}
.data-table th {{
  background: var(--bg-secondary);
  color: var(--text-secondary);
  padding: 10px 14px;
  text-align: left;
  font-weight: 600;
  border-bottom: 2px solid var(--border-color);
}}
.data-table td {{
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-primary);
}}
.data-table tr:hover td {{ background: rgba(59,130,246,0.04); }}
/* ── Venue Cards Grid ── */
.venue-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px; margin-bottom: 24px;
}}
.venue-card {{
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  padding: 16px; cursor: pointer;
  transition: var(--transition);
}}
.venue-card:hover, .venue-card.selected {{
  border-color: var(--accent-blue);
  box-shadow: var(--shadow-glow);
  transform: translateY(-2px);
}}
.venue-card.selected {{
  background: rgba(59,130,246,0.08);
}}
.venue-card .vname {{ font-weight: 700; font-size: 0.95rem; color: var(--text-primary); }}
.venue-card .vcity {{ font-size: 0.8rem; color: var(--text-muted); margin-top: 2px; }}
.venue-card .vcap {{ font-size: 0.78rem; color: var(--accent-cyan); margin-top: 4px; font-family: var(--font-mono); }}
/* ── Chat-like Fan Assistant ── */
.chat-container {{
  max-height: 500px; overflow-y: auto;
  padding: 16px; background: var(--bg-secondary);
  border-radius: var(--radius);
  border: 1px solid var(--border-color);
}}
.chat-bubble {{
  max-width: 85%; padding: 14px 18px;
  border-radius: 16px; margin-bottom: 12px;
  font-size: 0.88rem; line-height: 1.5;
}}
.chat-bubble.user {{
  background: var(--accent-blue);
  color: #fff; margin-left: auto;
  border-bottom-right-radius: 4px;
}}
.chat-bubble.ai {{
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-bottom-left-radius: 4px;
}}
/* ── Footer ── */
.site-footer {{
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
  padding: 20px 24px;
  text-align: center;
  color: var(--text-muted);
  font-size: 0.78rem;
}}
/* ── Responsive ── */
@media (max-width: 768px) {{
  .header-inner {{ flex-direction: column; text-align: center; }}
  .form-grid {{ grid-template-columns: 1fr; }}
  .venue-grid {{ grid-template-columns: 1fr; }}
  .weather-grid {{ grid-template-columns: repeat(2, 1fr); }}
  .nav-tabs {{ padding: 0 8px; }}
  .nav-tab {{ padding: 10px 12px; font-size: 0.78rem; }}
  main {{ padding: 16px; }}
}}
/* ── Print ── */
@media print {{
  .site-header, .nav-tabs, .btn, .form-group, .site-footer {{ display: none !important; }}
  body {{ background: #fff; color: #000; }}
  .card {{ border: 1px solid #ccc; box-shadow: none; }}
}}
/* ── Screen Reader Only ── */
.sr-only {{
  position: absolute; width: 1px; height: 1px;
  padding: 0; margin: -1px; overflow: hidden;
  clip: rect(0,0,0,0); white-space: nowrap; border: 0;
}}
/* ── Metric Cards ── */
.metric-row {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px; margin-bottom: 16px;
}}
.metric-card {{
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  padding: 16px; text-align: center;
}}
.metric-card .metric-value {{
  font-size: 1.8rem; font-weight: 800;
  font-family: var(--font-mono);
  background: var(--gradient-primary);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}}
.metric-card .metric-label {{
  font-size: 0.72rem; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px;
}}
</style>
</head>
<body>
<a href="#main-content" class="skip-link" id="skip-link">Skip to main content</a>

<header class="site-header" role="banner">
  <div class="header-inner">
    <div class="header-brand">
      <div>
        <h1>🏟️ Smart Stadium Operations Hub</h1>
        <div class="subtitle">FIFA World Cup 2026 — AI-Powered Operations Intelligence</div>
      </div>
    </div>
    <div class="header-meta">
      <span class="provider-badge {"no-key" if provider == "none" else ""}" aria-label="AI Provider: {html.escape(provider_label)}">
        🤖 {html.escape(provider_label)}
      </span>
      <span id="clock" aria-live="polite"></span>
    </div>
  </div>
</header>

<nav class="nav-tabs" role="tablist" aria-label="Main navigation">
  <button class="nav-tab active" role="tab" aria-selected="true" aria-controls="tab-dashboard" id="btn-dashboard" onclick="switchTab('dashboard')">📊 Dashboard</button>
  <button class="nav-tab" role="tab" aria-selected="false" aria-controls="tab-crowd" id="btn-crowd" onclick="switchTab('crowd')">👥 Crowd Mgmt</button>
  <button class="nav-tab" role="tab" aria-selected="false" aria-controls="tab-assist" id="btn-assist" onclick="switchTab('assist')">💬 Fan Assistant</button>
  <button class="nav-tab" role="tab" aria-selected="false" aria-controls="tab-sustainability" id="btn-sustainability" onclick="switchTab('sustainability')">🌱 Sustainability</button>
  <button class="nav-tab" role="tab" aria-selected="false" aria-controls="tab-ops" id="btn-ops" onclick="switchTab('ops')">⚙️ Ops Intelligence</button>
  <button class="nav-tab" role="tab" aria-selected="false" aria-controls="tab-transport" id="btn-transport" onclick="switchTab('transport')">🚌 Transport</button>
</nav>

<main id="main-content" role="main">

  <!-- ═══ DASHBOARD TAB ═══ -->
  <div class="tab-content active" id="tab-dashboard" role="tabpanel" aria-labelledby="btn-dashboard">
    <div class="card">
      <div class="card-header"><span class="icon">🌍</span><h2>FIFA World Cup 2026 Venues — Live Weather</h2></div>
      <p style="color:var(--text-secondary);font-size:0.85rem;margin-bottom:16px;">Select a venue to view live weather conditions. All data is fetched in real-time from Open-Meteo API.</p>
      <div class="venue-grid" id="venue-grid" role="listbox" aria-label="Select a venue"></div>
    </div>
    <div class="card" id="weather-card" style="display:none;">
      <div class="card-header"><span class="icon">🌤️</span><h3 id="weather-venue-name">Venue Weather</h3><span class="risk-badge risk-UNKNOWN" id="weather-risk-badge">—</span></div>
      <div class="weather-grid" id="weather-details"></div>
      <div id="forecast-section" style="margin-top:16px;"></div>
    </div>
  </div>

  <!-- ═══ CROWD MANAGEMENT TAB ═══ -->
  <div class="tab-content" id="tab-crowd" role="tabpanel" aria-labelledby="btn-crowd">
    <div class="card">
      <div class="card-header"><span class="icon">👥</span><h2>AI Crowd Management Advisor</h2></div>
      <p style="color:var(--text-secondary);font-size:0.85rem;margin-bottom:16px;">Get AI-powered crowd flow strategies, gate assignments, and emergency protocols based on real-time weather and venue data.</p>
      <div class="form-grid">
        <div class="form-group">
          <label for="crowd-venue" id="lbl-crowd-venue">Stadium</label>
          <select id="crowd-venue" aria-labelledby="lbl-crowd-venue" aria-required="true"></select>
        </div>
        <div class="form-group">
          <label for="crowd-attendance" id="lbl-crowd-att">Expected Attendance</label>
          <input type="number" id="crowd-attendance" min="1000" max="100000" value="50000" aria-labelledby="lbl-crowd-att" aria-required="true">
        </div>
        <div class="form-group">
          <label for="crowd-match" id="lbl-crowd-match">Match Type</label>
          <select id="crowd-match" aria-labelledby="lbl-crowd-match">
            <option value="group_stage">Group Stage</option>
            <option value="round_of_32">Round of 32</option>
            <option value="round_of_16">Round of 16</option>
            <option value="quarter_final">Quarter Final</option>
            <option value="semi_final">Semi Final</option>
            <option value="third_place">Third Place</option>
            <option value="final">Final</option>
          </select>
        </div>
      </div>
      <button class="btn btn-primary" id="btn-crowd-submit" onclick="submitCrowd()" aria-label="Analyze crowd management">🔍 Analyze Crowd Flow</button>
      <div class="spinner" id="crowd-spinner" role="status"><span class="sr-only">Analyzing...</span><div class="spinner-text">AI is analyzing crowd dynamics...</div></div>
      <div class="error-box" id="crowd-error" role="alert"></div>
      <div class="results-container" id="crowd-results"></div>
    </div>
  </div>

  <!-- ═══ FAN ASSISTANT TAB ═══ -->
  <div class="tab-content" id="tab-assist" role="tabpanel" aria-labelledby="btn-assist">
    <div class="card">
      <div class="card-header"><span class="icon">💬</span><h2>Multilingual Fan Assistant</h2></div>
      <p style="color:var(--text-secondary);font-size:0.85rem;margin-bottom:16px;">Ask any question about the stadium — directions, food, accessibility, transport. Get AI responses in 12+ languages.</p>
      <div class="form-grid">
        <div class="form-group">
          <label for="assist-venue" id="lbl-assist-venue">Stadium</label>
          <select id="assist-venue" aria-labelledby="lbl-assist-venue" aria-required="true"></select>
        </div>
        <div class="form-group">
          <label for="assist-lang" id="lbl-assist-lang">Language</label>
          <select id="assist-lang" aria-labelledby="lbl-assist-lang">
            <option value="English">English</option>
            <option value="Spanish">Español</option>
            <option value="French">Français</option>
            <option value="Portuguese">Português</option>
            <option value="Arabic">العربية</option>
            <option value="German">Deutsch</option>
            <option value="Japanese">日本語</option>
            <option value="Korean">한국어</option>
            <option value="Chinese">中文</option>
            <option value="Hindi">हिन्दी</option>
            <option value="Italian">Italiano</option>
            <option value="Dutch">Nederlands</option>
          </select>
        </div>
      </div>
      <div class="form-group" style="margin-bottom:16px;">
        <label for="assist-query" id="lbl-assist-query">Your Question</label>
        <textarea id="assist-query" placeholder="e.g., Where can I find wheelchair accessible seating?" maxlength="500" aria-labelledby="lbl-assist-query" aria-required="true" aria-describedby="assist-help"></textarea>
        <span id="assist-help" class="sr-only">Type your question about the stadium, up to 500 characters</span>
      </div>
      <button class="btn btn-primary" id="btn-assist-submit" onclick="submitAssist()" aria-label="Ask fan assistant">💬 Ask Assistant</button>
      <div class="spinner" id="assist-spinner" role="status"><span class="sr-only">Thinking...</span><div class="spinner-text">AI assistant is composing a response...</div></div>
      <div class="error-box" id="assist-error" role="alert"></div>
      <div id="assist-chat" style="margin-top:16px;"></div>
    </div>
  </div>

  <!-- ═══ SUSTAINABILITY TAB ═══ -->
  <div class="tab-content" id="tab-sustainability" role="tabpanel" aria-labelledby="btn-sustainability">
    <div class="card">
      <div class="card-header"><span class="icon">🌱</span><h2>Sustainability Monitor</h2></div>
      <p style="color:var(--text-secondary);font-size:0.85rem;margin-bottom:16px;">AI-driven sustainability analysis — carbon footprint, waste strategy, energy optimization, and water conservation.</p>
      <div class="form-grid">
        <div class="form-group">
          <label for="sust-venue" id="lbl-sust-venue">Stadium</label>
          <select id="sust-venue" aria-labelledby="lbl-sust-venue" aria-required="true"></select>
        </div>
        <div class="form-group">
          <label for="sust-attendance" id="lbl-sust-att">Expected Attendance</label>
          <input type="number" id="sust-attendance" min="1000" max="100000" value="50000" aria-labelledby="lbl-sust-att" aria-required="true">
        </div>
        <div class="form-group">
          <label for="sust-match" id="lbl-sust-match">Match Type</label>
          <select id="sust-match" aria-labelledby="lbl-sust-match">
            <option value="group_stage">Group Stage</option>
            <option value="round_of_16">Round of 16</option>
            <option value="quarter_final">Quarter Final</option>
            <option value="semi_final">Semi Final</option>
            <option value="final">Final</option>
          </select>
        </div>
      </div>
      <button class="btn btn-primary" id="btn-sust-submit" onclick="submitSustainability()" aria-label="Analyze sustainability">🌱 Analyze Sustainability</button>
      <div class="spinner" id="sust-spinner" role="status"><span class="sr-only">Analyzing...</span><div class="spinner-text">AI is computing sustainability metrics...</div></div>
      <div class="error-box" id="sust-error" role="alert"></div>
      <div class="results-container" id="sust-results"></div>
    </div>
  </div>

  <!-- ═══ OPS INTELLIGENCE TAB ═══ -->
  <div class="tab-content" id="tab-ops" role="tabpanel" aria-labelledby="btn-ops">
    <div class="card">
      <div class="card-header"><span class="icon">⚙️</span><h2>Operational Decision Support</h2></div>
      <p style="color:var(--text-secondary);font-size:0.85rem;margin-bottom:16px;">AI-generated operational briefings tailored to your role — security, medical, logistics, hospitality, or general management.</p>
      <div class="form-grid">
        <div class="form-group">
          <label for="ops-venue" id="lbl-ops-venue">Stadium</label>
          <select id="ops-venue" aria-labelledby="lbl-ops-venue" aria-required="true"></select>
        </div>
        <div class="form-group">
          <label for="ops-role" id="lbl-ops-role">Staff Role</label>
          <select id="ops-role" aria-labelledby="lbl-ops-role">
            <option value="security">Security</option>
            <option value="medical">Medical</option>
            <option value="logistics">Logistics</option>
            <option value="hospitality">Hospitality</option>
            <option value="volunteer_coordinator">Volunteer Coordinator</option>
            <option value="facilities">Facilities</option>
            <option value="general_manager">General Manager</option>
          </select>
        </div>
        <div class="form-group">
          <label for="ops-attendance" id="lbl-ops-att">Expected Attendance</label>
          <input type="number" id="ops-attendance" min="1000" max="100000" value="50000" aria-labelledby="lbl-ops-att" aria-required="true">
        </div>
        <div class="form-group">
          <label for="ops-match" id="lbl-ops-match">Match Type</label>
          <select id="ops-match" aria-labelledby="lbl-ops-match">
            <option value="group_stage">Group Stage</option>
            <option value="round_of_16">Round of 16</option>
            <option value="quarter_final">Quarter Final</option>
            <option value="semi_final">Semi Final</option>
            <option value="final">Final</option>
          </select>
        </div>
      </div>
      <button class="btn btn-primary" id="btn-ops-submit" onclick="submitOps()" aria-label="Generate ops briefing">⚙️ Generate Briefing</button>
      <div class="spinner" id="ops-spinner" role="status"><span class="sr-only">Generating...</span><div class="spinner-text">AI is preparing operational briefing...</div></div>
      <div class="error-box" id="ops-error" role="alert"></div>
      <div class="results-container" id="ops-results"></div>
    </div>
  </div>

  <!-- ═══ TRANSPORT TAB ═══ -->
  <div class="tab-content" id="tab-transport" role="tabpanel" aria-labelledby="btn-transport">
    <div class="card">
      <div class="card-header"><span class="icon">🚌</span><h2>Transportation Optimizer</h2></div>
      <p style="color:var(--text-secondary);font-size:0.85rem;margin-bottom:16px;">AI-powered transit plans, parking strategies, rideshare zones, and accessible transport options.</p>
      <div class="form-grid">
        <div class="form-group">
          <label for="trans-venue" id="lbl-trans-venue">Stadium</label>
          <select id="trans-venue" aria-labelledby="lbl-trans-venue" aria-required="true"></select>
        </div>
        <div class="form-group">
          <label for="trans-attendance" id="lbl-trans-att">Expected Attendance</label>
          <input type="number" id="trans-attendance" min="1000" max="100000" value="50000" aria-labelledby="lbl-trans-att" aria-required="true">
        </div>
        <div class="form-group">
          <label for="trans-match" id="lbl-trans-match">Match Type</label>
          <select id="trans-match" aria-labelledby="lbl-trans-match">
            <option value="group_stage">Group Stage</option>
            <option value="round_of_16">Round of 16</option>
            <option value="quarter_final">Quarter Final</option>
            <option value="semi_final">Semi Final</option>
            <option value="final">Final</option>
          </select>
        </div>
      </div>
      <button class="btn btn-primary" id="btn-trans-submit" onclick="submitTransport()" aria-label="Optimize transportation">🚌 Optimize Transport</button>
      <div class="spinner" id="trans-spinner" role="status"><span class="sr-only">Optimizing...</span><div class="spinner-text">AI is optimizing transportation routes...</div></div>
      <div class="error-box" id="trans-error" role="alert"></div>
      <div class="results-container" id="trans-results"></div>
    </div>
  </div>

</main>

<footer class="site-footer" role="contentinfo">
  <p>🏟️ Smart Stadium Operations Hub — FIFA World Cup 2026 | AI Provider: {html.escape(provider_label)}</p>
  <p style="margin-top:4px;">Built for Hack2Hack PromptWars Hackathon, Bengaluru 2026 | Zero Dependencies | WCAG AAA Accessible</p>
</footer>

<script>
"use strict";
/* ═══════════════════════════════════════════════════════════════════════════
   CLIENT-SIDE JAVASCRIPT — STADIUM OPS DASHBOARD
   ═══════════════════════════════════════════════════════════════════════════ */

const VENUES = {venues_json};
let selectedVenue = null;

// ── Initialize ──────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", function() {{
  renderVenueGrid();
  populateVenueSelects();
  updateClock();
  setInterval(updateClock, 1000);
}});

function updateClock() {{
  const el = document.getElementById("clock");
  if (el) el.textContent = new Date().toLocaleTimeString("en-US", {{hour12:false, hour:"2-digit", minute:"2-digit", second:"2-digit"}}) + " UTC+" + String(-new Date().getTimezoneOffset()/60);
}}

// ── Tab Navigation ──────────────────────────────────────────────────────────
function switchTab(tabId) {{
  document.querySelectorAll(".tab-content").forEach(function(t) {{ t.classList.remove("active"); }});
  document.querySelectorAll(".nav-tab").forEach(function(b) {{
    b.classList.remove("active");
    b.setAttribute("aria-selected", "false");
  }});
  var tab = document.getElementById("tab-" + tabId);
  var btn = document.getElementById("btn-" + tabId);
  if (tab) tab.classList.add("active");
  if (btn) {{
    btn.classList.add("active");
    btn.setAttribute("aria-selected", "true");
  }}
}}

// ── Venue Grid ──────────────────────────────────────────────────────────────
function renderVenueGrid() {{
  var grid = document.getElementById("venue-grid");
  if (!grid) return;
  grid.innerHTML = "";
  VENUES.forEach(function(v) {{
    var card = document.createElement("div");
    card.className = "venue-card";
    card.setAttribute("role", "option");
    card.setAttribute("tabindex", "0");
    card.setAttribute("aria-label", v.name + ", " + v.city + ", capacity " + v.capacity.toLocaleString());
    card.innerHTML = '<div class="vname">' + escHtml(v.name) + '</div>'
      + '<div class="vcity">📍 ' + escHtml(v.city) + ', ' + escHtml(v.country) + '</div>'
      + '<div class="vcap">🏟️ ' + v.capacity.toLocaleString() + ' seats</div>';
    card.onclick = function() {{ selectVenue(v.id); }};
    card.onkeydown = function(e) {{ if(e.key==="Enter"||e.key===" ") {{ e.preventDefault(); selectVenue(v.id); }} }};
    grid.appendChild(card);
  }});
}}

function selectVenue(venueId) {{
  selectedVenue = venueId;
  document.querySelectorAll(".venue-card").forEach(function(c, i) {{
    c.classList.toggle("selected", VENUES[i].id === venueId);
  }});
  loadWeather(venueId);
}}

function loadWeather(venueId) {{
  var card = document.getElementById("weather-card");
  var details = document.getElementById("weather-details");
  var nameEl = document.getElementById("weather-venue-name");
  var badge = document.getElementById("weather-risk-badge");
  var forecast = document.getElementById("forecast-section");
  card.style.display = "block";
  details.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:20px;">Loading weather data...</div>';
  fetch("/api/weather/" + venueId)
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      if (data.error) {{
        details.innerHTML = '<div style="color:var(--accent-red);">' + escHtml(data.error) + '</div>';
        return;
      }}
      var v = VENUES.find(function(x){{ return x.id === venueId; }});
      nameEl.textContent = "🌤️ " + (data.venue || (v ? v.name : "")) + " — Live Weather";
      badge.className = "risk-badge risk-" + (data.risk_level || "UNKNOWN");
      badge.textContent = data.risk_level || "UNKNOWN";
      var w = data.weather || {{}};
      details.innerHTML = metricHtml("🌡️", w.temperature_2m, "°C", "Temperature")
        + metricHtml("💧", w.relative_humidity_2m, "%", "Humidity")
        + metricHtml("🌧️", w.precipitation, " mm", "Precipitation")
        + metricHtml("💨", w.wind_speed_10m, " km/h", "Wind Speed")
        + metricHtml("🌪️", w.wind_gusts_10m, " km/h", "Wind Gusts")
        + metricHtml("🔵", w.surface_pressure, " hPa", "Pressure");
      var cond = data.condition || "N/A";
      details.innerHTML += '<div class="weather-metric" style="grid-column:1/-1;"><div class="value" style="font-size:1.1rem;">' + escHtml(cond) + '</div><div class="label">Current Condition</div></div>';
      // Forecast
      var fc = data.forecast || {{}};
      if (fc.time && fc.time.length > 0) {{
        var fhtml = '<h4 style="color:var(--accent-blue);margin-bottom:10px;">📅 3-Day Forecast</h4><table class="data-table"><thead><tr><th>Date</th><th>High</th><th>Low</th><th>Rain</th><th>Wind</th></tr></thead><tbody>';
        for (var i = 0; i < Math.min(fc.time.length, 3); i++) {{
          fhtml += '<tr><td>' + escHtml(fc.time[i]) + '</td>'
            + '<td>' + (fc.temperature_2m_max ? fc.temperature_2m_max[i] : "?") + '°C</td>'
            + '<td>' + (fc.temperature_2m_min ? fc.temperature_2m_min[i] : "?") + '°C</td>'
            + '<td>' + (fc.precipitation_sum ? fc.precipitation_sum[i] : 0) + ' mm</td>'
            + '<td>' + (fc.wind_speed_10m_max ? fc.wind_speed_10m_max[i] : 0) + ' km/h</td></tr>';
        }}
        fhtml += '</tbody></table>';
        forecast.innerHTML = fhtml;
      }}
    }})
    .catch(function(err) {{
      details.innerHTML = '<div style="color:var(--accent-red);">Failed to load weather: ' + escHtml(err.message) + '</div>';
    }});
}}

function metricHtml(icon, value, unit, label) {{
  return '<div class="weather-metric"><div class="value">' + icon + ' ' + (value != null ? value : "N/A") + (value != null ? unit : "") + '</div><div class="label">' + label + '</div></div>';
}}

// ── Populate Venue Selects ──────────────────────────────────────────────────
function populateVenueSelects() {{
  var selects = ["crowd-venue","assist-venue","sust-venue","ops-venue","trans-venue"];
  selects.forEach(function(id) {{
    var sel = document.getElementById(id);
    if (!sel) return;
    sel.innerHTML = '<option value="">— Select Stadium —</option>';
    VENUES.forEach(function(v) {{
      var opt = document.createElement("option");
      opt.value = v.id;
      opt.textContent = v.name + " (" + v.city + ")";
      sel.appendChild(opt);
    }});
  }});
}}

// ── API Submit Helpers ──────────────────────────────────────────────────────
function showSpinner(id) {{ var el = document.getElementById(id); if(el) el.classList.add("active"); }}
function hideSpinner(id) {{ var el = document.getElementById(id); if(el) el.classList.remove("active"); }}
function showError(id, msg) {{
  var el = document.getElementById(id);
  if(el) {{ el.textContent = msg; el.classList.add("active"); }}
}}
function hideError(id) {{ var el = document.getElementById(id); if(el) el.classList.remove("active"); }}
function disableBtn(id) {{ var el = document.getElementById(id); if(el) el.disabled = true; }}
function enableBtn(id) {{ var el = document.getElementById(id); if(el) el.disabled = false; }}

function apiPost(endpoint, body, spinnerId, errorId, btnId, resultId, renderFn) {{
  hideError(errorId);
  document.getElementById(resultId).innerHTML = "";
  showSpinner(spinnerId);
  disableBtn(btnId);
  fetch(endpoint, {{
    method: "POST",
    headers: {{ "Content-Type": "application/json" }},
    body: JSON.stringify(body)
  }})
  .then(function(r) {{ return r.json(); }})
  .then(function(data) {{
    hideSpinner(spinnerId);
    enableBtn(btnId);
    if (data.error) {{
      showError(errorId, data.error);
      return;
    }}
    document.getElementById(resultId).innerHTML = renderFn(data);
  }})
  .catch(function(err) {{
    hideSpinner(spinnerId);
    enableBtn(btnId);
    showError(errorId, "Request failed: " + err.message);
  }});
}}

// ── Crowd Management ────────────────────────────────────────────────────────
function submitCrowd() {{
  var venue = document.getElementById("crowd-venue").value;
  var attendance = parseInt(document.getElementById("crowd-attendance").value);
  var matchType = document.getElementById("crowd-match").value;
  if (!venue) {{ showError("crowd-error", "Please select a stadium."); return; }}
  if (!attendance || attendance < 1000) {{ showError("crowd-error", "Attendance must be at least 1,000."); return; }}
  apiPost("/api/crowd", {{venue_id: venue, attendance: attendance, match_type: matchType}},
    "crowd-spinner", "crowd-error", "btn-crowd-submit", "crowd-results", renderCrowdResults);
}}

function renderCrowdResults(data) {{
  var h = '';
  h += '<div class="metric-row">';
  h += '<div class="metric-card"><div class="metric-value">' + escHtml(data.venue || "") + '</div><div class="metric-label">Stadium</div></div>';
  h += '<div class="metric-card"><div class="metric-value"><span class="risk-badge risk-' + (data.weather_risk||"UNKNOWN") + '">' + (data.weather_risk||"?") + '</span></div><div class="metric-label">Weather Risk</div></div>';
  if (data.crowd_analysis) {{
    h += '<div class="metric-card"><div class="metric-value"><span class="risk-badge risk-' + (data.crowd_analysis.risk_level||"UNKNOWN") + '">' + (data.crowd_analysis.risk_level||"?") + '</span></div><div class="metric-label">Crowd Risk</div></div>';
  }}
  h += '</div>';
  if (data.crowd_analysis) {{
    var ca = data.crowd_analysis;
    if (ca.predicted_peak_arrival) h += '<div class="result-section"><h4>⏰ Peak Times</h4><p style="color:var(--text-secondary);font-size:0.85rem;">Arrival: ' + escHtml(ca.predicted_peak_arrival) + ' | Exit: ' + escHtml(ca.predicted_peak_exit||"N/A") + '</p></div>';
    if (ca.density_zones) {{
      h += '<div class="result-section"><h4>🗺️ Density Zones</h4>';
      ca.density_zones.forEach(function(z) {{
        h += '<div class="result-item"><div class="title">' + escHtml(z.zone) + ' — <span class="risk-badge risk-' + (z.expected_density||"UNKNOWN") + '">' + (z.expected_density||"?") + '</span></div><div class="desc">' + escHtml(z.recommendation||"") + '</div></div>';
      }});
      h += '</div>';
    }}
  }}
  if (data.gate_strategy) {{
    h += '<div class="result-section"><h4>🚪 Gate Strategy</h4><table class="data-table"><thead><tr><th>Gate</th><th>Allocation</th><th>Direction</th><th>Reason</th></tr></thead><tbody>';
    data.gate_strategy.forEach(function(g) {{
      h += '<tr><td>' + escHtml(g.gate) + '</td><td>' + g.allocation_pct + '%</td><td>' + escHtml(g.direction||"") + '</td><td>' + escHtml(g.reason||"") + '</td></tr>';
    }});
    h += '</tbody></table></div>';
  }}
  if (data.flow_recommendations) {{
    h += '<div class="result-section"><h4>📋 Flow Recommendations</h4>';
    data.flow_recommendations.forEach(function(r) {{
      h += '<div class="result-item priority-' + (r.priority||"MEDIUM") + '"><div class="title">' + escHtml(r.title) + '</div><div class="desc">' + escHtml(r.description) + '</div><div class="meta">Priority: ' + (r.priority||"?") + ' | Dept: ' + escHtml(r.department||"") + '</div></div>';
    }});
    h += '</div>';
  }}
  if (data.staffing_plan) {{
    var sp = data.staffing_plan;
    h += '<div class="result-section"><h4>👷 Staffing Plan</h4><div class="metric-row">';
    h += '<div class="metric-card"><div class="metric-value">' + (sp.security_personnel||0) + '</div><div class="metric-label">Security</div></div>';
    h += '<div class="metric-card"><div class="metric-value">' + (sp.medical_staff||0) + '</div><div class="metric-label">Medical</div></div>';
    h += '<div class="metric-card"><div class="metric-value">' + (sp.volunteer_guides||0) + '</div><div class="metric-label">Volunteers</div></div>';
    h += '<div class="metric-card"><div class="metric-value">' + (sp.traffic_controllers||0) + '</div><div class="metric-label">Traffic</div></div>';
    h += '</div></div>';
  }}
  if (data.emergency_protocols) {{
    h += '<div class="result-section"><h4>🚨 Emergency Protocols</h4>';
    data.emergency_protocols.forEach(function(e) {{
      h += '<div class="result-item priority-CRITICAL"><div class="title">' + escHtml(e.scenario) + '</div><div class="desc">' + escHtml(e.action) + '</div><div class="meta">Personnel: ' + (e.personnel_needed||"?") + ' | Evac Time: ' + (e.evacuation_time_minutes||"?") + ' min</div></div>';
    }});
    h += '</div>';
  }}
  if (data.weather_adaptations) {{
    h += '<div class="result-section"><h4>🌦️ Weather Adaptations</h4>';
    data.weather_adaptations.forEach(function(w) {{
      h += '<div class="result-item priority-' + (w.urgency==="IMMEDIATE"?"CRITICAL":"HIGH") + '"><div class="title">' + escHtml(w.condition) + '</div><div class="desc">' + escHtml(w.adaptation) + '</div><div class="meta">Urgency: ' + escHtml(w.urgency||"") + '</div></div>';
    }});
    h += '</div>';
  }}
  return h;
}}

// ── Fan Assistant ────────────────────────────────────────────────────────────
function submitAssist() {{
  var venue = document.getElementById("assist-venue").value;
  var query = document.getElementById("assist-query").value.trim();
  var lang = document.getElementById("assist-lang").value;
  if (!venue) {{ showError("assist-error", "Please select a stadium."); return; }}
  if (!query) {{ showError("assist-error", "Please enter a question."); return; }}
  hideError("assist-error");
  var chat = document.getElementById("assist-chat");
  chat.innerHTML += '<div class="chat-bubble user">' + escHtml(query) + '</div>';
  showSpinner("assist-spinner");
  disableBtn("btn-assist-submit");
  fetch("/api/assist", {{
    method: "POST",
    headers: {{ "Content-Type": "application/json" }},
    body: JSON.stringify({{venue_id: venue, query: query, language: lang}})
  }})
  .then(function(r) {{ return r.json(); }})
  .then(function(data) {{
    hideSpinner("assist-spinner");
    enableBtn("btn-assist-submit");
    if (data.error) {{ showError("assist-error", data.error); return; }}
    var bubble = '<div class="chat-bubble ai">';
    bubble += '<div style="font-weight:600;margin-bottom:6px;">🤖 ' + escHtml(data.venue||"") + ' Assistant (' + escHtml(data.language_used||lang) + ')</div>';
    bubble += '<div>' + escHtml(data.response||"No response") + '</div>';
    if (data.related_tips && data.related_tips.length) {{
      bubble += '<div style="margin-top:10px;padding-top:8px;border-top:1px solid var(--border-color);"><strong>💡 Tips:</strong><ul style="margin:4px 0 0 16px;">';
      data.related_tips.forEach(function(t) {{ bubble += '<li style="font-size:0.82rem;">' + escHtml(t) + '</li>'; }});
      bubble += '</ul></div>';
    }}
    if (data.weather_advisory) {{
      bubble += '<div style="margin-top:8px;font-size:0.82rem;color:var(--accent-cyan);">🌤️ ' + escHtml(data.weather_advisory) + '</div>';
    }}
    bubble += '</div>';
    chat.innerHTML += bubble;
    chat.scrollTop = chat.scrollHeight;
    document.getElementById("assist-query").value = "";
  }})
  .catch(function(err) {{
    hideSpinner("assist-spinner");
    enableBtn("btn-assist-submit");
    showError("assist-error", "Request failed: " + err.message);
  }});
}}

// ── Sustainability ──────────────────────────────────────────────────────────
function submitSustainability() {{
  var venue = document.getElementById("sust-venue").value;
  var attendance = parseInt(document.getElementById("sust-attendance").value);
  var matchType = document.getElementById("sust-match").value;
  if (!venue) {{ showError("sust-error", "Please select a stadium."); return; }}
  if (!attendance || attendance < 1000) {{ showError("sust-error", "Attendance must be at least 1,000."); return; }}
  apiPost("/api/sustainability", {{venue_id: venue, attendance: attendance, match_type: matchType}},
    "sust-spinner", "sust-error", "btn-sust-submit", "sust-results", renderSustResults);
}}

function renderSustResults(data) {{
  var h = '';
  if (data.carbon_metrics) {{
    var cm = data.carbon_metrics;
    h += '<div class="metric-row">';
    h += '<div class="metric-card"><div class="metric-value">' + (cm.estimated_event_footprint_tonnes||0) + '</div><div class="metric-label">Event CO₂ (tonnes)</div></div>';
    h += '<div class="metric-card"><div class="metric-value">' + (cm.per_fan_kg||0) + '</div><div class="metric-label">Per Fan (kg CO₂)</div></div>';
    h += '</div>';
    if (cm.breakdown) {{
      h += '<div class="result-section"><h4>📊 Carbon Breakdown</h4><table class="data-table"><thead><tr><th>Source</th><th>%</th><th>Tonnes</th></tr></thead><tbody>';
      cm.breakdown.forEach(function(b) {{
        h += '<tr><td>' + escHtml(b.source) + '</td><td>' + b.percentage + '%</td><td>' + b.tonnes + '</td></tr>';
      }});
      h += '</tbody></table></div>';
    }}
  }}
  if (data.sustainability_score) {{
    var ss = data.sustainability_score;
    h += '<div class="result-section"><h4>🏆 Sustainability Score</h4><div class="metric-row">';
    h += '<div class="metric-card"><div class="metric-value">' + (ss.current||0) + '/100</div><div class="metric-label">Current Score</div></div>';
    h += '<div class="metric-card"><div class="metric-value">' + (ss.target||0) + '/100</div><div class="metric-label">Target Score</div></div>';
    h += '<div class="metric-card"><div class="metric-value">' + escHtml(ss.grade||"?") + '</div><div class="metric-label">Grade</div></div>';
    h += '</div></div>';
  }}
  if (data.waste_strategy) {{
    var ws = data.waste_strategy;
    h += '<div class="result-section"><h4>♻️ Waste Strategy</h4>';
    h += '<div class="metric-row">';
    h += '<div class="metric-card"><div class="metric-value">' + (ws.estimated_waste_kg||0) + '</div><div class="metric-label">Est. Waste (kg)</div></div>';
    h += '<div class="metric-card"><div class="metric-value">' + (ws.recycling_target_pct||0) + '%</div><div class="metric-label">Recycling Target</div></div>';
    h += '<div class="metric-card"><div class="metric-value">' + (ws.recycling_stations_needed||0) + '</div><div class="metric-label">Recycling Stations</div></div>';
    h += '</div>';
    if (ws.recommendations) {{
      ws.recommendations.forEach(function(r) {{
        h += '<div class="result-item priority-MEDIUM"><div class="desc">' + escHtml(r) + '</div></div>';
      }});
    }}
    h += '</div>';
  }}
  if (data.energy_optimization) {{
    h += '<div class="result-section"><h4>⚡ Energy Optimization</h4>';
    data.energy_optimization.forEach(function(e) {{
      h += '<div class="result-item priority-HIGH"><div class="title">' + escHtml(e.system) + '</div><div class="desc">' + escHtml(e.recommendation) + '</div><div class="meta">Potential Savings: ' + (e.savings_pct||0) + '%</div></div>';
    }});
    h += '</div>';
  }}
  if (data.water_conservation) {{
    h += '<div class="result-section"><h4>💧 Water Conservation</h4>';
    data.water_conservation.forEach(function(w) {{
      h += '<div class="result-item priority-MEDIUM"><div class="title">' + escHtml(w.area) + '</div><div class="desc">' + escHtml(w.recommendation) + '</div><div class="meta">Savings: ' + (w.savings_liters||0) + ' liters</div></div>';
    }});
    h += '</div>';
  }}
  return h;
}}

// ── Ops Intelligence ────────────────────────────────────────────────────────
function submitOps() {{
  var venue = document.getElementById("ops-venue").value;
  var role = document.getElementById("ops-role").value;
  var attendance = parseInt(document.getElementById("ops-attendance").value);
  var matchType = document.getElementById("ops-match").value;
  if (!venue) {{ showError("ops-error", "Please select a stadium."); return; }}
  if (!attendance || attendance < 1000) {{ showError("ops-error", "Attendance must be at least 1,000."); return; }}
  apiPost("/api/ops", {{venue_id: venue, staff_role: role, attendance: attendance, match_type: matchType}},
    "ops-spinner", "ops-error", "btn-ops-submit", "ops-results", renderOpsResults);
}}

function renderOpsResults(data) {{
  var h = '';
  h += '<div class="metric-row">';
  h += '<div class="metric-card"><div class="metric-value">' + escHtml(data.venue||"") + '</div><div class="metric-label">Stadium</div></div>';
  h += '<div class="metric-card"><div class="metric-value">' + escHtml((data.role||"").replace(/_/g," ")) + '</div><div class="metric-label">Staff Role</div></div>';
  h += '<div class="metric-card"><div class="metric-value"><span class="risk-badge risk-' + (data.weather_risk||"UNKNOWN") + '">' + (data.weather_risk||"?") + '</span></div><div class="metric-label">Weather Risk</div></div>';
  h += '</div>';
  if (data.briefing_title) {{
    h += '<div class="result-section"><h4>📋 ' + escHtml(data.briefing_title) + '</h4>';
    if (data.situation_assessment) h += '<p style="color:var(--text-secondary);font-size:0.88rem;line-height:1.6;">' + escHtml(data.situation_assessment) + '</p>';
    h += '</div>';
  }}
  if (data.risk_matrix) {{
    h += '<div class="result-section"><h4>⚠️ Risk Matrix</h4><table class="data-table"><thead><tr><th>Risk</th><th>Likelihood</th><th>Impact</th><th>Mitigation</th></tr></thead><tbody>';
    data.risk_matrix.forEach(function(r) {{
      h += '<tr><td>' + escHtml(r.risk) + '</td><td><span class="risk-badge risk-' + (r.likelihood||"UNKNOWN") + '">' + (r.likelihood||"?") + '</span></td><td><span class="risk-badge risk-' + (r.impact||"UNKNOWN") + '">' + (r.impact||"?") + '</span></td><td>' + escHtml(r.mitigation) + '</td></tr>';
    }});
    h += '</tbody></table></div>';
  }}
  if (data.priority_actions) {{
    h += '<div class="result-section"><h4>🎯 Priority Actions</h4>';
    data.priority_actions.forEach(function(a) {{
      h += '<div class="result-item priority-' + (a.urgency||"MEDIUM") + '"><div class="title">[' + escHtml(a.phase||"") + '] ' + escHtml(a.action) + '</div><div class="desc">Location: ' + escHtml(a.location||"TBD") + ' | Personnel: ' + (a.personnel||"?") + '</div><div class="meta">Urgency: ' + (a.urgency||"?") + ' | Dept: ' + escHtml(a.department||"") + '</div></div>';
    }});
    h += '</div>';
  }}
  if (data.weather_impact) {{
    var wi = data.weather_impact;
    h += '<div class="result-section"><h4>🌦️ Weather Impact — <span class="risk-badge risk-' + (wi.severity||"UNKNOWN") + '">' + (wi.severity||"?") + '</span></h4>';
    if (wi.adaptations) {{
      wi.adaptations.forEach(function(a) {{ h += '<div class="result-item priority-HIGH"><div class="desc">' + escHtml(a) + '</div></div>'; }});
    }}
    if (wi.contingency) h += '<div class="result-item priority-CRITICAL"><div class="title">Contingency Plan</div><div class="desc">' + escHtml(wi.contingency) + '</div></div>';
    h += '</div>';
  }}
  if (data.kpis) {{
    h += '<div class="result-section"><h4>📊 KPIs</h4><table class="data-table"><thead><tr><th>Metric</th><th>Target</th><th>Measurement</th></tr></thead><tbody>';
    data.kpis.forEach(function(k) {{
      h += '<tr><td>' + escHtml(k.metric) + '</td><td>' + escHtml(k.target) + '</td><td>' + escHtml(k.measurement) + '</td></tr>';
    }});
    h += '</tbody></table></div>';
  }}
  return h;
}}

// ── Transport Optimizer ─────────────────────────────────────────────────────
function submitTransport() {{
  var venue = document.getElementById("trans-venue").value;
  var attendance = parseInt(document.getElementById("trans-attendance").value);
  var matchType = document.getElementById("trans-match").value;
  if (!venue) {{ showError("trans-error", "Please select a stadium."); return; }}
  if (!attendance || attendance < 1000) {{ showError("trans-error", "Attendance must be at least 1,000."); return; }}
  apiPost("/api/transport", {{venue_id: venue, attendance: attendance, match_type: matchType}},
    "trans-spinner", "trans-error", "btn-trans-submit", "trans-results", renderTransResults);
}}

function renderTransResults(data) {{
  var h = '';
  h += '<div class="metric-row">';
  h += '<div class="metric-card"><div class="metric-value">' + escHtml(data.venue||"") + '</div><div class="metric-label">Stadium</div></div>';
  h += '<div class="metric-card"><div class="metric-value"><span class="risk-badge risk-' + (data.weather_risk||"UNKNOWN") + '">' + (data.weather_risk||"?") + '</span></div><div class="metric-label">Weather Risk</div></div>';
  h += '</div>';
  if (data.transit_plan) {{
    h += '<div class="result-section"><h4>🚆 Transit Plan</h4><table class="data-table"><thead><tr><th>Mode</th><th>Route</th><th>Capacity/hr</th><th>Timing</th><th>Weather Impact</th></tr></thead><tbody>';
    data.transit_plan.forEach(function(t) {{
      h += '<tr><td>' + escHtml(t.mode) + '</td><td>' + escHtml(t.route) + '</td><td>' + (t.capacity_per_hour||"?") + '</td><td>' + escHtml(t.recommended_timing||"") + '</td><td>' + escHtml(t.weather_impact||"None") + '</td></tr>';
    }});
    h += '</tbody></table></div>';
  }}
  if (data.parking_strategy) {{
    var ps = data.parking_strategy;
    h += '<div class="result-section"><h4>🅿️ Parking Strategy</h4>';
    h += '<div class="metric-row">';
    h += '<div class="metric-card"><div class="metric-value">' + (ps.total_spaces||0) + '</div><div class="metric-label">Total Spaces</div></div>';
    h += '</div>';
    if (ps.recommended_arrival) h += '<p style="color:var(--text-secondary);font-size:0.85rem;">Recommended Arrival: ' + escHtml(ps.recommended_arrival) + '</p>';
    if (ps.lots) {{
      h += '<table class="data-table" style="margin-top:10px;"><thead><tr><th>Lot</th><th>Spaces</th><th>Distance</th><th>Shuttle</th></tr></thead><tbody>';
      ps.lots.forEach(function(l) {{
        h += '<tr><td>' + escHtml(l.name) + '</td><td>' + (l.spaces||"?") + '</td><td>' + (l.distance_km||"?") + ' km</td><td>' + (l.shuttle ? "✅" : "❌") + '</td></tr>';
      }});
      h += '</tbody></table>';
    }}
    h += '</div>';
  }}
  if (data.rideshare_zones) {{
    h += '<div class="result-section"><h4>🚗 Rideshare Zones</h4>';
    data.rideshare_zones.forEach(function(z) {{
      h += '<div class="result-item"><div class="title">' + escHtml(z.zone_name) + '</div><div class="desc">📍 ' + escHtml(z.location) + '</div><div class="meta">Capacity: ' + (z.capacity||"?") + ' | Est. Wait: ' + (z.estimated_wait_minutes||"?") + ' min</div></div>';
    }});
    h += '</div>';
  }}
  if (data.accessibility_transport) {{
    h += '<div class="result-section"><h4>♿ Accessible Transport</h4>';
    data.accessibility_transport.forEach(function(a) {{
      h += '<div class="result-item priority-HIGH"><div class="title">' + escHtml(a.service) + '</div><div class="desc">' + escHtml(a.details) + '</div><div class="meta">Booking: ' + escHtml(a.booking||"") + ' | Cost: ' + escHtml(a.cost||"Free") + '</div></div>';
    }});
    h += '</div>';
  }}
  if (data.post_match_dispersal) {{
    var pmd = data.post_match_dispersal;
    h += '<div class="result-section"><h4>🚶 Post-Match Dispersal</h4>';
    h += '<div class="metric-row"><div class="metric-card"><div class="metric-value">' + (pmd.estimated_dispersal_time_minutes||"?") + ' min</div><div class="metric-label">Est. Dispersal Time</div></div></div>';
    if (pmd.staggered_exit_plan) h += '<div class="result-item"><div class="desc">' + escHtml(pmd.staggered_exit_plan) + '</div></div>';
    h += '</div>';
  }}
  return h;
}}

// ── Utility ─────────────────────────────────────────────────────────────────
function escHtml(str) {{
  if (str == null) return "";
  var div = document.createElement("div");
  div.appendChild(document.createTextNode(String(str)));
  return div.innerHTML;
}}
</script>
</body>
</html>'''


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7: EMBEDDED TEST SUITE
# ═══════════════════════════════════════════════════════════════════════════════

class TestInputSanitization(unittest.TestCase):
    """Tests for XSS and injection prevention."""

    def test_xss_script_tag(self):
        self.assertEqual(sanitize_input("<script>alert(1)</script>"), "")

    def test_xss_event_handler(self):
        self.assertEqual(sanitize_input('x" onerror="alert(1)'), "")

    def test_xss_javascript_uri(self):
        self.assertEqual(sanitize_input("javascript:alert(1)"), "")

    def test_xss_iframe(self):
        self.assertEqual(sanitize_input("<iframe src=evil>"), "")

    def test_xss_object_tag(self):
        self.assertEqual(sanitize_input("<object data=evil>"), "")

    def test_xss_embed_tag(self):
        self.assertEqual(sanitize_input("<embed src=evil>"), "")

    def test_sql_select(self):
        self.assertEqual(sanitize_input("'; SELECT * FROM users --"), "")

    def test_sql_drop(self):
        self.assertEqual(sanitize_input("DROP TABLE venues"), "")

    def test_sql_union(self):
        self.assertEqual(sanitize_input("1 UNION SELECT password"), "")

    def test_clean_input(self):
        self.assertEqual(sanitize_input("MetLife Stadium"), "MetLife Stadium")

    def test_html_escape(self):
        self.assertNotIn("<", sanitize_input("test & <b>bold</b>"))

    def test_non_string_input(self):
        self.assertEqual(sanitize_input(None), "")
        self.assertEqual(sanitize_input(123), "")

    def test_empty_string(self):
        self.assertEqual(sanitize_input(""), "")

    def test_whitespace_strip(self):
        self.assertEqual(sanitize_input("  hello  "), "hello")


class TestValidation(unittest.TestCase):
    """Tests for input validators."""

    def test_valid_venue_id(self):
        self.assertEqual(validate_venue_id("metlife"), "metlife")
        self.assertEqual(validate_venue_id("azteca"), "azteca")

    def test_invalid_venue_id(self):
        self.assertEqual(validate_venue_id("nonexistent"), "")
        self.assertEqual(validate_venue_id(""), "")

    def test_venue_id_case_insensitive(self):
        self.assertEqual(validate_venue_id("MetLife"), "metlife")

    def test_valid_match_type(self):
        self.assertEqual(validate_match_type("group_stage"), "group_stage")
        self.assertEqual(validate_match_type("final"), "final")

    def test_invalid_match_type_defaults(self):
        self.assertEqual(validate_match_type("invalid"), "group_stage")

    def test_valid_staff_role(self):
        self.assertEqual(validate_staff_role("security"), "security")
        self.assertEqual(validate_staff_role("medical"), "medical")

    def test_invalid_staff_role_defaults(self):
        self.assertEqual(validate_staff_role("hacker"), "general_manager")

    def test_valid_language(self):
        self.assertEqual(validate_language("English"), "English")
        self.assertEqual(validate_language("spanish"), "Spanish")

    def test_invalid_language_defaults(self):
        self.assertEqual(validate_language("Klingon"), "English")

    def test_valid_attendance(self):
        self.assertEqual(validate_attendance("50000"), 50000)
        self.assertEqual(validate_attendance("1000"), 1000)

    def test_invalid_attendance(self):
        self.assertEqual(validate_attendance("500"), 0)
        self.assertEqual(validate_attendance("200000"), 0)
        self.assertEqual(validate_attendance("abc"), 0)

    def test_valid_query_text(self):
        result = validate_query_text("Where is gate A?")
        self.assertTrue(len(result) > 0)

    def test_empty_query_text(self):
        self.assertEqual(validate_query_text(""), "")

    def test_xss_in_query(self):
        self.assertEqual(validate_query_text("<script>alert(1)</script>"), "")


class TestWeather(unittest.TestCase):
    """Tests for weather data processing."""

    def test_interpret_clear(self):
        self.assertEqual(interpret_weather_code(0), "Clear sky")

    def test_interpret_thunderstorm(self):
        self.assertEqual(interpret_weather_code(95), "Thunderstorm")

    def test_interpret_heavy_rain(self):
        self.assertEqual(interpret_weather_code(65), "Heavy rain")

    def test_interpret_unknown(self):
        result = interpret_weather_code(999)
        self.assertIn("999", result)

    def test_risk_empty_data(self):
        self.assertEqual(assess_weather_risk({}), "UNKNOWN")
        self.assertEqual(assess_weather_risk({"current": {}}), "LOW")

    def test_risk_severe(self):
        data = {"current": {"weather_code": 95, "wind_speed_10m": 65,
                            "wind_gusts_10m": 90, "precipitation": 25,
                            "temperature_2m": 20}}
        risk = assess_weather_risk(data)
        self.assertIn(risk, ["SEVERE", "EXTREME"])

    def test_format_summary_empty(self):
        result = format_weather_summary({})
        self.assertIn("unavailable", result)

    def test_format_summary_with_data(self):
        data = {"current": {"temperature_2m": 25, "relative_humidity_2m": 60,
                            "precipitation": 0, "rain": 0, "wind_speed_10m": 10,
                            "wind_gusts_10m": 15, "surface_pressure": 1013,
                            "weather_code": 0, "apparent_temperature": 24}}
        result = format_weather_summary(data, "MetLife Stadium")
        self.assertIn("MetLife Stadium", result)
        self.assertIn("25", result)


class TestVenueData(unittest.TestCase):
    """Tests for venue database integrity."""

    def test_sixteen_venues(self):
        self.assertEqual(len(WC2026_VENUES), 16)

    def test_all_venues_have_required_fields(self):
        required = {"name", "city", "country", "capacity", "lat", "lon"}
        for vid, v in WC2026_VENUES.items():
            for field in required:
                self.assertIn(field, v, f"Venue {vid} missing {field}")

    def test_venue_coordinates_valid(self):
        for vid, v in WC2026_VENUES.items():
            self.assertTrue(-90 <= v["lat"] <= 90, f"{vid} lat out of range")
            self.assertTrue(-180 <= v["lon"] <= 180, f"{vid} lon out of range")

    def test_venue_capacity_positive(self):
        for vid, v in WC2026_VENUES.items():
            self.assertGreater(v["capacity"], 0, f"{vid} capacity <= 0")

    def test_three_countries(self):
        countries = set(v["country"] for v in WC2026_VENUES.values())
        self.assertEqual(countries, {"USA", "Mexico", "Canada"})


class TestAIPrompts(unittest.TestCase):
    """Tests for AI prompt construction."""

    def test_crowd_prompt_contains_venue(self):
        venue = WC2026_VENUES["metlife"]
        prompt = build_crowd_management_prompt(venue, 50000, "group_stage", "test weather")
        self.assertIn("MetLife Stadium", prompt)
        self.assertIn("50,000", prompt)

    def test_crowd_prompt_contains_json_schema(self):
        venue = WC2026_VENUES["metlife"]
        prompt = build_crowd_management_prompt(venue, 50000, "group_stage", "test weather")
        self.assertIn("crowd_analysis", prompt)
        self.assertIn("gate_strategy", prompt)

    def test_fan_prompt_contains_language(self):
        venue = WC2026_VENUES["azteca"]
        prompt = build_fan_assistant_prompt(venue, "Where is gate A?", "Spanish", "test")
        self.assertIn("Spanish", prompt)
        self.assertIn("Estadio Azteca", prompt)

    def test_sustainability_prompt_structure(self):
        venue = WC2026_VENUES["sofi"]
        prompt = build_sustainability_prompt(venue, 60000, "semi_final", "test")
        self.assertIn("carbon_metrics", prompt)
        self.assertIn("sustainability_score", prompt)

    def test_ops_prompt_contains_role(self):
        venue = WC2026_VENUES["mercedesbenz"]
        prompt = build_ops_decision_prompt(venue, "security", 70000, "final", "test")
        self.assertIn("security", prompt)
        self.assertIn("risk_matrix", prompt)

    def test_transport_prompt_structure(self):
        venue = WC2026_VENUES["bcplace"]
        prompt = build_transport_prompt(venue, 40000, "group_stage", "test")
        self.assertIn("transit_plan", prompt)
        self.assertIn("parking_strategy", prompt)


class TestSecurityHeaders(unittest.TestCase):
    """Tests for security response headers."""

    def test_csp_header(self):
        headers = _security_headers()
        self.assertIn("Content-Security-Policy", headers)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])

    def test_x_frame_deny(self):
        headers = _security_headers()
        self.assertEqual(headers["X-Frame-Options"], "DENY")

    def test_nosniff(self):
        headers = _security_headers()
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

    def test_xss_protection(self):
        headers = _security_headers()
        self.assertEqual(headers["X-XSS-Protection"], "1; mode=block")

    def test_hsts(self):
        headers = _security_headers()
        self.assertIn("max-age=", headers["Strict-Transport-Security"])

    def test_referrer_policy(self):
        headers = _security_headers()
        self.assertEqual(headers["Referrer-Policy"], "strict-origin-when-cross-origin")

    def test_permissions_policy(self):
        headers = _security_headers()
        self.assertIn("geolocation=()", headers["Permissions-Policy"])


class TestRateLimiter(unittest.TestCase):
    """Tests for rate limiting."""

    def setUp(self):
        global _rate_tokens
        _rate_tokens = {}

    def test_allow_initial_request(self):
        self.assertTrue(check_rate_limit("test_ip_1"))

    def test_block_after_limit(self):
        for _ in range(RATE_LIMIT_MAX):
            check_rate_limit("test_ip_2")
        self.assertFalse(check_rate_limit("test_ip_2"))

    def test_reset_after_window(self):
        for _ in range(RATE_LIMIT_MAX):
            check_rate_limit("test_ip_3")
        with _rate_lock:
            _rate_tokens["test_ip_3"]["window_start"] -= RATE_LIMIT_WINDOW + 1
        self.assertTrue(check_rate_limit("test_ip_3"))


class TestHTMLOutput(unittest.TestCase):
    """Tests for HTML dashboard structure."""

    def setUp(self):
        self.html = _build_dashboard_html()

    def test_doctype(self):
        self.assertTrue(self.html.strip().startswith("<!DOCTYPE html>"))

    def test_lang_attribute(self):
        self.assertIn('lang="en"', self.html)

    def test_viewport_meta(self):
        self.assertIn('name="viewport"', self.html)

    def test_meta_description(self):
        self.assertIn('name="description"', self.html)

    def test_single_h1(self):
        h1_count = self.html.count("<h1")
        self.assertEqual(h1_count, 1)

    def test_skip_link(self):
        self.assertIn("skip-link", self.html)
        self.assertIn("Skip to main content", self.html)

    def test_aria_labels(self):
        self.assertIn("aria-label", self.html)
        self.assertIn("aria-required", self.html)
        self.assertIn("role=", self.html)

    def test_semantic_header(self):
        self.assertIn("<header", self.html)
        self.assertIn("</header>", self.html)

    def test_semantic_main(self):
        self.assertIn("<main", self.html)
        self.assertIn("</main>", self.html)

    def test_semantic_footer(self):
        self.assertIn("<footer", self.html)
        self.assertIn("</footer>", self.html)

    def test_semantic_nav(self):
        self.assertIn("<nav", self.html)
        self.assertIn("role=\"tablist\"", self.html)

    def test_form_labels(self):
        self.assertIn("<label", self.html)
        self.assertIn("for=", self.html)

    def test_print_styles(self):
        self.assertIn("@media print", self.html)

    def test_sr_only_class(self):
        self.assertIn("sr-only", self.html)

    def test_focus_visible(self):
        self.assertIn("focus-visible", self.html)

    def test_wcag_contrast_vars(self):
        self.assertIn("--text-primary", self.html)
        self.assertIn("#f0f4ff", self.html)


class TestServerConfig(unittest.TestCase):
    """Tests for server configuration."""

    def test_host_binding(self):
        self.assertEqual(HOST, "0.0.0.0")

    def test_port_default(self):
        self.assertEqual(int(os.environ.get("PORT", 8080)), PORT)

    def test_ai_provider_detection(self):
        self.assertIn(get_ai_provider(), ["gemini", "groq", "openrouter", "none"])

    def test_valid_endpoints(self):
        self.assertTrue(GROQ_ENDPOINT.startswith("https://"))
        self.assertTrue(GEMINI_ENDPOINT.startswith("https://"))
        self.assertTrue(OPENROUTER_ENDPOINT.startswith("https://"))

    def test_rate_limit_config(self):
        self.assertGreater(RATE_LIMIT_MAX, 0)
        self.assertGreater(RATE_LIMIT_WINDOW, 0)

    def test_cache_ttl(self):
        self.assertGreater(CACHE_TTL, 0)

    def test_max_post_body(self):
        self.assertEqual(_MAX_POST_BODY, 10240)


class TestCacheSystem(unittest.TestCase):
    """Tests for API response caching."""

    def setUp(self):
        global _api_cache
        _api_cache = {}

    def test_cache_miss(self):
        self.assertIsNone(_get_cache("nonexistent"))

    def test_cache_set_and_get(self):
        _set_cache("test_key", {"value": 42})
        result = _get_cache("test_key")
        self.assertEqual(result, {"value": 42})

    def test_cache_expiry(self):
        _set_cache("expiry_key", {"value": 1})
        with _cache_lock:
            _api_cache["expiry_key"]["timestamp"] -= CACHE_TTL + 1
        self.assertIsNone(_get_cache("expiry_key"))


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8: SERVER ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Application entry point."""
    if "--test" in sys.argv:
        print("\n🧪 Running Smart Stadium Operations Hub Test Suite...\n")
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        test_classes = [
            TestInputSanitization, TestValidation, TestWeather,
            TestVenueData, TestAIPrompts, TestSecurityHeaders,
            TestRateLimiter, TestHTMLOutput, TestServerConfig,
            TestCacheSystem,
        ]
        for tc in test_classes:
            suite.addTests(loader.loadTestsFromTestCase(tc))
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        sys.exit(0 if result.wasSuccessful() else 1)

    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║  🏟️  Smart Stadium Operations Hub — FIFA World Cup 2026         ║
║  Server: http://{HOST}:{PORT}                                   ║
║  AI Provider: {get_ai_provider().upper():15s}                              ║
║  Venues: {len(WC2026_VENUES)} FIFA WC2026 Stadiums                          ║
║  Tests: python3 app.py --test                                   ║
╚══════════════════════════════════════════════════════════════════╝
""")

    server = http.server.HTTPServer((HOST, PORT), StadiumOpsHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
