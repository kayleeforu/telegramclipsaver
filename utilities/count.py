async def countClear():
    with open("resources/downloadedCount.txt", "r+") as f:
        count = f.read()
        print(f"The Downloaded Count was: {count}.\n")
        f.seek(0)
        f.truncate()
        f.write("0")

async def countAdd():
    with open("resources/downloadedCount.txt", "r+") as f:
        count = int(f.read())
        print(count)
        count += 1
        f.seek(0)
        f.truncate()
        f.write(str(count))