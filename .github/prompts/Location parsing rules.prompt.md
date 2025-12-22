---
agent: agent
---
When parsing location information from text, follow these rules to ensure accurate extraction and categorization:

# Location Parsing Rules

Every tokenized location that separated by a comma (",") should be treated as an individual location entity.

## Parenthetical Sub-locations

But if the string has "(" and ")", then the content inside the parentheses should be treated as a sub-location of the main location before the parentheses. The main location and sub-location should be linked together in one location entity.

Example 1: Luzon Batanes, Cagayan including Babuyan Islands, the northwestern portion of Isabela (Santo Tomas, Santa Maria, Quezon, Roxas, Delfin Albano, San Pablo, Cabagan, San Manuel, Mallig), Apayao, Abra, Kalinga, Mountain Province, Ifugao, Benguet, Ilocos Norte, Ilocos Sur, La Union, the western and central portions of Pangasinan (Basista, Lingayen, City of Alaminos, Anda, Malasiqui, San Fabian, Mangaldan, Mapandan, Burgos, Dagupan City, Binalonan, Bolinao, Aguilar, San Manuel, Sual, Labrador, Bani, Pozorrubio, City of Urdaneta, Laoac, Mabini, San Carlos City, Manaoag, Binmaley, San Jacinto, Bugallon, Infanta, Agno, Calasiao, Santa Barbara, Dasol, Sison, Mangatarem, Urbiztondo), and the northern portion of Zambales (Santa Cruz, Candelaria)

Example 1 when parsed:
- Luzon Batanes, 
- Cagayan including Babuyan Islands, 
- the northwestern portion of Isabela (Santo Tomas, Santa Maria, Quezon, Roxas, Delfin Albano, San Pablo, Cabagan, San Manuel, Mallig), 
- Apayao, 
- Abra, 
- Kalinga, 
- Mountain Province, 
- Ifugao, 
- Benguet, 
- Ilocos Norte, 
- Ilocos Sur, 
- La Union, 
- the western and central portions of Pangasinan (Basista, Lingayen, City of Alaminos, Anda, Malasiqui, San Fabian, Mangaldan, Mapandan, Burgos, Dagupan City, Binalonan, Bolinao, Aguilar, San Manuel, Sual, Labrador, Bani, Pozorrubio, City of Urdaneta, Laoac, Mabini, San Carlos City, Manaoag, Binmaley, San Jacinto, Bugallon, Infanta, Agno, Calasiao, Santa Barbara, Dasol, Sison, Mangatarem, Urbiztondo), 
- the northern portion of Zambales (Santa Cruz, Candelaria),

## Duplicates

If a location name is duplicate to another entry, check first on what major island group it belongs to (Luzon, Visayas, Mindanao, Other). If they belong to different island groups, keep both entries and tag them with their respective island groups. 

If they belong to the same island group, then it is in different province or city, so keep both entries as well if the difference is pointed out or if context is obvious, or else only keep one entry.

## Vague Locations

If a location is too vague (e.g., only the island group is mentioned like "northeastern Mindanao, Eastern Visayas" or "Most of Luzon, Western Visayas"), You should still keep the location entry as is without breaking it down further and assign it to the "Other" island group in typhoonHubType.ts

