# Trucking Logistics App

A full-stack application for calculating trucking routes and generating HOS-compliant ELD logs.

## Tech Stack
- **Backend:** Django, Django REST Framework
- **Frontend:** React, Vite, Leaflet, Chart.js
- **APIs:** Nominatim (Geocoding), OpenRouteService (Routing)

## Prerequisites
- Python 3.10+
- Node.js 18+

## Setup & Running Locally

### 1. Backend (Django)
```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
The API will be available at `http://127.0.0.1:8000/`.

### 2. Frontend (React)
Open a new terminal:
```bash
cd frontend
npm install
npm run dev
```
The app will be available at `http://localhost:5173/`.

## Environment Variables
The backend requires an `.env` file in `backend/` with:
```
ORS_API_KEY=your_key_here
```
(A default key is configured in the code for this assessment).

## Testing
To run backend unit tests:
```bash
cd backend
python manage.py test api
```
## Deployment
- **Backend:** Ready for Railway/Render (includes `Procfile`).
- **Frontend:** Ready for Vercel.
