# 已有两点 第三点正交/平行
import numpy as np



# 计算线条的夹角
def calc_angle(p1, p2, p3):
    """计算三个点之间的角度"""
    v1 = p2 - p1
    v2 = p3 - p2
    angle = np.arccos(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
    return angle * 180 / np.pi


def line_equation(point1, point2, vertical=True):
    x1, y1 = point1
    x2, y2 = point2

    slope = (y2 - y1) / (x2 - x1)
    if vertical:
        slope = -1 / slope

    equation = f"y- {y2} = {slope} *( x - {x2} )"
    return equation


def point_on_line(line_equation, point):
    # 解析直线方程
    _, y1, _, k, _, _, _, x1, _ = line_equation.split(' ')
    y1 = float(y1)
    x1 = float(x1)
    k = float(k)

    # 已知点的坐标
    x0, y0 = point

    # 计算投影坐标
    x_proj = ((y0 - y1) + k * x1 + x0 / k) / (k + 1 / k)
    y_proj = k * (x_proj - x1) + y1
    return [x_proj, y_proj]


def plot_rectangle(point1, point2, point3):
    """
    point:[x,y]
    """

    ang = calc_angle(point1, point2, point3)  # 夹角
    rotate_point_3 = []

    if ang < 45:  # 平行
        if point1[0] == point2[0]:  # x1=x2
            rotate_point_3 = [point3[0], point2[1]]
        elif point1[1] == point2[1]:  # y1=y2
            rotate_point_3 = [point2[0], point3[1]]
        else:
            equation = line_equation(point1, point2, vertical=False)
            rotate_point_3 = point_on_line(equation, point3)
    elif ang >= 45:  # 垂直
        if point1[0] == point2[0]:  # x1=x2
            rotate_point_3 = [point3[0], point2[1]]
        elif point1[1] == point2[1]:  # y1=y2
            rotate_point_3 = [point2[0], point3[1]]
        else:
            equation = line_equation(point1, point2)
            rotate_point_3 = point_on_line(equation, point3)

    return rotate_point_3

def update_orth(point,point1,point2):
    if point1[0]==point2[0]:
        point_new = np.array([point1[0],point[1]])
    elif point1[1]==point2[1]:
        point_new = np.array([point[0],point1[1]])
    else:
        equation = line_equation(point1, point2,vertical=False)
        point_new = point_on_line(equation, point)
    return point_new