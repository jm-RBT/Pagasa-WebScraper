type IslandGroupType = {
    Luzon: string | null,
    Visayas: string | null,
    Mindanao: string | null
} 

type TyphoonHubType = {
    typhoon_location_text: string,
    typhoon_movement: string,
    typhoon_windspeed: string,
    updated_datetime: string,
    signal_warning_tags1: IslandGroupType,
    signal_warning_tags2: IslandGroupType,
    signal_warning_tags3: IslandGroupType,
    signal_warning_tags4: IslandGroupType,
    signal_warning_tags5: IslandGroupType,
    rainfall_warning_tags1: IslandGroupType,
    rainfall_warning_tags2: IslandGroupType,
    rainfall_warning_tags3: IslandGroupType,
}