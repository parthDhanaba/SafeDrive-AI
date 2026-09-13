"""
SafeDrive-AI Driver and Vehicle Setup Utility
Creates and registers driver profiles and vehicle information in SQLite.
Supports interactive terminal prompts, command line flags, and quick defaults.
"""
import sys
import argparse
from database import initialize_database, add_driver, add_vehicle, get_default_profile, get_driver, get_vehicle
from logger import logger


def run_setup(
    driver_name: str,
    driver_phone: str,
    emergency_name: str,
    emergency_phone: str,
    vehicle_number: str,
    vehicle_type: str,
    owner_name: str
):
    initialize_database()

    driver_id = add_driver(
        name=driver_name,
        phone=driver_phone,
        emergency_contact_name=emergency_name,
        emergency_contact_phone=emergency_phone
    )

    vehicle_id = add_vehicle(
        vehicle_number=vehicle_number,
        vehicle_type=vehicle_type,
        owner_name=owner_name
    )

    print("\n" + "=" * 50)
    print("SafeDrive-AI Registration Successful")
    print("=" * 50)
    print(f"Driver ID        : {driver_id} ({driver_name})")
    print(f"Driver Phone     : {driver_phone}")
    print(f"Emergency Contact: {emergency_name} ({emergency_phone})")
    print(f"Vehicle ID       : {vehicle_id} ({vehicle_number} - {vehicle_type})")
    print(f"Vehicle Owner    : {owner_name}")
    print("=" * 50 + "\n")
    return driver_id, vehicle_id


def main():
    parser = argparse.ArgumentParser(description="SafeDrive-AI Driver & Vehicle Registration")
    parser.add_argument("--default", action="store_true", help="Set up default profile automatically")
    parser.add_argument("--name", type=str, default="", help="Driver full name")
    parser.add_argument("--phone", type=str, default="", help="Driver phone number")
    parser.add_argument("--contact-name", type=str, default="", help="Emergency contact name")
    parser.add_argument("--contact-phone", type=str, default="", help="Emergency contact phone number")
    parser.add_argument("--vehicle-num", type=str, default="", help="Vehicle registration plate number")
    parser.add_argument("--vehicle-type", type=str, default="Car", help="Vehicle type (Car, Truck, Van, etc.)")
    parser.add_argument("--owner", type=str, default="", help="Vehicle owner name")

    args = parser.parse_args()

    if args.default:
        run_setup(
            driver_name="Default Driver",
            driver_phone="+15550001234",
            emergency_name="Emergency Support",
            emergency_phone="+15559998888",
            vehicle_number="SAFE-001",
            vehicle_type="SUV",
            owner_name="Default Fleet"
        )
        return

    if args.name and args.vehicle_num:
        run_setup(
            driver_name=args.name,
            driver_phone=args.phone,
            emergency_name=args.contact_name or "Emergency Contact",
            emergency_phone=args.contact_phone or args.phone,
            vehicle_number=args.vehicle_num,
            vehicle_type=args.vehicle_type,
            owner_name=args.owner or args.name
        )
        return

    # Interactive flow
    print("=" * 50)
    print("SafeDrive-AI Driver & Vehicle Setup")
    print("=" * 50)

    try:
        name = input("Driver name [Default Driver]: ").strip() or "Default Driver"
        phone = input("Driver phone [+15550001234]: ").strip() or "+15550001234"
        emergency_name = input("Emergency contact name [Emergency Contact]: ").strip() or "Emergency Contact"
        emergency_phone = input("Emergency contact phone [+15559998888]: ").strip() or "+15559998888"

        print("-" * 50)
        vehicle_num = input("Vehicle number [MH-08-AB-1234]: ").strip() or "MH-08-AB-1234"
        vehicle_type = input("Vehicle type (Car/Truck/Bus) [Car]: ").strip() or "Car"
        owner = input(f"Vehicle owner [{name}]: ").strip() or name

        run_setup(name, phone, emergency_name, emergency_phone, vehicle_num, vehicle_type, owner)

    except (KeyboardInterrupt, EOFError):
        print("\nSetup cancelled.")
        sys.exit(0)


if __name__ == "__main__":
    main()