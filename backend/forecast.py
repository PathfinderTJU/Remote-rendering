from scipy.interpolate import lagrange
import numpy as np

points = [[1, 1], [1, 3], [1, 3]]  # 点集合，最多只有三个点
rotate_threshold = 1  # 旋转阈值


def distance(x1, y1, x2, y2):
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5


def twice_equation(a, b, c, direction):
    delta = b ** 2 - 4 * a * c
    if direction > 0:
        return (-b + delta ** 0.5) / (2 * a)
    elif direction < 0:
        return (-b - delta ** 0.5) / (2 * a)


# 接收新点
def receive_point(newData):
    global points
    if newData.reset:
        points = points[-1:]
    else:
        if len(points) == 3:
            points = points[1:]
    points.append([newData.x, newData.y])


# 分段预测
if __name__ == "__main__":
    # 两个点，线性预测
    if len(points) == 2:
        p1, p2 = points[:2]

        # 运动方向在x、y轴的分量，用正负来区分
        direction_x = p2[0] - p1[0]
        direction_y = p2[1] - p1[1]

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
            delta_x = ((rotate_threshold ** 2) / (k ** 2 + 1)) ** 0.5 # (k ^ 2 + 1) * delta_X = rotate_threshold ^ 2
            delta_y = k * delta_x
        elif direction_x < 0:
            delta_x = -((rotate_threshold ** 2) / (k ** 2 + 1)) ** 0.5  # (k ^ 2 + 1) * delta_X = rotate_threshold ^ 2
            delta_y = k * delta_x
        else:
            if direction_y > 0:
                delta_y = rotate_threshold
            elif direction_y < 0:
                delta_y = -rotate_threshold

        new_x = p2[0] + delta_x
        new_y = p2[1] + delta_y
    elif len(points) >= 3:    # 三个点及以上，只取最后三个点，使用拉格朗日预测
        last_points = points[-3:]
        # 处理点的序列cc
        x = []
        y = []
        for i in range(len(last_points)):
            x.append(last_points[i][0])
            y.append(last_points[i][1])

        # 基于拉格朗日法
        lagrange_f = lagrange(x, y)
        print(lagrange_f)

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

        new_x = 0
        new_y = 0

        # 由于已经进行了轨迹分割，因此不会有突兀转折，但是仍然可能出现三个点恰好在同一直线上，对垂直于x轴的要分开讨论
        if last_points[2][0] == last_points[1][0] == last_points[0][0]:
            new_x = last_points[2][0]
            if direction_y > 0:
                new_y = last_points[2][0] + rotate_threshold
            elif direction_y < 0:
                new_y = last_points[2][0] - rotate_threshold
        else: # 但是不会出现只后两个点垂直，属于突兀转折被排除了
            if direction_x > 0:
                new_x = last_points[2][0] + 1
                while True:
                    new_y = lagrange_f(new_x)
                    if distance(last_points[2][0], last_points[2][1], new_x, new_y) < rotate_threshold:
                        new_x += 1
                    else:
                        break
            elif direction_x < 0:
                new_x = last_points[2][0] - 1
                while True:
                    new_y = lagrange_f(new_x)
                    if distance(last_points[2][0], last_points[2][1], new_x, new_y) < rotate_threshold:
                        new_x -= 1
                    else:
                        break

        print(new_x, new_y)