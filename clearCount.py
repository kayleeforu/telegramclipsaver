with open("downloadedCount.txt", "r+") as f:
    count = f.read()
    print(f"The Downloaded Count was: {count}.\n")
    f.seek(0)
    f.truncate()
    f.write("0")