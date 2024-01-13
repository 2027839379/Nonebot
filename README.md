
## 声明
此项目仅用于学习交流，请勿用于非法用途

# Nonebot2
# 以下为最简部署和配置，如果你有基础并学习过nonebot2的话

```

                        # 克隆代码
git clone https://github.com/2027839379/Nonebot.git

cd Nonebot              # 进入目录
pip install poetry      # 安装 poetry
poetry install          # 安装依赖


# 进行基础配置数据库
                        # Ubuntu命令行输入
sudo apt update
sudo apt install postgresql postgresql-contrib

                        # 创建数据库和用户
sudo su - postgres      # 切换用户
psql
                                  # 密码↓
alter user postgres with password '123456'    # postgres的密码

        # 数据库名称↓       所有者↓
CREATE DATABASE naxida OWNER postgres;        # 创建数据库


# 开始运行bot
poetry shell            # 进入虚拟环境
                        # 安装chromium
playwright install chromium

python bot.py           # 启动
```

## 简单配置

```
1.在.env.dev文件中

  SUPERUSERS = [""]   # 机器人主人账号

2.在configs/config.py文件中
  * 数据库配置

3.在configs/config.yaml文件中 # 该文件需要启动一次后生成
  * 修改插件配置项

```


## zhenxun项目地址
[HibiKier/zhenxun_bot](https://github.com/HibiKier/zhenxun_bot) ：一个超棒的机器人 
 
