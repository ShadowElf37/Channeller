from PIL import Image
from PIL.ImageColor import getrgb

def open_image(path):
  newImage = Image.open(path)
  return newImage

# Save Image
def save_image(image, path):
  image.save(path, 'png')


# Create a new image with the given size
def create_image(i, j):
    return Image.new("RGBA", (i, j), "none")

def get_pixel(image, i, j):
    # Inside image bounds?
    width, height = image.size
    if i > width or j > height:
      return None

    # Get Pixel
    pixel = image.getpixel((i, j))
    return pixel

def grade(image, color='#FFF'):
    rgb = getrgb(color)

    # Get size
    width, height = image.size

    # Create new Image and a Pixel Map
    new = create_image(width, height)
    pixels = new.load()

    # Transform to grayscale
    for i in range(width):
        for j in range(height):
            # Get Pixel
            pixel = get_pixel(image, i, j)

            # Get R, G, B values (This are int from 0 to 255)
            red =   pixel[0]
            green = pixel[1]
            blue =  pixel[2]

            # Transform to grayscale
            print(rgb)
            color = (red * 0.299 * rgb[0]/255) + (green * 0.587 * rgb[1]/255) + (blue * 0.114 * rgb[2]/255)

            # Set Pixel in new image
            pixels[i, j] = (int(color), int(color), int(color), pixel[3])

            # Return new image
        return new

save_image(grade(open_image('pause.png'), '#F00'), 'test.png')