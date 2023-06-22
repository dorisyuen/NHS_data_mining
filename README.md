# NHS_data_mining
Development of a stream line data visualisation tool on National Health Service (NHS) publicly available statistical data using Agile methodology.

## Agile methodology
The first version 0.0.1 is the prototype of tool that only provides the basic examples function and only works on a single data. It consists of three components:
- Obtaining the data
- Pre-processing and storing of data
- Performing analysis

## Selected data
Only data about "A&E attendances and emergency admissions" was selected in version 0.0.1

https://www.england.nhs.uk/statistics/statistical-work-areas/ae-waiting-times-and-activity/ae-attendances-and-emergency-admissions-2023-24/

I believe that there are two most important indicators for the insufficient of medical resources and medical professions in the A&E (accident and emergency) department of a hospital, number of patients needed to wait for more than 12 hours (the maximum data provided in csv) and the number of total emergency cases monthly.

## System requirement
The main programming languages for this tool is Python (version 3.9.16) with SQL query. The version of required packages are shown below:
- datetime
- csv
- sqlite3
- requests 2.31.0
- matplotlib 3.6.1

## Design
- Step 0 is to create the SQLite database used to store all data, and this database is used for all following steps.
- Step 1 is to download all existing data (First available data is August 2020) and add into the constructed SQLite database in Step 0.
- Step 2 is to perform analysis on extracted data
  - Trend of Top 5 hospital with the highest number of patients needed to wait for more than 12 hours
  - Trend of Top 5 hospital with the highest number of total emergency cases monthly
  - Visualise the trends of number of patients needed to wait for more than 12 hours in a specific hospital
  - Visualise the trends of number of total emergency cases in a specific hospital

## Structure of SQLite database
- Organisation table: (Name and code for organisation and their parent organisation)
- MonthlyData table: All data extracted from NHS websites
- Relation: OrgCode as primary key in Organisation and forigen key in MonthlyData
- Pre-processing of data
  - Format of month is converted into "2020-08" for easier sorting and less storage than plain text
  - Duplicated input is omitted
  - To download the new data: Run the Python script every month to include the newest data
  - A csv file "organisation_code.csv" is generated to check the OrgCode for each organisation (hospital)

## Future plan
- Obtaining the period of month for data that database already stored for faster operation
– New function to download and add data in specific range of time
- Refactor SQLite table MonthlyData to divide data in each category into a table and linked with forigen key (Smaller table causes a faster SQL query)
- Add table in SQLite database about hospitals in each parent organisation
- Include more trend analysis function
- Include more NHS statistical data

## Example usage
- Run the Pyhton script: `python main.py`
- A SQLite database will be created with user defined filename
- Download and pre-processing of data are performed automatically
- 4 trend analysis are available (Option 1 to 4)
- Results for analysis of Hospital "WYE VALLEY NHS TRUST" (RLQ) are included 
