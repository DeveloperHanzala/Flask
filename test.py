import re
import openai
from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium.webdriver.common.by import By
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import time
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import threading
from flask import Flask
from pyngrok import ngrok
import os

app = Flask(__name__)
# Allow CORS from localhost:3000 with specific methods and headers
# CORS(app, resources={r"/*": {"origins": "http://localhost:3000", "methods": ["POST", "GET", "OPTIONS", "PUT", "DELETE"], "allow_headers": ["Content-Type"]}})
CORS(app, supports_credentials=True, origins=["https://localhost:3000"])

openai.api_key = ('sk-proj-hmQSzOkvXzzpDqm6A0Zy-A9bWYGArHXUq2TBBBuod4B'
                  '-74YZ696OoGohZ6USEwv4EBJ3djlh2vT3BlbkFJQ_4L_xEERm_HjdKlvrr1'
                  '-rW8MI96aCX9g8rHFe94cOZtweDozGpqGyw2cNV1cTJ13DSRf4TYcA')
# Replace with your actual API key  # Replace with your actual API key
# Oxylabs Proxy credentials
USERNAME = 'linkedinai927_mfjQF'
PASSWORD = 'Linkedinai927='
ENDPOINT = "pr.oxylabs.io:7777"

scraped_data = {}
user_responses = {}


# Proxy configuration function
def chrome_proxy(user: str, password: str, endpoint: str) -> dict:
    wire_options = {
        "proxy": {
            "http": f"http://{user}:{password}@{endpoint}",
            "https": f"https://{user}:{password}@{endpoint}",
        }
    }
    return wire_options


# Set up Selenium with proxy
def setup_driver_with_proxy():
    options = Options()
    options.add_argument('--start-maximized')

    # Set up the proxy using selenium-wire's proxy option
    # proxies = chrome_proxy(USERNAME, PASSWORD, ENDPOINT)

    # Initialize the Chrome driver with the proxy settings
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        # seleniumwire_options=proxies,
        options=options
    )
    return driver


# Function to validate LinkedIn URL
def validate_linkedin_url(url):
    linkedin_regex = r'^https?:\/\/(www\.)?linkedin\.com\/in\/[a-zA-Z0-9\-]+\/?$'
    return re.match(linkedin_regex, url) is not None


# Scrape the profile data
def scrape_linkedin_profile(linkedin_url):
    global scraped_data
    driver = setup_driver_with_proxy()

    # Login process
    driver.get('https://www.linkedin.com/checkpoint/lg/login')
    time.sleep(3)
    username = driver.find_element(By.ID, 'username')
    username.send_keys("applebananax1222@gmail.com")
    password = driver.find_element(By.ID, 'password')
    password.send_keys("MH11gaming")
    time.sleep(5)
    send_btn = driver.find_element(By.XPATH, '//*[@id="organic-div"]/form/div[3]/button')
    send_btn.click()
    time.sleep(5)
    input('wait')

    # Navigate to the LinkedIn profile
    driver.get(linkedin_url)
    time.sleep(5)

    try:
        try:
        # Scrape name, headline, and summary
            name = driver.find_element(By.CLASS_NAME, 'v-align-middle').text.strip()
        except:
            pass
        try:
            headline = driver.find_element(By.CSS_SELECTOR, "div.text-body-medium").text.strip()
        except:
            pass
        try:
            summary = driver.find_element(By.XPATH,
                                      '//*[@id="profile-content"]/div/div[2]/div/div/main/section[2]/div[3]/div/div/div/span[1]').text.strip()
        except:
            pass

        # Store the data
        scraped_data = {
            'name': name,
            'headline': headline,
            'summary': summary,
            'experience': [],
            'education': [],
            'skills': []
        }

        # Scrape experience, education, and skills sections
        sections = ['experience', 'education', 'skills']
        for section in sections:
            scrape_linkedin_section(driver, linkedin_url, section)

    except Exception as e:
        print(f"Error scraping profile: {e}")
    finally:
        driver.quit()


# Function to generate suggestions using OpenAI API
def generate_suggestions(profile_data):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user",
                   "content": f"Analyze the following LinkedIn profile data and provide suggestions for optimization "
                              f"and only rewrite it section by section :\n\n{profile_data}"}]
    )
    suggestions = response['choices'][0]['message']['content']
    return suggestions


# Function to dynamically scrape LinkedIn sections
def scrape_linkedin_section(driver, linkedin_url, section):
    global scraped_data

    section_url = f"{linkedin_url}/details/{section}/"
    driver.get(section_url)
    time.sleep(10)

    if section == "experience":
        try:
            # Locate the experiences using a more precise selector and filter duplicates
            experience_elements = driver.find_elements(By.CLASS_NAME, 'pvs-list__item--line-separated')

            # Initialize a list to store the formatted experiences
            unique_experiences = []

            # Loop through each experience element and extract relevant details
            for exp_element in experience_elements:
                e_text = exp_element.text.strip()

                # Replace 'to' with '-' to standardize date formats
                e_text = e_text.replace(" to ", " - ")

                # Split the text based on new lines (this helps with removing duplicated lines)
                lines = e_text.split("\n")

                # Use a set to filter out any repeated lines within the same experience block
                unique_lines = list(dict.fromkeys(lines))  # dict.fromkeys() preserves order and removes duplicates

                # Rejoin the filtered lines back into a single string for that experience (without newlines)
                formatted_experience = " ".join(unique_lines)  # Joins with a space instead of a newline

                # Check if the experience has already been added (to avoid duplicates across all experiences)
                if formatted_experience not in unique_experiences:
                    unique_experiences.append(formatted_experience)

            # Store the formatted unique experiences in the scraped_data object
            scraped_data['experience'] = unique_experiences

        except:
            print(f"Error scraping experience section")
            pass

    elif section == "education":
        try:
            # Find all education elements
            educations = driver.find_elements(By.XPATH,
                                              '//*[@id="profile-content"]/div/div[2]/div/div/main/section/div[2]/div/div[1]/ul/li')
            num_positions = len(educations)
            print(f"Found {num_positions} education entries.")

            # Extract institute names/details
            education_Details = driver.find_elements(By.CSS_SELECTOR, '.display-flex a span[aria-hidden="true"]')
            education_details = []

            # Adjust the range if num_positions == 1
            if num_positions == 1:
                loop_range = num_positions + 2
            else:
                loop_range = num_positions * num_positions

            # Ensure the loop runs according to the number of education entries found
            for i in range(loop_range):
                if i < len(education_Details):  # Prevent index error
                    education_text = education_Details[i].text.strip()
                    print(f"Institute Details: {education_text}")
                    education_details.append(education_text)
                else:
                    print(f"Institute Details: Not found for education at index {i}")
                    education_details.append("Details not found")

            scraped_data['education'] = education_details  # Save the education details
        except:
            print(f"Error scraping education section")
            pass

    elif section == "skills":
        try:
            skills = driver.find_elements(By.CSS_SELECTOR,
                                          '[data-field="skill_page_skill_topic"] div div div div span[aria-hidden="true"]')

            skill_details = []

            for s in skills:
                skill_text = s.text.strip().replace(",", '')

                # Only append non-empty skills
                if skill_text:
                    skill_details.append(skill_text)
                    print(f"Skill : {skill_text}")

            # Save the skills details only if there are skills
            if skill_details:
                scraped_data['skills'] = skill_details

        except:
            print(f"Error scraping skills section")
            pass


# API to submit LinkedIn URL for scraping
@app.route('/submit', methods=['POST'])
def submit_linkedin_url():
    data = request.get_json()
    linkedin_url = data.get('linkedin_url')

    # Validate LinkedIn URL
    if not linkedin_url:
        return jsonify({'error': 'No LinkedIn URL provided'}), 400
    if not isinstance(linkedin_url, str) or ',' in linkedin_url:
        return jsonify({'error': 'Please provide a single LinkedIn URL without commas.'}), 400
    if not validate_linkedin_url(linkedin_url):
        return jsonify(
            {'error': 'Invalid LinkedIn URL format. Please use the format: https://www.linkedin.com/in/username/'}), 400

    # Perform scraping directly and keep the POST request active until scraping is done
    scrape_linkedin_profile(linkedin_url)

    return jsonify({'message': 'Scraping complete for ' + linkedin_url, 'data': scraped_data}), 200


# API to get scraped data
@app.route('/data', methods=['GET'])
def get_scraped_data():
    # Wait for scraping to finish if data is still being processed
    wait_time = 0
    max_wait_time = 0  # Wait up to 30 seconds
    while not scraped_data and wait_time < max_wait_time:
        time.sleep(1)  # Wait for 1 second
        wait_time += 1

    if not scraped_data:
        return jsonify({"error": "Scraping is still in progress or no data was found."}), 202  # Status 202 Accepted

    return jsonify(scraped_data)


@app.route('/gpt-suggestion', methods=['POST'])
def generate_gpt_suggestions():
    global scraped_data
    if not scraped_data:
        return jsonify({'error': 'No scraped data available. Please scrape a LinkedIn profile first.'}), 400

    # Log the request to ensure data is received
    data = request.get_json()
    app.logger.info(f"Received data for GPT suggestion: {data}")

    # Get the responses from the frontend
    looking_for_job = data.get('looking_for_job', '').lower()  # "yes" or "no"
    job_type = data.get('job_type', '')  # "remote", "hybrid", "onsite"
    job_preference = data.get('job_preference', '')  # User input for job preference

    # Construct profile data string from scraped data
    profile_data = f"""
       Headline: {scraped_data.get('headline')}
       Summary: {scraped_data.get('summary')}
       Experience: {scraped_data.get('experience')}
       Education: {scraped_data.get('education')}
       Skills: {scraped_data.get('skills')}
       """

    if looking_for_job == 'yes':
        # If user is looking for a job, tailor the prompt to the job type and preference
        app.logger.info(f"User is looking for a {job_type} job with preference: {job_preference}")

        # Define prompt based on job type and preference
        prompt = f"""
        The user is looking for a {job_type} job. Their job preference is: "{job_preference}". Based on the following LinkedIn profile data, provide detailed suggestions for improvement for each section 
        (Headline, Summary, Experience, Education, Skills) to make the profile more attractive for {job_type} jobs. Also, consider the user's job preference.\n\n{profile_data}
        """
    else:
        # If user is not looking for a job, provide general suggestions for LinkedIn profile improvement
        app.logger.info(f"User is not looking for a job. Generating general profile improvement suggestions.")

        # Define a general prompt for improving the LinkedIn profile
        prompt = f"""
        The user is not actively looking for a job. Based on the following LinkedIn profile data, provide general suggestions for improvement for each section (Headline, Summary, Experience, Education, Skills) to enhance the profile for overall professional growth and networking opportunities.\n\n{profile_data}
        """

    app.logger.info(f"Generated prompt: {prompt}")

    try:
        # Generate suggestions using OpenAI GPT
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        gpt_suggestions = response['choices'][0]['message']['content']

        # Log the suggestions for debugging
        app.logger.info(f"Generated GPT suggestions: {gpt_suggestions}")

        # Structure the GPT suggestions in the same format as the scraped data
        structured_suggestions = {
            'headline': f"Headline Suggestion: {gpt_suggestions.split('Headline:')[1].split('Summary:')[0].strip() if 'Headline:' in gpt_suggestions else scraped_data.get('headline')}",
            'summary': f"Summary Suggestion: {gpt_suggestions.split('Summary:')[1].split('Experience:')[0].strip() if 'Summary:' in gpt_suggestions else scraped_data.get('summary')}",
            'experience': f"Experience Suggestion: {gpt_suggestions.split('Experience:')[1].split('Education:')[0].strip() if 'Experience:' in gpt_suggestions else scraped_data.get('experience')}",
            'education': f"Education Suggestion: {gpt_suggestions.split('Education:')[1].split('Skills:')[0].strip() if 'Education:' in gpt_suggestions else scraped_data.get('education')}",
            'skills': f"Skills Suggestion: {gpt_suggestions.split('Skills:')[1].strip() if 'Skills:' in gpt_suggestions else scraped_data.get('skills')}"
        }

        # Store the structured suggestions in scraped_data for further reference or retrieval
        scraped_data['gpt_suggestions'] = structured_suggestions

        return jsonify({
            'message': 'GPT suggestions generated successfully',
            'suggestions': structured_suggestions
        }), 200

    except Exception as e:
        # Log the error if something goes wrong
        app.logger.error(f"Error generating GPT suggestions: {e}")
        return jsonify({'error': 'Failed to generate suggestions from GPT'}), 500



@app.route('/get-gpt-suggestions', methods=['GET'])
# Endpoint for submitting user responses to GPT suggestions
def get_gpt_suggestions():
    global scraped_data
    # Check if GPT suggestions are available
    if 'gpt_suggestions' not in scraped_data:
        return jsonify({'error': 'No GPT suggestions available. Please generate suggestions first.'}), 400

    # Return only the GPT suggestions without the wrapper
    return jsonify(scraped_data['gpt_suggestions']), 200



@app.route('/submit_response', methods=['POST'])
def submit_response():
    data = request.get_json()
    linkedin_url = data.get('linkedin_url')
    suggestion_type = data.get('suggestion_type')
    response = data.get('response')

    if not linkedin_url or not suggestion_type or not response:
        return jsonify({'error': 'LinkedIn URL, suggestion type, or response not provided'}), 400

    if response.lower() not in ['yes', 'no']:
        return jsonify({'error': 'Response must be "yes" or "no"'}), 400

    if linkedin_url in user_responses:
        user_responses[linkedin_url]['responses'][suggestion_type] = response.lower()
    else:
        user_responses[linkedin_url] = {'suggestions': {}, 'responses': {suggestion_type: response.lower()}}

    return jsonify({'message': 'Response recorded successfully'}), 200


# Endpoint to fetch suggestions and user responses for a profile
@app.route('/get_user_responses', methods=['GET'])
def get_user_responses():
    linkedin_url = request.args.get('linkedin_url')
    if not linkedin_url or linkedin_url not in user_responses:
        return jsonify({'error': 'No data found for the given LinkedIn URL'}), 404

    return jsonify(user_responses[linkedin_url]), 200


@app.route('/submit', methods=['OPTIONS'])
def options():
    response = jsonify({'message': 'CORS preflight allowed'})
    response.headers.add('Access-Control-Allow-Origin', 'https://localhost:3000')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    return response


# Start the Flask app
if __name__ == '__main__':
    # app.run(debug=True,port=5000)
    app_port = 5000  # Default port Flask uses
    # Set your ngrok authtoken
    ngrok.set_auth_token('2mrU0CCGtMxJbUfYiFmJZlVdtlg_2xfJsFKnX96ASciY6D5K1')  # Replace with your actual ngrok authtoken
    # Start ngrok tunnel for the app
    public_url = ngrok.connect(app_port)
    print(f' * ngrok tunnel "{public_url}" -> "http://localhost:{app_port}"')
    # Run the Flask app
    app.run(port=app_port)









# import re
# import openai
# from flask import Flask, request, jsonify
# from flask_cors import CORS
# from selenium.webdriver.common.by import By
# from selenium import webdriver
# from webdriver_manager.chrome import ChromeDriverManager
# import time
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options

# app = Flask(__name__)

# # Allow CORS from localhost:3000 with specific methods and headers
# 

# openai.api_key = ('sk-proj-hmQSzOkvXzzpDqm6A0Zy-A9bWYGArHXUq2TBBBuod4B'
#                   '-74YZ696OoGohZ6USEwv4EBJ3djlh2vT3BlbkFJQ_4L_xEERm_HjdKlvrr1'
#                   '-rW8MI96aCX9g8rHFe94cOZtweDozGpqGyw2cNV1cTJ13DSRf4TYcA')
# # Replace with your actual API key  # Replace with your actual API key
# # Oxylabs Proxy credentials
# USERNAME = 'linkedinai927_mfjQF'
# PASSWORD = 'Linkedinai927='
# ENDPOINT = "pr.oxylabs.io:7777"

# scraped_data = {}
# user_responses = {}

# # Proxy configuration function
# def chrome_proxy(user: str, password: str, endpoint: str) -> dict:
#     wire_options = {
#         "proxy": {
#             "http": f"http://{user}:{password}@{endpoint}",
#             "https": f"https://{user}:{password}@{endpoint}",
#         }
#     }
#     return wire_options

# # Set up Selenium with proxy
# def setup_driver_with_proxy():
#     options = Options()
#     options.add_argument('--start-maximized')

#     # Initialize the Chrome driver with the proxy settings
#     driver = webdriver.Chrome(
#         service=Service(ChromeDriverManager().install()),
#         options=options
#     )
#     return driver

# # Function to validate LinkedIn URL
# def validate_linkedin_url(url):
#     linkedin_regex = r'^https?:\/\/(www\.)?linkedin\.com\/in\/[a-zA-Z0-9\-]+\/?$'
#     return re.match(linkedin_regex, url) is not None

# # Scrape the profile data
# def scrape_linkedin_profile(linkedin_url):
#     global scraped_data
#     driver = setup_driver_with_proxy()

#     # Login process
#     driver.get('https://www.linkedin.com/checkpoint/lg/login')
#     time.sleep(3)
#     username = driver.find_element(By.ID, 'username')
#     username.send_keys("a2505321@gmail.com")
#     password = driver.find_element(By.ID, 'password')
#     password.send_keys("abd@1234")
#     time.sleep(5)
#     send_btn = driver.find_element(By.XPATH, '//*[@id="organic-div"]/form/div[3]/button')
#     send_btn.click()
#     time.sleep(5)
#     input('wait')

#     # Navigate to the LinkedIn profile
#     driver.get(linkedin_url)
#     time.sleep(8)
#     # input('wait')
#     try:
#         # Scrape name, headline, and summary
#         name = driver.find_element(By.CLASS_NAME, 'v-align-middle').text.strip()
#         headline = driver.find_element(By.CSS_SELECTOR, "div.text-body-medium").text.strip()
#         summary = driver.find_element(By.XPATH,
#                                        '//*[@id="profile-content"]/div/div[2]/div/div/main/section[2]/div[3]/div/div/div/span[1]').text.strip()

#         # Store the data
#         scraped_data = {
#             'name': name,
#             'headline': headline,
#             'summary': summary,
#             'experience': [],
#             'education': [],
#             'skills': []
#         }

#         # Scrape experience, education, and skills sections
#         sections = ['experience','education', 'skills']
#         for section in sections:
#             scrape_linkedin_section(driver, linkedin_url, section)

#     except Exception as e:
#         print(f"Error scraping profile: {e}")
#     finally:
#         driver.quit()

# # Function to generate suggestions using OpenAI API
# def generate_suggestions(profile_data):
#     user_input = "I'm interested in improving my LinkedIn profile, can you suggest some sections to focus on? "
#     response = openai.ChatCompletion.create(
#         model="gpt-3.5-turbo",
#         messages=[{"role": "user",
#                    "content": f"{user_input}"
#                               f"and only rewrite it section by section :\n\n{profile_data}"}]
#     )

#     suggestions = response['choices'][0]['message']['content']
#     return suggestions

# # Function to dynamically scrape LinkedIn sections
# def scrape_linkedin_section(driver, linkedin_url, section):
#     global scraped_data

#     section_url = f"{linkedin_url}/details/{section}/"
#     driver.get(section_url)
#     time.sleep(10)

#     if section == "experience":
#         try:
#             # Locate the experiences using a more precise selector and filter duplicates
#             experience_elements = driver.find_elements(By.CLASS_NAME, 'pvs-list__item--line-separated')

#             # Initialize a list to store the formatted experiences
#             unique_experiences = []

#             # Loop through each experience element and extract relevant details
#             for exp_element in experience_elements:
#                 e_text = exp_element.text.strip()

#                 # Replace 'to' with '-' to standardize date formats
#                 e_text = e_text.replace(" to ", " - ")

#                 # Split the text based on new lines (this helps with removing duplicated lines)
#                 lines = e_text.split("\n")

#                 # Use a set to filter out any repeated lines within the same experience block
#                 unique_lines = list(dict.fromkeys(lines))  # dict.fromkeys() preserves order and removes duplicates

#                 # Rejoin the filtered lines back into a single string for that experience (without newlines)
#                 formatted_experience = " ".join(unique_lines)  # Joins with a space instead of a newline

#                 # Check if the experience has already been added (to avoid duplicates across all experiences)
#                 if formatted_experience not in unique_experiences:
#                     unique_experiences.append(formatted_experience)

#             # Store the formatted unique experiences in the scraped_data object
#             scraped_data['experience'] = unique_experiences

#         except Exception as e:
#             print(f"Error scraping experience section: {e}")

#     elif section == "education":
#         try:
#             # Find all education elements
#             educations = driver.find_elements(By.XPATH,
#                                               '//*[@id="profile-content"]/div/div[2]/div/div/main/section/div[2]/div/div[1]/ul/li')
#             num_positions = len(educations)
#             print(f"Found {num_positions} education entries.")

#             # Extract institute names/details
#             education_Details = driver.find_elements(By.CSS_SELECTOR, '.display-flex a span[aria-hidden="true"]')
#             education_details = []

#             # Adjust the range if num_positions == 1
#             if num_positions == 1:
#                 loop_range = num_positions + 2
#             else:
#                 loop_range = num_positions * num_positions

#             # Ensure the loop runs according to the number of education entries found
#             for i in range(loop_range):
#                 if i < len(education_Details):  # Prevent index error
#                     education_text = education_Details[i].text.strip()
#                     print(f"Institute Details: {education_text}")
#                     education_details.append(education_text)
#                 else:
#                     print(f"Institute Details: Not found for education at index {i}")
#                     education_details.append("Details not found")

#             scraped_data['education'] = education_details  # Save the education details
#         except Exception as e:
#             print(f"Error scraping education section: {e}")

#     elif section == "skills":
#         try:
#             skills = driver.find_elements(By.CSS_SELECTOR,
#                                           '[data-field="skill_page_skill_topic"] div div div div span[aria-hidden="true"]')

#             skill_details = []

#             for s in skills:
#                 skill_text = s.text.strip().replace(",", '')

#                 # Only append non-empty skills
#                 if skill_text:
#                     skill_details.append(skill_text)
#                     print(f"Skill : {skill_text}")

#             # Save the skills details only if there are skills
#             if skill_details:
#                 scraped_data['skills'] = skill_details

#         except Exception as e:
#             print(f"Error scraping skills section: {e}")


# # API to submit LinkedIn URL for scraping
# @app.route('/submit', methods=['POST'])
# def submit_linkedin_url():
#     data = request.get_json()
#     linkedin_url = data.get('linkedin_url')

#     # Validate LinkedIn URL
#     if not linkedin_url:
#         return jsonify({'error': 'No LinkedIn URL provided'}), 400
#     if not isinstance(linkedin_url, str) or ',' in linkedin_url:
#         return jsonify({'error': 'Please provide a single LinkedIn URL without commas.'}), 400
#     if not validate_linkedin_url(linkedin_url):
#         return jsonify({'error': 'Invalid LinkedIn URL format. Please use the format: https://www.linkedin.com/in/username/'}), 400

#     # Perform scraping directly and keep the POST request active until scraping is done
#     scrape_linkedin_profile(linkedin_url)

#     return jsonify({"message": "Profile submitted successfully", "url": linkedin_url}), 200

# # API to get scraped data
# @app.route('/data', methods=['GET'])
# def get_scraped_data():
#     # Wait for scraping to finish if data is still being processed
#     wait_time = 0
#     max_wait_time = 30  # Wait up to 30 seconds
#     while not scraped_data and wait_time < max_wait_time:
#         time.sleep(1)  # Wait for 1 second
#         wait_time += 1

#     if not scraped_data:
#         return jsonify({"error": "Scraping is still in progress or no data was found."}), 202  # Status 202 Accepted

#     return jsonify(scraped_data)

# # New API to get suggestions based on scraped data
# @app.route('/gpt-suggestion', methods=['POST'])
# def generate_gpt_suggestions():
#     global scraped_data
#     if not scraped_data:
#         return jsonify({'error': 'No scraped data available. Please scrape a LinkedIn profile first.'}), 400

#     # Construct profile data string
#     profile_data = f"""
#     Headline: {scraped_data.get('headline')}
#     Summary: {scraped_data.get('summary')}
#     Experience: {scraped_data.get('experience')}
#     Education: {scraped_data.get('education')}
#     Skills: {scraped_data.get('skills')}
#     """

#     # Generate suggestions using OpenAI
#     suggestions = generate_suggestions(profile_data)

#     # Store the GPT suggestions in scraped_data
#     scraped_data['s'] = suggestions

#     return jsonify({"suggestions": suggestions}), 200

# if __name__ == '__main__':
#     app.run(debug=True)