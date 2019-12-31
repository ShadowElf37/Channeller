def in_box(x, y, x1, y1, x2, y2):
    if x2 > x > x1 and y2 > y > y1:
        return True
    return False

class ChannelView:
    def __init__(self):
        ...