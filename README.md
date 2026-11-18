## JobTrack — Job Application Tracker

**Student:** Mohsin Valliani  
**Course:** COP4751  
**Project:** Job Application Tracker

JobTrack is a web application I created for my COP4751 project using Python, Flask, and MySQL. It helps users keep track of companies, job postings, applications, and contacts all in one place. It also includes a skill-matching feature that compares skills with job requirements.

## Requirements
- Python 3.10 or newer
- MySQL Server 8.0 or newer
- Git

## Setup Instructions

1. Clone or download the repository and open the `job_tracker` folder.
2. Create a virtual environment: `python3 -m venv .venv`
3. Activate it: `source .venv/bin/activate`
4. Install the required packages: `pip install -r requirements.txt`
5. Run `schema.sql` in MySQL Workbench to create the database and tables.
6. Copy `.env.example` to `.env` and enter your MySQL login information and Flask secret key.
7. Start the application: `python3 app.py`
8. Open http://127.0.0.1:5000 in your browser.

**Windows:** Use `py -m venv .venv`, `.venv\Scripts\activate`, and `py app.py`.

## Main Features
- Add, view, edit, and delete companies, jobs, applications, and contacts.
- Dashboard showing application totals and recent activity.
- Skill matching that displays match percentages and missing skills.
- MySQL database with four related tables and JSON fields.

## Database
The database has four tables: `companies`, `jobs`, `applications`, and `contacts`. They are connected using foreign keys, and JSON fields are used to store job requirements and interview details.

## Submission
The GitHub repository includes the project code, database schema, README, and `AI_USAGE.md`. A 3–7 minute demonstration video is also required for the assignment.