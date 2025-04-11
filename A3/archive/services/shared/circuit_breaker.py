import os
import json
import time

CIRCUIT_BREAKER_THRESHOLD = 5  # Number of failures before opening circuit
CIRCUIT_BREAKER_TIMEOUT = 60   # Seconds to keep circuit open
CIRCUIT_BREAKER_FILE = "/mnt/circuit/circuit_state.json"

def init_circuit_state():
    if not os.path.exists(CIRCUIT_BREAKER_FILE):
        with open(CIRCUIT_BREAKER_FILE, "w") as f:
            json.dump({"state": "closed", "last_failure": 0}, f)
            
            
def load_circuit_state() -> dict:
    try:
        with open(CIRCUIT_BREAKER_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"state": "closed", "last_failure": 0}

def save_circuit_state(state: dict):
    with open(CIRCUIT_BREAKER_FILE, "w") as f:
        json.dump(state, f)

def is_circuit_open():
    state = load_circuit_state()
    if state["state"] == "open":
        elapsed = time.time() - state["last_failure"]
        if elapsed >= CIRCUIT_BREAKER_TIMEOUT:
            return "half-open"
        return "open"
    return "closed"

def open_circuit():
    save_circuit_state({"state": "open", "last_failure": time.time()})

def close_circuit():
    save_circuit_state({"state": "closed", "last_failure": 0})
