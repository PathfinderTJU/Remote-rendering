import datetime
import sys
import os
import pygame
import base64
from io import BytesIO
from OpenGL.GL import *
from PIL import Image
from pygame import *
import time as tk
import light
from objloader import OBJ


def screenshot_and_send():
    # 截屏
    buffer = glReadPixels(0, 0, 600, 600, GL_RGBA, GL_UNSIGNED_BYTE)
    image = Image.frombuffer(mode="RGBA", size=(600, 600), data=buffer)
    image = image.transpose(Image.FLIP_TOP_BOTTOM)

    # 双线性差值压缩
    image = image.resize((600, 600), Image.BICUBIC)

    # 转码
    new_buffer = BytesIO()
    image.save(new_buffer, format="PNG")
    image_str = base64.b64encode(new_buffer.getvalue())
    with open("./base64.txt", "w") as f:
        f.write(str(image_str, "utf-8"))

    # 保存图片
    d = datetime.datetime.now()
    timestamp = str(tk.mktime(d.timetuple()))
    image.save("./image/" + timestamp + ".png")


def render(filename, filed):
    # filename = "taibaoding.obj"
    # filed = "./data/太保鼎10w/"

    # filename = "taibaoding.obj"
    # filed = "./data/太保鼎20w/"

    # filename = "taibaoding.obj"
    # filed = "./data/太保鼎1000w/"

    # filename = "ChunPingXiuFu.obj"
    # filed = "./data/瓶子10w/"

    # filename = "ChunPingXiuFu.obj"
    # filed = "./data/瓶子20w/"

    # filename = "ChunPingXiuFu.obj"
    # filed = "./data/瓶子150w/"

    # filename = "BaXianHuLu_10.obj"
    # filed = "./data/葫芦20w/"

    # filename = "yyt.obj"
    # filed = "./data/鱼砚台25w/"

    # filename = "yyt-remesh.obj"
    # filed = "./data/鱼砚台30w/"

    # filename = "up.obj"
    # filed = "./data/鱼砚台盒子上13w/"

    # filename = "down.obj"
    # filed = "./data/鱼砚台盒子下13w/"

    # filename = "shuangyu.obj"
    # filed = "./data/双鱼18w/"

    obj = OBJ(filed, filename)
    obj.create_bbox()

    # 初始化pygame引擎


    # 设置一个pygame展示窗口，参数为宽度、设置为opengl模式和双缓冲区
    viewport = (600, 600)
    srf = pygame.display.set_mode(viewport, OPENGL | DOUBLEBUF)
    # pygame.display.iconify()

    # 开启光照
    light.setup_lighting()
    glLightfv(GL_LIGHT0, GL_POSITION, (0, 0, 200, 0.0))

    # 开启更新深度缓冲区，深度值发生变化才更新缓冲区，使效果更加真实
    glEnable(GL_DEPTH_TEST)

    # 颜色平滑过渡
    glShadeModel(GL_SMOOTH)

    # 绘制模型
    obj.create_gl_list()

    # 定义交互
    # 获取时钟
    clock = pygame.time.Clock()

    # 定义操作opengl模型的矩阵类型为投影矩阵，并将投影矩阵单位化
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()

    cam = light.Camera

    # 定义投影矩阵
    cam.Ortho.bbox[:] = cam.Ortho.bbox * 4
    cam.Ortho.nf[:] = cam.Ortho.nf * 20
    glOrtho(*cam.Ortho.params)

    # 设置模型矩阵变换，变化模型通过矩阵运算进行
    glEnable(GL_DEPTH_TEST)
    glMatrixMode(GL_MODELVIEW)

    rx, ry = (0, -450)  # 旋转角度，初始让摄像机转到y轴负方向
    zpos = 3  # 缩放比例
    rotate = move = False  # 判断是否处于旋转状态

    while True:  # 开始监听交互

        clock.tick(60)  # 最大帧率

        # 一帧循环内捕获的所有交互
        for e in pygame.event.get():
            pass
            if e.type == QUIT:  # 退出
                sys.exit()
            elif e.type == KEYDOWN and e.key == K_ESCAPE:  # 按下ESC
                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
                pygame.display.flip()
                pygame.quit()
                return
            elif e.type == MOUSEBUTTONDOWN:  # 按下鼠标按键，1位左键，2位中键，3为右键, 4位滑轮上滚，5位滑轮下滚
                if e.button == 1:  # 旋转
                    rotate = True
                elif e.button == 4:  # 放大
                    zpos = min(10, zpos + 1)
                elif e.button == 5:  # 缩小
                    zpos = max(1, zpos - 1)
            elif e.type == MOUSEBUTTONUP:  # 松开鼠标按键
                if e.button == 1:
                    rotate = False

            elif e.type == MOUSEMOTION:  # 移动鼠标
                i, j = e.rel  # 获取鼠标的相对移动值
                if rotate:
                    rx -= i
                    ry -= j
                    print(rx, ry)

        # 刷新模型以响应交互
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # 旋转
        glRotate(ry / 5, 1, 0, 0)
        glRotate(rx / 5, 0, 0, 1)

        # 调整缩放(x, y, z轴）
        s = [zpos / obj.bbox_r] * 3
        glScale(*s)

        # 移动坐标系
        t = -obj.bbox_center
        glTranslate(*t)

        # 重新渲染
        glCallList(obj.gl_list)

        # 截屏
        screenshot_and_send()

        # 刷新缓冲区
        pygame.display.flip()


if __name__ == '__main__':

    filename = "ChunPingXiuFu.obj"
    filed = "./data/瓶子10w/"
    render(filename, filed)

    filename = "taibaoding.obj"
    filed = "./data/太保鼎10w/"
    render(filename, filed)