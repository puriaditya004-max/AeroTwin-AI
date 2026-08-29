from datetime import datetime, timezone

from models import SensorData, TelemetryFrame


def create_telemetry_frame():
    sensors = SensorData(
        rpm=4200,
        temperature_c=82,
        oil_pressure_psi=52,
        vibration_g=0.25,
        fuel_flow_lph=2.4,
        throttle_pct=65,
        altitude_m=1200,
        ambient_temperature_c=28,
    )

    return TelemetryFrame(
        engineId="ENGINE-001",
        missionId="MISSION-001",
        timestamp=datetime.now(timezone.utc),
        sensors=sensors,
    )


if __name__ == "__main__":
    frame = create_telemetry_frame()
    print(frame)