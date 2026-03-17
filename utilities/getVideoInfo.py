import cv2

async def getVideoInfo(filepath):

    framepath = filepath.replace(".mp4", "_frame.jpg")
    vid = cv2.VideoCapture(filepath)
    for i in range(20):
        success, image = vid.read()
    if success:
        cv2.imwrite(framepath, image)
    height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))
    width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))
    vid.release()

    return framepath, height, width