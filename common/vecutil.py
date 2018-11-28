import math
import numpy as np

def dir2angle(vec):
    return math.atan2(vec[1], vec[0]) * 180 / math.pi

def normalize(vec):
    norm = np.linalg.norm(vec)
    if norm == 0:
        return vec
    return vec / norm

def tangent(vec):
    return np.array((vec[1], -vec[0]))

def dist_from_ray(ray_o, ray_dir, point):
    proj = np.dot((point - ray_o),normalize(ray_dir))
    if proj < 0:
        return False
    return np.linalg.norm(point - ray_o - proj * ray_dir)
