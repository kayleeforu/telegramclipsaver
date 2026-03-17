import cv2

async def getThumbnail(filepath):
    print("\n\nTHUMBNAIL\n\n")
    framepath = filepath.replace(".mp4", "_frame.jpg")
    vid = cv2.VideoCapture(filepath)
    success, image = vid.read()
    if success:
        cv2.imwrite(framepath, image)
    vid.release()
    return framepath