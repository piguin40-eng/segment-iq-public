"""Render the application's own SIQ monogram as a Windows shortcut icon."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root=Path(__file__).resolve().parents[1]
assets=root/'assets'
assets.mkdir(exist_ok=True)
image=Image.new('RGBA',(256,256))
draw=ImageDraw.Draw(image)
draw.rounded_rectangle((5,5,251,251),radius=66,fill='#e52d4c')
font=Path('C:/Windows/Fonts/segoeuib.ttf')
draw.text((37,1),'S',font=ImageFont.truetype(str(font),197),fill='white')
draw.text((143,154),'IQ',font=ImageFont.truetype(str(font),60),fill='white')
image.save(assets/'segment-iq.ico',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
