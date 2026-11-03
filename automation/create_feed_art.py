#!/usr/bin/env python3
"""Gera somente uma arte inédita de feed em PNG, sem inventar telas do produto."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W,H=1080,1350
img=Image.new("RGB",(W,H))
p=img.load()
for y in range(H):
    t=y/H
    rgb=(int(12+7*t),int(29+14*t),int(45+17*t))
    for x in range(W): p[x,y]=rgb

d=ImageDraw.Draw(img)
def font(n,bold=False):
    suffix="DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/"+suffix,n)

teal=(65,218,168)
white=(241,248,251)
grey=(172,194,202)
d.rounded_rectangle((60,60,1020,1290),radius=52,outline=(62,106,112),width=3)
d.rounded_rectangle((104,112,455,168),radius=22,fill=(27,87,80))
d.text((131,121),"KIT CONTROLE FÁCIL",font=font(25,True),fill=white)
d.text((108,224),"Seu negócio",font=font(73,True),fill=white)
d.text((108,308),"mais organizado",font=font(73,True),fill=teal)
d.text((108,420),"4 controles que fazem a diferença",font=font(31),fill=grey)
items=[
    ("01","Vendas","Registre o que entrou no dia."),
    ("02","Despesas","Acompanhe os gastos do negócio."),
    ("03","Estoque","Observe os produtos disponíveis."),
    ("04","Caixa","Confira entradas e saídas."),
]
y=515
for num,title,desc in items:
    d.rounded_rectangle((107,y,973,y+137),radius=23,fill=(25,53,66),outline=(52,101,105),width=2)
    d.rounded_rectangle((133,y+30,213,y+105),radius=19,fill=(33,107,93))
    d.text((150,y+49),num,font=font(30,True),fill=white)
    d.text((249,y+20),title,font=font(38,True),fill=white)
    d.text((250,y+78),desc,font=font(26),fill=grey)
    y+=158

d.line((111,1175,968,1175),fill=(69,114,118),width=2)
d.text((110,1200),"Planilha Excel para pequenos negócios",font=font(26),fill=white)
d.text((110,1241),"@kitcontrolefacil.br",font=font(22),fill=teal)
path=Path("assets/post-checklist-controle-financeiro.png")
path.parent.mkdir(exist_ok=True)
img.save(path,optimize=True)
print("Arte gerada:",path,"bytes",path.stat().st_size)
