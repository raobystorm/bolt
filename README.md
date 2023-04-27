# bolt
AI based news digest project

## 建立本地开发环境
- 使用`docker compose up`启动MySQL的本地容器 
  - DB的会按照`db/schema.sql`进行建表和初始化
- 使用VSCode打开bolt的文件夹，安装Dev Container插件并选择 `Dev Container: Reopen in Container` 打开开发容器
- 参考`docker-compose.yaml`里DB容器的ip，用户名和密码连接到本地DB
  - TODO：编写用于开发的样本数据插入本地DB
