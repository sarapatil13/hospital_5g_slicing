from slice_config import URLLC_SLICE, EMBB_SLICE, MMTC_SLICE

class HospitalDevice:
    def __init__(self, device_id, name, device_type, slice_obj,
                 data_rate_mbps, critical):
        self.device_id = device_id
        self.name = name
        self.device_type = device_type
        self.slice_obj = slice_obj
        self.data_rate_mbps = data_rate_mbps
        self.critical = critical  # True = life-critical device
        self.active = True

    def __repr__(self):
        tag = "CRITICAL" if self.critical else "normal"
        return (f"  [{tag}] {self.name} | "
                f"Slice: {self.slice_obj.slice_type} | "
                f"Data Rate: {self.data_rate_mbps} Mbps")

# ----------------------------------------------------------
# URLLC Devices — life-critical, low latency
# ----------------------------------------------------------
SURGICAL_ROBOT_1  = HospitalDevice("D001", "Surgical Robot 1",
    "surgical_robot", URLLC_SLICE, 50, critical=True)
SURGICAL_ROBOT_2  = HospitalDevice("D002", "Surgical Robot 2",
    "surgical_robot", URLLC_SLICE, 50, critical=True)
ICU_MONITOR_1     = HospitalDevice("D003", "ICU Monitor 1",
    "icu_monitor", URLLC_SLICE, 10, critical=True)
ICU_MONITOR_2     = HospitalDevice("D004", "ICU Monitor 2",
    "icu_monitor", URLLC_SLICE, 10, critical=True)
EMERGENCY_ALERT   = HospitalDevice("D005", "Emergency Alert System",
    "emergency", URLLC_SLICE, 5, critical=True)

# ----------------------------------------------------------
# eMBB Devices — high bandwidth
# ----------------------------------------------------------
PATIENT_DB        = HospitalDevice("D006", "Patient Record System",
    "patient_db", EMBB_SLICE, 200, critical=False)
IMAGING_SYSTEM    = HospitalDevice("D007", "Medical Imaging System",
    "imaging", EMBB_SLICE, 500, critical=False)
VIDEO_CONSULT     = HospitalDevice("D008", "Video Consultation",
    "video", EMBB_SLICE, 100, critical=False)

# ----------------------------------------------------------
# mMTC Devices — IoT sensors, low power
# ----------------------------------------------------------
BED_TRACKER_1     = HospitalDevice("D009", "Bed Tracker 1",
    "bed_tracker", MMTC_SLICE, 1, critical=False)
BED_TRACKER_2     = HospitalDevice("D010", "Bed Tracker 2",
    "bed_tracker", MMTC_SLICE, 1, critical=False)
TEMP_SENSOR_1     = HospitalDevice("D011", "Temperature Sensor 1",
    "temp_sensor", MMTC_SLICE, 0.5, critical=False)
TEMP_SENSOR_2     = HospitalDevice("D012", "Temperature Sensor 2",
    "temp_sensor", MMTC_SLICE, 0.5, critical=False)
DRUG_DISPENSER    = HospitalDevice("D013", "Drug Dispenser",
    "drug_dispenser", MMTC_SLICE, 2, critical=False)

ALL_DEVICES = [
    SURGICAL_ROBOT_1, SURGICAL_ROBOT_2,
    ICU_MONITOR_1, ICU_MONITOR_2, EMERGENCY_ALERT,
    PATIENT_DB, IMAGING_SYSTEM, VIDEO_CONSULT,
    BED_TRACKER_1, BED_TRACKER_2,
    TEMP_SENSOR_1, TEMP_SENSOR_2, DRUG_DISPENSER
]

def print_device_summary():
    print("\n" + "="*60)
    print("        HOSPITAL DEVICES — SLICE ASSIGNMENT")
    print("="*60)
    for slice_type in ["URLLC", "eMBB", "mMTC"]:
        print(f"\n  --- {slice_type} Devices ---")
        for d in ALL_DEVICES:
            if d.slice_obj.slice_type == slice_type:
                print(d)
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    print_device_summary()