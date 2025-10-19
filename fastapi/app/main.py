from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, RedirectResponse
import json
import tempfile
from pathlib import Path
from datetime import date, timedelta
import logging
from badidatetime.badi_calendar import BahaiCalendar
from .monthnames import MONTHNAMES
from .bahai_events import BAHAI_EVENTS
from ics import Calendar, Event

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Bahá'í Calendar API", 
    description="API to obtain events from the Bahá'í calendar and export to .ics"
)

# Unified event mapping for translations
EVENT_KEYS = {
    'Naw-Rúz': 'nawruz',
    'First Day of Riḍván': '1Ridvan',
    'Ninth Day of Riḍván': '9Ridvan',
    'Twelfth Day of Riḍván': '12Ridvan',
    'Declaration of the Báb': 'declarationBab',
    'Ascension of Bahá\'u\'lláh': 'ascensionB',
    'Martyrdom of the Báb': 'martyrdomBab',
    'Birth of the Báb': 'birthBab',
    'Birth of Bahá\'u\'lláh': 'birthB',
    'Day of the Covenant': 'covenant',
    'Ascension of \'Abdu\'l-Bahá': 'ascensionA',
    'Ayyám-i-Há': 'ayyamiha',
    'Fast': 'fast'
}

def load_translation(lang='es'):
    """Load translations from JSON file"""
    translation_path = Path(__file__).parent / 'translations' / f'{lang}.json'
    if not translation_path.exists():
        translation_path = Path(__file__).parent / 'translations' / 'es.json'
    
    with open(translation_path, encoding='utf-8') as f:
        return json.load(f)

def get_calendar_instance():
    """Create Bahá'í calendar instance"""
    bc = BahaiCalendar()
    return bc, bc._BAHAI_LOCATION[:3]

def translate_event(event_name, lang, is_first_fast=False, is_last_fast=False):
    """Translate event name and description"""
    translations = load_translation(lang)
    
    if is_first_fast:
        key = '1fast'
    elif is_last_fast:
        key = '19fast'
    else:
        key = EVENT_KEYS.get(event_name, event_name)
    
    return {
        'name': translations['events']['names'].get(key, event_name),
        'desc': translations['events']['descriptions'].get(key, ""),
        'url': translations['events'].get('urls', {}).get(key, "")
    }

def create_event_dict(event_name, desc, badi_month, badi_day, gregorian_date, url=""):
    """Create standardized event dictionary"""
    return {
        "event": event_name,
        "desc": desc,
        "badi_month": badi_month,
        "badi_month_name": MONTHNAMES.get(badi_month, str(badi_month)),
        "badi_day": badi_day,
        "gregorian_date": gregorian_date.isoformat(),
        "url": url
    }

def get_bahai_events_for_gregorian_year(year: int, lang: str = 'es'):
    """Get Bahá'í events for a specific Gregorian year"""
    bc, (lat, lon, zone) = get_calendar_instance()
    
    # Calculate Bahá'í year and start/end dates
    badi_start = bc.badi_date_from_gregorian_date((year, 3, 21), lat, lon, zone, short=True, trim=True)
    badi_year = badi_start[0]
        
    nawruz_start = bc.naw_ruz_g_date(badi_year, lat, lon, zone)
    nawruz_end = bc.naw_ruz_g_date(badi_year + 1, lat, lon, zone)
    
    # Correct dates: events begin at sunset on the previous day
    start_date = date(nawruz_start[0], nawruz_start[1], int(nawruz_start[2])) + timedelta(days=1)
    end_date = date(nawruz_end[0], nawruz_end[1], int(nawruz_end[2])) + timedelta(days=1)
        
    events = []
    
    # 1. BAHAI_EVENTS REGULAR EVENTS
    for event in BAHAI_EVENTS:
        try:
            gdate = bc.gregorian_date_from_badi_date(
                (badi_year, event["month"], event["day"]), lat, lon, zone
            )
            # Correct date: events begin at sunset on the previous day
            event_date = date(gdate[0], gdate[1], gdate[2]) + timedelta(days=1)
            
            if start_date <= event_date < end_date:
                translated = translate_event(event["name"], lang)
                events.append(create_event_dict(
                    translated['name'], translated['desc'],
                    event["month"], event["day"], event_date, translated['url']
                ))
        except Exception as e:
            logger.warning(f"❌ Error processing event {event['name']}: {e}")
    
    # 2. AYYÁM-I-HÁ (intercalary days)
    try:
        ayyam_start = bc.gregorian_date_from_badi_date((badi_year, 0, 1), lat, lon, zone)
        # Correct date: begins at sunset on the previous day
        ayyam_start_date = date(ayyam_start[0], ayyam_start[1], ayyam_start[2]) + timedelta(days=1)

        # Calculate how many Ayyám-i-Há days there are
        month19_start = bc.gregorian_date_from_badi_date((badi_year, 19, 1), lat, lon, zone)
        month19_start_date = date(month19_start[0], month19_start[1], month19_start[2]) + timedelta(days=1)
        
        ayyam_days = (month19_start_date - ayyam_start_date).days
        
        for day in range(1, ayyam_days + 1):
            ayyam_date = ayyam_start_date + timedelta(days=day-1)
            if start_date <= ayyam_date < end_date:
                translated = translate_event('Ayyám-i-Há', lang)
                events.append(create_event_dict(
                    translated['name'] or "Ayyám-i-Há",
                    translated['desc'] or "Días Intercalares",
                    0, day, ayyam_date, translated['url']
                ))
        
    except Exception as e:
        logger.warning(f"❌ Error processing Ayyám-i-Há: {e}")

    # 3. FASTING (month 19, days 1-19)
    try:
        # First day of fasting
        fast_start = bc.gregorian_date_from_badi_date((badi_year, 19, 1), lat, lon, zone)
        # Correct date: begins at sunset on the previous day
        fast_start_date = date(fast_start[0], fast_start[1], fast_start[2]) + timedelta(days=1)
        
        if start_date <= fast_start_date < end_date:
            translated = translate_event('Fast', lang, is_first_fast=True)
            events.append(create_event_dict(
                translated['name'], translated['desc'],
                19, 1, fast_start_date, translated['url']
            ))
        
        # Last day of fasting
        fast_end = bc.gregorian_date_from_badi_date((badi_year, 19, 19), lat, lon, zone)
        # Correct date: begins at sunset on the previous day
        fast_end_date = date(fast_end[0], fast_end[1], fast_end[2]) + timedelta(days=1)
        
        if start_date <= fast_end_date < end_date:
            translated = translate_event('Fast', lang, is_last_fast=True)
            events.append(create_event_dict(
                translated['name'], translated['desc'],
                19, 19, fast_end_date, translated['url']
            ))
            
    except Exception as e:
        logger.warning(f"❌ Error processing fasting: {e}")

    # 4. ORDER EVENTS
    def sort_key(event):
        nawruz_name = translate_event('Naw-Rúz', lang)['name']
        if event['event'] == nawruz_name:
            return (0, event['gregorian_date'])  # Naw-Rúz first
        elif event['badi_month'] == 19 and event['badi_day'] == 19:
            return (2, event['gregorian_date'])  # Last day of fasting at the end
        else:
            return (1, event['gregorian_date'])  # Rest in chronological order

    events.sort(key=sort_key)
    
    return events

def create_ics_calendar(lang):
    """Create an empty ICS calendar with metadata"""
    calendar = Calendar()
    calendar.creator = "Bahá'í Calendar"
    calendar.version = "1.0"
    calendar.prodid = f"-//Bahá'í Calendar//{lang.upper()}"
    return calendar

def add_events_to_calendar(calendar, events_data, lang):
    """Add events to the ICS calendar"""
    translations = load_translation(lang)
    for event_data in events_data:
        event = Event()
        event.name = event_data["event"]
        event.description = event_data.get("desc", "")
        # Convert Gregorian date to date object
        event_date = date.fromisoformat(event_data["gregorian_date"])
        event.begin = event_date
        event.make_all_day()

        # Add URL if available
        if event_data.get("url"):
            event.description += f"\n\nMás información: {event_data['url']}"

        # Add additional information to the description
        if event_data.get("badi_day"):
            event.description += f"\n\nDía Bahá'í: {event_data['badi_day']}"
        
        calendar.events.add(event)
    
    return calendar

def add_months_to_calendar(calendar, months_data, year, lang):
    """Add month beginnings to the ICS calendar"""
    translations = load_translation(lang)
    
    for month_data in months_data:
        event = Event()
        event.name = f"{translations['title']} {month_data['badi_month_name']}"
        if month_data['badi_month'] == 0:
            event.name = f"{month_data['badi_month_name']}"
        
        desc = month_data.get("desc", "")
        event.description = desc
        # Convert Gregorian date to date object
        event_date = date.fromisoformat(month_data["gregorian_date"])
        event.begin = event_date
        event.make_all_day()

        # Add additional information
        if desc:  # Only add newlines if description is not empty
            event.description += f"\n{month_data.get('info', '')}"
        else:
            event.description = month_data.get('info', '')
        event.description += f"\nMes Bahá'í número: {month_data['badi_month']}"
        calendar.events.add(event)
    
    return calendar

def save_calendar_to_temp_file(calendar, filename):
    """Save ICS calendar to temporary file"""
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".ics", encoding='utf-8')
    temp_file.write(calendar.serialize())
    temp_file.close()
    return temp_file.name

@app.get("/", include_in_schema=False)
async def root():
    """Redirect automatically to the Swagger documentation"""
    return RedirectResponse(url="/docs")

@app.get("/bahai-months/{year}", summary="First Gregorian day of each Bahá'í month and its name")
def get_bahai_months(year: int, lang: str = Query('es', description="Language: 'es' or 'en'")):
    """Returns the first day of each Bahá'í month"""
    translations = load_translation(lang)
    month_names = {int(k): v for k, v in translations['month']['names'].items()}
    month_descriptions = {int(k): v for k, v in translations['month']['descriptions'].items()}

    bc, (lat, lon, zone) = get_calendar_instance()
    badi_start = bc.badi_date_from_gregorian_date((year, 3, 21), lat, lon, zone, short=True, trim=True)
    badi_year = badi_start[0]
    
    def create_month_entry(month_num, badi_year):
        gdate = bc.gregorian_date_from_badi_date((badi_year, month_num, 1), lat, lon, zone)
        corrected_date = date(gdate[0], gdate[1], gdate[2]) + timedelta(days=1)
        
        return {
            "badi_month": month_num,
            "badi_month_name": f"{MONTHNAMES[month_num]} ({month_names[month_num]})",
            "gregorian_date": corrected_date.strftime("%Y-%m-%d"),
            "desc": f"{month_descriptions[month_num]}",
            "info": "Comienza en el atardecer del día anterior",
        }
    
    result = []
    # Meses 1-19 + Ayyám-i-Há (mes 0)
    for month in range(1, 20):
        result.append(create_month_entry(month, badi_year))
    result.append(create_month_entry(0, badi_year))
    
    return {"year": year, "months": result}

@app.get("/events/{year}", summary="Obtener eventos Bahá'ís de un año")
def get_events(year: int, lang: str = Query('es', description="Idioma: 'es' o 'en'")):
    """Obtener todos los eventos Bahá'ís para un año gregoriano"""
    events = get_bahai_events_for_gregorian_year(year, lang)
    return {"year": year, "events": events}

@app.get("/complete/{year}", summary="Obtener eventos y meses Bahá'ís completos en JSON")
def get_complete_data(year: int, lang: str = Query('es', description="Idioma: 'es' o 'en'")):
    """Obtener eventos y meses Bahá'ís para un año gregoriano en un solo endpoint"""
    try:
        # Obtener eventos
        events = get_bahai_events_for_gregorian_year(year, lang)
        
        # Obtener meses
        months_response = get_bahai_months(year, lang)
        months = months_response["months"]
        
        return {
            "year": year,
            "language": lang,
            "events": events,
            "months": months,
        }
    except Exception as e:
        logger.error(f"Error obteniendo datos completos: {e}")
        raise

@app.get("/ics/events/{year}", summary="Descargar archivo .ics solo con eventos Bahá'ís")
def get_events_ics(year: int, lang: str = Query('es', description="Idioma: 'es' o 'en'")):
    """Generar y descargar archivo .ics con eventos Bahá'ís del año"""
    try:
        # Obtener eventos
        events = get_bahai_events_for_gregorian_year(year, lang)
        
        # Crear calendario ICS
        calendar = create_ics_calendar(lang)
        calendar = add_events_to_calendar(calendar, events, lang)
        
        # Guardar en archivo temporal
        temp_file_path = save_calendar_to_temp_file(calendar, f"bahai_events_{year}")
        
        return FileResponse(
            temp_file_path, 
            filename=f"bahai_events_{year}.ics",
            media_type="text/calendar"
        )
    except Exception as e:
        logger.error(f"Error generando ICS de eventos: {e}")
        raise

@app.get("/ics/months/{year}", summary="Descargar archivo .ics solo con meses Bahá'ís")
def get_months_ics(year: int, lang: str = Query('es', description="Idioma: 'es' o 'en'")):
    """Generar y descargar archivo .ics con inicio de meses Bahá'ís"""
    try:
        # Obtener meses
        months_response = get_bahai_months(year, lang)
        months = months_response["months"]
        
        # Crear calendario ICS
        calendar = create_ics_calendar(lang)
        calendar = add_months_to_calendar(calendar, months, year, lang)
        
        # Guardar en archivo temporal
        temp_file_path = save_calendar_to_temp_file(calendar, f"bahai_months_{year}")
        
        return FileResponse(
            temp_file_path, 
            filename=f"bahai_months_{year}.ics",
            media_type="text/calendar"
        )
    except Exception as e:
        logger.error(f"Error generando ICS de meses: {e}")
        raise

@app.get("/ics/complete/{year}", summary="Descargar archivo .ics completo con eventos y meses")
def get_complete_ics(year: int, lang: str = Query('es', description="Idioma: 'es' o 'en'")):
    """Generar y descargar archivo .ics con eventos y meses Bahá'ís"""
    try:
        # Obtener eventos y meses
        events = get_bahai_events_for_gregorian_year(year, lang)
        months_response = get_bahai_months(year, lang)
        months = months_response["months"]
        
        # Crear calendario ICS
        calendar = create_ics_calendar(lang)
        calendar = add_events_to_calendar(calendar, events, lang)
        calendar = add_months_to_calendar(calendar, months, year, lang)

        # Guardar en archivo temporal
        temp_file_path = save_calendar_to_temp_file(calendar, f"Bahai Calendar {year}-{year+1}")
        
        return FileResponse(
            temp_file_path, 
            filename=f"Bahai Calendar {year}-{year+1}.ics",
            media_type="text/calendar"
        )
    except Exception as e:
        logger.error(f"Error generando ICS completo: {e}")
        raise

# Mantener endpoint original para compatibilidad
@app.get("/ics/{year}", summary="Descargar archivo .ics con eventos Bahá'ís (compatibilidad)")
def get_ics(year: int, lang: str = Query('es', description="Idioma: 'es' o 'en'")):
    """Generar y descargar archivo .ics con eventos Bahá'ís (redirige a eventos)"""
    return get_events_ics(year, lang)