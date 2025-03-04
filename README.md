# **Service Desk Call Metric Retrieval**
![Python Version](https://img.shields.io/badge/python-3.6%2B-blue)
![License](https://img.shields.io/github/license/cadencejames/ServiceDeskCallMetrics)
![Last Commit](https://img.shields.io/github/last-commit/cadencejames/ServiceDeskCallMetrics)
![Contributors](https://img.shields.io/github/contributors/cadencejames/ServiceDeskCallMetrics)


This Python script parses the Call Detail Record CSV file pulled from CUCM to pull information regarding calls made to the service desk.

---

## **Features**
- Lists the number of calls made in the record (any call made in CUCM during the date range selected when downloading the csv file)
- Lists the number of calls made to the service desk in that date range
- Lists the number of calls made to the service desk that made it to voicemail
- Lists the number of calls made to the service desk in the evening time frame
- Lists each device/phone number/description of the device that answered a service desk call
- Lists how many calls each device answered

---

## **Workflow**
1. **Download CDR.csv**  
   
2. **Parse CSV using Get-ServiceDeskMetrics.py**  
   
3. **Output Results**  
   - Results will be posted to the terminal screen as well as two text files in the same directory for evening calls and any calls that made it to voicemail.
   
---

## **Requirements**
- **Python Version:** Python 3.6+
- **Libraries:**  
  - `pandas`: For working with CSVs.
  - `requests`: For implementing API calls to CUCM
  
- **Input Files:**  
  - `CDR.csv`: Contains the entire log of calls made inside CUCM

- **Output Files:**  
  - `evening_calls.txt`: Stores the date and time of any calls made to the service desk in the evening
  - `voicemail_calls.txt`: Stores the date and time of any calls made to the service desk that made it to voicemail

---

## **Usage**
1. Clone the repository and navigate to the script directory.
2. Update the Basic Auth in the headers variable (to facilitate logging into CUCM to pull device info)
3. Ensure the CDR.csv is in the same location as the script
4. Run the script:
   ```bash
   python .\Get-ServiceDeskMetrics.py
   ```
