# SDN Flow Audit - Simple Code Documentation

## 1. Purpose
This project checks whether a controller report matches the switch truth data.

It helps detect suspicious behavior such as:
- Hidden flows (in switch truth but missing from controller report)
- Extra flows (in controller report but not in switch truth)
- Tampered flows (same ID but different match/action fields)

## 2. Files
- comparer.py: Main Python GUI application.
- network.txt: Ground-truth flows from the switch.
- report.json: Flows reported by the controller app.

## 3. Input Format
### network.txt format
Each line should follow this pattern:
flow_id:<id>, match:<value>, action:<value>

Example:
flow_id:101, match:in_port=1, action:output=2

### report.json format
JSON object with a top-level flows list:
{
  "flows": [
    {"id": "101", "match": "in_port=1", "action": "output=2"}
  ]
}

## 4. How The Code Works
### parse_truth_file(path)
- Reads network.txt and report.json and compares them


## 5. Running The Program
From the project folder:

py comparer.py

This opens the GUI dashboard.
- Allows selecting truth and report files.
- Runs audit when user clicks Run Audit.
- Displays results in a scrollable text area.
- Shows status label in green (clean) or red (incident found).
