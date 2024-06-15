from flask import Flask, request, jsonify, render_template
from flask import redirect, url_for
import json
from fuzzywuzzy import process
import re
import pandas as pd
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os



app = Flask(__name__)
def load_projects():
    json_file = "ProjectsCheckData.json"
    try:
        with open(json_file) as f:
            projects = json.load(f)
        projects = {k.lower(): v for k, v in projects.items()}
        print("JSON data loaded successfully!")
        return projects
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        return None

projects = load_projects()

@app.route('/get_matching_projects', methods=['GET'])
def get_matching_projects():
    input_text = request.args.get('input', '')
    if projects:
        matching_projects = [project for project, details in projects.items() if input_text.lower() in project.lower() or input_text.lower() in details['client'].lower()]
        return jsonify(matching_projects)
    else:
        return jsonify([])

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        data = request.get_json()
        user_name = data.get('user_name')
        user_query = data.get('query')

        if not user_name:
            return jsonify([{"error": "User name is missing."}])

        if projects is None:
            return jsonify([{"error": "Project data is not loaded."}])

        if check_basic_access(user_name):
            query_result = process_query(user_query, user_name)
        else:
            query_result = [{"error": "Access denied. You do not have permission to access this project information."}]

        return jsonify(query_result)
    return render_template('index.html')
def check_basic_access(user_name):
    if user_name and projects:
        access_set = set()
        for project in projects.values():
            access_set.update([admin.strip() for admin in project['admin_access'].split(",")])
            access_set.update([general.strip() for general in project['general_access'].split(",")])

        return user_name.strip() in access_set
    return False
def process_query(query, user_name):
    query = query.lower().strip()
    info_requested, project_name = extract_info_and_project(query)

    if not project_name:
        # If the project name is not found, use the language model to generate a response
        return [{"response": "sorry i am unable to understand you"}]

    if not check_access(user_name, project_name):
        return [{"error": "Access denied. You do not have permission to access this project information."}]

    project_details = projects[project_name]
    response = {}

    if 'user_id' in info_requested:
        response['user_id'] = project_details.get('user', "User ID not found for the specified project.")
    if 'password' in info_requested:
        response['password'] = project_details.get('password', "Password not found for the specified project.")
    if 'rera' in info_requested:
        response['rera'] = project_details.get('rera', "RERA no. not found for the specified project.")
    if 'email' in info_requested:
        response['email'] = project_details.get('email', "Email not found for the specified project.")
    if 'phone' in info_requested:
        response['phone'] = project_details.get('phone', "Phone number not found for the specified project.")
    if 'client' in info_requested:
        response['client'] = project_details.get('client', "not found for the specified project.")


    if 'login' in info_requested:
        user_id = project_details.get('user')
        password = project_details.get('password')
        if user_id and password:
            login_status = login_to_maharerait(user_id, password)
            response['login_status'] = login_status
        else:
            response['login_status'] = "User ID or password not found for the specified project."

    print(f"user input: {query}")
    print(f"machine response: {response}")

    return [response] if response else [{"error": "Query does not specify a valid request for user ID and/or password."}]
def extract_info_and_project(query):
    user_id_password_patterns = [
        r"user id and password for (.+)",r"password and user id for (.+)",r"passcode and user of (.+)",
        r"(.+) user id and password", r"i need user id and password of (.+)", r"what will be password and user for (.+)",
        r"password and userid for (.+)", r"userid and password for (.+)", r"user id and password (.+)", r"user id & password for (.+)",
        r"can I have the user ID and password for project (.+)?", r"can I have the user ID and password for (.+)?",
        r"what are the credentials for project (.+)?", r"please provide the username and password for project (.+).",
        r"i need the logon details for project (.+).",
        r"could you give me the user ID and password for project (.+)?",
        r"i'm looking for the user ID and password for project (.+).",
        r"how do I login to project (.+)? Do you have the login credentials?",
        r"can you share the login info for project (.+)?",
        r"i require the user ID and password to login to project (.+).",
        r"what's the login details for project (.+)?",
        r"give me the username and password for project (.+)",
        r"what login credentials do I need for project (.+)?",
        r"could you tell me the user ID and password for accessing project (.+)?",
        r"i'm trying to login to project (.+). What should I use for the user ID and password?",
        r"can I get the username and password for project (.+)?",
        r"can I have the user ID and password for (.+)?",
        r"what are the credentials for (.+)?",
        r"please provide the username and password for (.+).",
        r"I need the login details for (.+).",
        r"Could you give me the user ID and password for (.+)?",
        r"I'm looking for the user ID and password for (.+).",
        r"How do I login to (.+)? Do you have the login credentials?",
        r"Can you share the login info for (.+)?",
        r"I require the user ID and password to login to (.+).",
        r"What's the login details for (.+)?",
        r"Give me the username and password for (.+)",
        r"What login credentials do I need for (.+)?",
        r"Could you tell me the user ID and password for accessing (.+)?",
        r"I'm trying to login to (.+). What should I use for the user ID and password?",
        r"Can I get the username and password for (.+)?",
        r"login details of (.+)", r"login details for (.+)",
        r"give me password and user id of (.+)",
        r"password and user id of (.+)", r"give me username and password of (.+)", r"give me user id and password of (.+)",
        # Patterns for user id only
        r"user id for (.+)",
        r"username for (.+)",
        r"what is the user id for (.+)",
        r"give me user id for (.+) ",
        r"give me user id of (.+) ",
        r"i need userid of (.+)",
        r"(.+) user id", r"what will be the userid of (.+)", r"user id for (.+)",
        r"username for (.+)",
        r"what is the user id for (.+)",
        r"give me user id for (.+)",
        r"give me user id of (.+)",
        r"i need userid of (.+)",
        r"(.+) user id",
        r"what will be the userid of (.+)",
        r"can i have the user id for (.+)",
        r"could you provide the user id for (.+)",
        r"please give me the user id for (.+)",
        r"may i have the user id for (.+)",
        r"provide the user id for (.+)",
        r"what's the user id for (.+)",
        r"tell me the user id for (.+)",
        r"i need the user id for (.+)",
        r"user name for (.+)",
        r"user name of (.+)",
        r"user id of (.+)",
        r"(.+) user name",
        r"user name of (.+)",
        r"what is the user name for (.+)",
        r"whats the user id for (.+)",
        r"what is user id of (.+)",
        r"give user id for (.+)",
        r"can you provide the user id for (.+)",
        r"need user id for (.+)",
        r"user id needed for (.+)",
        r"user id please for (.+)",
        r"what's the username for (.+)",
        r"whats the username for (.+)",
        r"whats the username of (.+)",
        r"give me the username for (.+)",
        r"give me the username of (.+)",
        r"i need the username of (.+)",
        r"i need username of (.+)",
        r"(.+) username",
        r"(.+) userid",
        r"(.+) usr id",
        r"(.+) usrname",
        r"what is the userid for (.+)",
        r"what's the userid for (.+)",
        r"whats the userid for (.+)",
        r"(.+) user id please",
        r"(.+) username please",
        r"can i get the user id for (.+)",
        r"can i get the username for (.+)",
        r"i need user id for (.+)",
        r"i need username for (.+)",
        r"can you tell me the user id for (.+)",
        r"can you tell me the username for (.+)",
        r"i want the user id for (.+)",
        r"i want the username for (.+)",
        r"i want userid for (.+)",
        r"i want username for (.+)",
        r"can you share the user id for (.+)",
        r"can you share the username for (.+)",
        r"let me know the user id for (.+)",
        r"let me know the username for (.+)",
        r"whats user id for (.+)",
        r"whats user name for (.+)",
        r"what user id for (.+)",
        r"what user name for (.+)",
        r"i need user for (.+)",
        r"give user for (.+)",
        r"can i get user for (.+)",
        r"can you provide user for (.+)",
        r"user id plz for (.+)",
        r"userid plz for (.+)",
        r"username plz for (.+)",
        r"user id pls for (.+)",
        r"userid pls for (.+)",
        r"username pls for (.+)",
        r"user id plese for (.+)",
        r"userid plese for (.+)",
        r"username plese for (.+)",
        r"userid for (.+)",
        r"username for (.+)",
        r"user-id for (.+)",
        r"user-name for (.+)",
        r"usr-id for (.+)",
        r"usr-name for (.+)",
        r"i need usrname for (.+)",
        r"i need usrname of (.+)",
        r"i need user id of (.+) ",
        r"i need userid (.+)",

        # Patterns for password only
        r"password for (.+)",r"passcode for (.+)",r"what is the password for (.+)", r"password of (.+)", r"password of (.+)",
        r"what is the password for (.+)",r"give me password for (.+) ",r"give me password of (.+) ",
        r"i need password of (.+)", r"(.+) password", r"what will be the password of (.+)",

        # Patterns for Contact info
        r"phone no for (.+)", r"phone for (.+)", r"what is the phone for (.+)", r"contact of (.+)",
        r"phone of (.+)",
        r"what is the phone no for (.+)", r"give me phone no for (.+) ", r"give me number of (.+) ",
        r"i need phone of (.+)", r"(.+) contact",r"(.+) phone", r"what will be the contact of (.+)",
        r"contact for (.+)",

        #patterns for rera no.
        r"give me rera no. of (.+)",
        r"what is the rera no for (.+)",
        r"i want rera of (.+)", r"i want rera for (.+)", r"rera no. of (.+)", r"rera (.+)", r"(.+) rera",

        #Patterns for email.
        r"give me email of (.+)",
        r"what is the email id for (.+)",
        r"i want email of (.+)", r"i want email for (.+)", r"email id of (.+)", r"email id (.+)", r"(.+) email",
        r"email (.+)",

        #patterns for email and phone,
        r"i need email and contact for (.+)",
        r"give me contact and email of (.+)",
        r"contact and email of (.+)", r"contact and email for (.+)",
        r"(.+) email id and contact", r"(.+) email and contact", r"email of (.+)", r"email for (.+)",
        r"give me email and phone for (.+)",
        r"email and contact for (.+)", r"email and contact of (.+)",

        # Auto Login Statements
        r"please login for (.+)",
        r"login for (.+)",
        r"login (.+)",
        r"rera login of (.+)",
        r"login on portal for (.+)",
        r"(.+) login",

        # Patterns for client name
        r"client of (.+)", r"client for (.+)",
        r"client name for (.+)", r"client name of (.+)",
        r"who is the client for (.+)",
        r"developer of (.+)", r"developer for (.+)",
        r"developer name for (.+)", r"developer name of (.+)",
        r"who is the developer for (.+)",
        r"promoter of (.+)", r"promoter for (.+)",
        r"promoter name for (.+)", r"promoter name of (.+)",
        r"who is the promoter for (.+)"
    ]

    info_requested = []
    project_name = None

    for pattern in user_id_password_patterns:
        match = re.search(pattern, query)
        if match:
            project_name = match.group(1).strip().lower()
            if 'login' in pattern or 'log in' in pattern:
                info_requested.append('login')
            if 'user id' in pattern or 'username' in pattern or 'user name' in pattern or 'userid' in pattern or 'user' in pattern:
                info_requested.append('user_id')
            if 'password' in pattern or 'passcode' in pattern:
                info_requested.append('password')
            if 'rera' in pattern:
                info_requested.append('rera')
            if 'phone' in pattern or 'contact' in pattern or 'phone no.' in pattern or 'contact no.' in pattern:
                info_requested.append('phone')
            if 'email' in pattern or 'email id' in pattern or 'emailid' in pattern or 'email address' in pattern:
                info_requested.append('email')
            if 'client' in pattern or 'client name' in pattern or 'promoter name' in pattern or 'promoter' in pattern or 'developer' in pattern:
                info_requested.append('client')
            break

    if project_name:
        project_name = extract_project_name(project_name)
        if project_name:
            return info_requested, project_name
    return None, None
def extract_project_name(query):
    project_names = list(projects.keys())
    closest_match, confidence = process.extractOne(query, project_names)
    if confidence > 70:
        return closest_match
    return None
def check_access(user_name, project_name):
    user_name = user_name.strip()
    project_info = projects[project_name]

    access_list = [admin.strip() for admin in project_info['admin_access'].split(',')] + \
                  [general.strip() for general in project_info['general_access'].split(',')]

    print(f"user_name requested: {user_name}")
    print(f"access list: {access_list}")

    return user_name in access_list
from playwright.sync_api import sync_playwright
import time

def login_to_maharerait(user_id, password):
    with sync_playwright() as p:
        # Launch a headless browser instance
        browser = p.chromium.launch(headless=False)  # Set headless=True for background operation
        page = browser.new_page()

        try:
            # Navigate to the login page
            page.goto("https://maharerait.mahaonline.gov.in/")

            # Wait for the username field and enter the user ID
            page.fill('input[id="UserName"]', user_id)

            # Wait for the password field and enter the password
            page.fill('input[id="Password"]', password)

            # Inform the user to complete the CAPTCHA and login manually
            print("User ID and Password entered. Please complete the CAPTCHA and login manually.")

            # Keep the browser open to allow manual CAPTCHA solving
            time.sleep(600)  # Wait for 10 minutes

        except Exception as e:
            print(f"An error occurred: {e}")

        finally:
            # Do not close the browser, leaving control to the user
            pass


# Route for admin page and authentication
@app.route('/admin', methods=['GET', 'POST'])
def admin_page():
    if request.method == 'POST':
        user_id = request.form.get('user_name')
        if check_admin_access(user_id):
            # Allow access to admin page and file uploading
            return render_template('admin.html', allow_upload=True, user_id=user_id)
        else:
            # Deny access and display error message
            return render_template('access_denied.html')

    # Render admin page without file uploader initially
    return render_template('admin.html', allow_upload=False)

@app.route('/upload', methods=['POST'])
def upload_file():
    user_id = request.form.get('user_name')
    if not check_admin_access(user_id):
        return jsonify({'error': 'Access denied'})

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})

    try:
        file_path = 'uploads/' + file.filename
        file.save(file_path)
        json_generator(file_path)
        return jsonify({'success': 'Database updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)})
# Check admin access based on user ID
def check_admin_access(user_id):
    if user_id and projects:
        for project in projects.values():
            admin_access = project.get('admin_access', '').lower().split(', ')
            if user_id.lower() in admin_access:
                return True
    return False
def json_generator(input_file):
    # Read the Excel sheet
    if input_file.endswith('.csv'):
        df = pd.read_csv(input_file)
    elif input_file.endswith('.xlsx'):
        df = pd.read_excel(input_file)
    else:
        raise ValueError("Unsupported file format. Please provide a CSV or Excel file.")

    # Convert DataFrame to JSON
    json_data = {}
    for index, row in df.iterrows():
        project_name = row['project_name']
        json_data[project_name] = {
            "rera": row['rera'],
            "client": row['client_name'],
            "email": row['email'],
            "phone": row['phone'],
            "user": row['user_id'],
            "password": row['password'],
            "admin_access": row['admin_access'],
            "general_access": row['general_access']
        }

    # Save JSON data to a file
    with open('ProjectsCheckData.json', 'w') as json_file:
        json.dump(json_data, json_file, indent=4)


