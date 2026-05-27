from network_simulator import NetworkSimulator
from emergency_scenario import EmergencyReallocation

def main():
    sim = NetworkSimulator()

    # Run normal simulation
    sim.run_normal()
    sim.print_summary(sim.results, label="— NORMAL")

    # Run emergency simulation
    emergency_results = sim.run_emergency()
    sim.print_summary(emergency_results, label="— EMERGENCY")

    # Run reallocation demo
    er = EmergencyReallocation()
    if er.detect_emergency(92):
        er.reallocate()
    er.restore()

if __name__ == "__main__":
    main()
