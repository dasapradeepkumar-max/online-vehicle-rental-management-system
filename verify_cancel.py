import urllib.request
import urllib.parse
import urllib.error
import datetime
import json
import os

BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")

def post_json(url, data=None, headers=None):
    if headers is None: headers = {}
    headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, method='POST')
    for k, v in headers.items(): req.add_header(k, v)
    body = json.dumps(data).encode('utf-8') if data else b''
    try:
        with urllib.request.urlopen(req, data=body) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())
        
def get_json(url, headers=None):
    if headers is None: headers = {}
    req = urllib.request.Request(url, method='GET')
    for k, v in headers.items(): req.add_header(k, v)
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

def run_test():
    # 1. Start session by requesting OTP
    print("Requesting OTP for testuser@vehiclehub.local...")
    email = "testuser@vehiclehub.local"
    status, res = post_json(f"{BASE_URL}/api/auth/send-otp", data={"identifier": email})
    if status != 200:
        print("Failed to send OTP:", res)
        return

    # To get the OTP, we will query the local sqlite DB
    import sqlite3
    conn = sqlite3.connect("instance/site.db")
    c = conn.cursor()
    c.execute("select id from user where email=?", (email,))
    user_id = c.fetchone()[0]
    
    c.execute("select code from otp where user_id=? order by id desc limit 1", (user_id,))
    otp_code = c.fetchone()[0]
    conn.close()
    print(f"Retrieved OTP from DB: {otp_code}")
    
    # 2. Verify OTP and get token
    status, res = post_json(f"{BASE_URL}/api/auth/verify-otp", data={"identifier": email, "otp": otp_code})
    if status != 200:
        print("Failed to verify OTP:", res)
        return
        
    token = res['token']
    headers = {"Authorization": f"Bearer {token}"}
    print("Successfully authenticated and received JWT.")
    
    # 3. Create a booking for a vehicle
    # Let's get vehicle ID 1
    today = datetime.date.today()
    # Use a future pickup safely beyond the 24-hour cancellation cutoff.
    start_date = (today + datetime.timedelta(days=30)).isoformat()
    end_date = (today + datetime.timedelta(days=32)).isoformat()
    
    print(f"Creating booking for Vehicle ID 1 from {start_date} to {end_date}...")
    status, res = post_json(f"{BASE_URL}/api/bookings", headers=headers, data={
        "vehicle_id": 1,
        "start_date": start_date,
        "end_date": end_date,
        "pickup_time": "12:00",
        "return_time": "18:00"
    })
    
    if status != 201:
        print("Failed to create booking:", res)
        return
        
    booking_data = res
    booking_id = booking_data['booking']['id']
    print(f"Successfully created Booking #{booking_id}")
    
    # 4. Check vehicle status via API
    status, res = get_json(f"{BASE_URL}/api/vehicles/1")
    if status == 200:
        print(f"Vehicle #1 Status before cancellation: {res.get('status')}")
    else:
        print("Failed to get vehicle:", res)
        
    # 5. Cancel the booking
    print(f"Cancelling Booking #{booking_id}...")
    status, res = post_json(f"{BASE_URL}/api/bookings/{booking_id}/cancel", headers=headers)
    if status != 200:
        print("Failed to cancel booking:", res)
        return
        
    cancel_data = res
    print(f"Cancellation Response: {json.dumps(cancel_data, indent=2)}")
    
    # 6. Check vehicle status again
    status, res = get_json(f"{BASE_URL}/api/vehicles/1")
    if status == 200:
        print(f"Vehicle #1 Status after cancellation: {res.get('status')}")
        v_status = res.get('status')
        if v_status == 'available':
            print("SUCCESS! Vehicle is correctly marked as available.")
        else:
            print("FAILURE! Vehicle status is not 'available'.")
    else:
        print("Failed to get vehicle:", res)

if __name__ == "__main__":
    run_test()
