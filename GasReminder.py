import asyncio
import cv2
import easyocr
from datetime import datetime
import discord
from discord.ext import commands
import pyperclip
import matplotlib.pyplot as plt
from matplotlib import font_manager
from picamera2 import Picamera2

FILE='[YourFileLocation]'
NANUM = font_manager.FontProperties(fname='/usr/share/fonts/truetype/nanum/NanumGothic.ttf')
gas=(939.2365+850)*1.1
whattime=''
date=[]
usage=[]

# 디스코드 보내기
TOKEN=[YourDiscordBotToken]
CHANNEL_ID=[YourDiscordChannelID]

bot=discord.Bot()

async def camera():
    global whattime

    # 사진 촬영
    cam = Picamera2()
    cam.start()
    whattime=datetime.now().strftime('%Y%m%d%H%M%S')
    image=cam.capture_array()
    cv2.imwrite(FILE+"gas" + whattime + ".jpg", image)
    cam.stop()

    # EasyOCR 작동
    reader=easyocr.Reader(['en'])
    result=reader.readtext(FILE+"gas" + whattime + ".jpg", detail=0)

    # 결과값 정리
    result=str(result)
    num=''
    for n in range(0, len(result), 1):
        for m in range(0, 10, 1):
            if(result[n]==str(m)):
                num+=result[n]

    # 메모장 로그
    with open(FILE+"log.txt", 'a') as file:
        file.write(whattime + "\n")
        file.write(num + "\n")

    if(num == ""):
        num='0'

    return num


async def load_log():
    global date, usage
    exnum='0'

    # 전 로그 불러오기
    with open(FILE+"log.txt", "r") as file:
        log=file.readlines()
        if(len(log)>3):
            exnum=log[len(log) - 3]
        exnum=exnum.replace('\n', '')
        print(exnum)

    #for n in range(0,len(date),1):
    #    date[n]=date[n][:8]

    date=[]
    usage=[]

    for n in range(0, len(log), 2):
        date.append(log[n][:8])
        if(log[n + 1] == '\n'):
            usage.append(0)
        else:
            usage.append(int(log[n + 1]))

    # 공백일경우
    if(exnum == ""):
        exnum='0'

    return exnum

async def check_time(bot: commands.Bot):
    while True:
        print(datetime.now().strftime('%d%H%M%S'))
        if(datetime.now().strftime('%d%H')=="0113"):
            task1=asyncio.create_task(camera())
            await task1
            
            task2=asyncio.create_task(load_log())
            await task2

            num = task1.result()
            exnum = task2.result()

            channel=bot.get_channel(CHANNEL_ID)
            embed=discord.Embed(title="오늘은 가스 검침날입니다!",description="잊지 말고 메세지를 보내시기 바랍니다.",color=0x00aaaa)
            embed.add_field(name="숫자인식 결과", value=num, inline=False)
            embed.add_field(name="전월대비 사용량.",value=f"{int(num)-int(exnum):+d} ({(int(num)-int(exnum))*gas:+.0f}원)",inline=False)
            embed.set_footer(text="사진의 숫자와 인식 결과가 다를 수 있으니 다시 한번 확인하시기 바랍니다.")
            
            file=discord.File(FILE+"gas" + whattime + ".jpg", filename="gas.jpg")
            embed.set_image(url="attachment://gas.jpg")
            await channel.send(file=file, embed=embed, view=Button1())
        await asyncio.sleep(3600)


@bot.event
async def on_ready():
    print('Logged on as', bot.user)
    bot.loop.create_task(check_time(bot))

class Button1(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label='사용량 비교하기', style=discord.ButtonStyle.blurple)
    async def button1(self, button: discord.ui.Button, interaction: discord.Interaction):
        # 평균 구하기
        avg=0
        for n in usage[-12::1]:
            avg+=int(n)
        avg/=12

        # 그래프 저장
        plt.bar(date[-12::1], usage[-12::1])
        plt.title('월별 가스 사용량 그래프', fontproperties=NANUM)
        plt.ylabel('가스 사용량 (m³)', fontproperties=NANUM)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(FILE + "graph" + whattime + ".jpg")
        plt.close()
        
        num=usage[-1]
        exnum=0
        if len(usage)>1:
            exnum=usage[-2]
        
        channel=interaction.channel
        embed=discord.Embed(title="사용량 비교하기", description="잊지 말고 메세지를 보내시기 바랍니다.", color=0x00aaaa)
        embed.add_field(name="평균 사용량 (최근 12개월)", value=f"{avg:.1f}"+f" ({avg*gas:.0f}원)", inline=False)
        embed.add_field(name="전월 사용량", value=str(int(exnum))+f" ({(int(num)-int(exnum)):+d})", inline=False)
        embed.add_field(name="예상 청구 금액", value=f"{int(num)*gas:.0f}원", inline=False)

        file=discord.File(FILE+"graph" + whattime + ".jpg", filename="graph.jpg")
        embed.set_image(url="attachment://graph.jpg")
        await interaction.response.send_message(file=file, embed=embed)

    @discord.ui.button(label='사용량이 이상해요!', style=discord.ButtonStyle.danger)
    async def button3(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message("'/직접입력'을 통해 값을 직접 입력해주세요.")

# 명령어
@bot.command()
async def 직접입력(ctx,value,description="사용량과 인식된 숫자가 일치하지 않을 때 수정할수 있습니다. "):
    if(len(value)>6 or len(value)==0 or not value.isdigit()):
        await ctx.respond(f'{"정상적인 값을 입력해주세요"}')
    else:
        await ctx.respond(f'{whattime[:8]+"의 값을 "+value+"로 변경하였습니다."}')
        usage[-1]=int(value)

        log=[]
        with open(FILE+"log.txt", "r") as file:
            log=file.readlines()
            log[-1]=value+"\n"
        with open(FILE+"log.txt", "w") as file:
            file.writelines(log)

@bot.command()
async def 수동측정(ctx,description="테스트용"):
    trigger=1

bot.run(TOKEN)
