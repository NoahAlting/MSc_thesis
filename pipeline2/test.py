import platform

if platform.system() == "Windows":
    import winsound
    for _ in range(3):  # three short beeps
        winsound.Beep(1000, 200)  # frequency (Hz), duration (ms)
