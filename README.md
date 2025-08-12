<p align="center"><img src="static/assets/favicon.svg" alt="Parkit V1 logo" width="72"></p>

<h1 align="center">Parkit V1</h1>

<p align="center">A vehicle parking app for 4-wheelers. Drivers book a spot in a parking lot and pay by the hour. An admin manages the lots and sees which car is parked where.</p>

**Live demo:** https://parkitapp.vercel.app

| | |
|---|---|
| Program | IIT Madras BS in Data Science, Diploma level |
| Course | Modern Application Development I - Project ([BSCS2003P](https://study.iitm.ac.in/ds/course_pages/BSCS2003P.html)), 2 credits |
| Theory course | Modern Application Development I ([BSCS2003](https://study.iitm.ac.in/ds/course_pages/BSCS2003.html)), 4 credits |
| Problem statement | [Vehicle Parking App - V1](https://docs.google.com/document/u/3/d/e/2PACX-1vR9h1TDBhntxl1XA3tWalsCSVw_tqw8dUZ6TtXotYHwfAmtC_GHDTCq_NakeJuP_EKQFR2JIubjnmiH/pub) (May 2025 term) |
| Project guidelines | [MAD I project document](https://docs.google.com/document/u/3/d/e/2PACX-1vQXZXcz4tZukKB1SY1YgFBwQsc_gAgfr822JmzvhJMnOC-kc1mXzyguVmWoOtXpykO1spBO8VHsEVap/pub) |
| Grade | B |

The V2 of this app, built for MAD II with a Flask API, Vue, Redis and Celery, is [Parkit V2](https://github.com/theshivam7/ParkitOne).

## Demo logins

| Role | Email | Password |
|---|---|---|
| Admin | `admin@parkit.com` | `admin@123` |
| User | `demo@parkit.com` | `demo1234` |

## Demo

<p align="center"><a href="static/assets/brag.mp4"><img src="static/assets/brag.gif" alt="Parkit V1 demo"></a></p>

## Features

**Users**
- Search lots by name or PIN code and see free spots and price
- Book a spot (the first free one is assigned), then release it when leaving
- Live parking time and cost, booking history, and a spend chart

**Admin**
- Create, edit, and delete lots. Spots are created to match the lot size
- Spot map for each lot, showing which vehicle is parked where
- Search reservations by vehicle number, user, or lot. Export as CSV
- Occupancy and revenue charts, and a list of users

Billing: you pay for the booked hours, plus a full hour for every extra hour or part of one.

## Tech stack

![Flask](https://img.shields.io/badge/Flask-000000?logo=flask&logoColor=white) ![Jinja](https://img.shields.io/badge/Jinja-B41717?logo=jinja&logoColor=white) ![Bootstrap](https://img.shields.io/badge/Bootstrap-7952B3?logo=bootstrap&logoColor=white) ![HTML5](https://img.shields.io/badge/HTML5-E34F26?logo=html5&logoColor=white) ![CSS3](https://img.shields.io/badge/CSS3-1572B6?logo=css3&logoColor=white) ![Chart.js](https://img.shields.io/badge/Chart.js-FF6384?logo=chartdotjs&logoColor=white) ![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)

This is the stack the course requires. SQLite is created by the app on first run.

## Run it locally

```bash
git clone https://github.com/theshivam7/Parkit.git
cd Parkit
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5001. The first run creates `instance/database.db` with the admin, a demo user, three lots, and some past bookings. Delete that file to start fresh.

## Deploy on Vercel

Import the repo in Vercel and set a `SECRET_KEY` environment variable. SQLite lives in `/tmp` there.

## JSON API

| Endpoint | Who | Returns |
|---|---|---|
| `GET /api/stats` | Admin | Counts of lots, spots, occupied spots, users, active bookings |
| `GET /api/current-booking` | User | Your active booking: elapsed time, running cost, end time |

## Author

Built by [Shivam Sharma](https://www.linkedin.com/in/theshivam7/), a student in the IIT Madras BS in Data Science program. Parkit V1 is my project for [Modern Application Development I](https://study.iitm.ac.in/ds/course_pages/BSCS2003.html), one of the courses for the Diploma in Programming.
