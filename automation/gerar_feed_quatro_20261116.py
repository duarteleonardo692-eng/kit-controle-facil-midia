from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
OUT=Path("assets")
W,H=1080,1350
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
items=[
{'slug':'01_vendas','kicker':'VENDAS & CAIXA','title':['VOCÊ SABE','QUANTO','VENDEU HOJE?'],'sub':'Transforme seus registros em clareza\npara tomar decisões no dia a dia.','chips':['Registre vendas','Acompanhe o caixa'],'accent':(62,238,160),'art':'bars'},
{'slug':'02_estoque','kicker':'CONTROLE DE ESTOQUE','title':['PRODUTO','ACABANDO?','SAIBA ANTES.'],'sub':'Acompanhe quantidades e identifique\no que precisa ser reposto.','chips':['Entradas e saídas','Ponto de atenção'],'accent':(79,205,249),'art':'boxes'},
{'slug':'03_despesas','kicker':'DESPESAS & ORGANIZAÇÃO','title':['PARA ONDE','VAI O SEU','DINHEIRO?'],'sub':'Organize os gastos do negócio\ne tenha uma visão mais clara do mês.','chips':['Controle despesas','Veja seus números'],'accent':(254,189,90),'art':'wallet'},
{'slug':'04_afiliados','kicker':'OPORTUNIDADE PARA DIVULGADORES','title':['SEJA','AFILIADO DO','KIT CONTROLE','FÁCIL'],'sub':'Compartilhe o Kit e conheça as\ncondições do programa de afiliados.','chips':['Convite de afiliados','Confira as regras'],'accent':(255,208,87),'art':'network'},
]
def ft(size,bold=False):return ImageFont.truetype(BOLD if bold else FONT,size)
def rounded(d,box,fill,r=24,outline=None,w=1):d.rounded_rectangle(box,radius=r,fill=fill,outline=outline,width=w)
def text(d,p,s,n=30,c='#ffffff',bold=False,anchor=None):d.text(p,s,font=ft(n,bold),fill=c,anchor=anchor)
def render(it):
  ac=it['accent']; im=Image.new('RGB',(W,H)); pix=im.load()
  for y in range(H):
    t=y/H;v=max(0,1-abs(y-580)/900)
    col=(int(8+7*t+3*v),int(24+10*t+6*v),int(48+14*t+6*v))
    for x in range(W):pix[x,y]=col
  d=ImageDraw.Draw(im,'RGBA')
  d.ellipse((610,-240,1370,530),fill=(*ac,20))
  d.ellipse((-220,520,320,1100),fill=(37,118,173,25))
  for i in range(7):
    x=60+i*155;d.line([(x,660),(x-40,1040)],fill=(255,255,255,9),width=2)
  rounded(d,(60,58,1020,1290),(10,28,51,230),40,(87,136,149,90),2)
  rounded(d,(88,87,418,152),(27,74,82,255),24)
  text(d,(112,103),'KIT CONTROLE FÁCIL',26,(240,255,251),True)
  text(d,(93,194),it['kicker'],27,(*ac,255),True)
  title_n=70 if it['slug']=='04_afiliados' else 77
  y=243
  for line in it['title']:
    text(d,(87,y),line,title_n,(*ac,255) if y>244 else (251,253,255,255),True)
    y+=101 if it['slug']=='04_afiliados' else 105
  sy=665 if it['slug']=='04_afiliados' else 625
  for i,line in enumerate(it['sub'].split('\n')):text(d,(93,sy+44*i),line,29,(210,230,239,255))
  art_y=775 if it['slug']!='04_afiliados' else 826
  rounded(d,(94,art_y,986,art_y+245),(17,45,72,255),30,(86,153,158,85),2)
  art=it['art']
  if art=='bars':
    for i,bh in enumerate([54,88,122,169,195]):
      x=158+i*141
      rounded(d,(x,art_y+214-bh,x+87,art_y+214),(*ac,135+20*i),13)
    d.line((147,art_y+216,910,art_y+216),fill=(205,239,243,140),width=3)
    d.line([(196,art_y+123),(325,art_y+140),(478,art_y+91),(642,art_y+70),(835,art_y+23)],fill=(238,255,250,205),width=9,joint='curve')
    d.polygon([(834,art_y+22),(808,art_y+29),(825,art_y+55)],fill=(238,255,250,255))
  elif art=='boxes':
    for i,(x,bh) in enumerate([(160,126),(420,185),(698,156)]):
      top=art_y+216-bh
      rounded(d,(x,top,x+185,art_y+215),(24,83,119,240),17,(102,214,245,190),4)
      d.line((x,top+45,x+185,top+45),fill=(102,214,245,110),width=4)
      d.line((x+92,top,x+92,art_y+215),fill=(102,214,245,100),width=4)
      text(d,(x+22,top+54),['08','03','12'][i],55,(*ac,255),True)
  elif art=='wallet':
    rounded(d,(190,art_y+45,780,art_y+202),(33,102,129,240),24,(251,209,125,200),3)
    rounded(d,(609,art_y+78,876,art_y+170),(6,39,63,255),22,(253,201,119,210),3)
    d.ellipse((707,art_y+102,752,art_y+147),fill=(*ac,255))
    for x,y,r in [(325,art_y+116,49),(410,art_y+116,36),(491,art_y+116,28)]:d.ellipse((x-r,y-r,x+r,y+r),outline=(*ac,170),width=5)
  else:
    pos=[(290,art_y+116),(545,art_y+70),(790,art_y+131)]
    d.line([pos[0],pos[1],pos[2]],fill=(*ac,220),width=10,joint='curve')
    d.line([pos[0],pos[2]],fill=(*ac,100),width=7)
    for x,y in pos:
      d.ellipse((x-57,y-57,x+57,y+57),fill=(26,86,111,255),outline=(*ac,245),width=7)
      d.ellipse((x-20,y-31,x+20,y+9),fill=(245,250,244,255))
      rounded(d,(x-39,y+16,x+39,y+39),(245,250,244,255),16)
  for i,chip in enumerate(it['chips']):
    x=96+i*449; y=1076
    rounded(d,(x,y,x+430,y+63),(23,71,77,255),18,(62,159,145,70))
    d.ellipse((x+19,y+20,x+41,y+42),fill=(*ac,255))
    text(d,(x+57,y+15),chip,25,(238,252,249,255),True)
  rounded(d,(94,1160,985,1228),(*ac,255),24)
  cta='VER O CONVITE DE AFILIADOS' if it['slug']=='04_afiliados' else 'CONHEÇA O SITE E A LOJA'
  text(d,(540,1192),cta,26,(4,29,44,255),True,'mm')
  text(d,(540,1258),'kit-controle-facil-site.pages.dev',22,(204,230,238,255),False,'mm')
  path=OUT/f"kit-post-{it['slug']}-20261116.jpg"
  im.save(path,'JPEG',quality=90,optimize=True,subsampling=0)
  print(str(path),path.stat().st_size)
if __name__=="__main__":
  OUT.mkdir(parents=True,exist_ok=True)
  for item in items:render(item)
