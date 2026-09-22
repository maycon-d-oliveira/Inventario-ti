"""
Arquivo: routes/pulsus.py
Propósito:
    Expor endpoint para buscar dados de dispositivo via API Pulsus.
"""

import os
import requests
from flask import Blueprint, jsonify

bp = Blueprint('pulsus', __name__)

@bp.route('/api/pulsus/device/<int:mdm_id>')
def get_device(mdm_id):
    # If mdm_id is provided, try to fetch from Pulsus API and persist data
    # If the device exists in DB, update its details; otherwise return fetched data
    from database import execute, query_one
    # Check if device already exists in aparelhos
    existing = query_one("SELECT id FROM aparelhos WHERE mdm_id = ?", (mdm_id,))
    if existing:
        # Device already in DB, just return its stored info
        device_row = query_one("SELECT marca, modelo, imei, mac_wifi, serial FROM aparelhos WHERE mdm_id = ?", (mdm_id,))
        return jsonify({
            'imei': device_row['imei'],
            'modelo': device_row['modelo'],
            'mac_wifi': device_row['mac_wifi'],
            'serial': device_row['serial'],
            'marca': device_row['marca']
        })
    # Not in DB, fetch from Pulsus

    token = os.getenv('PULSUS_TOKEN')
    if not token:
        return jsonify({'error': 'Pulsus token not configured'}), 500
    # Use the official Pulsus API endpoint.
    base_url = 'https://api.pulsus.mobi'
    url = f"{base_url}/v1/devices"
    headers = {
        'ApiToken': token,
        'Content-Type': 'application/json'
    }
    
    params = {
        'extended_format': 'true',
        'ids': mdm_id
    }
    try:
        resp = requests.get(url, headers=headers, params=params)
    except requests.exceptions.RequestException as e:
        # Log the exception for debugging (Flask's logger)
        import logging
        logging.getLogger('pulsus').error(f'Error contacting Pulsus API: {e}')
        return jsonify({'error': 'Unable to contact Pulsus API'}), 502
    if resp.status_code != 200:
        return jsonify({'error': 'Device not found'}), 404
    data = resp.json()
    
   
    if not isinstance(data, list) or len(data) == 0:
        return jsonify({'error': 'Device not found'}), 404


    device = data[0]
    
    result = {
        'imei': device.get('identifier'),
        'modelo': device.get('model'),
        'serial': device.get('serial_number'),
        'mac_wifi': device.get('mac_address'),
        'marca':device.get('manufacturer')
    }
    return jsonify(result)

