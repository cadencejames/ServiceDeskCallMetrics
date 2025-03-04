import pandas as pd
import requests
from lxml import etree
import warnings
from datetime import datetime
import pytz

#### Initialize CUCM settings
url = "192.168.1.1/axl" # Adjust URL for CUCM Publisher IP Address
headers = {
    'Authorization': 'Basic <BASIC AUTH HERE>', # Replace with actual authentication
    'Content-Type': 'text/plain',
    'Cookie': '<COOKIE HERE>' # Replace with actual cookie if required
}
warnings.filterwarnings("ignore", category=requests.packages.urllib3.exceptions.InsecureRequestsWarning) # Suppress SSL warnings

# Define XML namespace for parsing responses
ns = {
    "soapenv": "http://schemas.xmlsoap.org/soap/envelope/",
    "ns": "http://www.cisco.com/AXL/API/14.0"
}

# Define constants
helpDesk = "5551234" # Help desk phone number
voicemail_server = "VOICEMAIL_SERVER" # Voicemail server identifier

#### Read CDR (Call Detail Records) from CSV file
cdr_df = pd.read_csv('cdr.csv', low_memory=False)

#### Setting time zones and converting timestamps
utc_zone = pytz.utc
eastern_zone = pytz.timezone('America/New_York')

# Convert start time to Eastern Time
startTime = pd.to_datetime(cdr_df['dateTimeOrigination'].iloc[0], unit='s')
startTime = startTime.replace(tzinfo=utc_zone).astimezone(eastern_zone)
startTime = startTime.strftime("%Y-%m-%d %H:%M:%S")

# Convert end time to Eastern Time
endTime = pd.to_datetime(cdr_df['dateTimeOrigination'].iloc[-1], unit='s')
endTime = endTime.replace(tzinfo=utc_zone).astimezone(eastern_zone)
endTime = endTime.strftime("%Y-%m-%d %H:%M:%S")

#### Retrieve help desk phone devices via AXL API (replace the fknumplan id with the one specific to the help desk line)
payload = """
    <soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:ns=\"http://www.cisco.com/AXL/API/14.0\">
        <soapenv:Header />
        <soapenv:Body>
            <ns:executeSQLQuery>
                <sql>
                    SELECT d.name, d.description
                    FROM devicenumplanmap as dnpm
                    INNER JOIN device AS d ON dnpm.fkdevice = d.pkid
                    WHERE dnpm.fknumplan = 'c3f97eb6-aeae-280d-1aaf-9d2c47528011'
                </sql>
            </ns:executeSQLQuery>
        </soapenv:Body>
    </soapenv:Envelope>
"""
response = requests.request("POST", url, headers=headers, data=payload, verify=False)
responseText = response.text.encode('utf-8')
root = etree.fromstring(responseText)

# Parse device names and descriptions from XML response
device_names = root.xpath("//ns:executeSQLQueryResponse/return/row/name", namespace=ns)
descriptions = root.xpath("//ns:executeSQLQueryResponse/return/row/description", namespace=ns)
phones = {device_name.text: description.text for device_name, description in zip(device_names, descriptions)}

#### Sort calls into different categories
helpDeskCalls = cdr_df[cdr_df['originalCalledPartyPattern'] == helpDesk].copy()
helpDeskAnswered = helpDeskCalls[helpDeskCalls['finalCalledPartyPattern'] == helpDesk]

# Identify calls that reached voicemail
voicemailCalls = helpDeskCalls[helpDeskCalls['finalCalledPartyPattern'] == '8888'].copy()
voicemailCalls['dateTimeOrigination'] = pd.to_datetime(voicemailCalls['dateTimeOrigination'], unit='s', utc=True)
voicemailCalls['dateTimeEastern'] = voicemailCalls['dateTimeOrigination'].dt.tz_convert(eastern_zone)

# Convert call timestamps
helpDeskCalls['dateTimeOrigination'] = pd.to_datetime(helpDeskCalls['dateTimeOrigination'], unit='s', utc=True)
helpDeskCalls['dateTimeEastern'] = helpDeskCalls['dateTimeOrigination'].dt.tz_convert(eastern_zone)

# Identify calls made between 5 PM and 8 PM
eveningCalls = helpDeskCalls[
    (helpDeskCalls['dateTimeEastern'].dt.hour >= 17) &
    (helpDeskCalls['dateTimeEastern'].dt.hour < 20)
].copy()

#### Count calls per device
calling_numbers = helpDeskCalls['destDeviceName']
call_counts = calling_numbers.value_counts().reset_index()
call_counts.columns = ['DeviceName', 'CallCount']
call_counts['Description'] = call_counts['DeviceName'].map(phones)
call_counts.loc[call_counts['DeviceName'] == voicemail_server, 'Description'] = "Voicemail"
call_counts['Description'] = call_counts['Description'].fillna("Unknown")

#### Retrieve phone numbers for devices using AXL API
# Dictionary to store updates (index: phone_number)
updates = {}
# Iterate over DataFrame rows efficiently using .itertuples()
# index=True ensures we retain the original DataFrame index for updates
for row in call_counts.itertuples(index=True):
    device = row.DeviceName  # Get the device name for the current row
    if device == voicemail_server:
        updates[row.Index] = "8888"
        continue  # Skip the API call for voicemail servers
    payload = f"""
        <soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:ns=\"http://www.cisco.com/AXL/API/14.0\">
            <soapenv:Header />
            <soapenv:Body>
                <ns:getPhone>
                    <name>{device}</name>
                </ns:getPhone>
            </soapenv:Body>
        </soapenv:Envelope>
    """
    response = requests.request("POST", url, headers=headers, data=payload, verify=False)
    responseText = response.text.encode("utf-8")
    root = etree.fromstring(responseText)
    phone_numbers = root.xpath("//ns:getPhoneResponse/return/phone/lines/line/dirn/pattern", namespaces=ns)
    phone_number = phone_numbers[0].text if phone_numbers else "Unknown"
    updates[row.Index] = phone_number
# Apply all updates to the 'PhoneNumber' column in a single operation (faster than row-by-row modification)
call_counts.loc[list(updates.keys()), 'PhoneNumber'] = list(updates.values())
# Organize call counts data
call_counts = call_counts.reindex(columns=['PhoneNumber', 'Description', 'DeviceName', 'CallCount'])
call_counts = call_counts.sort_values(by='PhoneNumber', ascending=True)

#### Output evening and voicemail calls to text files
evening_calls_text = eveningCalls[['dateTimeEastern']].to_string(index=False, header=False)
with open('evening_calls.txt', 'w') as file:
    file.write(evening_calls_text)

voicemail_calls_text = voicemailCalls[['dateTimeEastern']].to_string(index=False, headers=False)
with open('voicemail_calls.txt', 'w') as file:
    file.write(voicemail_calls_text)

#### Print summary information
print("\n---------------------------")
print(f"Start Time: {startTime} ET")
print(f"End Time: {endTime} ET")
print("---------------------------")
print(f"Total Calls: {len(cdr_df)}")
print(f"Total Help Desk Calls: {len(helpDeskCalls)}")
print(f"Total Help Desk Voicemails: {len(voicemailCalls)}")
print(f"Total 5-8 Calls made: {len(eveningCalls)}")
print("---------------------------")
print(call_counts)
print("---------------------------\n")

