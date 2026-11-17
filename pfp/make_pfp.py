import sys, math, os
from PIL import Image, ImageDraw, ImageFont
OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
os.makedirs(OUT, exist_ok=True)
K = 2  # supersample
N = 1080
CREAM=(246,239,220); RED=(229,72,61); BLUE=(58,111,216); INK=(27,35,64)
MINT=(127,209,176); YEL=(244,197,66); WHITE=(255,255,255); DRED=(176,44,38); DBLUE=(36,76,166)
def new(bg):
    im = Image.new("RGB",(N*K,N*K),bg); return im, ImageDraw.Draw(im)
def s(v): return int(round(v*K))
def circ(d,cx,cy,r,fill,ow=0,oc=INK):
    d.ellipse([s(cx-r-ow),s(cy-r-ow),s(cx+r+ow),s(cy+r+ow)],fill=oc if ow else fill)
    if ow: d.ellipse([s(cx-r),s(cy-r),s(cx+r),s(cy+r)],fill=fill)
def line(d,pts,w,c=INK):
    P=[(s(x),s(y)) for x,y in pts]; d.line(P,fill=c,width=s(w),joint="curve")
    for x,y in P: d.ellipse([x-s(w)/2,y-s(w)/2,x+s(w)/2,y+s(w)/2],fill=c)
def ball(d,cx,cy,r,col,dark,face="det",look=0,ow=None):
    ow = ow if ow is not None else r*0.07
    circ(d,cx,cy,r,col,ow)
    d.pieslice([s(cx-r),s(cy-r),s(cx+r),s(cy+r)],35,150,fill=dark)
    circ(d,cx,cy,r*0.86,col)
    d.pieslice([s(cx-r),s(cy-r),s(cx+r),s(cy+r)],40,140,fill=dark)
    d.ellipse([s(cx-r*0.9),s(cy-r*0.98),s(cx+r*0.9),s(cy+r*0.8)],fill=col)
    d.arc([s(cx-r),s(cy-r),s(cx+r),s(cy+r)],0,360,fill=INK,width=s(ow))
    if face: eyes(d,cx,cy,r,face,look)
def eyes(d,cx,cy,r,mood,look=0):
    ex=r*0.34; ey=cy-r*0.08; er=r*0.24
    for sx in (-1,1):
        x=cx+sx*ex
        circ(d,x,ey,er,WHITE,r*0.045)
        circ(d,x+look*er*0.4,ey+er*0.08,er*0.5,INK)
        circ(d,x+look*er*0.4+er*0.15,ey-er*0.1,er*0.14,WHITE)
        if mood=="det": line(d,[(x+sx*er*1.1,ey-er*1.25),(x-sx*er*0.9,ey-er*0.95)],r*0.08)
        if mood=="smirk": line(d,[(x-er*0.9,ey-er*1.3),(x+er*0.9,ey-er*1.3+(-0.2*er if sx>0 else 0.15*er))],r*0.07)
    if mood=="det": line(d,[(cx-r*0.25,cy+r*0.45),(cx+r*0.25,cy+r*0.45)],r*0.075)
    elif mood=="smirk":
        d.arc([s(cx-r*0.1),s(cy+r*0.12),s(cx+r*0.45),s(cy+r*0.5)],10,150,fill=INK,width=s(r*0.07))
    elif mood=="grit":
        d.rectangle([s(cx-r*0.28),s(cy+r*0.36),s(cx+r*0.28),s(cy+r*0.56)],fill=WHITE,outline=INK,width=s(r*0.05))
        for i in range(-1,2): line(d,[(cx+i*r*0.14,cy+r*0.36),(cx+i*r*0.14,cy+r*0.56)],r*0.035)
    elif mood=="happy":
        d.arc([s(cx-r*0.3),s(cy+r*0.1),s(cx+r*0.3),s(cy+r*0.5)],15,165,fill=INK,width=s(r*0.07))
    elif mood=="hurt":
        line(d,[(cx-r*0.22,cy+r*0.5),(cx-r*0.07,cy+r*0.42),(cx+r*0.07,cy+r*0.5),(cx+r*0.22,cy+r*0.42)],r*0.06)
def bolt(d,cx,cy,h,col=YEL):
    w=h*0.45
    P=[(cx+w*0.15,cy-h/2),(cx-w*0.55,cy+h*0.05),(cx-w*0.05,cy+h*0.05),(cx-w*0.25,cy+h/2),(cx+w*0.6,cy-h*0.1),(cx+w*0.08,cy-h*0.1)]
    d.polygon([(s(x),s(y)) for x,y in P],fill=col,outline=INK,width=s(h*0.04))
def hpbar(d,x,y,w,h,frac,col):
    d.rounded_rectangle([s(x),s(y),s(x+w),s(y+h)],radius=s(h/2),fill=WHITE,outline=INK,width=s(h*0.12))
    p=h*0.16
    d.rounded_rectangle([s(x+p),s(y+p),s(x+p+(w-2*p)*frac),s(y+h-p)],radius=s((h-2*p)/2),fill=col)
def crown(d,cx,cy,w):
    h=w*0.7
    P=[(cx-w/2,cy+h/2),(cx-w/2,cy-h/2),(cx-w/4,cy),(cx,cy-h/2),(cx+w/4,cy),(cx+w/2,cy-h/2),(cx+w/2,cy+h/2)]
    d.polygon([(s(x),s(y)) for x,y in P],fill=YEL,outline=INK,width=s(w*0.04))
    for x in (cx-w/2,cx,cx+w/2): circ(d,x,cy-h/2,w*0.05,RED,w*0.02)
def txt(d,cx,cy,t,size,col,ow):
    f=None
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf","C:/Windows/Fonts/arialbd.ttf","/System/Library/Fonts/Helvetica.ttc"]:
        if os.path.exists(p): f=ImageFont.truetype(p,s(size)); break
    d.text((s(cx),s(cy)),t,font=f,fill=col,anchor="mm",stroke_width=s(ow),stroke_fill=INK)

def p1():
    im,d=new(CREAM)
    ball(d,390,570,250,RED,DRED,"grit",1); ball(d,700,510,250,BLUE,DBLUE,"grit",-1)
    for a in (200,235,270):
        r=math.radians(a); line(d,[(545+130*math.cos(r),540+130*math.sin(r)),(545+200*math.cos(r),540+200*math.sin(r))],18)
    return im
def p2():
    im,d=new(BLUE); ball(d,540,560,360,RED,DRED,"det"); return im
def p3():
    im,d=new(CREAM)
    ball(d,290,600,230,RED,DRED,"grit",1); ball(d,790,600,230,BLUE,DBLUE,"grit",-1); bolt(d,540,540,560); return im
def p4():
    im,d=new(MINT); circ(d,540,1010,230,(94,180,150))
    ball(d,540,640,300,RED,DRED,"happy"); crown(d,540,300,300); return im
def p5():
    im,d=new(CREAM)
    ball(d,300,430,200,RED,DRED,"grit",1); ball(d,780,430,200,BLUE,DBLUE,"grit",-1)
    txt(d,540,790,"VS",340,YEL,16); return im
def p6():
    im,d=new(CREAM); ball(d,500,640,310,RED,DRED,"hurt")
    line(d,[(430,360),(480,440),(440,490),(520,580)],18,INK)
    txt(d,720,250,"-25",170,BLUE,12); return im
def p7():
    im,d=new(CREAM); ball(d,540,500,330,RED,DRED,"smirk")
    y0=880; sq=60
    for r in range(2):
        for i in range(18):
            if (i+r)%2==0: d.rectangle([s(i*sq),s(y0+r*sq),s((i+1)*sq),s(y0+(r+1)*sq)],fill=INK)
    d.rectangle([s(0),s(y0),s(N),s(y0+2*sq)],outline=INK,width=s(8)); return im
def p8():
    im,d=new(MINT)
    for y,(f,c) in zip([820,700,580],((0.35,RED),(0.7,BLUE),(1.0,YEL))): hpbar(d,190,y,700,100,f,c)
    ball(d,540,350,200,RED,DRED,"happy"); return im
def p9():
    im,d=new(CREAM)
    for sx in (-1,1):
        d.arc([s(540+sx*270-110),s(400),s(540+sx*270+110),s(600)],90 if sx<0 else -90,270 if sx<0 else 90,fill=INK,width=s(18))
    d.rectangle([s(495),s(640),s(585),s(780)],fill=YEL,outline=INK,width=s(18))
    d.rounded_rectangle([s(330),s(780),s(750),s(880)],radius=s(20),fill=BLUE,outline=INK,width=s(18))
    ball(d,540,360,170,RED,DRED,"happy")
    d.polygon([(s(250),s(400)),(s(830),s(400)),(s(770),s(680)),(s(310),s(680))],fill=YEL,outline=INK,width=s(18))
    d.polygon([(s(330),s(430)),(s(380),s(430)),(s(410),s(640)),(s(360),s(640))],fill=CREAM)
    return im
def p10():
    im,d=new(CREAM); circ(d,540,540,520,YEL); ball(d,540,560,330,RED,DRED,"smirk",1); return im
names=["01_collision","02_determined_on_blue","03_faceoff_bolt","04_crown_bounce","05_vs","06_cracked_damage","07_finish_strip","08_hp_stack","09_trophy","10_smirk_on_yellow"]
fns=[p1,p2,p3,p4,p5,p6,p7,p8,p9,p10]
ims=[]
for n,f in zip(names,fns):
    im=f().resize((N,N),Image.LANCZOS); im.save(f"{OUT}/pfp_{n}.png"); ims.append(im)
T=360; pad=40; bg=(222,222,230)
sheet=Image.new("RGB",(5*T+6*pad,2*T+3*pad),bg)
m=Image.new("L",(T*4,T*4),0); ImageDraw.Draw(m).ellipse([0,0,T*4-1,T*4-1],fill=255); m=m.resize((T,T),Image.LANCZOS)
for i,im in enumerate(ims):
    t=im.resize((T,T),Image.LANCZOS); x=pad+(i%5)*(T+pad); y=pad+(i//5)*(T+pad); sheet.paste(t,(x,y),m)
sheet.save(f"{OUT}/pfp_contact_sheet.jpg",quality=92)
