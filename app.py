import json
import os
from datetime import date
from urllib.parse import urlparse

from flask import Flask, flash, redirect, render_template, request, url_for, abort
from mysql.connector import Error, IntegrityError
from dotenv import load_dotenv
from database import query, execute

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'local-development-only-change-me')

# The four database entities, with labels and form metadata.
TABLES = {
    'companies': {
        'pk': 'company_id', 'title': 'Companies', 'display': 'company_name',
        'fields': [('company_name','Company name','text',True),('industry','Industry','text',False),
                   ('website','Website','url',False),('city','City','text',False),
                   ('state','State','text',False),('notes','Notes','textarea',False)]},
    'jobs': {
        'pk': 'job_id', 'title': 'Jobs', 'display': 'job_title',
        'fields': [('company_id','Company','company',False),('job_title','Job title','text',True),
                   ('job_type','Job type','job_type',False),('salary_min','Minimum salary','number',False),
                   ('salary_max','Maximum salary','number',False),('job_url','Job URL','url',False),
                   ('date_posted','Date posted','date',False),('requirements','Required skills (comma-separated)','skills',False)]},
    'applications': {
        'pk': 'application_id', 'title': 'Applications', 'display': 'application_id',
        'fields': [('job_id','Job','job',False),('application_date','Application date','date',True),
                   ('status','Status','status',False),('resume_version','Resume version','text',False),
                   ('cover_letter_sent','Cover letter sent','checkbox',False),
                   ('interview_data','Interview details (JSON object)','json',False)]},
    'contacts': {
        'pk': 'contact_id', 'title': 'Contacts', 'display': 'contact_name',
        'fields': [('company_id','Company','company',False),('contact_name','Contact name','text',True),
                   ('title','Title','text',False),('email','Email','email',False),
                   ('phone','Phone','text',False),('linkedin_url','LinkedIn URL','url',False),
                   ('notes','Notes','textarea',False)]},
}

JOB_TYPES = ['Full-time', 'Part-time', 'Contract', 'Internship']

STATUSES = ['Applied', 'Screening', 'Phone Screen', 'Interview Scheduled', 'Interview Completed', 'Interview', 'Offer', 'Rejected', 'Withdrawn']


@app.template_filter('fromjson')
def fromjson(value):
    return skills_from_json(value)

@app.context_processor
def globals_for_templates():
    return {'tables': TABLES, 'job_types': JOB_TYPES, 'statuses': STATUSES}

def table_config(table):
    if table not in TABLES:
        abort(404)
    return TABLES[table]

def dropdowns():
    return {'companies': query('SELECT company_id, company_name FROM companies ORDER BY company_name'),
            'jobs': query('SELECT j.job_id, j.job_title, c.company_name FROM jobs j LEFT JOIN companies c ON j.company_id=c.company_id ORDER BY j.job_title')}

def validate_url(value):
    if value:
        parsed = urlparse(value)
        if parsed.scheme not in ('http','https') or not parsed.netloc:
            raise ValueError('URLs must begin with http:// or https://')
    return value

def parse_form(table):
    data = {}
    for name, label, kind, required in TABLES[table]['fields']:
        raw = request.form.get(name, '').strip()
        if kind == 'checkbox':
            data[name] = 1 if request.form.get(name) == 'on' else 0
            continue
        if required and not raw:
            raise ValueError(f'{label} is required.')
        if kind in ('company','job','number'):
            if raw:
                try:
                    number = int(raw)
                except ValueError:
                    raise ValueError(f'{label} must be a whole number.')
                if number < 0 or (kind in ('company','job') and number < 1):
                    raise ValueError(f'{label} must be positive.')
                data[name] = number
            else:
                data[name] = None
        elif kind == 'skills':
            # Store skills as a JSON array in MySQL.
            skills = list(dict.fromkeys(s.strip() for s in raw.split(',') if s.strip()))
            data[name] = json.dumps(skills)
        elif kind == 'json':
            try:
                parsed = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                raise ValueError(f'{label} must be valid JSON.')
            if not isinstance(parsed, dict):
                raise ValueError(f'{label} must be a JSON object.')
            data[name] = json.dumps(parsed)
        elif kind == 'job_type':
            if raw and raw not in JOB_TYPES: raise ValueError('Invalid job type.')
            data[name] = raw or None
        elif kind == 'status':
            if raw and raw not in STATUSES: raise ValueError('Invalid status.')
            data[name] = raw or None
        elif kind == 'url':
            data[name] = validate_url(raw) or None
        elif kind == 'date':
            if raw:
                try: date.fromisoformat(raw)
                except ValueError: raise ValueError(f'{label} must be a valid date.')
            data[name] = raw or None
        else:
            data[name] = raw or None
    if table == 'jobs' and data['salary_min'] is not None and data['salary_max'] is not None and data['salary_min'] > data['salary_max']:
        raise ValueError('Minimum salary cannot exceed maximum salary.')
    return data

@app.route('/')
def dashboard():
    counts = {t: query(f'SELECT COUNT(*) AS n FROM {t}', one=True)['n'] for t in TABLES}
    statuses = query('SELECT status, COUNT(*) AS total FROM applications GROUP BY status ORDER BY total DESC')
    recent = query('''SELECT a.application_id, a.application_date, a.status, j.job_title, c.company_name
                      FROM applications a LEFT JOIN jobs j ON a.job_id=j.job_id
                      LEFT JOIN companies c ON j.company_id=c.company_id
                      ORDER BY a.application_date DESC, a.application_id DESC LIMIT 8''')
    return render_template('dashboard.html', counts=counts, status_counts=statuses, recent=recent)

@app.route('/<table>')
def records(table):
    config = table_config(table)
    pk = config['pk']
    if table == 'jobs':
        rows = query('SELECT j.*, c.company_name FROM jobs j LEFT JOIN companies c ON j.company_id=c.company_id ORDER BY j.job_id DESC')
    elif table == 'applications':
        rows = query('''SELECT a.*, j.job_title, c.company_name FROM applications a
                        LEFT JOIN jobs j ON a.job_id=j.job_id LEFT JOIN companies c ON j.company_id=c.company_id
                        ORDER BY a.application_id DESC''')
    elif table == 'contacts':
        rows = query('SELECT ct.*, c.company_name FROM contacts ct LEFT JOIN companies c ON ct.company_id=c.company_id ORDER BY ct.contact_id DESC')
    else:
        rows = query('SELECT * FROM companies ORDER BY company_id DESC')
    return render_template('records.html', table=table, config=config, rows=rows)

@app.route('/<table>/new', methods=['GET','POST'])
def new_record(table):
    config = table_config(table)
    if request.method == 'POST':
        try:
            data = parse_form(table)
            columns = ', '.join(data)
            placeholders = ', '.join(['%s'] * len(data))
            execute(f'INSERT INTO {table} ({columns}) VALUES ({placeholders})', tuple(data.values()))
            flash('Record added successfully.', 'success')
            return redirect(url_for('records', table=table))
        except (ValueError, Error) as exc:
            flash(f'Could not save: {exc}', 'error')
    return render_template('form.html', table=table, config=config, record=None, options=dropdowns(), editing=False)

@app.route('/<table>/<int:record_id>/edit', methods=['GET','POST'])
def edit_record(table, record_id):
    config = table_config(table)
    pk = config['pk']
    record = query(f'SELECT * FROM {table} WHERE {pk}=%s', (record_id,), one=True)
    if not record: abort(404)
    if request.method == 'POST':
        try:
            data = parse_form(table)
            assignments = ', '.join(f'{key}=%s' for key in data)
            execute(f'UPDATE {table} SET {assignments} WHERE {pk}=%s', (*data.values(), record_id))
            flash('Record updated successfully.', 'success')
            return redirect(url_for('records', table=table))
        except (ValueError, Error) as exc:
            flash(f'Could not save: {exc}', 'error')
    return render_template('form.html', table=table, config=config, record=record, options=dropdowns(), editing=True)

@app.route('/<table>/<int:record_id>/delete', methods=['POST'])
def delete_record(table, record_id):
    config = table_config(table)
    try:
        execute(f'DELETE FROM {table} WHERE {config["pk"]}=%s', (record_id,))
        flash('Record deleted.', 'success')
    except IntegrityError:
        flash('Cannot delete this record while other records reference it. Delete dependent records first.', 'error')
    except Error as exc:
        flash(f'Delete failed: {exc}', 'error')
    return redirect(url_for('records', table=table))

def skills_from_json(value):
    try:
        data = json.loads(value) if isinstance(value, str) else value
        if isinstance(data, list):
            return [str(item).strip() for item in data if str(item).strip()]
        if isinstance(data, dict):
            return [str(item).strip() for item in data.get('skills', []) if str(item).strip()]
    except (ValueError, TypeError):
        pass
    return []

def calculate_matches(user_skills, required_skills):
    user = {s.casefold() for s in user_skills}
    required = list(dict.fromkeys(s for s in required_skills if s.strip()))
    matching = [s for s in required if s.casefold() in user]
    missing = [s for s in required if s.casefold() not in user]
    percentage = round(100 * len(matching) / len(required)) if required else 0
    return {'percentage': percentage, 'matching': matching, 'missing': missing, 'total': len(required)}

@app.route('/job-match', methods=['GET','POST'])
def job_match():
    raw = request.form.get('skills', '') if request.method == 'POST' else ''
    user_skills = list(dict.fromkeys(s.strip() for s in raw.split(',') if s.strip()))
    results = []
    if request.method == 'POST':
        jobs = query('SELECT j.job_id, j.job_title, j.requirements, c.company_name FROM jobs j LEFT JOIN companies c ON j.company_id=c.company_id')
        for job in jobs:
            match = calculate_matches(user_skills, skills_from_json(job['requirements']))
            results.append({**job, **match})
        results.sort(key=lambda j: (-j['percentage'], -len(j['matching']), j['job_title'].casefold()))
    return render_template('job_match.html', raw=raw, results=results, searched=request.method == 'POST')

if __name__ == '__main__':
    app.run(debug=True)
