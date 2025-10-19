# Bahá'í Calendar API

A FastAPI-based web service that generates Bahá'í (Badi) calendar events and exports them in iCalendar (.ics) format for easy import into Apple Calendar, Google Calendar, and other calendar applications.

## 🌟 Features

- **Complete Bahá'í Calendar Events**: Generates all major Bahá'í holy days, feasts, and observances
- **19-Day Feast Dates**: Calculates the first day of each of the 19 Bahá'í months
- **Ayyám-i-Há Dates**: Includes intercalary days (varies between 4-5 days depending on the year)
- **Fasting Period**: Marks the beginning and end of the 19-day fast
- **Multiple Languages**: Supports English and Spanish translations
- **iCalendar Export**: Downloads events as .ics files compatible with all major calendar apps
- **RESTful API**: Clean JSON endpoints for integration with other applications
- **Interactive Documentation**: Built-in Swagger UI for easy testing and exploration

## 📅 Supported Events

### Holy Days

- Naw-Rúz (Bahá'í New Year)
- First, Ninth, and Twelfth Days of Riḍván
- Declaration of the Báb
- Ascension of Bahá'u'lláh
- Martyrdom of the Báb
- Birth of the Báb
- Birth of Bahá'u'lláh
- Day of the Covenant
- Ascension of 'Abdu'l-Bahá

### Other Observances

- 19-Day Feasts (first day of each Bahá'í month)
- Ayyám-i-Há (intercalary days)
- Fast period (beginning and end)

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip

### Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd badi-datetime
```

2. Install dependencies:

```bash
pip install -r fastapi/requirements.txt
```

3. Run the development server:

```bash
cd fastapi
uvicorn app.main:app --reload
```

4. Open your browser and navigate to:
   - API Documentation: `http://localhost:8000/docs`
   - Alternative docs: `http://localhost:8000/redoc`

## 📖 API Usage

### Get All Events for a Year

```bash
curl "http://localhost:8000/events/2024?lang=en"
```

### Download iCalendar File

```bash
curl "http://localhost:8000/ics/complete/2024?lang=en" --output bahai_calendar_2024.ics
```

### Get Month Information

```bash
curl "http://localhost:8000/bahai-months/2024?lang=es"
```

## 🌐 API Endpoints

| Endpoint               | Description                             | Output         |
| ---------------------- | --------------------------------------- | -------------- |
| `/events/{year}`       | Get all Bahá'í events for a year        | JSON           |
| `/bahai-months/{year}` | Get first day of each Bahá'í month      | JSON           |
| `/complete/{year}`     | Get both events and months              | JSON           |
| `/ics/events/{year}`   | Download events as .ics file            | iCalendar file |
| `/ics/months/{year}`   | Download month starts as .ics file      | iCalendar file |
| `/ics/complete/{year}` | Download complete calendar as .ics file | iCalendar file |

### Query Parameters

- `year`: Gregorian year (required)
- `lang`: Language code - `en` (English) or `es` (Spanish, default)

## 🔧 Technical Details

### Dependencies

- **FastAPI**: Modern, fast web framework for building APIs
- **badidatetime**: Bahá'í calendar calculations library
- **ics**: iCalendar file generation
- **uvicorn**: ASGI server for running the application

### Calendar Calculations

The API uses the `badidatetime` library which provides accurate Bahá'í calendar calculations based on:

- Astronomical sunset times
- Proper handling of intercalary days (Ayyám-i-Há)
- Accurate conversion between Gregorian and Badi dates
- Geographic location considerations for sunset calculations

### Date Handling

- Events begin at sunset of the previous Gregorian day
- All exported dates are automatically adjusted for proper calendar display
- Supports leap years and varying Ayyám-i-Há lengths

## 🌍 Internationalization

The application supports multiple languages through JSON translation files:

- English (`translations/en.json`)
- Spanish (`translations/es.json`)

Event names, descriptions, and month names are fully localized.

## 📱 Calendar Integration

### Importing to Apple Calendar

1. Download the .ics file from the API
2. Double-click the file or use "File > Import" in Calendar
3. Choose the destination calendar

### Importing to Google Calendar

1. Download the .ics file from the API
2. Go to Google Calendar settings
3. Click "Import & export" > "Import"
4. Select the .ics file

### Other Calendar Apps

The generated .ics files follow the iCalendar standard (RFC 5545) and should work with most calendar applications including Outlook, Thunderbird, and mobile calendar apps.

## 🔗 References

- [Badidatetime Documentation](https://badidatetime.readthedocs.io/en/latest/)
- [Bahá'í Calendar GitHub Repository](https://github.com/cnobile2012/bahai-calendar)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [iCalendar Specification (RFC 5545)](https://tools.ietf.org/html/rfc5545)
