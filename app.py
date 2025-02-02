from flask import Flask, render_template, request, redirect, url_for, flash, session as flask_session
import requests
import json

app = Flask(__name__)
app.secret_key = "7dc848c512eed53b1c2fb55cdf60262d27266cab1dc1207ac8cc3dd38a5f7ad7"
LOGIN_URL = "https://sahrdaya.etlab.in/user/login"
LOGOUT_URL = "https://sahrdaya.etlab.in/user/logout"
REFERRER = "https://sahrdaya.etlab.in/ktuacademics/student/viewattendancesubjectdutyleave/16"

try:
    with open("courses.json", "r") as json_file:
        sub = json.load(json_file)
except FileNotFoundError:
    sub = {}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Content-Type": "application/x-www-form-urlencoded",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Priority": "u=0, i"
}

PAYLOAD = {
    "format": "csv",

}

@app.route('/')
def home():
    flask_session.clear()
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    flask_session.clear()
    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        flash('Username and password are required.', 'danger')
        return redirect(url_for('home'))

    with requests.Session() as session:
        login_payload = {
            "LoginForm[username]": username,
            "LoginForm[password]": password,
            "yt0": ""
        }
        try:
            login_response = session.post(LOGIN_URL, headers=HEADERS, data=login_payload, timeout=10)
            login_response.raise_for_status()
        except requests.RequestException as e:
            flash(f'Error logging in: {e}', 'danger')
            return redirect(url_for('home'))

        if "Invalid" not in login_response.text:
            flash('Logged in successfully!', 'success')
            flask_session['session_cookies'] = json.dumps(session.cookies.get_dict())
            return redirect(url_for('display'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')
            return redirect(url_for('home'))

def calculate_additional_classes(attended, total, target_percentage=75):
    if total <= 0:
        return 0, ""
    current_percentage = (attended / total) * 100
    if current_percentage >= target_percentage:
        additional_needed = int(((attended * 100) / target_percentage) - total)
        direction = "less"
    else:
        additional_needed = int((attended - (target_percentage * total) / 100) / ((target_percentage / 100) - 1))
        direction = "more"
    return additional_needed, direction

@app.route('/display')
def display():
    if 'session_cookies' not in flask_session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('home'))

    target_percentage = request.args.get('p', default=75, type=int)

    if 'attendance_data' not in flask_session:
        cookies = json.loads(flask_session['session_cookies'])
        with requests.Session() as session_instance:
            session_instance.cookies.update(cookies)
            try:
                response = session_instance.post(REFERRER, headers=HEADERS, data=PAYLOAD, timeout=10)
                response.raise_for_status()
            except requests.RequestException as e:
                flash(f'Error fetching attendance data: {e}', 'danger')
                return redirect(url_for('home'))

            lines = response.text.splitlines()
            header = lines[1].replace('"', '').split(',')
            data = lines[2].replace('"', '').split(',')
            details_dict = dict(zip(header, data))

            flask_session['attendance_data'] = details_dict

            try:
                session_instance.get(LOGOUT_URL, headers=HEADERS)
            except requests.RequestException as e:
                flash(f'Error logging out: {e}', 'warning')
    else:
        details_dict = flask_session['attendance_data']

    name = details_dict.get("Name", "Unknown")
    Uni_Reg_No = details_dict.get("Uni Reg No", "N/A")
    Roll_no = details_dict.get("Roll No", "N/A")
    data_lines = []
    for subject, attendance in details_dict.items():
        subject_name = sub.get(subject, subject)
        if '/' in attendance:
            attended, total = map(int, attendance.split(' ')[0].split('/'))
            additional_needed, direction = calculate_additional_classes(attended, total, target_percentage)
            current = round((attended / total) * 100,2) if total > 0 else 0
            data_lines.append(f"For {subject_name}: Attended {attended}/{total} ({current}%). To reach {target_percentage}%, attend {additional_needed} {direction} classes.")

    return render_template('display.html', name=name, Uni_Reg_No=Uni_Reg_No, Roll_no=Roll_no, data_lines=data_lines,target_percentage=target_percentage)

if __name__ == '__main__':
    app.run()
