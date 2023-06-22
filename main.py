import requests
from datetime import datetime
import sqlite3
import csv
import pandas as pd
import os
import matplotlib.pyplot as plt


def CreateSQL(db_name: str):
    """
    Function to create SQLite database for data storage and analysis
    2 tables (Organisation and MonthlyData) are linked with the OrgCode (Organisation code)
    :param db_name: name of db
    """
    if os.path.exists(''.join([db_name, '.db'])):
        print("SQLite database file already exists.")
        return


    conn = sqlite3.connect(''.join([db_name, '.db']))
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE Organisation (
      OrgCode TEXT PRIMARY KEY,
      ParentOrg TEXT,
      OrgName TEXT
    );
    ''')
    cursor.execute('''
    CREATE TABLE MonthlyData (
      Period VARCHAR(7),
      OrgCode TEXT,
      AttType1 INTEGER,
      AttType2 INTEGER,
      AttOther INTEGER,
      AttBookedType1 INTEGER,
      AttBookedType2 INTEGER,
      AttBookedOther INTEGER,
      AttOver4Type1 INTEGER,
      AttOver4Type2 INTEGER,
      AttOver4Other INTEGER,
      AttOver4BookedType1 INTEGER,
      AttOver4BookedType2 INTEGER,
      AttOver4BookedOther INTEGER,
      FourtoTwelve INTEGER,
      Twelveplus INTEGER,
      EmergencyType1 INTEGER,
      EmergencyType2 INTEGER,
      EmergencyOther INTEGER,
      Other INTEGER,
      FOREIGN KEY (OrgCode) REFERENCES Organisation (OrgCode)
    );
    ''')
    conn.commit()
    conn.close()


def Download_existing_data(db_name: str):
    """
    Function to download and insert all data to input SQLite database
    Duplicated input are omitted
    :param db_name: the name of SQLite database created
    :return a csv containing organisation code, organisation name and their parent organisation
    """
    base_url = "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2"
    start_year = 2020
    end_year = datetime.now().year
    end_month = datetime.now().month - 1        # Data released a month later
    for year in range(start_year, end_year + 1):
        for month in range(1, 13 if year != end_year else end_month + 1):
            if year == 2020 and month < 8:      # First valid data is from 2020-08
                continue
            month_name = \
                ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                 "November", "December"][month - 1]
            if month == 12:
                url = f"{base_url}/{year + 1}/{1:02d}/Monthly-AE-{month_name}-{year}.csv"
            else:
                url = f"{base_url}/{year}/{month + 1:02d}/Monthly-AE-{month_name}-{year}.csv"
            response = requests.get(url)
            if response.status_code == 200:
                csv_data = response.content.decode('utf-8').splitlines()
                csv_reader = csv.reader(csv_data)
                next(csv_reader)  # Skip header

                conn = sqlite3.connect(''.join([db_name, '.db']))
                cursor = conn.cursor()
                for row in csv_reader:
                    period_str = row[0]
                    if period_str != 'TOTAL':   # Skip total for each monthly data
                        period_parts = period_str.split('-')
                        # Format in csv: MSitAE-AUGUST-2020  -> convert to 2020-08
                        period_month = datetime.strptime(period_parts[1], "%B").strftime("%m")
                        period_year = period_parts[2]
                        period = f"{period_year}-{period_month}"

                        org_code = row[1]
                        parent_org = row[2]
                        org_name = row[3]

                        # Add new organisation info to Organisation table
                        cursor.execute("SELECT * FROM Organisation WHERE OrgCode = ?", (org_code,))
                        existing_org = cursor.fetchone()
                        if not existing_org:
                            cursor.execute("INSERT INTO Organisation (OrgCode, ParentOrg, OrgName) VALUES (?, ?, ?)",
                                           (org_code, parent_org, org_name))

                        # Add new data to Monthly data (Need to improve)
                        cursor.execute("SELECT * FROM MonthlyData WHERE Period = ? AND OrgCode = ?", (period, org_code))
                        existing_data = cursor.fetchone()
                        if not existing_data:
                            cursor.execute('''INSERT INTO MonthlyData (
                                Period, OrgCode, AttType1, AttType2,AttOther,AttBookedType1, AttBookedType2, AttBookedOther,
                                AttOver4Type1, AttOver4Type2, AttOver4Other,AttOver4BookedType1, AttOver4BookedType2, 
                                AttOver4BookedOther, FourtoTwelve ,Twelveplus, EmergencyType1, EmergencyType2, EmergencyOther, Other
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                           (period, org_code) + tuple(row[4:]))
                conn.commit()

                # Export organisation table as a csv (For analysis)
                cursor.execute('SELECT * FROM Organisation')
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                with open('organisation_code.csv', 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(columns)
                    writer.writerows(rows)
                cursor.close()
                conn.close()


def emergency_trend(db_name):
    """
    Analysis using the processed data in database, to show the trend of top 5 hospitals with the highest number of emergenecy cases
    :param db_name: name of database
    :return png to show the trend
    """
    conn = sqlite3.connect(''.join([db_name, '.db']))
    cursor = conn.cursor()
    # SQL query to count sum of emergency case (3 types) for each OrgCode for each period
    query = '''
    SELECT Period, MonthlyData.OrgCode, SUM(EmergencyType1 + EmergencyType2 + EmergencyOther) AS EmergencySum, Organisation.OrgName
    FROM MonthlyData
    INNER JOIN Organisation ON MonthlyData.OrgCode = Organisation.OrgCode
        AND MonthlyData.OrgCode IN (
            SELECT OrgCode
            FROM MonthlyData
            GROUP BY OrgCode
            HAVING COUNT(*) = (
                SELECT COUNT(DISTINCT Period)
                FROM MonthlyData
            )
        )
    GROUP BY Period, MonthlyData.OrgCode
    '''
    org_data = {}
    org_names = set()
    for row in cursor.execute(query):
        period = row[0]
        org_code = row[1]
        emergency_sum = row[2]
        org_name = row[3]
        if org_code not in org_data:
            org_data[org_code] = {'name': org_name, 'data': {}}
        org_data[org_code]['data'][period] = emergency_sum
        org_names.add(org_name)
    conn.close()

    top_5_orgs = []
    for org_code, org_info in org_data.items():
        org_sum = sum(org_info['data'].values())
        top_5_orgs.append((org_info['name'], org_sum))
    # Select top 5 only (may improve to top N on user requirement)
    top_5_orgs = sorted(top_5_orgs, key=lambda x: x[1], reverse=True)[:5]
    for org_name, _ in top_5_orgs:
        periods = []
        sums = []
        for org_code, org_info in org_data.items():
            if org_info['name'] == org_name:
                for period, sum_value in org_info['data'].items():
                    periods.append(period)
                    sums.append(sum_value)
                break
        plt.plot(periods, sums, label=org_name)

    fig = plt.gcf()
    fig.set_size_inches(12, 8)
    plt.xlabel('Period')
    plt.ylabel('Total emergency cases')
    plt.title('Trend of total emergency cases for the Top 5 hospitals')
    plt.legend(bbox_to_anchor=(0.5, -0.3), loc='upper center', ncol=1)
    plt.xticks(rotation=80, ha='right')
    plt.subplots_adjust(bottom=0.4)

    plt.savefig('Total_Emergency_Trend.png')
    plt.close()


def twelve_hour_plus_trend(db_name: str):
    """
    Analysis using the processed data in database, to show the trend of top 5 hospitals with the highest number of patients waited for 12 hours or more
    :param db_name: name of database
    :return png to show the trend
    """
    conn = sqlite3.connect(''.join([db_name, '.db']))
    cursor = conn.cursor()
    # SQL query (Criteria: having patients in all period)
    query = '''
    SELECT Period, MonthlyData.OrgCode, Twelveplus, Organisation.OrgName
    FROM MonthlyData
    INNER JOIN Organisation ON MonthlyData.OrgCode = Organisation.OrgCode
    WHERE MonthlyData.OrgCode IN (
            SELECT OrgCode
            FROM MonthlyData
            WHERE Twelveplus > 0
            GROUP BY OrgCode
            HAVING COUNT(*) = (
                SELECT COUNT(DISTINCT Period)
                FROM MonthlyData
                WHERE Twelveplus > 0
            )
        )
    ORDER BY MonthlyData.OrgCode, Period
    '''
    org_data = {}
    for row in cursor.execute(query):
        period = row[0]
        org_code = row[1]
        twelveplus = row[2]
        org_name = row[3]
        if org_code not in org_data:
            org_data[org_code] = {'periods': [], 'twelveplus': [], 'org_name': org_name}
        org_data[org_code]['periods'].append(period)
        org_data[org_code]['twelveplus'].append(twelveplus)
    conn.close()

    # Top 5 hospitals
    top_5_orgs = sorted(org_data.keys(), key=lambda x: max(org_data[x]['twelveplus']), reverse=True)[:5]
    plt.figure(figsize=(12, 8))
    for org_code in top_5_orgs:
        data = org_data[org_code]
        periods = data['periods']
        twelveplus_values = data['twelveplus']
        org_name = data['org_name']
        plt.plot(periods, twelveplus_values, label=org_name)

    fig = plt.gcf()
    fig.set_size_inches(12, 8)
    plt.xlabel('Month')
    plt.ylabel('Number of patients')
    plt.title('Trend of top 5 hospitals having the highest number of patients waited for over 12hr')
    plt.xticks(rotation=80)
    plt.legend(bbox_to_anchor=(0.5, -0.3), loc='upper center', ncol=1)
    plt.subplots_adjust(bottom=0.2)
    plt.subplots_adjust(bottom=0.4)
    plt.savefig('12hr+_Trend.png')
    plt.close()


def twelve_hour_plus_individual_organisation(db_name: str, org_code: str):
    """
    Analysis using the processed data in database, to show the trend of number of patients waited for 12 hours or more in the input hospital
    :param db_name: name of database
    :param org_code: Organisation code of hospital of interest (Referred to the csv)
    :return png to show the trend
    """
    conn = sqlite3.connect(''.join([db_name, '.db']))
    cursor = conn.cursor()
    query = '''
    SELECT Period, Twelveplus
    FROM MonthlyData
    WHERE OrgCode = ?
    ORDER BY Period
    '''
    cursor.execute(query, (org_code,))
    results = cursor.fetchall()
    conn.close()

    periods = [row[0] for row in results]
    twelveplus_values = [row[1] for row in results]

    plt.plot(periods, twelveplus_values)
    plt.xlabel('Month')
    plt.ylabel('Number of patients')
    plt.title('Trend of patients waited for over 12hr for Organization ' + org_code)
    plt.xticks(rotation=80)
    plt.subplots_adjust(bottom=0.2)
    filename = org_code + "_12hr+.png"
    plt.savefig(filename)
    plt.close()


def emergency_individual_organisation(db_name, org_code):
    """
    Analysis using the processed data in database, to show the trend of number of total emergency cases in the input hospital
    :param db_name: name of database
    :param org_code: Organisation code of hospital of interest (Referred to the csv)
    :return png to show the trend
    """
    conn = sqlite3.connect(''.join([db_name, '.db']))
    cursor = conn.cursor()
    query = '''
    SELECT Period, SUM(EmergencyType1 + EmergencyType2 + EmergencyOther) AS EmergencySum
    FROM MonthlyData
    WHERE OrgCode = ?
    GROUP BY Period
    ORDER BY Period
    '''
    cursor.execute(query, (org_code,))
    results = cursor.fetchall()
    conn.close()

    periods = [row[0] for row in results]
    emergency_sums = [row[1] for row in results]

    plt.plot(periods, emergency_sums)
    plt.xlabel('Period')
    plt.ylabel('Total Emergency Cases')
    plt.title('Trend of total Emergency Cases for Organization ' + org_code)
    plt.xticks(rotation=80)
    plt.subplots_adjust(bottom=0.2)
    filename = org_code + "_emergency.png"
    plt.savefig(filename)
    plt.close()

def main(db_name):

    # Step 0: Create SQL database
    CreateSQL(db_name)

    # Step 1: Download all existing data
    Download_existing_data(db_name)

    # Step 2: Analysis
    # Perform analysis based on user input
    while True:
        print("Choose an analysis option:")
        print("1. Trend of top 5 hospitals with the highest number of patients waited for >12hr in A&E")
        print("2. Trend of top 5 hospitals with the highest total emergency cases over time")
        print("3. Trend of number of patients waited for >12hr in A&E for a specific hospital")
        print("4. Trend of total emergency cases for a specific hospital")
        print("0. Exit")
        option = input("Enter the option number: ")
        code_list = pd.read_csv('organisation_code.csv')

        if option == '1':
            twelve_hour_plus_trend(db_name)
        elif option == '2':
            emergency_trend(db_name)
        elif option == '3':
            hospital_code = input("Enter the hospital code: ")
            if hospital_code in code_list['OrgCode'].values:
                twelve_hour_plus_individual_organisation(db_name, hospital_code)
            else:
                print("Invalid hospital code. Please try again.")
        elif option == '4':
            hospital_code = input("Enter the hospital code: ")
            if hospital_code in code_list['OrgCode'].values:
                emergency_individual_organisation(db_name, hospital_code)
            else:
                print("Invalid hospital code. Please try again.")
        elif option == '0':
            print("Exiting...")
            break
        else:
            print("Invalid option. Please try again.")


if __name__ == '__main__':
    custom_db_name = input("Enter the desired database name: ")
    main(custom_db_name)




