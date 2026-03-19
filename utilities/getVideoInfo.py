import cv2
import os
import time

async def getVideoInfo(filepath):
    framepath = filepath.replace(".mp4", "_frame.jpg")
    
    for _ in range(10):
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            break
        time.sleep(0.5)
    
    vid = cv2.VideoCapture(filepath)
    
    if not vid.isOpened():
        print(f"[getVideoInfo] Cannot open video: {filepath}")
        return framepath, 0, 0
    
    total_frames = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
    
    target_frame = min(60, max(0, total_frames - 1))
    vid.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
    
    success, image = vid.read()
    
    if not success:
        vid.set(cv2.CAP_PROP_POS_FRAMES, 0)
        success, image = vid.read()
    
    if success:
        cv2.imwrite(framepath, image)
    else:
        print(f"[getVideoInfo] Could not read any frame from: {filepath}")
    
    height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))
    width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))
    vid.release()
    
    return framepath, height, width