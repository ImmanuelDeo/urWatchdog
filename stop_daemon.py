from glass_panel import Backend

def stop():
    Backend().stop()
    print("urWatchdog stop requested; camera and countdown will release safely.")

if __name__ == "__main__": stop()
