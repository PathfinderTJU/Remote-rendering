import socket
import sys
import os
import json
import threading
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
from scipy.interpolate import lagrange
import numpy as np


# 一次渲染循环
def socket_service(skt):
    # 获取模型名称
    model_name, get_name_conn = get_name(skt)
    print("[Server:]model rendering...", model_name)

    # 初始化模型
    obj, clock, cam = init_render(model_name)

    # 定义模型参数
    rx, ry = (0, -450)  # 旋转角度，初始让摄像机转到y轴负方向
    zpos = 3  # 缩放比例

    # 渲染初始图像，返回给后端，完成第一次GET的响应
    # 响应格式：
    # {
    #     'data': 初始zpos = 3图像,
    #     'more': zpos = 4缓存图像,
    #     'less': zpos = 2缓存图像
    # }
    first_res = {
        'data': render(rx, ry, zpos, obj),
        'more': render(rx, ry, zpos + 1, obj),
        'less': render(rx, ry, zpos - 1, obj)
    }
    response_get_name(first_res, get_name_conn)

    # 定义预测使用的点集合，其中，点坐标采用前端标准即[0, 360)
    points_set = []

    print("[Server:]Start receiving operation")

    # 开始监听用户的操作
    while True:
        # 一个连接建立
        conn, addr = skt.accept()

        # 获取请求头
        data = conn.recv(1024)
        data = str(data, encoding="UTF-8")
        data = data.split('\r\n')
        head = data[0].split(' ')[0]

        # OPTIONS要响应200，便于后续的POST发送
        if head == 'OPTIONS':
            options_response = 'HTTP/1.1 200 OK\r\n' \
                               + 'Allow: CONVERT\r\n'
            conn.send(options_response.encode())
            conn.close()
            print('[OPTIONS:] While receiving user data, a OPTIONS is received.')
        # POST请求，为交互请求
        elif head == 'POST':
            print('User data Received!')

            # 获得POST请求中的数据
            data = json.loads(data[-1])

            # 退出本次渲染
            if data['exit']:
                exit_render(conn)
                return

            zpos = data['zoom']
            res = {}  # 返回报文中的数据对象

            # 根据发送的数据进行路由跳转
            # 放缩的请求缓存：
            if data['type'] == 'zoom':
                rx, ry = normal_coord(data['rx'], data['ry'])

                # 放缩缓存一定会命中，并且只需请求一个方向的缓存
                if data['more']:
                    res['more'] = render(rx, ry, zpos + 1, obj)
                if data['less']:
                    res['less'] = render(rx, ry, zpos - 1, obj)
            elif data['type'] == 'rotate':
                flag, next_x, next_y, points_set = forecast(data['rx'], data['ry'], points_set)
                next_x = int(next_x)
                next_y = int(next_y)
                rx, ry = normal_coord(data['rx'], data['ry'])

                if data['miss']:
                    res['data'] = render(rx, ry, zpos, obj)

                next = {
                    'rx': next_x,
                    'ry': next_y,
                    'flag': flag
                }

                if not flag:
                    next_x, next_y = normal_coord(next_x, next_y)
                    next['data'] = render(next_x, next_y, zpos, obj)
                res['next'] = next
            # 响应

            res = json.dumps(res)
            post_response = 'HTTP/1.1 200 OK\r\n' \
                            + 'Content-type:text/plain; charset=utf-8\r\n' \
                            + 'Access-Control-Allow-Origin: *\r\n' \
                            + 'Content-length: ' + str(len(res)) + '\r\n' \
                            + '\r\n' \
                            + res + '\r\n'
            conn.send(post_response.encode())
            conn.close()

        # 其它类型，均抛出404
        else:
            other_response = 'HTTP/1.1 404 NotFound'
            conn.send(other_response.encode())
            conn.close()
            print('[Warn:] While receiving user data, rejected a illegal request: ', head)


# 等待一个GET请求，获取模型的名称，返回模型名称、GET请求的连接
def get_name(skt):
    model_name = ""
    while True:
        conn, addr = skt.accept()

        model_name = conn.recv(1024)
        model_name = str(model_name, encoding="UTF-8")
        model_name = model_name.split('\r\n')

        head = model_name[0].split(' ')[0]
        if head == 'GET':
            model_name = model_name[0].split(' ')[1]
            break
        elif head == 'OPTIONS':
            options_response = 'HTTP/1.1 200 OK\r\n' \
                               + 'Allow: CONVERT\r\n'
            conn.send(options_response.encode())
            conn.close()
            print('[OPTIONS:] While receiving the name, received a OPTIONS')
        else:
            other_response = 'HTTP/1.1 404 NotFound'
            conn.send(other_response.encode())
            conn.close()
            print('[Warn:] Before receiving the name, rejected a illegal request: ', head)

    model_name = model_name.lstrip('/')
    return model_name, conn


# 响应get_name中的GET请求
def response_get_name(first_res, conn):
    first_res = json.dumps(first_res)
    first_response = 'HTTP/1.1 200 OK\r\n' \
                     + 'Content-type:text/plain; charset=utf-8\r\n' \
                     + 'Access-Control-Allow-Origin: *\r\n' \
                     + 'Content-length: ' + str(len(first_res)) + '\r\n' \
                     + '\r\n' \
                     + first_res

    conn.send(first_response.encode())
    conn.close()


# 初始化渲染：初始化pygame、读取模型文件、初始化渲染，返回obj：模型对象，clock：pygame时钟，cam：相机
def init_render(model_name):
    filename = "ChunPingXiuFu.obj"
    filed = "./data/瓶子10w/"

    obj = OBJ(filed, filename)
    obj.create_bbox()

    # 初始化pygame引擎
    pygame.init()

    # 设置一个pygame展示窗口，参数为宽度、设置为opengl模式和双缓冲区
    viewport = (600, 600)
    srf = pygame.display.set_mode(viewport, OPENGL | DOUBLEBUF)

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

    return obj, clock, cam


# 根据参数渲染，返回图像编码
def render(rx, ry, zpos, obj):
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
    res = screenshot_and_send()
    pygame.display.flip()

    return res


# 统一前后端的坐标，按后端标准(-180, 180] * 5倍，便于渲染
def normal_coord(rx, ry):
    if rx > 180:
        rx -= 360
    rx *= 5

    if ry > 180:
        ry -= 360
    ry *= 5
    return rx, ry


# 从内存中获取图像并压缩、转码生成字符串，返回图像编码
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
    image_str = str(image_str, "utf-8")

    return image_str

    # with open("./base64.txt", "w") as f:
    #     f.write(str(image_str, "utf-8"))

    # 保存图片
    # d = datetime.datetime.now()
    # timestamp = str(tk.mktime(d.timetuple()))
    # image.save("./image/" + timestamp + ".png")


# 退出一个模型的渲染程序
def exit_render(conn):
    exit_response = 'HTTP/1.1 200 OK'
    conn.send(exit_response.encode())
    conn.close()
    print('[Server:] render ended')

    pygame.display.quit()
    pygame.quit()


# 获取两点间距离
def distance(x1, y1, x2, y2):
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5


# 求解一元二次方程
def twice_equation(a, b, c, direction):
    delta = b ** 2 - 4 * a * c
    if direction > 0:
        return (-b + delta ** 0.5) / (2 * a)
    elif direction < 0:
        return (-b - delta ** 0.5) / (2 * a)


# 接收新点, 判断是否有突兀转折，预测下一个点
def forecast(newx, newy, points_set):
    length = len(points_set)

    # 重复点
    if len(points_set) > 0 and newx == points_set[-1][0] and newy == points_set[-1][1]:
        return 1, -1, -1, points_set

    # len(points_set) ∈ [0, 3]
    # 判断突兀转折
    if length < 2:
        pass
    else:
        # 只取最后两个点
        x1, y1 = points_set[-2]
        x2, y2 = points_set[-1]
        points_set = points_set[-2:]

        # 前两个点垂直
        if x1 == x2:
            # 新点不垂直于前两个点，保留后两一个点
            if newx != x1:
                points_set = [(x2, y2)]
        else:
            # 前两个点不垂直
            # 后两个点垂直的话，保留后两个点
            if newx == x2:
                points_set = [(x2, y2)]
            else:
                # 斜率向量夹角小于90
                v_origin = np.array([x2 - x1, y2 - y1])
                v_now = np.array([newx - x2, newy - y2])
                theta = np.dot(v_origin, v_now) / (np.sqrt(np.sum(v_origin * v_origin)) * np.sqrt(np.sum(v_now * v_now)))

                if theta <= 0:
                    points_set = [(x2, y2)]

    points_set.append((newx, newy))

    # 预测
    flag = 0 # 是否进行了预测，false为无法预测
    next_x = -1
    next_y = -1

    if len(points_set) < 2:
        flag = 2
    elif len(points_set) == 2:
        p1, p2 = points_set[:2]

        # 运动方向在x、y轴的分量，用正负来区分
        direction_x = p2[0] - p1[0]
        direction_y = p2[1] - p1[1]

        rotate_threshold = abs(direction_x)

        # y = k * x + b 的线性函数，求参数k、b
        k = 0
        b = 0
        if direction_x != 0:
            k = (p2[1] - p1[1]) / (p2[0] - p1[0])
            b = (p2[0] * p1[1] - p1[0] * p2[1]) / (p2[0] - p1[0])

        # 斜率 = 寻找下一个点，直接利用勾股定理
        delta_x = 0
        delta_y = 0
        if direction_x > 0:
            delta_x = ((rotate_threshold ** 2) / (k ** 2 + 1)) ** 0.5  # (k ^ 2 + 1) * delta_X = rotate_threshold ^ 2
            delta_y = k * delta_x
        elif direction_x < 0:
            delta_x = -((rotate_threshold ** 2) / (k ** 2 + 1)) ** 0.5  # (k ^ 2 + 1) * delta_X = rotate_threshold ^ 2
            delta_y = k * delta_x
        else:
            if direction_y > 0:
                delta_y = rotate_threshold
            elif direction_y < 0:
                delta_y = -rotate_threshold

        next_x = p2[0] + delta_x
        next_y = p2[1] + delta_y
    else:
        last_points = points_set
        # 处理点的序列cc
        x = []
        y = []
        for i in range(len(last_points)):
            x.append(last_points[i][0])
            y.append(last_points[i][1])

        # 基于拉格朗日法
        lagrange_f = lagrange(x, y)
        # print(lagrange_f)

        # 基于重心拉格朗日法
        # weight_lagrange_f = BarycentricInterpolator(x, y)

        # 基于二次函数拟合法
        # def polynomial_two_f(X, a, b, c):
        #     y = a * (X ** 2) + b * X + c
        #     return y
        # twice_f = polynomial_two_f(x)

        # 运动方向在x、y轴的分量，用正负来区分
        direction_x = last_points[2][0] - last_points[1][0]
        direction_y = last_points[2][1] - last_points[1][1]

        rotate_threshold = abs(direction_x)

        # 由于已经进行了轨迹分割，因此不会有突兀转折，但是仍然可能出现三个点恰好在同一直线上，对垂直于x轴的要分开讨论
        if last_points[2][0] == last_points[1][0] == last_points[0][0]:
            next_x = last_points[2][0]
            if direction_y > 0:
                next_y = last_points[2][0] + rotate_threshold
            elif direction_y < 0:
                next_y = last_points[2][0] - rotate_threshold
        else:  # 但是不会出现只后两个点垂直，属于突兀转折被排除了
            if direction_x > 0:
                next_x = last_points[2][0] + 1
                while True:
                    next_y = lagrange_f(next_x)
                    if distance(last_points[2][0], last_points[2][1], next_x, next_y) < rotate_threshold:
                        next_x += 1
                    else:
                        break
            elif direction_x < 0:
                next_x = last_points[2][0] - 1
                while True:
                    next_y = lagrange_f(next_x)
                    if distance(last_points[2][0], last_points[2][1], next_x, next_y) < rotate_threshold:
                        next_x -= 1
                    else:
                        break

        # 无法拟合成函数
        if next_y == -1:
            flag = 3

    return flag, next_x, next_y, points_set


if __name__ == "__main__":
    try:
        skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 防止重启后占用端口号

        skt.bind(('127.0.0.1', 30000))
        skt.listen(10)
    except socket.error as msg:
        print(msg)
        sys.exit(1)

    print("[Server:]service start...waiting for connect")

    while True:
        socket_service(skt)
