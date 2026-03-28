import cv2
import os
import time
import logging 

async def getVideoInfo(filepath):
    framepath = filepath.replace(".mp4", "_frame.jpg")
    
    prev_size = -1
    stable_count = 0
    while stable_count < 3:
        current_size = os.path.getsize(filepath)
        if current_size == prev_size:
            stable_count += 1
        else:
            stable_count = 0
            prev_size = current_size
        time.sleep(0.5)
    
    vid = cv2.VideoCapture(filepath)
    
    if not vid.isOpened():
        print(f"[getVideoInfo] Cannot open video: {filepath}")
        return framepath, 0, 0
    
    total_frames = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
    
    target_frame = int(total_frames * 0.1)
    target_frame = max(1, min(target_frame, total_frames - 1))
    vid.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
    
    success, image = vid.read()
    
    if not success:
        vid.set(cv2.CAP_PROP_POS_FRAMES, 0)
        success, image = vid.read()
    
    if success:
        cv2.imwrite(framepath, image)
        logging.info(f"[getVideoInfo] Frame path created: {framepath}")
    else:
        logging.info(f"[getVideoInfo] Could not read any frame from: {filepath}")
    
    height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))
    width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))
    vid.release()
    
    return framepath, height, width