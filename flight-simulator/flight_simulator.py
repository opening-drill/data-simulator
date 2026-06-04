import json
import os
import sched
import threading
import time
import redis


def _redis_client() -> redis.Redis:
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        password=os.getenv("REDIS_PASSWORD") or None,
        decode_responses=True,
    )


def advance_drone_step(scheduler_instance, flight_id: str, interval_seconds: float):
    """מקדמת את הרחפן בהתבסס על מפתח הטיסה flight:flight_id ברדיס."""
    r = _redis_client()

    # המפתח החדש המאחד את כל נתוני הטיסה
    flight_key = f"flight:{flight_id}"

    # 1. שליפת אובייקט הטיסה המלא
    raw_flight_data = r.get(flight_key)
    if not raw_flight_data:
        print(f"[{time.strftime('%X')}] ⚠️ Flight {flight_id}: Data not found. Retrying later...")
        # נתזמן בדיקה חוזרת למקרה שהנתונים יעלו בהמשך
        scheduler_instance.enter(
            interval_seconds, 1, advance_drone_step, (scheduler_instance, flight_id, interval_seconds)
        )
        return

    try:
        flight_data = json.loads(raw_flight_data)
        path_coords = flight_data.get("path", [])
        current_loc = flight_data.get("current_location")
    except (json.JSONDecodeError, TypeError):
        print(f"[{time.strftime('%X')}] ⚠️ Flight {flight_id}: Error parsing JSON.")
        scheduler_instance.enter(
            interval_seconds, 1, advance_drone_step, (scheduler_instance, flight_id, interval_seconds)
        )
        return

    # אם אין מסלול מוגדר באובייקט
    if not path_coords:
        print(f"[{time.strftime('%X')}] ⚠️ Flight {flight_id}: Path is empty.")
        scheduler_instance.enter(
            interval_seconds, 1, advance_drone_step, (scheduler_instance, flight_id, interval_seconds)
        )
        return

    # 2. חיפוש אינדקס המיקום הנוכחי במערך
    current_index = -1
    if current_location is not None:
        if current_loc in path_coords:
            current_index = path_coords.index(current_loc)

    # 3. אם המיקום הנוכחי לא נמצא במערך - מחכים במקום
    if current_index == -1:
        print(
            f"[{time.strftime('%X')}] ⚠️ Flight {flight_id}: Current location missing/not found in path. Holding position..."
        )
        # מתזמנים בדיקה מחדש מבלי לשנות כלום ברדיס
        scheduler_instance.enter(
            interval_seconds, 1, advance_drone_step, (scheduler_instance, flight_id, interval_seconds)
        )
        return

    # 4. קביעת האינדקס הבא
    next_index = current_index + 1

    # 5. בדיקה האם הגענו לסוף המערך
    if next_index >= len(path_coords):
        current_time_str = time.strftime("%X")
        
        # עדכון זמן הגעה בתוך אובייקט הטיסה
        flight_data["arrival_time"] = current_time_str
        r.set(flight_key, json.dumps(flight_data))
        
        print(f"[{current_time_str}] 🏁 Flight {flight_id} reached destination! Stopping.")
        return

    # 6. עדכון המיקום הבא בתוך אובייקט הטיסה ושמירה ברדיס
    next_location = path_coords[next_index]
    flight_data["current_location"] = next_location
    r.set(flight_key, json.dumps(flight_data))

    print(
        f"[{time.strftime('%X')}] 🛸 Flight {flight_id} advanced to point {next_index}: {next_location}"
    )

    # 7. תזמון הצעד הבא בעוד X שניות
    scheduler_instance.enter(
        interval_seconds, 1, advance_drone_step, (scheduler_instance, flight_id, interval_seconds)
    )


def run_single_drone_thread(flight_id: str, interval_seconds: float):
    """מייצרת מתזמן ייעודי עבור הטיסה ומפעילה אותו בתוך התהליכון שלו."""
    local_scheduler = sched.scheduler(time.time, time.sleep)

    # תזמון הצעד הראשוני
    local_scheduler.enter(
        0, 1, advance_drone_step, (local_scheduler, flight_id, interval_seconds)
    )

    # הפעלת הלולאה החוסמת של המתזמן הנוכחי
    local_scheduler.run()


def track_all_flights(interval_seconds: float):
    """סורקת את רדיס, מוצאת את כל הטיסות הפעילות ומפעילה לכל אחת תהליכון מעקב."""
    r = _redis_client()

    print("Scanning Redis for active flights...")

    flight_ids = set()
    # סריקה לפי תבנית המפתח החדשה flight:*
    for key in r.scan_iter(match="flight:*"):
        parts = key.split(":")
        if len(parts) >= 2:
            flight_ids.add(parts[1])

    if not flight_ids:
        print("No flights found in Redis.")
        return

    print(f"Found {len(flight_ids)} flights: {list(flight_ids)}. Launching threads...")

    threads = []

    for flight_id in flight_ids:
        t = threading.Thread(
            target=run_single_drone_thread,
            args=(flight_id, interval_seconds),
            daemon=True,
        )
        threads.append(t)
        t.start()
        print(f"Started tracking thread for flight: {flight_id}")

    print("All tracking threads are running. Press Ctrl+C to stop.")
    try:
        while any(t.is_alive() for t in threads):
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping all flight tracking.")


if __name__ == "__main__":
    interval = float(os.getenv("FLIGHT_INTERVAL_SECONDS", "3"))
    track_all_flights(interval_seconds=interval)