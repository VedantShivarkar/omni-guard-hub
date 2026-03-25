def generate_dji_kml(target_lat, target_lng, neighbor_signals):
    kml_header = """<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2">
    <Document><name>OmniGuard Recon Mission</name>"""
    
    waypoints = f"<Placemark><name>Priority 1</name><Point><coordinates>{target_lng},{target_lat},100</coordinates></Point></Placemark>"
    
    # Simple logic: Add nearby critical signals to the flight path
    for i, sig in enumerate(neighbor_signals[:5]):
        # Assume sig['location_str'] parsing logic here
        waypoints += f"<Placemark><name>Waypoint {i+2}</name><Point><coordinates>{sig['lng']},{sig['lat']},100</coordinates></Point></Placemark>"
    
    kml_footer = "</Document></kml>"
    return kml_header + waypoints + kml_footer