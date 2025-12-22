---
agent: agent
---
We need to improve the accuracy of text extraction from the PDFs

# Location of the annotated files
Location: ./dataset/pdfs_annotation/

These annotated files have manual extracted typhoon data and it should be considered as the benchmark for accuracy testing. 

These files should not be modified for any reason.

# Table Format
When analyzing the typhoon data especially when extracting the Wind and Tainfall Signals, this should be the expected table.

This is an example of the expected table format for typhoon wind signals:
|------------------------------------------------------------------------------------------------------------|
|                               TROPICAL CYCLONE WIND SIGNALS IN EFFECT                                      |
|------------------------------------------------------------------------------------------------------------|
| TCWS No. | Luzon                         | Visayas                       | Mindanao                        |
|----------|-------------------------------|-------------------------------|---------------------------------|
| **2**    | Quezon, (ex. Luzon cities...) | Cebu, (ex. Visayas cities...) | Davao, (ex. Mindanao cities...) |
|----------|-------------------------------|-------------------------------|---------------------------------|
| **1**    | Makati, (ex. Luzon cities...) | Talisay, (ex. Visayas cities...) | Sulu, (ex. Mindanao cities...) |
|------------------------------------------------------------------------------------------------------------|

And this is an example of the expected table format for typhoon rainfall signals:
|------------------------------------------------------------------------------------------------------------|
|                                    HAZARDS AFFECTING LAND AREAS                                            |
|------------------------------------------------------------------------------------------------------------|
|Heavy Rainfall                                                                                              |
|Tonight through tomorrow afternoon, Tropical Storm “DANTE” is forecast to bring:                            |
| Moderate to heavy with at times intense rains over Surigao del Norte, Dinagat Islands, Leyte, Southern Leyte, Biliran, Masbate, and Romblon  |
| Moderate to heavy rains over Surigao del Sur, Agusan del Norte, Camiguin, Samar, Bohol, the northern portion of Cebu including Bantayan and Camotes Islands, Capiz, Iloilo, Sorsogon, Albay, Camarines Norte, Camarines Sur, Marinduque, and the southern portion of Quezon |
| Light to moderate with at times heavy rains are also likely over Misamis Oriental, Agusan del Sur, Bukidnon, Catanduanes, and the rest of Visayas.|
|------------------------------------------------------------------------------------------------------------|

# Expected Output
When extracting the typhoon data from the PDF, the output should be structured in a way that reflects the table format above.

For Wind Signals:
"signal_warning_tags1": {
  "Luzon": "Makati, (ex. Luzon cities...)",
  "Visayas": "Talisay, (ex. Visayas cities...)",
  "Mindanao": "Sulu, (ex. Mindanao cities...)",
  "Other": null
},
"signal_warning_tags2": {
  "Luzon": "Quezon, (ex. Luzon cities...)",
  "Visayas": "Cebu, (ex. Visayas cities...)",
  "Mindanao": "Davao, (ex. Mindanao cities...)",
  "Other": null
},
"signal_warning_tags3": {
  "Luzon": null,
  "Visayas": null,
  "Mindanao": null,
  "Other": null
},
"signal_warning_tags4": {
  "Luzon": null,
  "Visayas": null,
  "Mindanao": null,
  "Other": null
},
"signal_warning_tags5": {
  "Luzon": null,
  "Visayas": null,
  "Mindanao": null,
  "Other": null
},

For Rainfall Signals:
"rainfall_warning_tags1": {
  "Luzon": "Romblon",
  "Visayas": "Leyte, Southern Leyte, Biliran, Masbate",
  "Mindanao": "Surigao del Norte, Dinagat Islands",
  "Other": null
},
"rainfall_warning_tags2": {
  "Luzon": "Sorsogon, Albay, Camarines Norte, Camarines Sur, Marinduque, Southern Quezon",
  "Visayas": "Samar, Bohol, Northern Cebu, Capiz, Iloilo",
  "Mindanao": "Surigao del Sur, Agusan del Norte, Camiguin",
  "Other": null
},
"rainfall_warning_tags3": {
  "Luzon": "Catanduanes",
  "Visayas": null,
  "Mindanao": "Misamis Oriental, Agusan del Sur, Bukidnon",
  "Other": "The rest of Visayas"
}