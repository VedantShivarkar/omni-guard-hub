import json

def generate_drone_mission(target_signal, nearby_signals):
    """
    Generates a KML file for DJI Pilot. 
    It creates a path from HQ -> Target -> Nearby Critical Points.
    """
    # Parse target coords
    t_lat, t_lng = parse_coords(target_signal['location_str'])
    
    kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>OmniGuard_Mission_{target_signal['id'][:8]}</name>
    <Style id="waypoint"><IconStyle><scale>1.2</scale></IconStyle></Style>
    <Placemark>
      <name>PRIORITY_ALPHA</name>
      <styleUrl>#waypoint</styleUrl>
      <Point><coordinates>{t_lng},{t_lat},100</coordinates></Point>
    </Placemark>
    """
    
    # Add nearby waypoints for recon
    for i, sig in enumerate(nearby_signals):
        coords = parse_coords(sig['location_str'])
        if coords:
            kml += f"""
    <Placemark>
      <name>RECON_{i+1}</name>
      <Point><coordinates>{coords[1]},{coords[0]},80</coordinates></Point>
    </Placemark>"""
            
    kml += "\n  </Document>\n</kml>"
    return kml

def parse_coords(s):
    try:
        parts = s.split(',')
        return float(parts[0]), float(parts[1])
    except: return None