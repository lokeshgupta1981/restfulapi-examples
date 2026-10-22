from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont
from bs4 import BeautifulSoup
import json
root=Path('C:\\Users\\lokes\\OneDrive\\Documents\\ChatGPT\\restfulapi\\ai-drafts-review')
items=json.loads((root/'manifest.json').read_text())
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
for group in range(4):
    canvas=Image.new('RGB',(1920,1800),'white'); draw=ImageDraw.Draw(canvas)
    for row,item in enumerate(items[group*4:group*4+4]):
        draw.text((16,row*450+6),item['title'],fill='black',font=font)
        soup=BeautifulSoup((root/'originals'/(item['id']+'.wp.html')).read_text(encoding='utf-8'),'html.parser')
        for col,tag in enumerate(soup.select('img')):
            im=Image.open(root/'images'/tag['src'].split('/')[-1]).convert('RGB')
            im.thumbnail((620,392))
            canvas.paste(im,(col*640+(640-im.width)//2,row*450+42+(392-im.height)//2))
    canvas.save(root/f'asset-sheet-{group+1}.jpg',quality=94)
