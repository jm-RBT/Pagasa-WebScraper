---
agent: Python Programmer Agent
---
This is a prompt for the rules that needs to be followed when extracting tables from a text of PAGASA Advisory page HTML DOM

# Overview
Originally designed for extracting heavy rainfall advisory data from PAGASA's advisory pages, this prompt outlines the rules and guidelines for accurately parsing and structuring the information into a tabular format.

The official URL for PAGASA's heavy rainfall advisory page is:
- https://www.pagasa.dost.gov.ph/weather/weather-advisory

But sometimes there will be no weather advisory issued, in that case, the URL we will be using is from web archive:
- https://web.archive.org/cdx/search/cdx?url=https://www.pagasa.dost.gov.ph/weather/weather-advisory&matchType=prefix&output=json

Get the json data and open each of the URLs based on timestamp to extract the advisory data using this URL pattern:
- https://web.archive.org/web/{timestamp}/https://www.pagasa.dost.gov.ph/weather/weather-advisory

# Extraction Rules

This will be the indicator of the first column of each row in the table, if the text starts with any of these keywords:
- "Forecast Rainfall", "Forecast" > This is the first column of the table header or first row.
- "200 mm", ">200 mm", "(>200 mm)" > This is the first column of the table after the header row.
- "100 - 200 mm", "(100 - 200 mm)" > This is the first column of the table after which will be the 2nd row after header row.
- "50 - 100 mm", "(50 - 100 mm)" > This is the first column of the table after which will be the 3rd row after header row.

Identifying the next table header row is useless since we will be consolidating all location data into one assignment based on first column's row indicators.

We should only extract text after the first column's row indicators, and stop at text that doesn't match in the bin/consolidated_locations.csv file. Other indicator as well is that if there is a triple or double whitespace between texts, that means it's the end of that row's location data and after the whitespace is another column data for "Potential Impacts" column which is the last column of the table that we don't need to extract. Sometimes the column data will also be empty where it will have "-" or double whitespace only.

# Rainfall Warning Categories Reference

```
Forecast Rainfall Amounts:
(Red) 200 mm or more - Heavy to intense rainfall likely to cause widespread flooding in low-lying areas 

(Orange) 100 - 200 mm - Heavy rainfall likely to cause flooding in low-lying areas

(Yellow) 50 - 100 mm - Moderate to heavy rainfall likely to cause minor flooding in low-lying areas
```

# Example Table structure to be extracted
Forecast Rainfall | Today | Tomorrow | Next tomorrow | Potential Impacts |
--------------------------------------------------------------------------------|
(>200mm) | Locations | Locations | Locations | Impacts |
--------------------------------------------------------------------------------|
(100 - 200 mm) | Locations | Locations | Locations | Impacts |
--------------------------------------------------------------------------------|
(50 - 100 mm) | Locations | Locations | Locations | Impacts |
--------------------------------------------------------------------------------|

Only extract the Locations and ignore the Potential Impacts column. The Locations should be consolidated into one cell per row separated by commas.

# Notes
- Ensure that the extracted locations match those in the bin/consolidated_locations.csv file. Check the locations against this file to ensure accuracy. Follow the "Location parsing rules" prompt as much as possible.

- If no advisory is issued, return an empty table or a message indicating no data is available.

- Be mindful of variations in formatting and structure across different advisory pages. Adapt the extraction logic as needed to handle these differences while adhering to the core rules outlined above.

# Output Format
The ouput of the extraction should be in JSON format as follows:

```
  "rainfall_warnings": {
    "red": [],
    "orange": [],
    "yellow": []
  }
```

Where:
- "red" corresponds to locations under the (>200 mm) category.
- "orange" corresponds to locations under the (100 - 200 mm) category.
- "yellow" corresponds to locations under the (50 - 100 mm) category.

# Example Output
```
{
  "rainfall_warnings": {
    "red": ["Location1", "Location2", "Location3"],
    "orange": ["Location4", "Location5"],
    "yellow": ["Location6", "Location7", "Location8"]
  }
}
```

# End of Prompt