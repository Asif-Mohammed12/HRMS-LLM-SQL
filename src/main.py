import argparse
from .sql_generator import query_hrms

def main():
    parser = argparse.ArgumentParser(description="HRMS LLM‑SQL demo")
    parser.add_argument("prompt", help="Natural‑language request, e.g. 'list employees hired last month'")
    args = parser.parse_args()
    try:
        rows = query_hrms(args.prompt)
        for row in rows:
            print(row)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
