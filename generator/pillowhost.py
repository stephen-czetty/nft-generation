import numpy
from stegpy.lsb import HostElement

class PillowHostElement(HostElement):
    def __init__(self, image):
        if image.mode != 'RGB':
            image = image.convert('RGB')
        self.data = numpy.array(image)
        self.format = 'png'
