from requests import get
from bs4 import BeautifulSoup
from itertools import compress

url = "https://en.wikipedia.org/wiki/List_of_California_wildfires"

page = get(url).text

soup = BeautifulSoup(page, 'html.parser')

# Table Titles
table_titles_html = soup.find_all(class_ = 'mw-headline')
table_titles = [title.get_text() for title in table_titles_html][:-3]
mask = [1,1,1,0,0,1,1,0]
table_titles = list(compress(table_titles, mask))


# Column Titles
tables = soup.find_all('table')
table_headers_html = [table.find_all('th') for table in tables]
table_headers = []
for table in table_headers_html:
    table_headers_next = [header.get_text().replace('\n','') for header in table]
    table_headers.append(table_headers_next)
table_headers = table_headers[:5]

# Table Data
table_data_html = [table.find_all('tr')[1:] for table in tables]
table_data = []
for table in table_data_html:
    rows = []
    for row_html in table:
        row = []
        next_row = row_html.find_all('td')
        for element in next_row:
            next_element = element.get_text().replace('\n','')
            row.append(next_element)
        rows.append(row)
    table_data.append(rows)
table_data = table_data[:5]

# All together now
import pandas as pd
tables_all_data = zip(table_titles, table_headers, table_data)
dfs = {title: pd.DataFrame(data, columns=headers) for title, headers, data in tables_all_data}

# Yearly Statistics has different column headers and format. Process independently.
summary_post_2000 = dfs['Yearly statistics']
dfs.pop('Yearly statistics', None)
table_titles = ['Largest wildfires','Deadliest wildfires','Most destructive wildfires','Notable fires']

# Cleaning data
# Remove Wikipedia reference links
summary_post_2000 = summary_post_2000.drop(columns='Ref')
dfs['Notable fires'] = dfs['Notable fires'].drop(columns='Ref')
dfs['Deadliest wildfires'].iloc[0,0] = dfs['Deadliest wildfires'].iloc[0,0].replace('[13][14][15]','')
dfs['Most destructive wildfires'].iloc[0,0] = dfs['Most destructive wildfires'].iloc[0,0].replace('[13][14][15]','')

# Drop totals column
summary_post_2000 = summary_post_2000[:-1]

# Alter 'Start date' column to reflect 'start year'. Change type to int
start_year = [int(date.split(' ')[1]) for date in dfs['Largest wildfires']['Start date']]
dfs['Largest wildfires']['Start date'] = start_year

# Change type of Hectares and Acres to numerical
for title in dfs:
    for index, val in enumerate(dfs[title]['Hectares']):
        dfs[title]['Hectares'][index] = val.replace(',','')
    for index, val in enumerate(dfs[title]['Acres']):
        dfs[title]['Acres'][index] = val.replace(',','')

# Fill missing data
missing_acres = dfs['Most destructive wildfires']['Acres'][9]
conversion = .404686
dfs['Most destructive wildfires']['Hectares'][9] = round(int(missing_acres) * conversion)

for title in dfs:
    dfs[title]['Hectares'] = dfs[title]['Hectares'].astype('int')
    dfs[title]['Acres'] = dfs[title]['Acres'].astype('int')

def cleanCounties(county_list):
    return county_list.split(',')[0]

# For fires that span multiple counties, pick one to map it
for title in dfs:
    dfs[title]['County'] = dfs[title]['County'].apply(cleanCounties)

fips = pd.read_csv("csv/ca_fips.csv", dtype={"fips": str})

def findCountyFips(county):
    for index, row in fips.iterrows():
        if row[1] == county:
            return row[0]

# Add fips codes to dfs
for title in dfs:
    dfs[title]['fips'] = dfs[title]['County'].apply(findCountyFips)

from urllib.request import urlopen
import json
with urlopen('https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json') as response:
    counties = json.load(response)

# Determine dimensionality of array
def isSimpleArray(ndarray):
    answer = (len(ndarray) == 1)
    return answer

# Approximate latitude and longitude of county to a single point
def returnLatLon(ndarray):
    if isSimpleArray(ndarray):
        return ndarray[0][0][::-1]
    return ndarray[0][0][0][::-1]

ca_counties = []
for county in counties['features']:
    if county['properties']['STATE'] == '06':
        lat_lon = returnLatLon(county['geometry']['coordinates'])
        fips_and_coordinates = (county['id'], lat_lon)
        ca_counties.append(fips_and_coordinates)

def findCountyLat(fips):
    for county in ca_counties:
        if county[0] == fips:
            return county[1][0]

def findCountyLon(fips):
    for county in ca_counties:
        if county[0] == fips:
            return county[1][1]

# Add Lat and Lon for each county
for title in dfs:
    dfs[title]['lat'] = dfs[title]['fips'].apply(findCountyLat)
    dfs[title]['lon'] = dfs[title]['fips'].apply(findCountyLon)

# Manually update some county locations for higher accuracy
county_lat_lon = dict(
    los_angeles = (34.0522222,-118.2427778),
    ventura = (34.2783352,-119.2931676),
    santa_barbara = (34.4208333,-119.6972222),
    mendocino = (39.3076744,-123.7994591),
    fresno = (36.7477778,-119.7713889),
    napa = (38.2972222,-122.2844444),
    san_joaqin = (36.6066162,-120.1890447),
    lassen = (40.651844,-120.869483),
    san_bernardino = (34.115784,-117.302399)
)
for title in dfs:
    for index, row in enumerate(dfs[title]['County']):
        if row == 'Los Angeles':
            dfs[title]['lat'][index] = 34.0522222
            dfs[title]['lon'][index] = -118.2427778
        if row == 'Ventura':
            dfs[title]['lat'][index] = 34.2783352
            dfs[title]['lon'][index] = -119.2931676
        if row == 'Santa Barbara':
            dfs[title]['lat'][index] = 34.4208333
            dfs[title]['lon'][index] = -119.6972222
        if row == 'Mendocino':
            dfs[title]['lat'][index] = 39.3076744
            dfs[title]['lon'][index] = -123.7994591
        if row == 'Fresno':
            dfs[title]['lat'][index] = 36.7477778
            dfs[title]['lon'][index] = -119.7713889
        if row == 'Napa':
            dfs[title]['lat'][index] = 38.2972222
            dfs[title]['lon'][index] = -122.2844444
        if row == 'San Joaqin':
            dfs[title]['lat'][index] = 36.6066162
            dfs[title]['lon'][index] = -120.1890447
        if row == 'Lassen':
            dfs[title]['lat'][index] = 40.651844
            dfs[title]['lon'][index] = -120.869483
        if row == 'San Bernardino':
            dfs[title]['lat'][index] = county_lat_lon['san_bernardino'][0]
            dfs[title]['lon'][index] = county_lat_lon['san_bernardino'][1]