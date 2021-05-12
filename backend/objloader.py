# 加载OBJ和MTL文件
import numpy as np
import pygame
from OpenGL.GL import *


# 加载mtl文件
def MTL(fdir, filename):
    contents = {}
    mtl = {}

    for line in open(fdir + filename, "r"):
        line = line.strip() # 删除左右的空格
        if line.startswith('#'):  # 以#为开头的行为注释，跳过之
            continue
        else:
            data = line.split(" ")
            if len(data) == 0:  # 空行也要跳过
                continue

            # 读取一个新的材质组，首先读取mtl材质组名称
            if data[0] == "newmtl":
                mtl = contents[data[1]] = {}
            elif mtl is None:  # 未读取到任何材质组名称，则报错
                raise ValueError("Material file doesn't start with a newmtl statement")
            elif data[0] == "map_Kd": #材质组映射的文件
                mtl[data[0]] = data[1]
                surf = pygame.image.load(fdir + mtl["map_Kd"])  # 使用pygame加载图像
                image = pygame.image.tostring(surf, "RGBA", 1)  # 将图像转换为字符串描述
                ix, iy = surf.get_rect().size  # 获取左上角顶点坐标
                texid = mtl["texture_kd"] = glGenTextures(1) #生成一个纹理对象
                # 将纹理映射为像素
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER,
                                GL_LINEAR)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER,
                                GL_LINEAR)
                # 生成2D纹理
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, ix, iy, 0, GL_RGBA,
                             GL_UNSIGNED_BYTE, image)
            else: # 其它则存储
                try:
                    mtl[data[0]] = [float(x) for x in data[1:4]]
                    if data[0] == 'Kd' and mtl[data[0]] == [0, 0, 0]: # 有的模型漫反射光设置的为0，需要补光
                        mtl[data[0]] = [1.0, 1.0, 1.0]
                except ValueError:
                    mtl[data[0]] = data[1:4]

    return contents


# 加载OBJ文件
class OBJ:
    def __init__(self, fdir, filename):  # 构造函数，解析obj文件
        self.vertices = []  # 顶点
        self.normals = []  # 法向量
        self.texcoords = []  # 纹理坐标
        self.faces = []  # 多边形

        self.mtl = None  # 材质文件路径
        self.material = [] # 材质名称
        nowmaterial = None
        for line in open(fdir + filename, "r"):
            line.rstrip("\n")
            if line.startswith("#"):  # 过滤注释
                continue
            data = line.split()
            if len(data) == 0:  # 过滤空行
                continue

            if data[0] == "v":  # 顶点x, y, z
                v = [float(x) for x in data[1:4]]
                v = [v[0], v[2], v[1]]
                self.vertices.append(v)
            elif data[0] == "vn":  # 法线向量x, y, z
                vn = [float(x) for x in data[1:4]]
                vn = [vn[0], vn[2], vn[1]]
                self.normals.append(vn)
            elif data[0] == "vt":  # 纹理坐标u, v
                vt = [float(x) for x in data[1:3]]
                # vt = [vt[1], vt[0]]
                self.texcoords.append(vt)
            elif data[0] in ("usemtl", "usemat"):  # 纹理名称
                self.material.append(data[1])
                nowmaterial = data[1]
            elif data[0] == "mtllib":  # 纹理文件
                self.mtl = [fdir, data[1]]
            elif data[0] == "f":  # 三角形索引，有可能只存在法向量索引而不存在贴图索引(x//x形式，因此需要判断分割后每个数的长度是否不为0)
                face = []  # 点索引
                texcoords = []  # 点纹理贴图坐标索引
                norms = []  # 点法向量索引
                for v in data[1:]:
                    w = v.split("/")
                    face.append(int(w[0]))  # 第一个值肯定为点索引
                    if len(w) >= 2 and len(w[1]) > 0:  # 存在纹理贴图索引
                        texcoords.append(int(w[1]))
                    else:
                        texcoords.append(0)
                    if len(w) >= 3 and len(w[2]) > 0:  # 存在法向量索引
                        norms.append(int(w[2]))
                    else:
                        norms.append(0)
                self.faces.append((face, norms, texcoords, nowmaterial))  # 一个面的各个点，每个点包括点、纹理、法向量索引

    # 确定模型渲染的初始位置，建立一个正方形模型盒子，确保能装下模型
    def create_bbox(self):
        ps = np.array(self.vertices)
        vmin = ps.min(axis=0)  # 各坐标最小值
        vmax = ps.max(axis=0)  # 各坐标最大值

        self.bbox_center = (vmax + vmin) / 2  # 模型中心
        self.bbox_r = np.max(vmax - vmin) / 2  # 模型最大半径

    # 创建显示列表
    def create_gl_list(self):
        if self.mtl is not None:
            self.mtl = MTL(*self.mtl)  # 传入所有的材质文件

        self.gl_list = glGenLists(1)  # 生成一组空的显示列表
        glNewList(self.gl_list, GL_COMPILE)  # 新建显示列表
        glEnable(GL_TEXTURE_2D)  # 启用二维纹理
        glFrontFace(GL_CW)  # 定义多边形的正面，CCW为逆时针，即描述多边形的顶点时从左下角开始逆时针

        for face in self.faces:
            vertices, normals, texcoords, material = face  # 获取这个面的点索引、法向量索引、纹理索引、材质名称
            mtl = self.mtl[material]
            if "texture_Kd" in mtl:
                glBindTexture(GL_TEXTURE_2D, mtl["texture_Kd"])  # 绑定外部文件
            else:
                glColor(*mtl['Kd'])

            # hasNorm = True
            # for i in range(len(normals)):
            #     if normals[i - 1] == 0:
            #         hasNorm = False
            #         break
            #
            # if not hasNorm:
            #     v1 = np.array(self.vertices[vertices[0] - 1])
            #     v2 = np.array(self.vertices[vertices[1] - 1])
            #     v3 = np.array(self.vertices[vertices[2] - 1])
            #
            #     n1 = np.cross(v1 - v2, v1 - v3)
            #     n2 = np.cross(v2 - v3, v2 - v1)
            #     n3 = np.cross(v3 - v1, v3 - v2)
            #     normals = [n1, n2, n3]

            glBegin(GL_POLYGON)  # 绘制一个凸多边形
            for i in range(len(vertices)):
                # if not hasNorm: # 不存在法向量索引，此时已经是法向量
                #     glNormal3fv(normals[i])
                if normals[i] > 0:  # 存在法向量索引
                    glNormal3fv(self.normals[normals[i] - 1])

                if texcoords[i] > 0:  # 纹理
                    glTexCoord2fv(self.texcoords[texcoords[i] - 1])
                glVertex3fv(self.vertices[vertices[i] - 1])  # 顶点
            glEnd()

        # 关闭渲染
        glDisable(GL_TEXTURE_2D)
        glEndList()
