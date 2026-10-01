import csv
import os

def generate_csv(filepath: str, count: int = 1000):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Company Name", "Contact Person", "Email Address", "Phone Number", "City", "Industry", "Opportunity Title"])
        for i in range(1, count + 1):
            writer.writerow([
                f"Enterprise Corp {i}",
                f"Executive {i}",
                f"executive{i}@enterprisecorp{i}.in",
                f"+91 98200 {i:05d}",
                "Mumbai" if i % 2 == 0 else "Bengaluru",
                "Manufacturing" if i % 3 == 0 else "Technology",
                f"High Voltage Equipment Supply #{i}"
            ])
    print(f"Generated {count}-row test CSV at {filepath}")

if __name__ == "__main__":
    generate_csv("storage_uploads/test_1000_leads.csv", 1000)
