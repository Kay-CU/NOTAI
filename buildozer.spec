[app]

# 应用名称
title = 赛事分析

# 包名
package.name = notai

# 包域名
package.domain = org.notai

# 源码目录
source.dir = .

# 主文件
source.include_exts = py,png,jpg,kv,atlas,json

# 版本号
version = 1.0.0

# 应用需求
requirements = python3,kivy,urllib3

# 权限
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# API级别
android.api = 33

# 最低API级别
android.minapi = 21

# 架构
android.archs = arm64-v8a,armeabi-v7a

# 预编译包
android.presplash_color = #0F0F0F

# 方向
orientation = portrait

# 是否全屏
fullscreen = 0

# 主题色
android.allow_backup = 1

[buildozer]
log_level = 2
warn_on_root = 1
