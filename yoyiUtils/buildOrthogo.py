import numpy as np
import math
import geopandas as gpd
from shapely.geometry import Polygon

def pldist(x0, x1, x2):
    """
    Calculates the distance from the point ``x0`` to the line given
    by the points ``x1`` and ``x2``.
    :param x0: a point
    :type x0: a 2x1 numpy array
    :param x1: a point of the line
    :type x1: 2x1 numpy array
    :param x2: another point of the line
    :type x2: 2x1 numpy array
    """
    x0, x1, x2 = x0[:2], x1[:2], x2[:2] # discard timestamp
    if x1[0] == x2[0]:
        return np.abs(x0[0] - x1[0])

    return np.divide(np.linalg.norm(np.linalg.det([x2 - x1, x1 - x0])),
                     np.linalg.norm(x2 - x1))

def _rdp(M, epsilon, dist):
    """
    Simplifies a given array of points.
    :param M: an array
    :type M: Nx2 numpy array
    :param epsilon: epsilon in the rdp algorithm
    :type epsilon: float
    :param dist: distance function
    :type dist: function with signature ``f(x1, x2, x3)``
    """
    dmax = 0.0
    index = -1

    for i in range(1, M.shape[0]):
        d = dist(M[i], M[0], M[-1])

        if d > dmax:
            index = i
            dmax = d

    if dmax > epsilon:
        r1 = _rdp(M[:index + 1], epsilon, dist)
        r2 = _rdp(M[index:], epsilon, dist)

        return np.vstack((r1[:-1], r2))
    else:
        return np.vstack((M[0], M[-1]))

def _rdp_nn(seq, epsilon, dist):
    """
    Simplifies a given array of points.
    :param seq: a series of points
    :type seq: sequence of 2-tuples
    :param epsilon: epsilon in the rdp algorithm
    :type epsilon: float
    :param dist: distance function
    :type dist: function with signature ``f(x1, x2, x3)``
    """
    return _rdp(np.array(seq), epsilon, dist).tolist()

def rdp(M, epsilon=0, dist=pldist):
    """
    Simplifies a given array of points.
    :param M: a series of points
    :type M: either a Nx2 numpy array or sequence of 2-tuples
    :param epsilon: epsilon in the rdp algorithm
    :type epsilon: float
    :param dist: distance function
    :type dist: function with signature ``f(x1, x2, x3)``
    """
    if "numpy" in str(type(M)):
        return _rdp(M, epsilon, dist)
    return _rdp_nn(M, epsilon, dist)

# 计算两点距离
def cal_dist(point_1, point_2):
    dist = np.sqrt(np.sum(np.power((point_1-point_2), 2)))
    return dist

# 计算两条线的夹角
def cal_ang(point_1, point_2, point_3):
    """
    根据三点坐标计算夹角
    :param point_1: 点1坐标
    :param point_2: 点2坐标
    :param point_3: 点3坐标
    :return: 返回任意角的夹角值，这里只是返回点2的夹角
    """
    a=math.sqrt((point_2[0]-point_3[0])*(point_2[0]-point_3[0])+(point_2[1]-point_3[1])*(point_2[1] - point_3[1]))
    b=math.sqrt((point_1[0]-point_3[0])*(point_1[0]-point_3[0])+(point_1[1]-point_3[1])*(point_1[1] - point_3[1]))
    c=math.sqrt((point_1[0]-point_2[0])*(point_1[0]-point_2[0])+(point_1[1]-point_2[1])*(point_1[1]-point_2[1]))
    B=math.degrees(math.acos((b*b-a*a-c*c)/(-2*a*c)))
    return B

# 计算线条的方位角
def azimuthAngle(point_0, point_1):
    x1, y1 = point_0
    x2, y2 = point_1

    if x1 < x2:
        if y1 < y2:
            ang = math.atan((y2 - y1) / (x2 - x1))
            ang = ang * 180 / math.pi
            return ang
        elif y1 > y2:
            ang = math.atan((y1 - y2) / (x2 - x1))
            ang = ang * 180 / math.pi
            return 90 + (90 - ang)
        elif y1==y2:
            return 0
    elif x1 > x2:
        if y1 < y2:
            ang = math.atan((y2-y1)/(x1-x2))
            ang = ang*180/math.pi
            return 90+(90-ang)
        elif y1 > y2:
            ang = math.atan((y1-y2)/(x1-x2))
            ang = ang * 180 / math.pi
            return ang
        elif y1==y2:
            return 0

    elif x1==x2:
        return 90

# 计算线条的夹角
def calc_angle(p1, p2, p3):
    """计算三个点之间的角度"""
    v1 = p2 - p1
    v2 = p3 - p2
    cos = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    if cos > 1:
        cos = 1
    elif cos < -1:
        cos = -1
    angle = np.arccos(cos)
    return angle * 180 / np.pi

def line_equation(point1, point2, vertical=True):
    x1, y1 = point1
    x2, y2 = point2
    if x1 == x2:
        if vertical:
            return f"y- {y2} = 1 *( 0 - 0 )"
        else:
            return f"- 0 = 1 *( x - {x2} )"
    if y1 == y2:
        if vertical:
            return f"- 0 = 1 *( x - {x2} )"
        else:
            return f"y- {y2} = 1 *( 0 - 0 )"

    slope = (y2 - y1) / (x2 - x1)
    if vertical:
        slope = -1 / slope

    equation = f"y- {y2} = {slope} *( x - {x2} )"
    return equation

def point_on_line(line_equation, point):
    # 解析直线方程
    y, y1, _, k, _, x, _, x1, _ = line_equation.split(' ')
    y1 = float(y1)
    x1 = float(x1)
    k = float(k)

    # 判断是否有斜率
    if y == '-':
        return [x1, point[1]]
    if x == '0':
        return [point[0], y1]

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
    ori = 0
    if ang < 45:
        ori = 1
        equation = line_equation(point1, point2, vertical=False)
        rotate_point_3 = point_on_line(equation, point3)
    else:
        ori = 0
        equation = line_equation(point1, point2)
        rotate_point_3 = point_on_line(equation, point3)
    return rotate_point_3, ori

def getPolyCoords(geometry, coord_type):
    """Returns the coordinates ('x|y') of edges/vertices of a Polygon/others"""

    # Parse the geometries and grab the coordinate

    # print(geometry.type)

    if geometry.type == 'Polygon':
        if coord_type == 'x':
            # Get the x coordinates of the exterior
            # Interior is more complex: xxx.interiors[0].coords.xy[0]
            return list(geometry.exterior.coords.xy[0])
        elif coord_type == 'y':
            # Get the y coordinates of the exterior
            return list(geometry.exterior.coords.xy[1])

    if geometry.type in ['Point', 'LineString']:
        if coord_type == 'x':
            return list(geometry.xy[0])
        elif coord_type == 'y':
            return list(geometry.xy[1])

    if geometry.type == 'MultiLineString':
        all_xy = []
        for ea in geometry:
            if coord_type == 'x':
                all_xy.append(list(ea.xy[0]))
            elif coord_type == 'y':
                all_xy.append(list(ea.xy[1]))
        return all_xy

    if geometry.type == 'MultiPolygon':
        all_xy = []
        for ea in geometry:
            if coord_type == 'x':
                all_xy.extend(list(ea.exterior.coords.xy[0]))
            elif coord_type == 'y':
                all_xy.extend(list(ea.exterior.coords.xy[1]))
        return all_xy

    else:
        # Finally, return empty list for unknown geometries
        return []

def boundary_regularization(xy, epsilon=6):
    # 轮廓精简（DP）
    contours = rdp(xy, epsilon=epsilon)
    # contours = xy

    # 轮廓规则化
    dists = []
    azis_index = []
    if len(contours) == 2:
        return xy

    # 获取每条边的长度
    for i in range(contours.shape[0]):
        cur_index = i
        next_index = i + 1 if i < contours.shape[0] - 1 else 0
        cur_point = contours[cur_index]
        next_point = contours[next_index]
        dist = cal_dist(cur_point, next_point)
        if dist == 0:
            continue
        dists.append(dist)
        azis_index.append([cur_index, next_index])

    # 以最长的边的方向作为主方向
    longest_edge_idex = np.argmax(dists)
    point_0_index, point_1_index = azis_index[longest_edge_idex]
    point_index_list = azis_index[longest_edge_idex + 1:] + azis_index[:longest_edge_idex + 1]
    dists = dists[longest_edge_idex + 1:] + dists[:longest_edge_idex]
    main_point_0, main_point_1 = contours[point_0_index], contours[point_1_index]
    # 方向纠正，绕起点旋转到与主方向垂直或者平行
    final_points = [main_point_0, main_point_1]  # 加入主边

    for i, (point_0_cur_index, point_1_cur_index) in enumerate(point_index_list):
        cur_edge_point_0, cur_edge_point_1 = final_points[-2], final_points[-1]  # 当前线段
        next_edge_point_0, next_edge_point_1 = contours[point_0_cur_index], contours[point_1_cur_index]  # 下条线段

        point_1_new, ori = plot_rectangle(np.array(cur_edge_point_0), np.array(cur_edge_point_1),
                                          np.array(next_edge_point_1))

        final_points.append(point_1_new)
        final_points.append(next_edge_point_1)

    final_points.append(final_points[0])
    # final_points = rdp(np.array(final_points), epsilon=1)
    final_points = np.array(final_points).transpose(1, 0)

    return final_points

def mk_valid(x):
    if x.geometry.type == 'GeometryCollection':
        for k in x.geometry.geoms:
            if k.type == 'Polygon' or k.type == 'MultiPolygon':
                return k
    elif x.geometry.type == 'Polygon' or x.geometry.type == 'MultiPolygon':
        return x.geometry

def regular(row, ):
    # 获取多边形对象
    polygon = row['geometry']
    # pixels = rasterio.transform.rowcol(transform, getPolyCoords( polygon,'x'), getPolyCoords( polygon,'y'))
    # 修改多边形的顶点
    try:
        if row.geometry.length * row.geometry.length - 16 * row.geometry.area >= 0:
            h = (row.geometry.length + np.sqrt(row.geometry.length * row.geometry.length - 16 * row.geometry.area)) / 4
            w = row.geometry.area / h
            epsilon = min(w / 6, 4)
        else:
            epsilon = 1
        new_coords = boundary_regularization(
            np.array([getPolyCoords(polygon, 'x'), getPolyCoords(polygon, 'y')]).astype('float').transpose(1, 0),
            epsilon=epsilon)
        # new_polygon = Polygon(list(new_coords))
        # geo_xy = xy(new_coords[0], new_coords[1])
        new_polygon = Polygon(list(np.array(new_coords).transpose(1, 0)))
        return new_polygon
    except:
        return polygon
    
def shp_orthogo_process(input, output):
    print("input",input)
    data = gpd.read_file(input)
    #print(data.)
    #crs = data.crs

    data = data.to_crs(4546)
    print(data)
    data['geometry'] = data.apply(lambda row: regular(row, ), axis=1)
    data['geometry'] = data['geometry'].buffer(0.005, join_style=2, cap_style=1)
    data['geometry'] = data['geometry'].buffer(-0.005, join_style=2, cap_style=1)
    data['geometry'] = data['geometry'].buffer(-0.005, join_style=2, cap_style=1)
    data['geometry'] = data['geometry'].buffer(0.005, join_style=2, cap_style=1)
    data['geometry'] = data.make_valid()
    data = data.loc[data['geometry'].notna()]
    if len(data)>0:
        data['geometry'] = data.apply(lambda row: mk_valid(row), axis=1)
    data = data.to_crs(4326)
    data.to_file(output,encoding="UTF-8")
    print('成功保存在{}'.format(output))
