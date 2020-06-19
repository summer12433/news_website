# -*- coding: utf-8 -*-
# @Time    : 2020/6/18 19:09
# @Author  : summer
# @File    : demo.py

#冒泡排序
#比较相邻元素，如果第一个比第二个大，就交换位置
#重复遍历，一直到最大的元素在最后为止


def maopao_sort(alist):
    for j in range(len(alist)-1,0,-1):
        print(j)
        for i in range(j):
            if alist[i] > alist[i+1]:
                alist[i], alist[i+1] = alist[i+1], alist[i]


li = [33, 38, 78, 74, 64, 37, 29, 71, 8, 2]

maopao_sort(li)

