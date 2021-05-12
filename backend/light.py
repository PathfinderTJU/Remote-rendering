import numpy as np
from OpenGL.GL import *
from OpenGL.GLUT.freeglut import *


# 设置光照模型：光源、光照环境、材质
def setup_lighting():
    draw_2side = True  # 是否要双面光照

    # 设置背景颜色为黑色
    c = [1.0, 1.0, 1.0]  # 背景色
    glColor3fv(c)

    # 设置光源
    light0_ambient = [1, 1, 1, 1]  # 光源1环境光(r, g, b, a)
    light0_diffuse = [0, 0, 0, 1]  # 光源1散射光(r, g, b, a)
    light0_specular = [0, 0, 0, 1]  # 光源1镜面光(r, g, b, a)
    glLightfv(GL_LIGHT0, GL_AMBIENT, light0_ambient)  # 设置光源1环境光强度
    glLightfv(GL_LIGHT0, GL_DIFFUSE, light0_diffuse)  # 设置光源1散射光强度
    glLightfv(GL_LIGHT0, GL_SPECULAR, light0_specular)  # 设置光源1镜面反射强度的

    # 设置材质光
    # mat_specular = [1, 1, 1, 1]  # 镜面反射(r, g, b, a)
    # mat_shininess = [50]  # 漫反射
    # glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, mat_specular)  # 设置镜面反射材质
    # glMaterialfv(GL_FRONT_AND_BACK, GL_SHININESS, mat_shininess)  # 设置漫反射材质
    # 自动设置材质光
    glEnable(GL_COLOR_MATERIAL)  # 将材质应用光反射
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)  # 设置颜色材质

    # 设置光照环境
    global_ambient = [1, 1, 1, 1]  # 全局环境光
    glLightModelfv(GL_LIGHT_MODEL_AMBIENT, global_ambient)  # 全局环境光
    glLightModeli(GL_LIGHT_MODEL_LOCAL_VIEWER, GL_FALSE)  # 无限远的观察点
    glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, draw_2side)  # 单面光照

    glEnable(GL_LIGHTING)  # 启动灯源
    glEnable(GL_LIGHT0)  # 启动光源
    glEnable(GL_NORMALIZE)  # 启用法向量

class Camera:
    # 设置一个观察窗口
    class Ortho:
        params = np.array([-1, 1, -1, 1, 1, -1], np.float32)
        bbox = params[0:4]
        nf = params[4:]
