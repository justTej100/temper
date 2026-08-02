"""Known Polymarket weather cities → ICAO / coordinates."""

STATIONS: dict[str, dict] = {
    "new york": {"name": "New York City", "icao": "KLGA", "lat": 40.7772, "lon": -73.8726, "country": "US"},
    "nyc": {"name": "New York City", "icao": "KLGA", "lat": 40.7772, "lon": -73.8726, "country": "US"},
    "chicago": {"name": "Chicago", "icao": "KORD", "lat": 41.9742, "lon": -87.9073, "country": "US"},
    "dallas": {"name": "Dallas", "icao": "KDAL", "lat": 32.8471, "lon": -96.8518, "country": "US"},
    "atlanta": {"name": "Atlanta", "icao": "KATL", "lat": 33.6407, "lon": -84.4277, "country": "US"},
    "miami": {"name": "Miami", "icao": "KMIA", "lat": 25.7959, "lon": -80.2870, "country": "US"},
    "los angeles": {"name": "Los Angeles", "icao": "KLAX", "lat": 33.9425, "lon": -118.4081, "country": "US"},
    "seattle": {"name": "Seattle", "icao": "KSEA", "lat": 47.4502, "lon": -122.3088, "country": "US"},
    "denver": {"name": "Denver", "icao": "KDEN", "lat": 39.8561, "lon": -104.6737, "country": "US"},
    "houston": {"name": "Houston", "icao": "KIAH", "lat": 29.9902, "lon": -95.3368, "country": "US"},
    "london": {"name": "London", "icao": "EGLL", "lat": 51.4700, "lon": -0.4543, "country": "GB"},
    "paris": {"name": "Paris", "icao": "LFPG", "lat": 49.0097, "lon": 2.5479, "country": "FR"},
    "tokyo": {"name": "Tokyo", "icao": "RJTT", "lat": 35.5494, "lon": 139.7798, "country": "JP"},
    "seoul": {"name": "Seoul (Incheon)", "icao": "RKSI", "lat": 37.4602, "lon": 126.4407, "country": "KR"},
    "seoul (incheon)": {"name": "Seoul (Incheon)", "icao": "RKSI", "lat": 37.4602, "lon": 126.4407, "country": "KR"},
    "hong kong": {"name": "Hong Kong", "icao": "VHHH", "lat": 22.3080, "lon": 113.9185, "country": "HK"},
    "shanghai": {"name": "Shanghai", "icao": "ZSPD", "lat": 31.1443, "lon": 121.8083, "country": "CN"},
    "singapore": {"name": "Singapore", "icao": "WSSS", "lat": 1.3644, "lon": 103.9915, "country": "SG"},
    "madrid": {"name": "Madrid", "icao": "LEMD", "lat": 40.4983, "lon": -3.5676, "country": "ES"},
    "milan": {"name": "Milan", "icao": "LIMC", "lat": 45.6306, "lon": 8.7281, "country": "IT"},
    "munich": {"name": "Munich", "icao": "EDDM", "lat": 48.3538, "lon": 11.7861, "country": "DE"},
    "amsterdam": {"name": "Amsterdam", "icao": "EHAM", "lat": 52.3105, "lon": 4.7683, "country": "NL"},
    "toronto": {"name": "Toronto", "icao": "CYYZ", "lat": 43.6777, "lon": -79.6248, "country": "CA"},
    "buenos aires": {"name": "Buenos Aires", "icao": "SAEZ", "lat": -34.8222, "lon": -58.5358, "country": "AR"},
    "wellington": {"name": "Wellington", "icao": "NZWN", "lat": -41.3272, "lon": 174.8050, "country": "NZ"},
    "auckland": {"name": "Auckland", "icao": "NZAA", "lat": -37.0082, "lon": 174.7850, "country": "NZ"},
    "kuala lumpur": {"name": "Kuala Lumpur", "icao": "WMKK", "lat": 2.7456, "lon": 101.7099, "country": "MY"},
    "beijing": {"name": "Beijing", "icao": "ZBAA", "lat": 40.0799, "lon": 116.6031, "country": "CN"},
    "taipei": {"name": "Taipei", "icao": "RCTP", "lat": 25.0777, "lon": 121.2328, "country": "TW"},
    "istanbul": {"name": "Istanbul", "icao": "LTFM", "lat": 41.2753, "lon": 28.7519, "country": "TR"},
    "moscow": {"name": "Moscow", "icao": "UUEE", "lat": 55.9726, "lon": 37.4146, "country": "RU"},
    "tel aviv": {"name": "Tel Aviv", "icao": "LLBG", "lat": 32.0114, "lon": 34.8867, "country": "IL"},
    "helsinki": {"name": "Helsinki", "icao": "EFHK", "lat": 60.3172, "lon": 24.9633, "country": "FI"},
    "warsaw": {"name": "Warsaw", "icao": "EPWA", "lat": 52.1657, "lon": 20.9671, "country": "PL"},
    "cape town": {"name": "Cape Town", "icao": "FACT", "lat": -33.9715, "lon": 18.6021, "country": "ZA"},
    "karachi": {"name": "Karachi", "icao": "OPKC", "lat": 24.9065, "lon": 67.1608, "country": "PK"},
    "jeddah": {"name": "Jeddah", "icao": "OEJN", "lat": 21.6796, "lon": 39.1565, "country": "SA"},
    "ankara": {"name": "Ankara", "icao": "LTAC", "lat": 40.1281, "lon": 32.9951, "country": "TR"},
    "manila": {"name": "Manila", "icao": "RPLL", "lat": 14.5086, "lon": 121.0198, "country": "PH"},
    "busan": {"name": "Busan", "icao": "RKPK", "lat": 35.1795, "lon": 128.9382, "country": "KR"},
    "shenzhen": {"name": "Shenzhen", "icao": "ZGSZ", "lat": 22.6393, "lon": 113.8107, "country": "CN"},
    "guangzhou": {"name": "Guangzhou", "icao": "ZGGG", "lat": 23.3924, "lon": 113.2988, "country": "CN"},
    "wuhan": {"name": "Wuhan", "icao": "ZHHH", "lat": 30.7838, "lon": 114.2081, "country": "CN"},
    "chengdu": {"name": "Chengdu", "icao": "ZUUU", "lat": 30.5785, "lon": 103.9470, "country": "CN"},
    "chongqing": {"name": "Chongqing", "icao": "ZUCK", "lat": 29.7192, "lon": 106.6417, "country": "CN"},
    "qingdao": {"name": "Qingdao", "icao": "ZSQD", "lat": 36.2661, "lon": 120.3744, "country": "CN"},
    "lucknow": {"name": "Lucknow", "icao": "VILK", "lat": 26.7606, "lon": 80.8893, "country": "IN"},
}


def resolve_city(raw_name: str) -> dict | None:
    key = raw_name.strip().lower()
    if key in STATIONS:
        return STATIONS[key]
    for k, v in STATIONS.items():
        if k in key or key in k:
            return v
    return None
