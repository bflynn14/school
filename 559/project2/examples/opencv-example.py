import sys
from lib.CVtypes import cv
 
def detect(image):
    image_size = cv.GetSize(image)
 
    # create grayscale version
    grayscale = cv.CreateImage(image_size, 8, 1)
    cv.CvtColor(image, grayscale, cv.BGR2GRAY)
 
    # create storage
    storage = cv.CreateMemStorage(0)
    cv.ClearMemStorage(storage)
 
    # equalize histogram
    cv.EqualizeHist(grayscale, grayscale)
 
    # detect objects
    cascade = cv.LoadHaarClassifierCascade('images/haarcascade_frontalface_alt.xml', cv.Size(1,1))
    faces = cv.HaarDetectObjects(grayscale, cascade, storage, 1.2, 2, cv.HAAR_DO_CANNY_PRUNING, cv.Size(50, 50))
 
    if faces:
        print 'face detected!'
        for i in faces:
            cv.Rectangle(image, cv.Point( int(i.x), int(i.y)),
                         cv.Point(int(i.x + i.width), int(i.y + i.height)),
                         cv.RGB(0, 255, 0), 3, 8, 0)
 
if __name__ == "__main__":
    print "OpenCV version: %s (%d, %d, %d)" % (cv.VERSION,
                                               cv.MAJOR_VERSION,
                                               cv.MINOR_VERSION,
                                               cv.SUBMINOR_VERSION)
 
    # create windows
    cv.NamedWindow('Camera', cv.WINDOW_AUTOSIZE)
 
    # face detection
    #frame = cv.LoadImage("images/example.jpg")
    frame = cv.LoadImage("input.jpg")
    detect(frame)
    cv.ShowImage('Camera', frame)
    cv.WaitKey(100000000)
    