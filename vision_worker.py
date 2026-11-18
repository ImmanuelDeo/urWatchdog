"""Camera worker entry point; importing does not open hardware."""
import json

def emit(**data):
    print(json.dumps(data), flush=True)

if __name__ == "__main__":
    from camera_runtime import main
    main()

