import cv2

def getThumbnail(filepath):
    framepath = filepath.replace(".mp4", "_frame.jpg")
    vid = cv2.VideoCapture("downloadedVideos/video222.mp4")
    success, image = vid.read()
    if success:
        cv2.imwrite(framepath, image)
    vid.release()
    return framepath